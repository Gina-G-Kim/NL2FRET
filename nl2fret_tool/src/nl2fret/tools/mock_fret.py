#!/usr/bin/env python3
"""OFFLINE TEST ONLY. Writes a fake results_nl3/fret_realizability.jsonl (random verdicts) so that score3.py final and score_lm.py can be exercised without docker.
Never use its output for anything but code tests."""
import hashlib
import json
import sys
from pathlib import Path

res = Path(sys.argv[1])
rows = [json.loads(l) for l in open(res / "variants.jsonl", encoding="utf-8")]
seen, out = {}, []
for r in rows:
    for k, t in enumerate(r["fretish"]):
        h = int(hashlib.sha1(t.encode()).hexdigest(), 16) % 100
        v = "realizable" if h < 80 else "unrealizable" if h < 90 else "unknown" if h < 96 else "not_run"
        out.append({"item_id": r["item_id"], "arm": r["arm"], "rep": r["rep"], "sentence_idx": k, "kind": "gen", "mode": "single_requirement", "sentence": t, "result": v, "detail": "MOCK"})
data = [json.loads(l) for l in open(Path(__file__).resolve().parent.parent / "data/lm_items.jsonl", encoding="utf-8")]
ltl = {}
for d in data:
    for pi, part in enumerate(d["gt_parts"]):
        for vi, v in enumerate(part):
            out.append({"item_id": d["id"], "arm": "GT", "rep": None, "sentence_idx": f"{pi}.{vi}", "kind": "gt", "gt_ref": v["reqid"], "mode": "single_requirement", "sentence": v["fretish"], "result": "realizable", "detail": "MOCK"})
            ltl[v["fretish"]] = {"sentence": v["fretish"], "parser_ok": True, "ltl_ft": v["ltl"]["future_time"], "ltl_pt": v["ltl"]["past_time"]}
for r in rows:
    for t in r["fretish"]:
        ltl.setdefault(t, {"sentence": t, "parser_ok": True, "ltl_ft": "MOCK(" + t[:20] + ")", "ltl_pt": "MOCK"})
open(res / "fret_ltl.jsonl", "w", encoding="utf-8").write("".join(json.dumps(x) + "\n" for x in ltl.values()))
open(res / "fret_realizability.jsonl", "w", encoding="utf-8").write("".join(json.dumps(x) + "\n" for x in out))
print("mock rows", len(out))
