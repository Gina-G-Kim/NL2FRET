#!/usr/bin/env python3
"""Scoring and failure records of v3. No model call.

  python3 -I score3.py build   --results results_nl3 [--data data/lm_items.jsonl]    -> units_v3.jsonl, variants.jsonl   (before the realizability check)
  python3 -I score3.py final   --results results_nl3 [--data ...]                    -> units_scored.jsonl               (after fret_check/check.py single)

Unit = item x arm x repetition. Variants of one unit:
  v0  first answer of the arm (no feedback)
  vn  first answer after the mechanical syntax normalizer (fretlint.normalize_fretish; structure untouched)
  vf  answer after the feedback rounds from the official parser (identical to v0 when no sentence was rejected)
Unified failure (the user's definition, kept from the run 2 report): a unit fails when it is not realizable. In the denominator of every rate is EVERY unit. The status of a
unit is the worst of its sentences: pipeline > parse_error > not_run > unknown > unrealizable > realizable. 'pipeline' collects every reason for which no FRETish
sentence set exists (stage A failed, template not readable by the script, slot lint, rule without mapping, call failed, no output); the code says which.
"""
import argparse
import collections
import json
import os
import re
import sys

import fretlint as L
import fretparse
import prompts3 as P
import units3 as U
from common import (best_alignment, field_matches, fretish_parse, load_jsonl, struct_key)

ORDER = ["pipeline", "parse_error", "not_run", "unknown", "unrealizable", "realizable"]
CORE = ["scope_class", "cond_present", "component", "timing", "response"]
VARS = ["v0", "vn", "vf"]


def paths(a):
    res = a.results if os.path.isabs(a.results) else os.path.join(os.path.dirname(os.path.abspath(__file__)), a.results)
    data = a.data if os.path.isabs(a.data) else os.path.join(os.path.dirname(os.path.abspath(__file__)), a.data)
    return res, data


def tokens_of(rows, iid, arm, rep, stages):
    t = {}
    for st in stages:
        r = rows.get(U.skey(iid, arm, rep, st))
        if r:
            t[st] = r.get("total_tokens") or 0
    return t


def core_score(texts, gt_list):
    if not texts:
        return 0.0, {k: 0.0 for k in CORE}
    gparsed = [fretish_parse(g) for g in gt_list]
    out = [fretish_parse(t) for t in texts]
    pairs = best_alignment(texts, gt_list)
    fm = []
    for oi, gi in pairs:
        fm.append(field_matches(out[oi], gparsed[gi]) if oi is not None else {k: False for k in CORE})
    per = {k: sum(1 for m in fm if m[k]) / len(fm) for k in CORE}
    return sum(per.values()) / len(CORE), per


def numbers_in(s):
    return collections.Counter(re.findall(r"\d+(?:\.\d+)?", s or ""))


def build(a):
    res, data = paths(a)
    items = load_jsonl(data)
    rows = {r["stage_key"]: r for r in load_jsonl(os.path.join(res, "calls.jsonl"))}
    comp = fretparse._load_cache(os.path.join(res, "parser_cache.jsonl"))
    reps = sorted({int(k.split("|")[2]) for k in rows})
    st_path = os.path.join(res, "run_state.json")
    arms_run = json.load(open(st_path))["arms"] if os.path.exists(st_path) else P.ARMS_MAIN
    out, var_rows = [], []
    for it in items:
        for arm in arms_run:
            for rep in reps:
                rec = U.derive(rows, it, arm, rep, comp)
                if rec["pending"]:
                    continue
                u = {"item_id": it["id"], "pid": it.get("pid"), "src": it.get("src"), "stratum": it.get("stratum"), "arm": arm, "rep": rep, "base": P.base_of(arm),
                     "n_rounds": len(rec["rounds"]) - 1}
                stages = ["A", U.first_stage(arm), "F1", "F2"] if not P.is_direct(arm) else ["D", "F1", "F2"]
                tk = tokens_of(rows, it["id"], arm, rep, stages)
                u["tokens_by_stage"] = tk
                u["tokens_total"] = sum(tk.values())
                u["wall_s"] = round(sum((rows.get(U.skey(it["id"], arm, rep, s)) or {}).get("wall_s", 0) for s in stages), 2)
                if rec["A"]:
                    u["A_sentences"] = rec["A"]["sentences"]
                    u["A_n"] = len(rec["A"]["sentences"])
                    u["conformance"] = rec.get("conformance")
                    u["conforms"] = bool(rec.get("conformance")) and all(c["ok"] for c in rec["conformance"])
                u["variants"] = {}
                for v in VARS:
                    stt, code, detail, texts = U.variant(rec, v)
                    if stt == "pending":
                        continue
                    rr = rec["rounds"][0] if (rec["rounds"] and v in ("v0", "vn")) else (rec["rounds"][-1] if rec["rounds"] else None)
                    all_texts = []
                    if rr:
                        for s in rr["sentences"]:
                            tx = s.get("norm_text") if (v == "vn" and s.get("norm_text")) else s.get("text")
                            if tx:
                                all_texts.append(tx)
                    core, per = core_score(all_texts, it["gt_list"])
                    nums_raw = numbers_in(it["raw_nl"])
                    nums_out = numbers_in(" ".join(all_texts))
                    dropped = sum((nums_raw - nums_out).values())
                    u["variants"][v] = {"pre": stt, "code": code, "detail": detail[:400], "texts": all_texts, "accepted_texts": texts, "core": round(core, 4),
                                        "core_fields": {k: round(x, 3) for k, x in per.items()}, "numbers_dropped": dropped, "numbers_in_raw": sum(nums_raw.values()),
                                        "norm_rules": sorted({r for s in (rr["sentences"] if rr else []) for r in (s.get("norm_rules") or [])}) if v == "vn" else [],
                                        "rules": sorted({r for s in (rr["sentences"] if rr else []) for r in (s.get("rules") or [])}),
                                        "slot_fixes": sorted({r for s in (rr["sentences"] if rr else []) for r in (s.get("slot_fixes") or [])})}
                    if stt == "parsed" and texts:
                        var_rows.append({"item_id": it["id"], "arm": f"{arm}#{v}", "rep": rep, "fretish": texts})
                    # official rejections of this variant, per sentence (appendix material)
                    rej = []
                    if rr:
                        for s in rr["sentences"]:
                            o = s.get("norm_official") if v == "vn" else s.get("official")
                            if o and not o["ok"]:
                                rej.append({"cls": o["cls"], "grp": o["grp"], "error": (o["error"] or "")[:300]})
                    u["variants"][v]["rejections"] = rej
                if rec["rounds"]:
                    u["unmapped_first"] = rec["rounds"][0].get("unmapped", [])
                out.append(u)
    with open(os.path.join(res, "units_v3.jsonl"), "w", encoding="utf-8") as f:
        for u in out:
            f.write(json.dumps(u, ensure_ascii=False) + "\n")
    with open(os.path.join(res, "variants.jsonl"), "w", encoding="utf-8") as f:
        for r in var_rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("units", len(out), "variant rows for the realizability check", len(var_rows), "distinct sentences", len({t for r in var_rows for t in r["fretish"]}))


def final(a):
    res, data = paths(a)
    units = load_jsonl(os.path.join(res, "units_v3.jsonl"))
    rz = [r for r in load_jsonl(os.path.join(res, "fret_realizability.jsonl")) if r.get("kind") == "gen" and r.get("mode") == "single_requirement"]
    by = collections.defaultdict(list)
    for r in rz:
        by[(r["item_id"], r["arm"], r["rep"])].append(r)
    out = []
    for u in units:
        u = dict(u)
        for v, d in u["variants"].items():
            if d["pre"] == "pipeline":
                d["status"], d["fail_stage"] = "pipeline", "pipeline"
            elif d["pre"] == "parse_error":
                d["status"], d["fail_stage"] = "parse_error", "parser"
            else:
                rs = by.get((u["item_id"], f"{u['arm']}#{v}", u["rep"]), [])
                if not rs:
                    d["status"], d["fail_stage"] = "not_run", "realizability"
                    d["code"], d["detail"] = "no_fret_row", "no realizability row for this unit"
                else:
                    ss = [r["result"] for r in rs]
                    d["status"] = next(o for o in ORDER if o in ss)
                    d["fail_stage"] = None if d["status"] == "realizable" else "realizability"
                    if d["status"] != "realizable":
                        bad = [r for r in rs if r["result"] == d["status"]][0]
                        d["code"], d["detail"] = d["status"], str(bad.get("detail"))[:300]
            d["failed"] = d["status"] != "realizable"
        out.append(u)
    with open(os.path.join(res, "units_scored.jsonl"), "w", encoding="utf-8") as f:
        for u in out:
            f.write(json.dumps(u, ensure_ascii=False) + "\n")
    c = collections.Counter((u["arm"], u["variants"]["vf"]["status"]) for u in out if "vf" in u["variants"])
    print("units", len(out))
    for arm in P.ARMS3:
        tot = sum(v for (a_, s), v in c.items() if a_ == arm)
        if tot:
            print(f"{arm:16s} n={tot:4d} " + " ".join(f"{s}={c.get((arm, s), 0)}" for s in ORDER))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "final"])
    ap.add_argument("--results", default="results_nl3")
    ap.add_argument("--data", default="data/lm_items.jsonl")
    a = ap.parse_args()
    build(a) if a.cmd == "build" else final(a)
