#!/usr/bin/env python3
"""Merge the judge shards (instruction 4.3). Reads runs/shard<k>/{judge_records.jsonl, run_header.json, smv/}, refuses to merge when a pair id occurs twice or a record
belongs to no unit, and writes <out>/judge_records.jsonl (the ORIGINAL record lines, unchanged, ordered by unit order of the full units.json and sentence index),
<out>/smv/ (union of the SMV files), <out>/run_header.json (the header of shard 1 plus a 'shards' list with the input hash and code hash of every shard) and
<out>/run_header_shard<k>.json (the shard headers, unchanged). The code is not touched; make aggregate is run afterwards on <out>.
usage: python3 -I -B merge_judge.py <runs dir> <out dir> <full units.json> <N shards> <expected code_tree_sha256> [<shards_manifest.json>]"""
import hashlib
import json
import os
import shutil
import sys
import time

runs, out, units_path, n, expect_code = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
man_path = sys.argv[6] if len(sys.argv) > 6 else None
units = json.load(open(units_path, encoding="utf-8"))["units"]
pos = {(u["item"], u["arm"], int(u["rep"])): i for i, u in enumerate(units)}
lines, seen, problems, shards = [], {}, [], []
for k in range(1, n + 1):
    d = os.path.join(runs, f"shard{k}")
    jr = os.path.join(d, "judge_records.jsonl")
    hdr = json.load(open(os.path.join(d, "run_header.json"), encoding="utf-8"))
    raw = open(jr, "rb").read()
    if raw and not raw.endswith(b"\n"):
        problems.append(f"shard {k}: judge_records.jsonl does not end with a newline (incomplete last line)")
    cnt = 0
    for ln in raw.decode("utf-8").split("\n"):
        if not ln.strip():
            continue
        try:
            rec = json.loads(ln)
        except ValueError:
            problems.append(f"shard {k}: unreadable line {cnt + 1}")
            continue
        pid = rec["pair_id"]
        item, arm, rep, idx = pid.rsplit("|", 3)[0], *pid.rsplit("|", 3)[1:]
        key = (item, arm, int(rep))
        if key not in pos:
            problems.append(f"shard {k}: pair {pid} belongs to no unit")
            continue
        if pid in seen:
            problems.append(f"duplicate pair_id {pid} (shards {seen[pid]} and {k})")
            continue
        seen[pid] = k
        lines.append(((pos[key], int(idx)), ln))
        cnt += 1
    shards.append({"shard": k, "records": cnt, "units_sha256": (hdr.get("inputs") or {}).get("units"), "ltl_sha256": (hdr.get("inputs") or {}).get("ltl"),
                   "rlz_sha256": (hdr.get("inputs") or {}).get("rlz"), "reference_sha256": (hdr.get("inputs") or {}).get("reference"), "code_tree_sha256": hdr.get("code_tree_sha256"),
                   "frozen": hdr.get("frozen"), "frozen_check": hdr.get("frozen_check"), "started_at": hdr.get("started_at"), "header": f"run_header_shard{k}.json"})
    if hdr.get("frozen") is not True:
        problems.append(f"shard {k}: header frozen is {hdr.get('frozen')!r}")
    if hdr.get("code_tree_sha256") != expect_code:
        problems.append(f"shard {k}: code_tree_sha256 {hdr.get('code_tree_sha256')} differs from the expected manifest hash")
if problems:
    print("NOT MERGED:")
    for p in problems:
        print(" -", p)
    sys.exit(1)
os.makedirs(os.path.join(out, "smv"), exist_ok=True)
lines.sort(key=lambda x: x[0])
with open(os.path.join(out, "judge_records.jsonl"), "w", encoding="utf-8") as f:
    for _, ln in lines:
        f.write(ln + "\n")
n_smv = 0
for k in range(1, n + 1):
    sd = os.path.join(runs, f"shard{k}", "smv")
    for name in os.listdir(sd):
        dst = os.path.join(out, "smv", name)
        if os.path.exists(dst):
            if open(dst, "rb").read() != open(os.path.join(sd, name), "rb").read():
                print("SMV file with the same sha256 name but different content:", name)
                sys.exit(1)
        else:
            shutil.copyfile(os.path.join(sd, name), dst)
            n_smv += 1
    shutil.copyfile(os.path.join(runs, f"shard{k}", "run_header.json"), os.path.join(out, f"run_header_shard{k}.json"))
hdr = json.load(open(os.path.join(runs, "shard1", "run_header.json"), encoding="utf-8"))
hdr["shards"] = shards
hdr["merged"] = {"merged_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "records": len(lines), "full_units_sha256": hashlib.sha256(open(units_path, "rb").read()).hexdigest(),
                 "shards_manifest": json.load(open(man_path)) if man_path else None, "rule": "original record lines unchanged, ordered by unit order and sentence index"}
json.dump(hdr, open(os.path.join(out, "run_header.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(f"merged {len(lines)} records from {n} shards (duplicate pair_id 0), {n_smv} distinct SMV files, header with a shards list written to {out}")
