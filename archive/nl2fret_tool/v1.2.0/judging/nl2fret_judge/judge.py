"""Judge one (generated, reference) pair.

Flow: align vocabulary (align.py) -> boolean abstraction -> three queries (equiv, sound, compl) per chosen alignment -> role.
A pair is
  judged : all three queries gave a verdict. role = SAME | PROOF | REFUTE | NEITHER
  UND    : no vocabulary alignment exists (role 'UND', und_reason set). This includes the case that align.candidates finds same-type counterparts but
           no injective renaming (empty candidate list); v1.0.0 recorded that case as N/M 'other' / 'no candidate'.
  N/M    : the engine could not decide (nm True; nm_reason one of converter_limit, syntax, timeout, nusmv_output, no_verdict, other).
           A pair whose candidates all fail in _prepare (window cap, syntax) stays N/M with the reason of the first failure.
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
from .engines import AUX, QueryResult

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


# Selection rank of a reference part in best_over_references (smaller is better). v1.2.0 makes the two non-role entries explicit: a record the engine could not
# decide (nm true, role None) ranks 3, a record without a vocabulary alignment (role "UND") ranks 4. v1.1.0 computed the same values inline (RANK.get(role,
# 3 if role is None else 4)), so the selection did not change.
RANK = {"SAME": 0, "PROOF": 1, "REFUTE": 1, "NEITHER": 2, "N/M": 3, "UND": 4}


def rank_of(rec):
    """Rank of one judge_pair record: N/M is identified by the nm flag, UND by role == 'UND', every other record by its role."""
    if rec["nm"]:
        return RANK["N/M"]
    if rec["role"] == "UND":
        return RANK["UND"]
    return RANK[rec["role"]]


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
           "gen_sat": None, "gen_valid": None, "queries": [], "ap_check": None, "engine": getattr(engine, "name", "?")}
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
        if not maps:
            # v1.1.0: an empty candidate list means that no vocabulary alignment exists (for example two generated variables whose only same-type
            # reference counterpart is the same variable). That is UND, like the 'und' results of align.candidates above; v1.0.0 recorded N/M 'other'.
            rec["role"] = "UND"
            rec["und_reason"] = "atomization_mismatch"
            rec["nm_detail"] = {"message": "no injective renaming candidate"}
            rec["ap_check"] = ap_check(None, None)
            return _finish(rec, store, t0)
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
                # defensive only: an empty candidate list returns UND above, and every candidate that fails records first_fail
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
    rec["queries"] = [q.to_record() for q in store]
    rec["elapsed_sec_total"] = round(time.time() - t0, 3)
    rec["_smv"] = {q.smv_sha256: q.smv_text for q in store if q.smv_sha256}
    return rec


def _trial(r):
    """Summary of one reference-part attempt for reference_trials. The raw query output (stdout, stderr, cmd) stays only in the 'queries' of the kept record."""
    qs = r["queries"]
    return {"reference_part": r["reference_part"], "role": r["role"], "nm": r["nm"], "nm_reason": r["nm_reason"], "und_reason": r["und_reason"],
            "n_queries": len(qs), "smv_sha256": [q["smv_sha256"] for q in qs if q["smv_sha256"]],
            "queries": [{"kind": q["kind"], "verdict": q["verdict"], "elapsed_sec": q["elapsed_sec"]} for q in qs]}


def best_over_references(gen_pt, ref_parts, engine, **kw):
    """Compare one generated formula with several reference parts (all versions) and keep the best record (SAME < PROOF = REFUTE < NEITHER < N/M, UND last).
    v1.1.0: the kept record also carries reference_trials (one summary per attempted part, in order; the loop stops at the first SAME) and the SMV files of
    every attempt (merged into _smv, so that the recorder stores them in smv/). The selection rule is unchanged."""
    best = None
    trials, smv = [], {}
    for i, (ref_id, ref_pt, ref_ft) in enumerate(ref_parts):
        r = judge_pair(gen_pt, ref_pt, engine, ref_ft=ref_ft, **kw)
        r["reference_part"] = ref_id
        trials.append(_trial(r))
        smv.update(r.get("_smv") or {})
        rank = rank_of(r)
        if best is None or rank < best[0]:
            best = (rank, r)
        if rank == 0:
            break
    if not best:
        return None
    rec = best[1]
    rec["reference_trials"] = trials
    rec["_smv"] = smv
    return rec
