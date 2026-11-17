#!/usr/bin/env python3
"""Observation-only record of a dev run. Usage: python3 tools/dev_record.py results_dev > results_dev/DEV_RECORD.md
Counts only. No judgment of meaning, no comparison of arms."""
import json, sys, collections, pathlib
d = pathlib.Path(sys.argv[1])
rows = [json.loads(l) for l in open(d / "calls.jsonl")]
st = json.loads((d / "run_state.json").read_text())
print("# DEV_RECORD (observation only)\n")
print(f"- status: {st.get('status')}, start: {st.get('start_iso')}, elapsed_h: {st.get('elapsed_since_first_start_h')}, resumes: {st.get('resumes')}, rules_hash: {st.get('rules_hash')}")
print(f"- call rows: {len(rows)}; distinct stage_key: {len(set(r['stage_key'] for r in rows))}")
print(f"- wall_s sum (h): {sum(r.get('wall_s',0) for r in rows)/3600:.2f}; waited_s sum (h): {sum(r.get('waited_s',0) for r in rows)/3600:.2f}")
print("\n| stage | status | n |\n|---|---|---|")
for k, v in sorted(collections.Counter((r['stage'], r['status']) for r in rows).items()):
    print(f"| {k[0]} | {k[1]} | {v} |")
print("\n| arm | stage A/D rows ok | parse_error rows |\n|---|---|---|")
arms = sorted(set(r['arm'] for r in rows))
for a in arms:
    ok = sum(1 for r in rows if r['arm'] == a and r['stage'] in ("A", "D") and r['status'] == "ok")
    pe = sum(1 for r in rows if r['arm'] == a and r['status'] == "parse_error")
    print(f"| {a} | {ok} | {pe} |")
mu = collections.Counter(tuple(sorted((r.get('model_used') or []))) if isinstance(r.get('model_used'), list) else str(r.get('model_used')) for r in rows)
print("\nmodel_used distribution:", dict(mu))
