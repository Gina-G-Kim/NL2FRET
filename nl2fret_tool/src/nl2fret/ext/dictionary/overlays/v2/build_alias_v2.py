#!/usr/bin/env python3
"""Dictionary v2 = dictionary v1 + the columns alias_of and alias_evidence (docs/V20_BATCH_DESIGN.md 7.6, judge side only).
An alias pair `old -> current` is written only with an original text evidence: a NASA requirement of LM_requirements.json whose `comments` contain "Originally" and in which a token diff
of the comment text against the current `fulltext` shows `old` replaced by `current` at the same place (one identifier replaced by one identifier). Candidate pairs are the dictionary names of the
form <base>_<i>_<j> whose <base>_<i><j> is also a dictionary name of the same challenge. A pair without evidence gets no alias entry (unknown).
v1 rows are copied unchanged; for a row with evidence `alias_of` = the current name, `alias_evidence` = the requirement id(s), and the requirement id is appended to `sources` as nasa_req:<id>.
usage: python3 -I -B build_alias_v2.py --v1 lm_dictionary.csv --nasa .../LM_requirements.json --out lm_dictionary_v2.csv --evidence alias_evidence.json"""
import argparse
import csv
import difflib
import json
import re

TOK = re.compile(r"[A-Za-z_][A-Za-z0-9_]*|\d+(?:\.\d+)?|<=>|=>|<=|>=|!=|==|[-+*/()<>=&|!,]")
PAIR = re.compile(r"^(.+)_(\d+)_(\d+)$")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--v1", required=True)
    ap.add_argument("--nasa", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--evidence", required=True)
    a = ap.parse_args()
    rows = list(csv.DictReader(open(a.v1, encoding="utf-8-sig")))
    names = {(r["challenge"], r["name"]) for r in rows}
    cand = {}
    for ch, n in names:
        m = PAIR.match(n)
        if m and (ch, f"{m.group(1)}_{m.group(2)}{m.group(3)}") in names:
            cand[(ch, n)] = f"{m.group(1)}_{m.group(2)}{m.group(3)}"
    nasa = json.load(open(a.nasa, encoding="utf-8"))
    ev = {}
    for r in nasa["requirements"]:
        c = r.get("comments") or ""
        mm = re.search(r"Originally:?", c)
        if not mm:
            continue
        x, y = TOK.findall(c[mm.end():]), TOK.findall(r["fulltext"])
        for op, i1, i2, j1, j2 in difflib.SequenceMatcher(a=x, b=y, autojunk=False).get_opcodes():
            if op == "replace" and i2 - i1 == 1 and j2 - j1 == 1:
                for (ch, old), cur in cand.items():
                    if old == x[i1] and cur == y[j1]:
                        ev.setdefault((ch, old), {"current": cur, "requirements": []})["requirements"].append(r["reqid"])
    fields = list(rows[0].keys()) + ["alias_of", "alias_evidence"]
    with open(a.out, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in rows:
            e = ev.get((r["challenge"], r["name"]))
            r2 = dict(r, alias_of="", alias_evidence="")
            if e:
                ids = sorted(set(e["requirements"]))
                r2["alias_of"] = e["current"]
                r2["alias_evidence"] = "+".join(ids)
                r2["sources"] = (r["sources"] + "+" if r["sources"] else "") + "+".join("nasa_req:" + i for i in ids)
            w.writerow(r2)
    report = {"candidate_pairs": len(cand), "with_evidence": len(ev), "without_evidence": len(cand) - len(ev),
              "evidence": [{"challenge": k[0], "alias": k[1], **v} for k, v in sorted(ev.items())],
              "unknown": [{"challenge": k[0], "name": k[1], "current": cur} for k, cur in sorted(cand.items()) if k not in ev]}
    json.dump(report, open(a.evidence, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"candidates {len(cand)}, with evidence {len(ev)}, unknown {len(cand) - len(ev)}")


if __name__ == "__main__":
    main()
