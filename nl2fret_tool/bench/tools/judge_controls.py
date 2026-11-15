#!/usr/bin/env python3
"""Judge controls (instrument validity). The judge is run on pairs whose correct role is known by construction, using only the reference formulas.

Positive controls (a correct spec in another form: expected SAME; any other role is a FALSE FAILURE of the instrument):
  C+ID   the reference formula itself
  C+NN   !(!(f))
  C+AND  (f) & (f)
Negative controls (expected NOT success; SAME or PROOF is a FALSE SUCCESS of the instrument):
  C-TAUT  (f) | !(f)    valid formula, weaker than every reference
  C-CONTR (f) & !(f)    unsatisfiable formula, stronger than every reference (PROOF risk: the judge's success = SAME or PROOF)
  C-NEG   !(f)
  C-SHIFT the formula of reference part k judged against part k+1 of the same item (cyclic), items with >= 2 parts, all versions, best role kept.
          Two parts of an item are different requirements. Informational: some parts can be legitimately equivalent or implied.
Output: controls.jsonl (one judge record per control pair) and controls.md. Run with --engine z3 (sandbox, bounded horizon) or --engine nusmv (final numbers).
"""
import argparse, json, os, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "judging"))
from nl2fret_judge.judge import judge_pair          # noqa: E402
from nl2fret_judge.engines import NuSMVEngine, Z3Engine   # noqa: E402
from nl2fret_judge import parts as PT               # noqa: E402

ORDER = PT.ORDER
SUCCESS = PT.SUCCESS


def role(r):
    return r.get("role") or ("NM" if r.get("nm") else "UND")


def variants(f):
    return {"C+ID": f, "C+NN": f"(! (! ({f})))", "C+AND": f"(({f}) & ({f}))",
            "C-TAUT": f"(({f}) | (! ({f})))", "C-CONTR": f"(({f}) & (! ({f})))", "C-NEG": f"(! ({f}))"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", default=os.path.join(ROOT, "data/reference/lm_reference_with_ltl.jsonl"))
    ap.add_argument("--engine", choices=["z3", "nusmv"], default="z3")
    ap.add_argument("--nusmv", default="NuSMV")
    ap.add_argument("--horizon", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=120)
    ap.add_argument("--cap", type=int, default=128, help="converter window cap (judge default 128)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", help="comma separated item ids")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    eng = Z3Engine(a.horizon) if a.engine == "z3" else NuSMVEngine(a.nusmv.split(), timeout=a.timeout, workdir=os.path.join(a.out, "work"))
    refs = PT.load_reference_parts(a.reference)
    only = set(a.only.split(",")) if a.only else None
    fo = open(os.path.join(a.out, "controls.jsonl"), "w", encoding="utf-8")
    res = collections.defaultdict(lambda: collections.Counter())
    n = 0
    for item, ref in refs.items():
        if only and item not in only:
            continue
        for pi, versions in enumerate(ref["parts"], 1):
            for vi, (rid, pt, ft) in enumerate(versions, 1):
                if not pt:
                    continue
                for name, g in variants(pt).items():
                    r = judge_pair(g, pt, eng, cap=a.cap, aux=True, pair_id=f"{item}|{name}|p{pi}|v{vi}", meta={"group": "control", "mutation": name})
                    r.pop("_smv", None)
                    r.update({"item": item, "control": name, "part": pi, "version": vi, "reference_id": rid})
                    fo.write(json.dumps(r, ensure_ascii=False) + "\n")
                    res[name][role(r)] += 1
                    n += 1
        parts = ref["parts"]
        if len(parts) >= 2:
            for pi, versions in enumerate(parts, 1):
                other = parts[pi % len(parts)]
                best = None
                for vi, (rid, pt, ft) in enumerate(versions, 1):
                    for vj, (rid2, pt2, ft2) in enumerate(other, 1):
                        if not pt or not pt2:
                            continue
                        r = judge_pair(pt, pt2, eng, cap=a.cap, aux=True, pair_id=f"{item}|C-SHIFT|p{pi}|v{vi}|w{vj}", meta={"group": "control", "mutation": "C-SHIFT"})
                        r.pop("_smv", None)
                        r.update({"item": item, "control": "C-SHIFT", "part": pi, "version": vi, "reference_id": rid, "against": rid2})
                        fo.write(json.dumps(r, ensure_ascii=False) + "\n")
                        n += 1
                        if best is None or ORDER[("NM" if role(r) == "NM" else role(r))] < ORDER[best]:
                            best = role(r)
                if best:
                    res["C-SHIFT"][best] += 1
        print(item, n, flush=True)
    fo.close()
    exp = {"C+ID": "SAME", "C+NN": "SAME", "C+AND": "SAME"}
    lines = ["# Judge controls", "", f"engine: {eng.name}; reference rows judged per control; roles per control (count)", "",
             "| control | n | SAME | PROOF | REFUTE | NEITHER | NM | UND | rate flagged as instrument error |", "|---|---|---|---|---|---|---|---|---|"]
    summary = {}
    for name in ["C+ID", "C+NN", "C+AND", "C-TAUT", "C-CONTR", "C-NEG", "C-SHIFT"]:
        c = res[name]
        tot = sum(c.values())
        if not tot:
            continue
        if name.startswith("C+"):
            bad, lab = tot - c["SAME"], "false failure (not SAME)"
        else:
            bad, lab = c["SAME"] + c["PROOF"], "false success (SAME or PROOF)"
        summary[name] = {"n": tot, "roles": dict(c), "flag": lab, "flag_count": bad, "flag_rate": round(bad / tot, 4)}
        lines.append(f"| {name} | {tot} | {c['SAME']} | {c['PROOF']} | {c['REFUTE']} | {c['NEITHER']} | {c['NM']} | {c['UND']} | {bad}/{tot} = {bad / tot:.3f} ({lab}) |")
    open(os.path.join(a.out, "controls.md"), "w").write("\n".join(lines) + "\n")
    json.dump(summary, open(os.path.join(a.out, "controls_summary.json"), "w"), indent=1)
    print("\n".join(lines))


if __name__ == "__main__":
    main()
