#!/usr/bin/env python3
"""v3: realizability verdicts of the official FRET toolchain for the sentences that the official PARSER accepted. Records only; nothing is fed back.

usage (from the bench folder, with python3 -I):
  python3 -I fret_check/check.py single [--results results_nl3] [--procs 3]
Reads results_nl3/variants.jsonl (written by `score3.py build`: one row per unit and variant v0 / vn / vf with the parser-accepted sentences, arm name "ARM#variant"),
runs every DISTINCT sentence once, and writes results_nl3/fret_realizability.jsonl (reference rows of every item first, then generated sentences) and fret_ltl.jsonl.

FRET is not installed as a desktop app. It lives in the docker image fret-lab (see FRET_NOTES.md). The helper pieces (fret_compile.py, fret_rlz.py, fretexpr.py,
fret_import.js, fretjs/) are the ones of run 2. The variable table is built for every sentence by ONE rule (variable_policy.md) that never looks at the reference.
"""
import argparse
import collections
import concurrent.futures as cf
import copy
import datetime as dt
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "tools"))
import fret_rlz as F  # noqa: E402

ROOT = os.path.dirname(HERE)
SET_CAP_S = 300          # one set check: agent wall cap 5 min


def now():
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def jl(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def detail_of(r):
    """Original FRET message as far as the CLI gives one."""
    if r.get("tail"):
        return f"{r.get('detail')}: {r['tail']}"
    err = r.get("error")
    raw = r.get("raw_result")
    return f"raw_result={raw}; error={json.dumps(err, ensure_ascii=False) if err else None}"


def table_of(text, res):
    """One table per sentence, built from this sentence only (never from the reference)."""
    return F.build_table("S", [{"text": text, "res": res, "kind": "gen"}])


def single_job(text, res):
    """Returns (job, None) or (None, (verdict, reason))."""
    if not res["ok"]:
        return None, ("parse_error", str(res["error"])[:300])
    info = F.sentence_info(res)
    if info["funcs"]:
        return None, ("not_run", "user defined function application not mappable: " + ",".join(sorted(info["funcs"])))
    sem = res["sem"]
    proj = "S" + F.sha(text)
    cname = sem.get("component_name") or "component"
    reqs, vd = F.docs_for(proj, cname, [("R1", text, sem)], table_of(text, res))
    return {"project": proj, "comp": cname, "reqs": reqs, "vdocs": vd}, None


def run_parallel(batch, jobs, procs, per=60):
    chunks = [jobs[i:i + per] for i in range(0, len(jobs), per)]
    results = {}
    with cf.ThreadPoolExecutor(max_workers=procs) as ex:
        futs = {ex.submit(F.run_batch, f"{batch}{i:03d}", ch, SET_CAP_S): i for i, ch in enumerate(chunks)}
        for fu in cf.as_completed(futs):
            r = fu.result()
            r.pop("_batch_wall_s", None)
            results.update(r)
            print(now(), f"{batch} chunk {futs[fu]} done; results so far {len(results)}/{len(jobs)}", flush=True)
    return results


def verdict_row(r):
    """result and detail of a container result; rc 124 is the 5 minute wall cap (timeout), reported as not_run for sets and unknown for singles."""
    return r["result"], detail_of(r)


def inventory(items, units):
    """Generated sentences (kind gen) and every reference FRETish version of every item (kind gt). Both go through the same single-requirement check."""
    inv = []
    src = {d["id"]: d["src"] for d in items}
    for d in items:
        for pi, part in enumerate(d["gt_parts"]):
            for vi, v in enumerate(part):
                inv.append({"item": d["id"], "src": d["src"], "arm": "GT", "rep": None, "idx": f"{pi}.{vi}", "text": v["fretish"], "kind": "gt", "gt_ref": v["reqid"]})
    for u in units:
        f = u.get("fretish") or []
        for k, t in enumerate(f if isinstance(f, list) else [f]):
            inv.append({"item": u["item_id"], "src": src[u["item_id"]], "arm": u["arm"], "rep": u["rep"], "idx": k, "text": t, "kind": "gen"})
    return inv


def run_single(inv, comp, procs):
    jobs, skipped, seen = [], {}, set()
    for s in inv:
        t = s["text"]
        if t in seen:
            continue
        seen.add(t)
        job, sk = single_job(t, comp[t])
        if job:
            jobs.append(job)
        else:
            skipped[t] = sk
    print(now(), f"single jobs {len(jobs)}; decided before FRET {len(skipped)}", flush=True)
    res = run_parallel("single", jobs, procs)
    rows = []
    for s in inv:
        t = s["text"]
        base = {"item_id": s["item"], "arm": s["arm"], "rep": s["rep"], "sentence_idx": s["idx"], "kind": s["kind"], "mode": "single_requirement",
                "sentence_sha": F.sha(t), "sentence": t, "gt_ref": s.get("gt_ref"), "fret_ts": now()}
        if t in skipped:
            v, why = skipped[t]
            rows.append({**base, "result": v, "detail": why})
            continue
        r = res.get("S" + F.sha(t))
        if r is None:
            rows.append({**base, "result": "not_run", "detail": "no result returned by the container"})
        else:
            v, why = verdict_row(r)
            rows.append({**base, "result": v, "detail": why, "raw_result": r.get("raw_result"), "fret_mode": r.get("mode"), "time_s": r.get("time_s"), "wall_s": r.get("wall_s"),
                         "rc": r.get("rc"), "n_cc": r.get("n_cc")})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage", choices=["single"])
    ap.add_argument("--results", default=os.path.join(ROOT, "results_lm"))
    ap.add_argument("--data", default=os.path.join(ROOT, "data/lm_items.jsonl"))
    ap.add_argument("--procs", type=int, default=3)
    ap.add_argument("--out", default=None)
    ap.add_argument("--type-policy", choices=["literal", "double"], default="literal", help="probe: double = every numeric variable is typed double (see variable_policy.md)")
    a = ap.parse_args()
    F.TYPE_POLICY = a.type_policy
    items = jl(a.data)
    units = jl(os.path.join(a.results, "variants.jsonl"))
    inv = inventory(items, units)
    comp = F.compile_cached([s["text"] for s in inv])
    print(now(), f"{len(inv)} sentences, {len({s['text'] for s in inv})} distinct; official parser ok={sum(1 for t in {s['text'] for s in inv} if comp[t]['ok'])}", flush=True)
    # the official compile output of every distinct sentence (reference and generated): the LTL strings are what the judge reads later. No comparison is made here.
    ltl_out = os.path.join(a.results, "fret_ltl.jsonl")
    with open(ltl_out, "w", encoding="utf-8") as f:
        for t in sorted({s["text"] for s in inv}):
            c = comp[t]
            sem = c.get("sem") or {}
            f.write(json.dumps({"sentence": t, "parser_ok": bool(c["ok"]), "error": c.get("error"), "ltl_ft": c.get("ltl_ft"), "ltl_pt": c.get("ltl_pt"),
                                "scope": (sem.get("scope") or {}).get("type") if isinstance(sem.get("scope"), dict) else sem.get("scope"), "condition": sem.get("condition"),
                                "timing": sem.get("timing"), "response": sem.get("response"), "component": sem.get("component_name"),
                                "post_condition": sem.get("post_condition"), "variables": sem.get("variables")}, ensure_ascii=False) + "\n")
    print(now(), "wrote", ltl_out, flush=True)
    rows = run_single(inv, comp, a.procs)
    out = a.out or os.path.join(a.results, "fret_realizability.jsonl")
    with open(out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    for k, v in sorted(collections.Counter((r["mode"], r["arm"] == "GT", r["result"]) for r in rows).items()):
        print(k, v)
    print(now(), "wrote", out, len(rows))


if __name__ == "__main__":
    main()
