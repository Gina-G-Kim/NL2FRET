"""Judge one (generated, reference) pair.

Flow: align vocabulary (align.py) -> boolean abstraction -> three queries (equiv, sound, compl) per chosen alignment -> role.
A pair is
  judged : all three queries gave a verdict. role = SAME | PROOF | REFUTE | NEITHER
  UND    : no vocabulary alignment exists (role 'UND', und_reason set)
  N/M    : the engine could not decide (nm True; nm_reason one of converter_limit, syntax, timeout, nusmv_output, no_verdict, other)
Role mapping (Sound = GT -> Pred holds, Compl = Pred -> GT holds):
  sound & compl -> SAME ; compl only -> PROOF (no MISS, ALARM) ; sound only -> REFUTE (MISS, no ALARM) ; neither -> NEITHER
Alignment search: for every candidate renaming the sound and compl queries are run; the best candidate (fewest failed queries, as in legacy/judge4.py) is kept and
the equiv query is run for it. Candidates for which a query gave no verdict are skipped; if every candidate has no verdict the pair is N/M.
"""
import re
import time
import uuid

from . import abstraction as A
from . import align
from .ap_check import ap_check
from .engines import AUX, QueryResult, parse_nusmv_trace

def clean_markup(t):
    """FRET marks some reference formulas with <b>/<i> emphasis tags; they are not part of the formula."""
    if not isinstance(t, str):
        return t
    t = re.sub(r"</?[bi]>", "", t)
    try:
        A.abstract(t)
        return t
    except Exception:  # noqa: BLE001
        pass
    try:  # FRET prints some formulas with operator precedence instead of full parentheses; re-print them fully parenthesised
        return _fully_parenthesised(align.J2.parse(align.J2.lex(t)))
    except Exception:  # noqa: BLE001
        return t


def _fully_parenthesised(a):
    k = a[0]
    if k == "var":
        return a[1]
    if k in ("num", "TRUE", "FALSE"):
        return a[1] if k == "num" else k
    if k == "neg":
        return "-" + _fully_parenthesised(a[1])
    if k == "fn":
        return a[1] + "(" + ",".join("(" + _fully_parenthesised(x) + ")" for x in a[2:]) + ")"
    if len(a) == 2:
        return "(" + k + " " + _fully_parenthesised(a[1]) + ")"
    return "(" + _fully_parenthesised(a[1]) + " " + k + " " + _fully_parenthesised(a[2]) + ")"


RANK = {"SAME": 0, "PROOF": 1, "REFUTE": 1, "NEITHER": 2}
CEX_ROLES = ("NEITHER", "UND", "NM")      # v9: the counterexample of a failed query is always recorded for these roles (NM = engine could not decide); it is recorded for the other roles as well when a query failed
CEX_MEANING = {"sound": "the reference holds and the generated formula is violated (ALARM)", "compl": "the generated formula holds and the reference is violated (MISS)",
               "equiv": "the two formulas differ"}


def role_of(sound, compl):
    if sound is None or compl is None:
        return None
    if sound and compl:
        return "SAME"
    if compl:
        return "PROOF"
    if sound:
        return "REFUTE"
    return "NEITHER"


class _Fail(Exception):
    def __init__(self, reason, detail):
        self.reason, self.detail = reason, detail


def _prepare(gen_text, ref_text, cap):
    try:
        gb, rb = A.abstract(gen_text), A.abstract(ref_text)
    except A.Unsupported as e:
        raise _Fail("converter_limit", {"message": "unsupported operator: " + str(e)})
    except Exception as e:  # noqa: BLE001
        raise _Fail("syntax", {"message": str(e)[:200]})
    try:
        gs, rs = A.to_smv(gb, cap), A.to_smv(rb, cap)
    except A.Unsupported as e:
        raise _Fail("converter_limit", {"message": str(e), "cap": cap})
    return gb, rb, gs, rs, sorted(set(A.atoms(gb)) | set(A.atoms(rb)))


def _run(engine, kind, gs, rs, atoms, gen_text, ref_text, store):
    q = engine.query(kind, gs, rs, atoms, gen_text=gen_text, ref_text=ref_text)
    store.append(q)
    return q


def judge_pair(gen_pt, ref_pt, engine, mode="anchor", cap=128, aux=False, pair_id=None, meta=None, gen_ft=None, ref_ft=None):
    """-> record dict (see docs/DESIGN.md section 7). 'queries' holds every query that was run (search queries included)."""
    meta = meta or {}
    gen_pt, ref_pt = clean_markup(gen_pt), clean_markup(ref_pt)
    rec = {"run_id": meta.get("run_id"), "pair_id": pair_id or uuid.uuid4().hex[:12], "group": meta.get("group"), "mutation": meta.get("mutation"),
           "gt_pt": ref_pt, "pred_pt": gen_pt, "gt_ft": ref_ft, "pred_ft": gen_ft, "atoms_gt": None, "atoms_pred": None, "atoms_union": None,
           "atom_abstraction": None, "ap_dictionary": meta.get("ap_dictionary"), "alignment": {"mode": mode, "mapping": None, "n_candidates": 0, "n_tried": 0, "und": None},
           "equiv": None, "sound": None, "compl": None, "role": None, "nm": False, "nm_reason": None, "nm_detail": None, "und_reason": None,
           "gen_sat": None, "gen_valid": None, "counterexamples": [], "queries": [], "ap_check": None, "engine": getattr(engine, "name", "?")}
    store = []
    t0 = time.time()
    try:
        if not gen_pt or not ref_pt:
            raise _Fail("other", {"message": "missing formula"})
        al = align.candidates(gen_pt, ref_pt, mode)
        if "und" in al:
            rec["role"] = "UND"
            rec["und_reason"] = al["und"]
            rec["nm_detail"] = {"message": al.get("detail")}
            rec["ap_check"] = ap_check(None, None)
            return _finish(rec, store, t0)
        maps = al["maps"]
        rec["alignment"].update(n_candidates=len(maps), anchored=al.get("anchored"))
        best = None
        first_fail = None
        for m in maps:
            g2 = A.rename_identifiers(gen_pt, m)
            try:
                gb, rb, gs, rs, atoms = _prepare(g2, ref_pt, cap)
            except _Fail as f:
                first_fail = first_fail or f
                continue
            rec["alignment"]["n_tried"] += 1
            qs = _run(engine, "sound", gs, rs, atoms, g2, ref_pt, store)
            if qs.verdict is None:
                first_fail = first_fail or _Fail(qs.reason or "no_verdict", {"message": f"sound query: {qs.reason}"})
                if qs.timed_out:
                    continue
            qc = _run(engine, "compl", gs, rs, atoms, g2, ref_pt, store) if not qs.timed_out else QueryResult("compl", "", executed=False)
            if qc.verdict is None:
                first_fail = first_fail or _Fail(qc.reason or "no_verdict", {"message": f"compl query: {qc.reason}"})
                continue
            if qs.verdict is None:
                continue
            score = (0 if (qs.verdict and qc.verdict) else 1 if (qs.verdict or qc.verdict) else 2)
            if best is None or score < best[0]:
                best = (score, m, g2, gb, rb, gs, rs, atoms, qs, qc)
            if score == 0:
                break
        if best is None:
            if first_fail is None:
                first_fail = _Fail("other", {"message": "no candidate"})
            raise first_fail
        _, m, g2, gb, rb, gs, rs, atoms, qs, qc = best
        rec["alignment"]["mapping"] = m
        rec["atoms_gt"], rec["atoms_pred"], rec["atoms_union"] = A.atoms(rb), A.atoms(gb), atoms
        rec["atom_abstraction"] = {"gt": A.atom_map(ref_pt), "pred": A.atom_map(g2)}
        rec["ap_check"] = ap_check(rec["atoms_gt"], rec["atoms_pred"])
        rec["sound"], rec["compl"] = qs.verdict, qc.verdict
        qe = _run(engine, "equiv", gs, rs, atoms, g2, ref_pt, store)
        rec["equiv"] = qe.verdict
        rec["counterexamples"] = [{"kind": q.kind, "meaning": CEX_MEANING[q.kind], "smv_sha256": q.smv_sha256, "smv_path": f"smv/{q.smv_sha256}.smv", "spec_text": q.spec_text,
                                   "trace": parse_nusmv_trace(q.stdout)} for q in (qs, qc, qe) if q.verdict is False]
        if qe.verdict is None:
            raise _Fail(qe.reason or "no_verdict", {"message": f"equiv query: {qe.reason}"})
        rec["role"] = role_of(rec["sound"], rec["compl"])
        if aux:
            qa = _run(engine, "sat", gs, rs, atoms, g2, ref_pt, store)
            qv = _run(engine, "valid", gs, rs, atoms, g2, ref_pt, store)
            rec["gen_sat"] = (not qa.verdict) if qa.verdict is not None else None
            rec["gen_valid"] = qv.verdict
    except _Fail as f:
        rec["nm"] = True
        rec["nm_reason"] = f.reason
        rec["nm_detail"] = f.detail
        rec["role"] = None
        if rec["ap_check"] is None:
            rec["ap_check"] = ap_check(rec["atoms_gt"], rec["atoms_pred"])
    return _finish(rec, store, t0)


def _finish(rec, store, t0):
    role = rec["role"] or ("NM" if rec["nm"] else None)
    cex = rec.get("counterexamples") or []
    need = role in CEX_ROLES
    if cex and all(c["trace"] is None for c in cex):
        rec["counterexample_status"] = "engine_gave_no_trace"          # z3 bounded engine: no trace text exists
    elif cex:
        rec["counterexample_status"] = "recorded"
    elif need:
        rec["counterexample_status"] = "not_available:" + (rec.get("und_reason") or rec.get("nm_reason") or "no_failed_query")
    else:
        rec["counterexample_status"] = "not_needed"
    rec["counterexample_required"] = need
    rec["queries"] = [q.to_record() for q in store]
    rec["elapsed_sec_total"] = round(time.time() - t0, 3)
    rec["_smv"] = {q.smv_sha256: q.smv_text for q in store if q.smv_sha256}
    return rec


def best_over_references(gen_pt, ref_parts, engine, **kw):
    """Compare one generated formula with several reference parts (all versions) and keep the best record (SAME < PROOF = REFUTE < NEITHER < N/M, UND last)."""
    best = None
    for i, (ref_id, ref_pt, ref_ft) in enumerate(ref_parts):
        r = judge_pair(gen_pt, ref_pt, engine, ref_ft=ref_ft, **kw)
        r["reference_part"] = ref_id
        rank = RANK.get(r["role"], 3 if r["role"] is None else 4)
        if best is None or rank < best[0]:
            best = (rank, r)
        if rank == 0:
            break
    return best[1] if best else None
