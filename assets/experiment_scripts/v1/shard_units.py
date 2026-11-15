#!/usr/bin/env python3
"""Split units.json into N shards by item (instruction 4.1): item ids sorted, round robin (item number i goes to shard i mod N), whole items, units are never split.
usage: python3 -I -B shard_units.py <units.json> <out dir> <N> [--prefix units_shard]
Writes <out dir>/<prefix><k>.json (k = 1..N, same serialization as units.json: json.dumps({"units": [...]}, ensure_ascii=False)) and <out dir>/shards_manifest.json
(items per shard, units per shard, sha256 of every shard file and of the input). fret_ltl_gen.jsonl and fret_realizability_gen.jsonl are used whole by every shard."""
import hashlib
import json
import os
import sys

src, out, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
prefix = sys.argv[sys.argv.index("--prefix") + 1] if "--prefix" in sys.argv else "units_shard"
units = json.load(open(src, encoding="utf-8"))["units"]
items = sorted({u["item"] for u in units})
shard_of = {it: (i % n) + 1 for i, it in enumerate(items)}
os.makedirs(out, exist_ok=True)
man = {"input": os.path.abspath(src), "input_sha256": hashlib.sha256(open(src, "rb").read()).hexdigest(), "n_shards": n, "rule": "item ids sorted, round robin, whole items", "shards": []}
total = 0
for k in range(1, n + 1):
    us = [u for u in units if shard_of[u["item"]] == k]
    path = os.path.join(out, f"{prefix}{k}.json")
    with open(path, "w", encoding="utf-8") as f:
        f.write(json.dumps({"units": us}, ensure_ascii=False))
    total += len(us)
    man["shards"].append({"shard": k, "file": os.path.basename(path), "items": sorted({u["item"] for u in us}), "n_items": len({u["item"] for u in us}), "n_units": len(us),
                          "n_sentences": sum(len(u["texts"]) for u in us), "sha256": hashlib.sha256(open(path, "rb").read()).hexdigest()})
assert total == len(units), "units were lost or duplicated"
json.dump(man, open(os.path.join(out, "shards_manifest.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
for s in man["shards"]:
    print(f"shard {s['shard']}: {s['n_items']} items, {s['n_units']} units, {s['n_sentences']} sentences, sha256 {s['sha256'][:16]}")
print("total units", total, "| input sha256", man["input_sha256"][:16])
