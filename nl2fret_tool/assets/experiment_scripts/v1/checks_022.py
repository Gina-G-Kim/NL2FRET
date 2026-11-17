#!/usr/bin/env python3
"""Checks of the 022 run that scripts/judge_checks.py (the 020 script, run per merged folder) does not cover. Read-only. Writes <out md> and <out json>.
usage: python3 -I -B checks_022.py --tool-dir T --pkg <bench/nl2fret_tool> --expected expected_pairs.json [--expected-swap expected_pairs_swap.json] --expect-code SHA --logs-dir <logs> --out-md F --out-json F
Checks per run (main, ctrl, alias_dictonly, swap when present): (1) headers of the four shards (frozen true, code_tree_sha256, mode anchor, cap 128, timeout 120, engine nusmv,
allow_unfrozen false, selfcheck passed, input hashes), (2) pair counts per shard and per run against the expected counts and pair sets, (3) time per shard and per run (console time
stamps, sum of pair times) and the NuSMV timeout pairs."""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys

sys.dont_write_bytecode = True

# tag -> (units file, ltl file) relative to the work tree of the tool
RUNS = {"main": ("inputs/dict/units.json", "inputs/dict/fret_ltl_gen.jsonl"),
        "ctrl": ("inputs/control/units_control.json", "inputs/dict/fret_ltl_gen.jsonl"),
        "alias_dictonly": ("inputs/alias/units_alias_subset.json", "inputs/dict_only/fret_ltl_gen_dict_only.jsonl"),
        "swap": ("inputs/swap/units_swap.json", "inputs/swap/fret_ltl_swap.jsonl")}
RLZ = "inputs/dict/fret_realizability_gen.jsonl"


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def md_table(headers, rows):
    out = ["| " + " | ".join(str(h) for h in headers) + " |", "|" + "---|" * len(headers)]
    for r in rows:
        out.append("| " + " | ".join("" if c is None else str(c) for c in r) + " |")
    return "\n".join(out)


def shard_stats(path):
    n, tsum, tmax, timeouts = 0, 0.0, 0.0, []
    with open(path, encoding="utf-8") as f:
        for ln in f:
            if not ln.strip():
                continue
            r = json.loads(ln)
            n += 1
            e = r.get("elapsed_sec_total") or 0.0
            tsum += e
            tmax = max(tmax, e)
            if r.get("nm_reason") == "timeout" or any(q.get("timed_out") for q in r.get("queries") or []):
                timeouts.append(r["pair_id"])
    return n, tsum, tmax, timeouts


def console_times(path):
    starts, exits = [], []
    if not os.path.exists(path):
        return starts, exits
    for ln in open(path, encoding="utf-8", errors="replace"):
        m = re.match(r"== judge_\S+ start .*\((\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\)", ln)
        if m:
            starts.append(m.group(1))
        m = re.match(r"== judge_\S+ exit (\d+) \((\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\)", ln)
        if m:
            exits.append((int(m.group(1)), m.group(2)))
    return starts, exits


def main():
    ap = argparse.ArgumentParser()
    for k in ("tool-dir", "pkg", "expected", "expect-code", "logs-dir", "out-md", "out-json"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--expected-swap")
    a = ap.parse_args()
    sys.path.insert(0, os.path.join(a.tool_dir, "judging"))
    from nl2fret_judge import units as U                                # noqa: E402  (frozen tool code, read-only import)
    exp = json.load(open(a.expected))
    if a.expected_swap and os.path.exists(a.expected_swap):
        exp.update(json.load(open(a.expected_swap)))
    rlz_hash = sha256_file(os.path.join(a.pkg, RLZ))
    R, md = {}, ["# 점검 (022)\n"]
    rows_h, rows_c, rows_t, to_all = [], [], [], {}
    f = "%Y-%m-%d %H:%M:%S"
    for tag, (units_rel, ltl_rel) in RUNS.items():
        merged = os.path.join(a.pkg, "runs", tag + "_merged")
        if not os.path.isdir(merged):
            rows_h.append([tag, "합친 폴더 없음"])
            continue
        hdr = json.load(open(os.path.join(merged, "run_header.json"), encoding="utf-8"))
        shards = (hdr.get("merged") or {}).get("shards_manifest", {}).get("shards") or []
        ltl_hash = sha256_file(os.path.join(a.pkg, ltl_rel))
        units = U.load_units(os.path.join(a.pkg, units_rel), os.path.join(a.pkg, ltl_rel), os.path.join(a.pkg, RLZ))
        want = {f"{u['item']}|{u['arm']}|{u['rep']}|{i}" for u in units for i, s in enumerate(u["sentences"]) if s["parser_ok"] and s["ltl_pt"]}
        got = set()
        with open(os.path.join(merged, "judge_records.jsonl"), encoding="utf-8") as fh:
            for ln in fh:
                if ln.strip():
                    got.add(json.loads(ln)["pair_id"])
        missing, extra = sorted(want - got), sorted(got - want)
        total_exp = exp.get(tag + "_total")
        rows_c.append([tag, len(got), total_exp if total_exp is not None else len(want), len(want), len(missing), len(extra), ", ".join(missing[:3] + extra[:3])])
        starts_all, ends_all, sum_all, timeouts = [], [], 0.0, []
        for k in range(1, 5):
            sh = json.load(open(os.path.join(merged, f"run_header_shard{k}.json"), encoding="utf-8"))
            man_sha = shards[k - 1]["sha256"] if len(shards) >= k else None
            ok = (sh.get("frozen") is True and sh.get("code_tree_sha256") == a.expect_code and sh.get("mode") == "anchor" and sh.get("cap") == 128 and sh.get("timeout") == 120
                  and sh.get("engine") == "nusmv" and (sh.get("inputs") or {}).get("units") == man_sha and (sh.get("inputs") or {}).get("ltl") == ltl_hash
                  and (sh.get("inputs") or {}).get("rlz") == rlz_hash and sh.get("allow_unfrozen") is False and sh.get("selfcheck_passed") is True)
            rows_h.append([tag, k, sh.get("mode"), sh.get("frozen"), sh.get("frozen_check"), (sh.get("code_tree_sha256") or "")[:12], sh.get("cap"), sh.get("timeout"), sh.get("started_at"), "예" if ok else "아니오"])
            n, tsum, tmax, to = shard_stats(os.path.join(a.pkg, "runs", tag, f"shard{k}", "judge_records.jsonl"))
            starts, exits = console_times(os.path.join(a.logs_dir, f"judge_{tag}_s{k}.console"))
            wall = None
            if starts and exits:
                wall = (dt.datetime.strptime(exits[-1][1], f) - dt.datetime.strptime(starts[0], f)).total_seconds()
                starts_all.append(starts[0])
                ends_all.append(exits[-1][1])
            exp_n = (exp.get(tag) or {}).get(str(k))
            rows_t.append([tag, k, n, exp_n, starts[0] if starts else "확인하지 못함", exits[-1][1] if exits else "확인하지 못함", f"{wall / 3600:.2f}" if wall is not None else "확인하지 못함",
                           f"{tsum / 3600:.2f}", f"{tmax:.1f}", len(to), len(starts), ",".join(str(x[0]) for x in exits)])
            sum_all += tsum
            timeouts += to
        to_all[tag] = timeouts
        if starts_all and ends_all:
            wall = (max(dt.datetime.strptime(x, f) for x in ends_all) - min(dt.datetime.strptime(x, f) for x in starts_all)).total_seconds()
            rows_t.append([tag, "실행 전체", "", "", min(starts_all), max(ends_all), f"{wall / 3600:.2f}", f"{sum_all / 3600:.2f}", "", len(timeouts), "", ""])
    R["headers"], R["counts"], R["time"], R["timeout_pairs"] = rows_h, rows_c, rows_t, to_all
    md.append("## 1. 헤더\n\n" + md_table(["실행", "분할", "mode", "frozen", "frozen_check", "code_tree_sha256", "cap", "timeout", "started_at",
                                          "기대와 같음(frozen, 코드 해시, 모드 anchor, cap, timeout, 엔진, 입력 해시, allow_unfrozen false, selfcheck)"], rows_h) + "\n")
    md.append("## 2. 쌍 수\n\n" + md_table(["실행", "기록 수(서로 다른 pair_id)", "기대(입력에서 센 값)", "입력에서 다시 센 쌍 수", "빠진 쌍", "기대에 없는 쌍", "예"], rows_c) + "\n")
    md.append("## 3. 소요 시간과 시간 초과\n\n" + md_table(["실행", "분할", "기록 수", "기대 쌍 수", "시작", "끝", "벽시계(시간)", "쌍 시간 합(시간)", "쌍 최대(초)", "시간 초과 쌍", "시작 횟수", "종료 코드"], rows_t) + "\n")
    for tag, to in to_all.items():
        md.append(f"- {tag}: 질의 시간 초과가 있는 쌍 {len(to)}개" + (": " + ", ".join(to[:60]) + (" ..." if len(to) > 60 else "") if to else "") + "\n")
    open(a.out_md, "w", encoding="utf-8").write("\n".join(md))
    json.dump(R, open(a.out_json, "w", encoding="utf-8"), indent=1, ensure_ascii=False, default=str)
    print("checks written:", a.out_md)


if __name__ == "__main__":
    main()
