#!/usr/bin/env python3
"""Version comparison of two analysed runs (same items, same 11 approaches) under the criteria fixed in docs/ANALYSIS_PLAN.md before any run.
usage: python3 tools/compare_runs.py --base RUN_A/analysis --new RUN_B/analysis [--out DIR]
Unit of inference = ITEM (parts and repetitions of one item are not independent). Per approach and item: rate = mean over repetitions x parts of the metric.
Test = exact one-sided sign test over the items whose rate changed (ties dropped), alpha 0.05. An approach 'passes' a metric when the new version is better in significantly more items.
Metrics: reading_same, ntiming_same (mechanism, H1) and strict (outcome, H2); lenient and SAME-only are reported, never gating."""
import argparse, collections, json, math, os


def jl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def metric(r, m):
    if m == "reading_same":
        return None if r["dp_diff"] is None else int("reading" not in r["dp_diff"])
    if m == "ntiming_same":
        return None if r["dp_diff"] is None else int("ntiming" not in r["dp_diff"])
    if m == "strict":
        return int(r["strict"])
    if m == "lenient":
        return int(r["lenient"])
    if m == "same_only":
        return int(r["role"] == "SAME")
    raise KeyError(m)


def per_item(rows, arm, m):
    d = collections.defaultdict(list)
    for r in rows:
        if r["arm"] != arm:
            continue
        v = metric(r, m)
        if v is None:
            v = 0                      # a part without a generated sentence counts as not agreeing (denominator = all parts)
        d[r["item"]].append(v)
    return {k: sum(v) / len(v) for k, v in d.items()}


def sign_p(better, worse):
    n = better + worse
    if n == 0:
        return 1.0
    return sum(math.comb(n, k) for k in range(better, n + 1)) / 2 ** n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--out")
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--min-arms", type=int, default=8, help="of 11 approaches for ntiming_same and strict (fixed in the plan); reading_same is gated on the model-owned approaches")
    a = ap.parse_args()
    A, B = jl(f"{a.base}/part_analysis.jsonl"), jl(f"{a.new}/part_analysis.jsonl")
    arms = sorted({r["arm"] for r in A} & {r["arm"] for r in B}, key=lambda x: (not x.startswith("DIRECT"), x))
    out, res = [], {}
    md = ["# Version comparison (criteria in docs/ANALYSIS_PLAN.md)", "", f"base: {a.base}", f"new: {a.new}", f"alpha {a.alpha} one-sided sign test over items; gate: at least {a.min_arms} of {len(arms)} approaches", ""]
    for m, gating in (("reading_same", "H1"), ("ntiming_same", "H1"), ("strict", "H2"), ("lenient", "-"), ("same_only", "-")):
        md += [f"## {m} ({gating})", "", "| approach | base mean over items | new mean over items | items better | items worse | ties | p (one-sided) | pass |", "|---|---|---|---|---|---|---|---|"]
        npass = 0
        for ar in arms:
            x, y = per_item(A, ar, m), per_item(B, ar, m)
            items = sorted(set(x) & set(y))
            better = sum(1 for i in items if y[i] > x[i])
            worse = sum(1 for i in items if y[i] < x[i])
            p = sign_p(better, worse)
            ok = p < a.alpha and better > worse
            npass += ok
            res.setdefault(m, {})[ar] = {"better": better, "worse": worse, "ties": len(items) - better - worse, "p": p, "pass": ok}
            md.append(f"| {ar} | {sum(x[i] for i in items) / len(items):.3f} | {sum(y[i] for i in items) / len(items):.3f} | {better} | {worse} | {len(items) - better - worse} | {p:.4f} | {'yes' if ok else 'no'} |")
        res[m]["_arms_passing"] = npass
        mo = [ar for ar in arms if not ar.endswith("+R2")]
        npass_mo = sum(1 for ar in mo if res[m][ar]["pass"])
        res[m]["_model_owned_passing"] = npass_mo
        md += ["", f"approaches passing: {npass}/{len(arms)}; model-owned approaches (DIRECT and +G; in +R2 the script writes the condition keyword) passing: {npass_mo}/{len(mo)}", ""]
    n_mo = len([ar for ar in arms if not ar.endswith("+R2")])
    h1 = res["reading_same"]["_model_owned_passing"] >= n_mo - 1       # reading in +R2 is fixed by the assembly code, so the gate counts the model-owned approaches only: all but one
    h1t = res["ntiming_same"]["_arms_passing"] >= a.min_arms
    h2 = res["strict"]["_arms_passing"] >= a.min_arms
    verdict = {"H1_reading": h1, "H1_timing": h1t, "H2_strict_success": h2,
               "decision": ("H1 and H2 hold: the intent version is the main condition, the base version is reported as the 'convention not stated' condition" if (h1 and h2) else
                            "H1 holds, H2 does not: the reading moved but success did not; the next step is the EXPRESSION and INSTRUMENT causes of analysis.md, no tool change before reading them" if h1 else
                            "H1 does not hold: the intent declaration did not move the reading; hypothesis rejected, no second attempt on these items without a new pre-registered hypothesis")}
    md += ["## Predeclared decision", "", json.dumps(verdict, ensure_ascii=False, indent=1)]
    print("\n".join(md))
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        open(f"{a.out}/comparison.md", "w").write("\n".join(md) + "\n")
        json.dump({"results": res, "verdict": verdict}, open(f"{a.out}/comparison.json", "w"), indent=1)


if __name__ == "__main__":
    main()
