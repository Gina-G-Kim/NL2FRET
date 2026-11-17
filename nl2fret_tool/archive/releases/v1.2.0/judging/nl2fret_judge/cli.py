"""Command line: python -m nl2fret_judge <selfcheck|judge|aggregate|release> ...   (run from the judging/ directory)"""
import argparse
import json
import os
import platform
import sys
import time

from . import __version__, aggregate as AG, freeze as FZ, selfcheck as SC, units as U
from .ap_check import RULE_ID
from .engines import NuSMVEngine, Z3Engine
from .judge import best_over_references
from .recorder import Recorder, sha256_file


def make_engine(a):
    if a.engine == "z3":
        return Z3Engine(a.horizon)
    return NuSMVEngine(a.nusmv.split(), timeout=a.timeout, workdir=os.path.join(a.out, "work"))


def common(p):
    p.add_argument("--engine", choices=["nusmv", "z3"], default="nusmv")
    p.add_argument("--nusmv", default="NuSMV", help="NuSMV command (docker wrapper allowed)")
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("--horizon", type=int, default=8, help="z3 engine only")
    p.add_argument("--out", required=True, help="record directory")


def cmd_selfcheck(a):
    eng = make_engine(a)
    ok, rows = SC.run(eng)
    os.makedirs(a.out, exist_ok=True)
    json.dump({"engine": eng.name, "ok": ok, "rows": rows}, open(os.path.join(a.out, "selfcheck.json"), "w"), indent=1)
    for r in rows:
        print(("PASS " if r["ok"] else "FAIL ") + r["case"], r["got"], r["role"])
    print("SELFCHECK", "PASSED" if ok else "FAILED")
    return 0 if ok else 2


def cmd_release(a):
    """Write JUDGE_FROZEN_MANIFEST.sha256 (hashes of the judging code). Refused when the manifest exists: a released tree is never released again."""
    try:
        path, entries, sha = FZ.write_manifest()
    except FileExistsError:
        print(f"refused: {FZ.MANIFEST_NAME} already exists; a released tree is not released again", file=sys.stderr)
        return 2
    print(f"released: {len(entries)} code files, {path}, manifest sha256 {sha}")
    return 0


def cmd_judge(a):
    fz = FZ.check_manifest()          # before anything is created: a refused run leaves no files behind
    if fz["status"] in ("mismatch", "invalid"):
        if not a.allow_unfrozen:
            print(f"refused: the judging code does not match {FZ.MANIFEST_NAME} ({FZ.describe(fz)}); pass --allow-unfrozen to run anyway "
                  "(the run header then records frozen=false)", file=sys.stderr)
            return 2
        print(f"warning: --allow-unfrozen, the judging code does not match {FZ.MANIFEST_NAME} ({FZ.describe(fz)}); the run header records frozen=false",
              file=sys.stderr, flush=True)
    eng = make_engine(a)
    ok, _ = SC.run(eng)
    if not ok and not a.skip_selfcheck:
        print("self check failed; engine not usable (use --skip-selfcheck only for debugging)")
        return 2
    refs = U.load_reference(a.reference)
    units = U.load_units(a.units, a.ltl, a.rlz)
    header = {"tool": "nl2fret_judge", "version": __version__, "engine": eng.name, "engine_version": getattr(eng, "version", lambda: None)(),
              "mode": a.mode, "cap": a.cap, "timeout": a.timeout, "aux": a.aux, "ap_rule": RULE_ID, "python": platform.python_version(),
              "inputs": {"units": sha256_file(a.units), "ltl": sha256_file(a.ltl), "rlz": sha256_file(a.rlz) if a.rlz else None,
                         "reference": sha256_file(a.reference)}, "selfcheck_passed": ok}
    header.update(FZ.provenance())          # v1.2.0: python_version, z3_version, code_sha256, code_tree_sha256, smv_template_id, query_templates
    header.update({"frozen": fz["status"] == "match" and not a.allow_unfrozen, "frozen_manifest_sha256": fz["manifest_sha256"], "frozen_check": fz["status"],
                   "allow_unfrozen": a.allow_unfrozen})
    if fz["diff"]:
        header["frozen_diff"] = fz["diff"]
    rec = Recorder(a.out, header)
    n = 0
    t0 = time.time()
    for u in units:
        for i, s in enumerate(u["sentences"]):
            pid = f"{u['item']}|{u['arm']}|{u['rep']}|{i}"
            if rec.has(pid) or not s["parser_ok"] or not s["ltl_pt"]:
                continue
            r = best_over_references(s["ltl_pt"], refs.get(u["item"], []), eng, mode=a.mode, cap=a.cap, aux=a.aux, pair_id=pid,
                                     meta={"group": "generated", "run_id": os.path.basename(os.path.abspath(a.out))}, gen_ft=s["ltl_ft"])
            if r is None:
                continue
            smv = r.pop("_smv", {})
            r["sentence"] = s["text"]
            rec.write(r, smv)
            n += 1
            if n % 25 == 0:
                print(f"{n} pairs, {time.time() - t0:.0f}s", flush=True)
    print("judged pairs written:", n)
    return 0


def cmd_aggregate(a):
    units = U.load_units(a.units, a.ltl, a.rlz)
    recs = AG.read_records(os.path.join(a.out, "judge_records.jsonl"))
    rows = AG.aggregate(units, recs)
    res = {"by_arm": AG.table(rows, "arm"), "by_stratum": AG.table(rows, "stratum"), "pair_outcomes": AG.nm_summary(recs)}
    json.dump(res, open(os.path.join(a.out, "aggregate.json"), "w"), indent=1, ensure_ascii=False)
    for r in res["by_arm"]:
        print(r)
    print(res["pair_outcomes"])
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(prog="nl2fret_judge")
    sp = p.add_subparsers(dest="cmd", required=True)
    s = sp.add_parser("selfcheck"); common(s); s.set_defaults(f=cmd_selfcheck)
    j = sp.add_parser("judge"); common(j)
    for k in ("units", "ltl"):
        j.add_argument("--" + k, required=True)
    j.add_argument("--rlz"); j.add_argument("--reference", default="../data/reference/lm_reference_with_ltl.jsonl")
    j.add_argument("--mode", default="anchor", choices=["anchor", "lex", "strict", "free"]); j.add_argument("--cap", type=int, default=128)
    j.add_argument("--aux", action="store_true"); j.add_argument("--skip-selfcheck", action="store_true")
    j.add_argument("--allow-unfrozen", action="store_true", help="run although the judging code differs from JUDGE_FROZEN_MANIFEST.sha256 (header: frozen=false)")
    j.set_defaults(f=cmd_judge)
    g = sp.add_parser("aggregate"); common(g)
    for k in ("units", "ltl"):
        g.add_argument("--" + k, required=True)
    g.add_argument("--rlz"); g.set_defaults(f=cmd_aggregate)
    r = sp.add_parser("release", help="write JUDGE_FROZEN_MANIFEST.sha256 (once)"); r.set_defaults(f=cmd_release)
    a = p.parse_args(argv)
    return a.f(a)


if __name__ == "__main__":
    sys.exit(main())
