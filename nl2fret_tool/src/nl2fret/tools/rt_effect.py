#!/usr/bin/env python3
"""Effect of the feedback steps (analysis C, fixed before any run). Reads part_results.jsonl of the judge folders of the variants v0 (first answer), vf (after parser feedback), kc (after the keyword check) and
rt (after round trip). With --keyword-inputs it also counts the keywords (condition, timing, scope) that the sentences of the variants use (check for a drift toward one keyword). Per arm and variant: units, parts, parts with success (SAME or PROOF), rate. Per arm and pair of variants: parts that change from failure to success (gain)
and from success to failure (loss) on the same (item, rep, part). Counts only; no test statistic.
--only-item / --only-challenge count only the parts of the named items / challenges (for a partial run, where the units of the items that were not run are pending). Without them every row is counted.
usage: python3 -m nl2fret.tools.rt_effect --judge v0=RUN/judge_v0 vf=RUN/judge_vf kc=RUN/judge_kc rt=RUN/judge_rt [--keyword-inputs vf=RUN/inputs_vf kc=RUN/inputs_kc] [--only-item ID...] [--only-challenge 06_EB...] [--out FILE.json]"""
import argparse, collections, json, os


def load(d, only_items=None, only_challenges=None):
    out = {}
    for l in open(os.path.join(d, "part_results.jsonl"), encoding="utf-8"):
        if l.strip():
            r = json.loads(l)
            if only_items and r["item"] not in only_items:
                continue
            if only_challenges and r.get("challenge") not in only_challenges:
                continue
            for p in r["parts"]:
                out[(r["arm"], r["item"], r["rep"], p["part"])] = bool(p["success"])
    return out


def keyword_distribution(specs, only_items=None, only_challenges=None):
    """-> {variant: {"sentences": n, "condition": {keyword: n}, "timing": {keyword: n}, "scope": {keyword: n}}}, counted over the units.json of the folders (sentences accepted by the parser)"""
    out = {}
    for spec in specs:
        name, d = spec.split("=", 1)
        c = {"sentences": 0, "condition": collections.Counter(), "timing": collections.Counter(), "scope": collections.Counter()}
        for u in json.load(open(os.path.join(d, "units.json"), encoding="utf-8"))["units"]:
            if only_items and u["item"] not in only_items:
                continue
            if only_challenges and (u["item"].split("-")[1] if u["item"].startswith("LM-") else None) not in only_challenges:
                continue
            for k in u.get("keywords") or []:
                c["sentences"] += 1
                for f in ("condition", "timing", "scope"):
                    if k.get(f):
                        c[f][k[f]] += 1
        out[name] = {"sentences": c["sentences"], **{f: dict(sorted(c[f].items())) for f in ("condition", "timing", "scope")}}
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--judge", nargs="+", required=True)
    ap.add_argument("--only-item", nargs="*", default=None)
    ap.add_argument("--only-challenge", nargs="*", default=None)
    ap.add_argument("--keyword-inputs", nargs="*", default=None, help="name=folder of make_judge_inputs output (units.json with the field keywords) of the variants to compare")
    ap.add_argument("--out")
    a = ap.parse_args()
    data = {k: load(v, a.only_item, a.only_challenge) for k, v in (x.split("=", 1) for x in a.judge)}
    names = list(data)
    arms = sorted({k[0] for d in data.values() for k in d})
    rep = {"per_arm": {}, "pairs": {}}
    for arm in arms:
        rep["per_arm"][arm] = {n: {"parts": sum(1 for k in d if k[0] == arm), "success": sum(v for k, v in d.items() if k[0] == arm)} for n, d in data.items()}
    for i, x in enumerate(names):
        for y in names[i + 1:]:
            for arm in arms:
                keys = [k for k in data[x] if k[0] == arm and k in data[y]]
                gain = sum(1 for k in keys if not data[x][k] and data[y][k])
                loss = sum(1 for k in keys if data[x][k] and not data[y][k])
                rep["pairs"].setdefault(f"{x}->{y}", {})[arm] = {"common_parts": len(keys), "gain": gain, "loss": loss}
    if a.keyword_inputs:
        rep["keyword_distribution"] = keyword_distribution(a.keyword_inputs, a.only_item, a.only_challenge)
    print(json.dumps(rep, indent=1))
    if a.out:
        json.dump(rep, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
