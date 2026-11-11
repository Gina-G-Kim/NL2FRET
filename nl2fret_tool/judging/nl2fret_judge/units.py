"""Unit collection. A unit is item x arm x repetition and carries its final FRETish sentences.

Input interface (arm independent), one JSON object per unit:
  {"item": str, "arm": str, "rep": int, "status": "parsed"|..., "texts": [sentence, ...]}
Per-sentence data are joined from
  fret_ltl_gen.jsonl            sentence -> parser_ok, ltl_pt, ltl_ft           (bench/ pipeline output, FRET compile)
  fret_realizability_gen.jsonl  (item, arm, rep, sentence) -> result            (realizable | unknown | unrealizable | not_run)
The reference (answer key) comes from data/reference/lm_reference_with_ltl.jsonl: gt_parts[i][j] = one reference sentence version with its compiled LTL.
A sentence without a parsed formula stays in the unit (it counts as parser-rejected, i.e. failure, never as excluded).
"""
import json


def read_jsonl(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def load_reference(path):
    """-> {item_id: [(ref_id, ltl_pt, ltl_ft), ...]} over all reference sentences and versions of the item."""
    out = {}
    for r in read_jsonl(path):
        parts = []
        for i, grp in enumerate(r["gt_parts"]):
            for j, p in enumerate(grp):
                l = p.get("ltl") or {}
                if l.get("past_time"):
                    parts.append((f"{p.get('reqid', i)}#{j}", l["past_time"], l.get("future_time")))
        out[r["id"]] = parts
    return out


def load_units(units_path, ltl_path, rlz_path=None):
    d = json.load(open(units_path, encoding="utf-8"))
    units = d["units"] if isinstance(d, dict) else d
    ltl = {r["sentence"]: r for r in read_jsonl(ltl_path)}
    rlz = {}
    if rlz_path:
        for r in read_jsonl(rlz_path):
            rlz[(r["item_id"], r["arm"], int(r["rep"]), r["sentence"])] = r["result"]
    out = []
    for u in units:
        sents = []
        for t in u.get("texts") or []:
            L = ltl.get(t) or {}
            sents.append({"text": t, "parser_ok": bool(L.get("parser_ok")), "ltl_pt": L.get("ltl_pt"), "ltl_ft": L.get("ltl_ft"),
                          "realizability": rlz.get((u["item"], u["arm"], int(u["rep"]), t), "not_run")})
        out.append({"item": u["item"], "arm": u["arm"], "rep": int(u["rep"]), "status": u.get("status"), "stratum": u.get("stratum"), "sentences": sents})
    return out
