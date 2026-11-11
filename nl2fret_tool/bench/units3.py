"""Derives the state of one unit (item x arm x repetition) from the stage rows of calls.jsonl and the parser results. Deterministic, no model call.
Used by run_pipeline.py (to decide what is still to do) and by score3.py (final records), so both always agree.
"""
import fretlint as L
import tpl_rules as T
from prompts3 import MAX_ROUNDS, TPLS, akey, base_of, is_rule, is_r2, is_direct, parse_slot_output, ARM_D  # noqa: F401

FIXABLE_PRE = {"slot_lint"}   # codes for which a feedback round makes sense (the rule layer cannot repair the others)


def skey(item_id, arm, rep, stage):
    return f"{item_id}|{akey(arm) if stage == 'A' else arm}|{rep}|{stage}"


def first_stage(arm):
    return "D" if is_direct(arm) else ("S" if is_rule(arm) else "B")


def _official(comp, text):
    r = comp.get(text)
    if r is None:
        return None
    cid, grp, _ = L.classify_error(r["error"]) if not r["ok"] else (None, None, None)
    return {"ok": r["ok"], "error": r["error"], "cls": cid, "grp": grp}


def _free_round(rnd_no, stage, row, comp):
    """D / B / F rows of the arms without the rule layer: the model wrote the FRETish."""
    rr = {"round": rnd_no, "stage": stage, "row": row, "sentences": []}
    if row is None:
        rr["pending"] = True
        return rr
    if row["status"] != "ok":
        rr["sentences"].append({"text": None, "pre": {"code": "call_failed", "detail": row["status"]}, "official": None})
        return rr
    texts = [t.strip() for t in (row["parsed"] or {}).get("fretish", []) if isinstance(t, str) and t.strip()]
    if not texts:
        rr["sentences"].append({"text": None, "pre": {"code": "no_output", "detail": "empty fretish list"}, "official": None})
    for t in texts:
        nt, ap = L.normalize_fretish(t)
        rr["sentences"].append({"text": t, "pre": None, "official": _official(comp, t), "norm_text": nt, "norm_rules": ap, "norm_official": _official(comp, nt), "rules": []})
    rr["unmapped"] = (row["parsed"] or {}).get("unmapped_content", [])
    return rr


def _slot_round(rnd_no, stage, row, parses, reqs, comp, r2=False):
    rr = {"round": rnd_no, "stage": stage, "row": row, "sentences": []}
    if row is None:
        rr["pending"] = True
        return rr
    if row["status"] != "ok":
        rr["sentences"].append({"text": None, "pre": {"code": "call_failed", "detail": row["status"]}, "official": None})
        return rr
    sl = row["parsed"]["slots"]
    rr["unmapped"] = row["parsed"].get("unmapped_content", [])
    for i, (p, rq) in enumerate(zip(parses, reqs), 1):
        lint = T.lint_slots(rq, sl.get(i) or sl.get(str(i)) or {})
        a = T.assemble(p, lint, r2)
        ent = {"text": a.get("fretish"), "pre": None, "official": None, "rules": a.get("rules", []), "slot_fixes": sorted({f for v in lint.values() for f in v.get("fixes", [])})}
        if not a["ok"]:
            ent["pre"] = {"code": a["code"], "detail": a["detail"]}
        else:
            ent["official"] = _official(comp, a["fretish"])
            nt, ap = L.normalize_fretish(a["fretish"])
            ent.update(norm_text=nt, norm_rules=ap, norm_official=_official(comp, nt))
        rr["sentences"].append(ent)
    return rr


def derive(rows, item, arm, rep, comp):
    """rows: dict stage_key -> row. comp: dict text -> {"ok","error"}. -> unit record."""
    iid = item["id"]
    rec = {"item_id": iid, "arm": arm, "rep": rep, "base": base_of(arm), "rounds": [], "A": None, "pipeline": None, "pending": False, "parses": None}
    rule = is_rule(arm)
    base = base_of(arm)
    a_sents = None
    if not is_direct(arm):
        a = rows.get(skey(iid, arm, rep, "A"))
        if a is None:
            rec["pending"] = True
            return rec
        rec["A"] = {"status": a["status"], "sentences": (a.get("parsed") or {}).get("sentences", []), "tokens": a.get("total_tokens", 0)}
        if a["status"] != "ok":
            rec["pipeline"] = {"code": "A_failed", "detail": a["status"]}
            return rec
        a_sents = rec["A"]["sentences"]
        # template conformance, checked by the same script for every template arm (also for the arms without the rule layer)
        cf = [] if base == "PARA" else [T.parse_template(base, s) for s in a_sents]
        rec["conformance"] = [{"ok": c["ok"], "code": c.get("code"), "detail": c.get("detail"), "rules": c.get("rules", []), "notes": c.get("notes", []),
                               "nomap": c.get("nomap", [])} for c in cf]
        if rule:
            rec["parses"] = cf
            bad = [c for c in cf if not c["ok"]]
            if bad:
                rec["pipeline"] = {"code": bad[0]["code"], "detail": bad[0]["detail"]}
                rec["rounds"] = [{"round": 0, "stage": "rule", "row": None, "sentences": [{"text": None, "pre": {"code": c.get("code") or "ok", "detail": c.get("detail", "")},
                                                                                         "official": None} for c in cf if not c["ok"]]}]
                return rec
    first = first_stage(arm)
    if rule:
        reqs = [T.slot_requests(p, is_r2(arm)) for p in rec["parses"]]
        rec["reqs"] = reqs
        mk = lambda n, st, row: _slot_round(n, st, row, rec["parses"], reqs, comp, is_r2(arm))
    else:
        mk = lambda n, st, row: _free_round(n, st, row, comp)
    r0 = mk(0, first, rows.get(skey(iid, arm, rep, first)))
    rec["rounds"].append(r0)
    if r0.get("pending"):
        rec["pending"] = True
        return rec
    for k in range(1, MAX_ROUNDS + 1):
        row = rows.get(skey(iid, arm, rep, f"F{k}"))
        if row is None:
            break
        rec["rounds"].append(mk(k, f"F{k}", row))
    return rec


def round_failed(rnd):
    return any((s["pre"] is not None) or (s["official"] is not None and not s["official"]["ok"]) for s in rnd["sentences"])


def needs_feedback(rec):
    """True when the last round has a sentence a feedback round can address (parser rejection or slot_lint) and rounds are left."""
    if rec["pending"] or rec["pipeline"] or not rec["rounds"]:
        return False
    last = rec["rounds"][-1]
    if last.get("pending") or len(rec["rounds"]) - 1 >= MAX_ROUNDS:
        return False
    for s in last["sentences"]:
        if s["pre"] is not None and s["pre"]["code"] not in FIXABLE_PRE:
            return False   # call_failed, no_output, rule_no_mapping, unit problems: not addressed by feedback
    return any((s["pre"] is not None) or (s["official"] is not None and not s["official"]["ok"]) for s in last["sentences"])


def pending_compile(rec):
    """Texts of the last round that still need an official parser verdict."""
    need = []
    if rec["pending"] or not rec["rounds"]:
        return need
    for rr in rec["rounds"]:
        for s in rr["sentences"]:
            if s.get("text") and s["official"] is None:
                need.append(s["text"])
            if s.get("norm_text") and s.get("norm_official") is None:
                need.append(s["norm_text"])
    return need


# ------------------------------------------------------------------ variants
def variant(rec, v):
    """v0 = first answer, vn = first answer after the mechanical normalizer, vf = after the feedback rounds.
    -> (stage_status, code, detail, texts)  stage_status: pipeline | parse_error | parsed ; texts = sentences accepted by the official parser."""
    if rec["pending"]:
        return "pending", "pending", "", []
    if rec["pipeline"]:
        return "pipeline", rec["pipeline"]["code"], rec["pipeline"]["detail"], []
    rr = rec["rounds"][0] if v in ("v0", "vn") else rec["rounds"][-1]
    sents = rr["sentences"]
    for s in sents:
        if s["pre"] is not None:
            return "pipeline", s["pre"]["code"], s["pre"]["detail"], []
    texts, bad = [], []
    for s in sents:
        t, o = (s.get("norm_text"), s.get("norm_official")) if v == "vn" else (s["text"], s["official"])
        if o is None:
            return "pending", "pending", "", []
        if o["ok"]:
            texts.append(t)
        else:
            bad.append(o)
    if bad:
        return "parse_error", bad[0]["cls"], bad[0]["error"] or "", texts
    return "parsed", "", "", texts
