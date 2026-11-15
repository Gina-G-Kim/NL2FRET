#!/usr/bin/env python3
"""Checks of the merged judging (instruction 4.4). Read-only. Writes <out md> and <out json>.
usage: python3 -I -B judge_checks.py --units U --ltl L --merged <merged dir> --expect-code <sha256> --out-md F --out-json F [--previous <judge_records.jsonl of an earlier run>]
Checks: (1) record count against the sentences that have a parsed formula (list of differences), (2) headers frozen true and code_tree_sha256 equal, (3) role distribution, UND
and N/M reasons, (4) timeout pairs and time per pair, (5) the same sentence of the same item in different units got the same verdict (violations listed), (6) comparison
with an earlier run on pairs with the same generated and reference formula (comparison only)."""
import argparse
import collections
import json
import os
import statistics

ap = argparse.ArgumentParser()
for k in ("units", "ltl", "merged", "expect-code", "out-md", "out-json"):
    ap.add_argument("--" + k, required=True)
ap.add_argument("--previous")
a = ap.parse_args()
jl = lambda p: [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
units = json.load(open(a.units, encoding="utf-8"))["units"]
ltl = {r["sentence"]: r for r in jl(a.ltl)}
recs = jl(os.path.join(a.merged, "judge_records.jsonl"))
hdr = json.load(open(os.path.join(a.merged, "run_header.json"), encoding="utf-8"))
R = {}
md = ["# 판정 점검 (4.4)\n"]
# (1) counts
exp = {}
for u in units:
    for i, t in enumerate(u["texts"]):
        L = ltl.get(t) or {}
        if L.get("parser_ok") and L.get("ltl_pt"):
            exp[f"{u['item']}|{u['arm']}|{u['rep']}|{i}"] = t
got = {r["pair_id"]: r for r in recs}
missing, extra = sorted(set(exp) - set(got)), sorted(set(got) - set(exp))
R["counts"] = {"records": len(recs), "distinct_pair_ids": len(got), "expected_sentences_with_formula": len(exp), "missing": len(missing), "extra": len(extra), "missing_examples": missing[:10], "extra_examples": extra[:10]}
md.append(f"## 1. 쌍 수\n\n- 기록 {len(recs)}줄, 서로 다른 `pair_id` {len(got)}개, `units.json`에서 `parser_ok`이고 LTL이 있는 문장 {len(exp)}개. 기록이 없는 문장 {len(missing)}개, 기대에 없는 기록 {len(extra)}개." + (" 같음." if not missing and not extra else f" 차이 예: {missing[:3]} {extra[:3]}") + "\n")
# (2) headers
sh = hdr.get("shards") or []
R["headers"] = [{k: s.get(k) for k in ("shard", "frozen", "frozen_check", "code_tree_sha256", "units_sha256")} for s in sh]
ok_h = all(s.get("frozen") is True and s.get("code_tree_sha256") == a.expect_code for s in sh)
md.append(f"## 2. 헤더\n\n- 분할 {len(sh)}개의 헤더 모두 `frozen: true`이고 `code_tree_sha256`이 기대값 `{a.expect_code[:16]}...`와 같은가: **{'예' if ok_h else '아니오'}**. 합친 헤더의 `selfcheck_passed` {hdr.get('selfcheck_passed')}, `mode` {hdr.get('mode')}, `cap` {hdr.get('cap')}, `timeout` {hdr.get('timeout')}, `aux` {hdr.get('aux')}, 엔진 {hdr.get('engine')} ({hdr.get('engine_version')}).\n")
# (3) roles
lab = lambda r: "N/M" if r.get("nm") else r.get("role")
rc = collections.Counter(lab(r) for r in recs)
und = collections.Counter(r.get("und_reason") for r in recs if r.get("role") == "UND")
nmr = collections.Counter(r.get("nm_reason") for r in recs if r.get("nm"))
R["roles"] = dict(rc)
R["und_reasons"] = {str(k): v for k, v in und.items()}
R["nm_reasons"] = {str(k): v for k, v in nmr.items()}
md.append("## 3. 역할 분포\n\n" + "\n".join(f"- {k}: {v}" for k, v in sorted(rc.items(), key=lambda x: str(x[0]))) + f"\n- UND 사유: {dict(und) or '없음'}\n- N/M 사유: {dict(nmr) or '없음'}\n")
# (4) time
def timed_out(r):
    return r.get("nm_reason") == "timeout" or any(q.get("timed_out") for q in r.get("queries") or [])
to = [r["pair_id"] for r in recs if timed_out(r)]
ts = [r["elapsed_sec_total"] for r in recs if r.get("elapsed_sec_total") is not None]
R["time"] = {"timeout_pairs": len(to), "timeout_pair_ids": to, "pairs_with_time": len(ts), "mean_sec": statistics.mean(ts) if ts else None, "median_sec": statistics.median(ts) if ts else None,
             "max_sec": max(ts) if ts else None, "sum_hours": sum(ts) / 3600 if ts else None}
md.append(f"## 4. 시간 초과와 쌍당 시간\n\n- 질의 시간 초과가 있는 기록 {len(to)}개: {to[:40]}{' ...' if len(to) > 40 else ''}\n- 쌍당 시간(초): 평균 {R['time']['mean_sec']:.2f}, 중앙값 {R['time']['median_sec']:.2f}, 최대 {R['time']['max_sec']:.1f}, 합계 {R['time']['sum_hours']:.2f}시간 (분할 4개가 동시에 돌았으므로 벽시계 시간은 아님)\n" if ts else "## 4. 시간\n\n기록 없음\n")
# (5) determinism
g = collections.defaultdict(set)
for r in recs:
    item = r["pair_id"].split("|")[0]
    g[(item, r.get("sentence"))].add((r.get("role"), r.get("nm"), r.get("nm_reason"), r.get("und_reason"), r.get("sound"), r.get("compl")))
viol = [(k, sorted(map(str, v))) for k, v in g.items() if len(v) > 1]
R["determinism"] = {"distinct_item_sentence_pairs": len(g), "violations": len(viol), "violation_examples": [{"item": k[0], "sentence": k[1], "verdicts": v} for k, v in viol[:20]]}
md.append(f"## 5. 결정성 (같은 항목의 같은 문장이 다른 단위에서 받은 판정)\n\n- 서로 다른 (항목, 문장) {len(g)}개 중 판정이 다른 것: **{len(viol)}개**" + ("" if not viol else "\n" + "\n".join(f"  - {k[0]} | {k[1][:100]} | {v}" for k, v in viol[:20])) + "\n")
# (6) comparison with an earlier run
if a.previous and os.path.exists(a.previous):
    prev = {(r["pred_pt"], r["gt_pt"]): r for r in jl(a.previous) if r.get("pred_pt") and r.get("gt_pt")}
    cur = {}
    for r in recs:
        cur.setdefault((r["pred_pt"], r["gt_pt"]), []).append(r)
    ov = [(k, prev[k], cur[k]) for k in prev if k in cur]
    same = sum(1 for k, p, cs in ov if all((lab(c), c.get("nm_reason"), c.get("und_reason")) == (lab(p), p.get("nm_reason"), p.get("und_reason")) for c in cs))
    diffs = [(k[0][:60], lab(p), sorted({str(lab(c)) for c in cs})) for k, p, cs in ov if not all(lab(c) == lab(p) for c in cs)]
    R["previous_run"] = {"file": a.previous, "previous_pairs": len(prev), "overlapping_formula_pairs": len(ov), "same_verdict": same, "different": len(ov) - same, "examples": diffs[:10]}
    md.append(f"## 6. 이전 v1.2 실행과 겹치는 쌍 (비교만)\n\n- 이전 기록 {len(prev)}쌍 중 (생성 식, 기준 식)이 같은 쌍 {len(ov)}개. 역할과 사유가 같은 쌍 {same}개, 다른 쌍 {len(ov) - same}개." + ("" if len(ov) == same else f" 다른 예: {diffs[:5]}") + "\n")
else:
    R["previous_run"] = None
    md.append("## 6. 이전 v1.2 실행과 겹치는 쌍\n\n이전 기록 파일을 찾지 못함(확인하지 못함).\n")
open(a.out_md, "w", encoding="utf-8").write("\n".join(md))
json.dump(R, open(a.out_json, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print("checks written:", a.out_md, "| records", len(recs), "| missing", len(missing), "| extra", len(extra), "| determinism violations", len(viol), "| frozen headers ok", ok_h)
