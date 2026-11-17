#!/usr/bin/env python3
"""Rule semantics checks against the OFFICIAL FRET parser. A tool rule that maps a template phrase to a FRETish construct is only as good as the claim that the construct means the same.
Where the claim is an EQUIVALENCE between two FRETish forms (e.g. `unless p` and `if !(p)`), the parser's own past-time LTL for both is compared with the judge engine (role SAME = equivalent).
usage: python3 tools/rule_semantics_check.py --parser node|docker --engine z3|nusmv [--nusmv NuSMV] --out data/rule_semantics_results.json
(node: env NL2FRET_NODE_PARSER and NODE_PATH as in fret_check/tools/fret_compile.py)"""
import argparse, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
ROOT = os.path.dirname(BENCH)
sys.path.insert(0, os.path.join(BENCH, "fret_check", "tools"))
sys.path.insert(0, os.path.join(ROOT, "judging"))
import fret_compile                                  # noqa: E402
from nl2fret_judge.judge import judge_pair          # noqa: E402
from nl2fret_judge.engines import NuSMVEngine, Z3Engine   # noqa: E402

S = "the s shall"
CHECKS = [
    # id, claim, left FRETish, right FRETish
    ("S1a", "upon, when, if, where give the same requirement (timing immediately)", [f"{k} p {S} immediately satisfy q" for k in ("upon", "when", "if", "where")]),
    ("S1b", "upon, when, if, where give the same requirement (timing eventually)", [f"{k} p {S} eventually satisfy q" for k in ("upon", "when", "if", "where")]),
    ("S1c", "upon, when, if, where give the same requirement (timing within)", [f"{k} p {S} within 3 ticks satisfy q" for k in ("upon", "when", "if", "where")]),
    ("S2", "`unless p` is `if !(p)`", [f"unless p {S} immediately satisfy q", f"if !(p) {S} immediately satisfy q"]),
    ("S3", "`whenever p ... immediately r` is `always satisfy p => r`", [f"whenever p {S} immediately satisfy q", f"{S} always satisfy p => q"]),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parser", default="node", choices=["node", "docker"])
    ap.add_argument("--engine", default="z3", choices=["z3", "nusmv"])
    ap.add_argument("--nusmv", default="NuSMV")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    eng = Z3Engine(8) if a.engine == "z3" else NuSMVEngine(a.nusmv.split(), timeout=120, workdir="/tmp/rsc_work")
    texts = sorted({t for _, _, ts in CHECKS for t in ts})
    comp = {r["fretish"]: r for r in fret_compile.compile_list(texts, backend=a.parser)}
    res = {}
    for cid, claim, ts in CHECKS:
        ref = comp[ts[0]]
        ok = bool(ref["ok"])
        rows = []
        for t in ts[1:]:
            c = comp[t]
            if not (ok and c["ok"]):
                ok = False
                rows.append({"text": t, "role": None, "identical_ltl": None})
                continue
            same_str = c["ltl_pt"] == ref["ltl_pt"]
            r = judge_pair(c["ltl_pt"], ref["ltl_pt"], eng, aux=False, pair_id=cid)
            rows.append({"text": t, "ltl_pt": c["ltl_pt"], "identical_ltl": same_str, "role": r.get("role")})
            ok = ok and r.get("role") == "SAME"
        res[cid] = {"claim": claim, "reference_form": ts[0], "reference_ltl_pt": ref.get("ltl_pt"), "compared": rows, "pass": ok}
        print(cid, "PASS" if ok else "FAIL", claim)
    json.dump({"engine": eng.name, "parser": a.parser, "checks": res}, open(a.out, "w"), indent=1, ensure_ascii=False)
    sys.exit(0 if all(v["pass"] for v in res.values()) else 1)


if __name__ == "__main__":
    main()
