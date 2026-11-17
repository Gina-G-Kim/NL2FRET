#!/usr/bin/env python3
"""Challenge level realizability (auxiliary metric of v2.0). The final FRETish sentences that one approach produced for ALL requirements of a challenge in one repetition are checked as ONE
requirement set of one software component with the FRET realizability check (fretCLI realizability, kind2, docker image fret-lab). The reference FRETish of the same challenge is checked the same
way as the baseline of the set. The result never feeds back to the conversion and never changes a sentence level judgment.

usage (from bench/, with python3 -I):
  python3 fret_check/group_rlz.py --inputs RUN/inputs --reference ../data/reference/lm_reference_with_ltl.jsonl --out RUN/group_rlz.jsonl [--only-challenge 01_FSM] [--dry-run]
Rules (assumptions of the bench, fixed before any run; same policy file as the single sentence check, variable_policy.md)
  * set = the sentences accepted by the official parser in the units of (approach, challenge, repetition); sentences with a user defined function application cannot be modelled and are left out (counted)
  * one component name for the whole set; one variable table for the whole set built from the set's own sentences only (generated sets never read the reference)
  * the reference set uses the first reference version of every part
Result values: realizable, unrealizable, unknown (CLI printed ERROR/UNKNOWN or no usable JSON), empty (no sentence left), not_run (--dry-run).
Input normalization N-LIT (docs/V20_BATCH_DESIGN.md 7.1): every set is checked twice when integer literals can be converted: as written (raw) and with the integer literals that share an arithmetic
expression or comparison with a double variable written as real literals (normalized; tools/litnorm.py). Columns: result_raw (= result), result_normalized, cli_result_raw, cli_result_normalized,
n_literals_converted, n_sentences_changed, type_changes (variables whose table type differs between the two tables). The sentences of the judge and of the model are never changed.
Primary and secondary (docs/V20_BATCH_DESIGN.md 7.4): `result` and `raw_result` (and fret_mode, time_s, wall_s, rc, error) are those of the NORMALIZED check (primary); the raw check is kept in
result_raw, cli_result_raw and error_raw (secondary). A set without a convertible literal is checked once and both are the same.
"""
import argparse
import copy
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
from nl2fret.fret_check.tools import fret_rlz as F
from nl2fret.fret_check.tools import litnorm

COMP = "SYS"


def sha(s):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:10]


def jl(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def set_job(tag, texts, comp):
    """-> (job or None, info). comp: {text: compile result with sem}"""
    keep, excluded, rejected = [], [], []
    for t in dict.fromkeys(texts):
        r = comp[t]
        if not r["ok"]:
            rejected.append(t)
            continue
        info = F.sentence_info(r)
        if info["funcs"]:
            excluded.append(t)
            continue
        keep.append(t)
    meta = {"n_sentences": len(keep), "n_excluded_function": len(excluded), "n_rejected": len(rejected)}
    if not keep:
        return None, meta
    table = F.build_table(tag, [{"text": t, "res": comp[t], "kind": "gen"} for t in keep])
    items = []
    for i, t in enumerate(keep, 1):
        sem = copy.deepcopy(comp[t]["sem"])
        sem["component_name"] = COMP
        items.append((f"R{i}", t, sem))
    proj = "G" + sha(tag + "".join(keep))
    reqs, vd = F.docs_for(proj, COMP, items, table)
    meta["_table"] = {v: t.get("dataType") for v, t in table["variables"].items()}
    return {"project": proj, "comp": COMP, "reqs": reqs, "vdocs": vd}, meta


def keep_texts(texts, comp):
    """the sentences of a set that enter the job (accepted by the parser, no user defined function), in order, without duplicates"""
    out = []
    for t in dict.fromkeys(texts):
        r = comp[t]
        if r["ok"] and not F.sentence_info(r)["funcs"]:
            out.append(t)
    return out


def double_vars(tag, keep, comp):
    table = F.build_table(tag, [{"text": t, "res": comp[t], "kind": "gen"} for t in keep])
    return {v for v, t in table["variables"].items() if t.get("dataType") == "double"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", required=True, help="folder written by tools/make_judge_inputs.py (units.json)")
    ap.add_argument("--reference", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only-challenge", nargs="*")
    ap.add_argument("--parser", default="docker", choices=["docker", "node"])
    ap.add_argument("--procs", type=int, default=2)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    refs = jl(a.reference)
    chal_of = {r["id"]: r["challenge"] for r in refs}
    units = json.load(open(os.path.join(a.inputs, "units.json"), encoding="utf-8"))["units"]
    groups = {}
    for u in units:
        ch = chal_of.get(u["item"])
        if ch is None or (a.only_challenge and ch not in a.only_challenge):
            continue
        g = groups.setdefault((u["arm"], ch, u["rep"]), {"texts": [], "n_units": 0, "n_units_no_text": 0})
        g["n_units"] += 1
        g["texts"] += u["texts"]
        g["n_units_no_text"] += 0 if u["texts"] else 1
    for r in refs:
        if a.only_challenge and r["challenge"] not in a.only_challenge:
            continue
        g = groups.setdefault(("REFERENCE", r["challenge"], None), {"texts": [], "n_units": 0, "n_units_no_text": 0})
        g["n_units"] += 1
        g["texts"] += [part[0]["fretish"] for part in r["gt_parts"] if part]
    alltexts = list(dict.fromkeys(t for g in groups.values() for t in g["texts"]))
    from nl2fret.fret_check.tools import fret_compile
    comp = {r["fretish"]: r for r in fret_compile.compile_list(alltexts, backend=a.parser)} if alltexts else {}
    # N-LIT: normalized texts per set (the same sentences, integer literals written as real literals where they share an expression with a double variable)
    norm = {}
    for (arm, ch, rep), g in groups.items():
        tag = f"{arm}|{ch}|{rep}"
        keep = keep_texts(g["texts"], comp)
        if not keep:
            continue
        dv = double_vars(tag, keep, comp)
        new, n_conv, n_chg = {}, 0, 0
        for t in keep:
            nt, n = litnorm.normalize_sentence(t, comp[t]["sem"], dv)
            new[t] = nt
            n_conv += n
            n_chg += 1 if n else 0
        norm[(arm, ch, rep)] = {"texts": new, "n_conv": n_conv, "n_chg": n_chg}
    new_texts = list(dict.fromkeys(nt for v in norm.values() if v["n_conv"] for nt in v["texts"].values() if nt not in comp))
    if new_texts:
        for r in fret_compile.compile_list(new_texts, backend=a.parser):
            comp[r["fretish"]] = r
    jobs, rows, norm_jobs = [], [], {}
    for (arm, ch, rep), g in sorted(groups.items(), key=lambda x: (x[0][1], x[0][0], x[0][2] if x[0][2] is not None else -1)):
        job, meta = set_job(f"{arm}|{ch}|{rep}", g["texts"], comp)
        raw_types = meta.pop("_table", None)
        row = {"arm": arm, "challenge": ch, "rep": rep, "n_units": g["n_units"], "n_units_no_text": g["n_units_no_text"], **meta, "result": "empty" if job is None else "not_run"}
        nm = norm.get((arm, ch, rep))
        row["n_literals_converted"] = nm["n_conv"] if nm else 0
        row["n_sentences_changed"] = nm["n_chg"] if nm else 0
        row["type_changes"] = {}
        if job is not None:
            row["project"] = job["project"]
            jobs.append(job)
            if nm and nm["n_conv"]:
                ntexts = [nm["texts"][t] for t in dict.fromkeys(g["texts"]) if t in nm["texts"]]
                job2, meta2 = set_job(f"{arm}|{ch}|{rep}|norm", ntexts, comp)
                if job2 is not None:
                    tt = meta2.pop("_table", {})
                    row["type_changes"] = {v: [raw_types.get(v), tt.get(v)] for v in sorted(set(raw_types) | set(tt)) if raw_types.get(v) != tt.get(v)}
                    row["project_normalized"] = job2["project"]
                    jobs.append(job2)
        rows.append(row)
    res = {}
    if not a.dry_run and jobs:
        for i in range(0, len(jobs), 40):
            r = F.run_batch(f"grp{i // 40:03d}", jobs[i:i + 40])
            r.pop("_batch_wall_s", None)
            res.update(r)
        for row in rows:
            r = res.get(row.get("project"))
            if r is not None:
                row.update({"result": r["result"], "raw_result": r.get("raw_result"), "fret_mode": r.get("mode"), "time_s": r.get("time_s"), "wall_s": r.get("wall_s"), "rc": r.get("rc"),
                            "error": r.get("error") or r.get("tail")})
            elif row["result"] == "not_run":
                row["result"] = "unknown"
                row["error"] = "no result returned by the container"
    for row in rows:       # raw and normalized columns (a set without a convertible literal is checked once: normalized = raw); the primary columns are the normalized ones
        row["result_raw"], row["cli_result_raw"], row["error_raw"] = row["result"], row.get("raw_result"), row.get("error")
        pn = row.get("project_normalized")
        if pn and not a.dry_run:
            r2 = res.get(pn)
            row["result_normalized"] = r2["result"] if r2 else "unknown"
            row["cli_result_normalized"] = r2.get("raw_result") if r2 else None
            if r2:
                row.update({"fret_mode": r2.get("mode"), "time_s": r2.get("time_s"), "wall_s": r2.get("wall_s"), "rc": r2.get("rc"), "error": r2.get("error") or r2.get("tail")})
        elif pn:
            row["result_normalized"], row["cli_result_normalized"] = "not_run", None
        else:
            row["result_normalized"], row["cli_result_normalized"] = row["result"], row.get("raw_result")
        row["result"], row["raw_result"] = row["result_normalized"], row["cli_result_normalized"]
    with open(a.out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(rows)} sets ({len(jobs)} jobs) -> {a.out}")


if __name__ == "__main__":
    main()
