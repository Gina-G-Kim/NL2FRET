#!/usr/bin/env python3
"""Name-swap control (post hoc, outside the frozen tool). Input: judge_records.jsonl of the dictionary run, the dictionary inputs.
For every pair judged SAME whose generated formula has at least two distinct variables, two variables (the first two in sorted order) are swapped in ltl_pt and ltl_ft.
Output: units_swap.json (one unit per pair, item = the pair's item) and fret_ltl_swap.jsonl (sentence key = original text + ' #swap').
Expected: not SAME, except when the formula is symmetric in the two swapped variables (reported separately, checked by hand).
usage: python3 -I -B swap_control.py RECORDS INPUTS_DIR OUT_DIR"""
import json, re, sys, os
rec, ind, out = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
TOK = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
KW = {"H", "Y", "O", "S", "LAST", "V", "TRUE", "FALSE", "true", "false", "X", "F", "G", "U", "R", "T", "Z"}
def vs(s):
    o = []
    for m in TOK.finditer(s or ""):
        w = m.group(0)
        if s[m.end():].lstrip().startswith("(") or w in KW or w in o: continue
        o.append(w)
    return o
def swap(s, a, b):
    return TOK.sub(lambda m: b if m.group(0) == a else a if m.group(0) == b else m.group(0), s)
ltl = {}
for l in open(f"{ind}/fret_ltl_gen.jsonl"):
    r = json.loads(l); ltl[r["sentence"]] = r
units = {}
for u in json.load(open(f"{ind}/units.json"))["units"]:
    units[(u["item"], u["arm"], int(u["rep"]))] = u
same = [json.loads(l) for l in open(rec)]
same = [r for r in same if r.get("role") == "SAME"]
nu, rows, skipped = [], [], 0
for r in same:
    item, arm, rep, i = r["pair_id"].split("|"); u = units[(item, arm, int(rep))]
    t = u["texts"][int(i)]; row = ltl[t]
    v = sorted(vs(row["ltl_pt"]))
    if len(v) < 2: skipped += 1; continue
    a, b = v[0], v[1]
    nr = dict(row); nr["sentence"] = t + " #swap"
    nr["ltl_pt"] = swap(row["ltl_pt"], a, b); nr["ltl_ft"] = swap(row["ltl_ft"], a, b)
    rows.append(nr)
    nu.append({"item": item, "arm": arm, "rep": int(rep), "status": "parsed", "code": "", "texts": [t + " #swap"], "n_rounds": 1, "stratum": u.get("stratum"), "orig_pair_id": r["pair_id"], "swapped": [a, b]})
json.dump({"units": nu}, open(f"{out}/units_swap.json", "w"), ensure_ascii=False)
with open(f"{out}/fret_ltl_swap.jsonl", "w") as f:
    for x in rows: f.write(json.dumps(x, ensure_ascii=False) + "\n")
print("SAME pairs", len(same), "swapped", len(nu), "skipped (fewer than 2 variables)", skipped)
