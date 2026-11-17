#!/usr/bin/env python3
"""Negative control input of the 021 run (instruction section 3, step 3): 300 units drawn with seed 20261112, the item of every drawn unit replaced by another item id.

Rules (written into control_sampling.json and into notes/PRE_RUN_DEFINITIONS_021.md before any judging):
  draw   : the units of units.json in FILE ORDER get one number each from random.Random(20261112).random() (the stream of random() is the part of the random module that
           the Python documentation guarantees to stay the same across versions); the 300 units with the smallest numbers are drawn and written in file order.
  item   : the 61 item ids sorted ascending are numbered 0..60; the item with number i is replaced by the item with number (i + 31) mod 61 (31 is not a multiple of 61, so every
           item gets another item; the map is a bijection, so item x arm x rep stays a unique key). Sentences (texts), arm, rep, status and stratum stay as they are.
usage: python3 -I -B make_control_units.py <units.json> <out dir> [--n 300] [--seed 20261112] [--shift 31]
Writes <out dir>/units_control.json (the serialization of units.json: json.dumps({"units": [...]}, ensure_ascii=False)) and <out dir>/control_sampling.json."""
import argparse
import hashlib
import json
import os
import random
import sys

sys.dont_write_bytecode = True

ap = argparse.ArgumentParser()
ap.add_argument("units")
ap.add_argument("out")
ap.add_argument("--n", type=int, default=300)
ap.add_argument("--seed", type=int, default=20261112)
ap.add_argument("--shift", type=int, default=31)
a = ap.parse_args()

raw = open(a.units, "rb").read()
units = json.loads(raw.decode("utf-8"))["units"]
items = sorted({u["item"] for u in units})
assert a.shift % len(items) != 0, "the shift would map an item onto itself"
new_of = {it: items[(i + a.shift) % len(items)] for i, it in enumerate(items)}
assert all(new_of[i] != i for i in items) and len(set(new_of.values())) == len(items)
rng = random.Random(a.seed)
nums = [rng.random() for _ in units]                                   # one number per unit, in file order
drawn = sorted(sorted(range(len(units)), key=lambda k: nums[k])[:a.n])    # the n smallest numbers, written back in file order
out_units, picked = [], []
for k in drawn:
    u = dict(units[k])
    picked.append({"file_index": k, "item": u["item"], "arm": u["arm"], "rep": u["rep"], "new_item": new_of[u["item"]], "n_texts": len(u.get("texts") or [])})
    u["item"] = new_of[u["item"]]
    out_units.append(u)
keys = [(u["item"], u["arm"], int(u["rep"])) for u in out_units]
assert len(set(keys)) == len(keys), "control keys are not unique"
os.makedirs(a.out, exist_ok=True)
path = os.path.join(a.out, "units_control.json")
with open(path, "w", encoding="utf-8") as f:
    f.write(json.dumps({"units": out_units}, ensure_ascii=False))
info = {"input": os.path.basename(a.units), "input_sha256": hashlib.sha256(raw).hexdigest(), "units_in_input": len(units), "n_drawn": len(out_units), "seed": a.seed, "shift": a.shift,
        "rule_draw": "random.Random(seed).random() once per unit in file order, the n smallest numbers, written in file order",
        "rule_item": "sorted item ids numbered 0..60, item i replaced by item (i + shift) mod 61", "item_map": new_of, "drawn_units": picked,
        "output": "units_control.json", "output_sha256": hashlib.sha256(open(path, "rb").read()).hexdigest()}
json.dump(info, open(os.path.join(a.out, "control_sampling.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(f"drawn {len(out_units)} of {len(units)} units, {len({u['item'] for u in out_units})} new item ids, sentences {sum(len(u.get('texts') or []) for u in out_units)}, output sha256 {info['output_sha256'][:16]}")
