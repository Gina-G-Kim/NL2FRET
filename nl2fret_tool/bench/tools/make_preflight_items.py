#!/usr/bin/env python3
"""Writes data/lm_preflight.jsonl: the 6 smoke items (a subset of the 61 main-run items, chosen before any result and mixing types).
The main run still contains all 61 items. The preflight folder is separate and its results are never merged into the main run."""
import json
import sys

IDS = ["LM-02_TUSTIN-N2", "LM-07_AP-0", "LM-07_AP-1.2", "LM-03_REG-N01", "LM-01_FSM-N01", "LM-09_EUL-N2"]
rows = [json.loads(l) for l in open("data/lm_items.jsonl", encoding="utf-8")]
sel = [d for d in rows if d["id"] in IDS]
assert len(sel) == 6, len(sel)
nv = sum(len(p) for d in sel for p in d["gt_parts"])
assert nv == 11, nv
open("data/lm_preflight.jsonl", "w", encoding="utf-8").write("".join(json.dumps(d, ensure_ascii=False) + "\n" for d in sel))
print("wrote", len(sel), "items; reference versions", nv)
