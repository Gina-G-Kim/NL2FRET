#!/usr/bin/env python3
"""Semantic table of FRETish (condition kind x timing) forms, computed with the OFFICIAL FRET parser and the judge engine.
Purpose: the decision-point analyzer and the tool rules may only treat two forms as the same decision when this table says the LTL is equivalent (role SAME). Nothing here is hand-merged.
Every form is compared with every other form (generated-vs-reference direction: role of row form as generated, column form as reference).
usage: python3 tools/timing_semantics.py --parser node|docker --engine z3|nusmv [--nusmv NuSMV] --out data/timing_semantics.json"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); BENCH = os.path.dirname(HERE); ROOT = os.path.dirname(BENCH)
from nl2fret.fret_check.tools import fret_compile
from nl2fret_judge.judge import judge_pair           # noqa: E402
from nl2fret_judge.engines import NuSMVEngine, Z3Engine   # noqa: E402

S = "the s shall"
TIMINGS = {"omitted": "", "immediately": "immediately", "always": "always", "next": "at the next timepoint", "eventually": "eventually", "finally": "finally", "within3": "within 3 ticks"}
CONDS = {"whenever": "whenever p", "when": "when p", "none_impl": None}


def forms():
    f = {}
    for cn, c in CONDS.items():
        for tn, t in TIMINGS.items():
            if c is None:
                if tn in ("omitted", "immediately", "always", "next", "eventually", "finally", "within3"):
                    f[f"{cn}|{tn}"] = f"{S} {t + ' ' if t else ''}satisfy p => q"
            else:
                f[f"{cn}|{tn}"] = f"{c} {S} {t + ' ' if t else ''}satisfy q"
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parser", default="node", choices=["node", "docker"]); ap.add_argument("--engine", default="z3", choices=["z3", "nusmv"])
    ap.add_argument("--nusmv", default="NuSMV"); ap.add_argument("--out", required=True); ap.add_argument("--workdir")
    a = ap.parse_args()
    wd = a.workdir or os.path.join(os.path.dirname(os.path.abspath(a.out)), "ts_work")
    eng = Z3Engine(8) if a.engine == "z3" else NuSMVEngine(a.nusmv.split(), timeout=120, workdir=wd)
    F = forms(); comp = {k: r for k, r in zip(F, fret_compile.compile_list(list(F.values()), backend=a.parser))}
    ok = {k: c for k, c in comp.items() if c["ok"]}
    rejected = sorted(set(F) - set(ok))
    table = {}
    for g in ok:
        for r in ok:
            if g == r: continue
            res = judge_pair(ok[g]["ltl_pt"], ok[r]["ltl_pt"], eng, aux=False, pair_id=f"{g}__{r}")
            table[f"{g} vs {r}"] = res.get("role")
    classes = []
    for k in ok:
        for c in classes:
            if table.get(f"{k} vs {c[0]}") == "SAME": c.append(k); break
        else: classes.append([k])
    out = {"engine": eng.name, "forms": F, "ltl_pt": {k: v["ltl_pt"] for k, v in ok.items()}, "parser_rejected": rejected, "equivalence_classes": classes, "roles": table}
    json.dump(out, open(a.out, "w"), indent=1, ensure_ascii=False)
    print("parser rejected:", rejected)
    for c in classes: print("class:", c)
    ref = "none_impl|always"
    print(f"\nrole of each form (as generated) against reference form `{F[ref]}`:")
    for k in ok:
        if k != ref: print(f"  {k:24s} {table.get(f'{k} vs {ref}')}")

if __name__ == "__main__": main()
