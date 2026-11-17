#!/usr/bin/env python3
"""J+def (docs/V20_BATCH_DESIGN.md 7.2, 7.5, 7.6): derived judge inputs in which (1) alias names of the dictionary are written as their current names and (2) the dictionary terms of kind
`defined` whose definition is a FRET expression are replaced by their definition, in the generated AND the reference sentences. The strict judge is not changed and `judging/` is not touched:
this tool only writes derived input files that the unchanged `nl2fret_judge judge-parts` reads.

Term level rule (7.5): a defined term is substitutable iff its `definition` parses as a FRET expression (official parser, probe sentences) and the term is not on a cycle of the definition graph.
A term that is not substitutable stays an atom on both sides and is recorded as lustre_only (reason parse_error or cycle). Lustre expressions are never translated.
Alias rule (7.6): rows with a value in the dictionary column alias_of (dictionary v2) are renamed to that name in condition and response, before the substitution.

Reads   <inputs>/units.json and the dictionary / reference files. Writes <out>/units.json, <out>/fret_ltl_gen.jsonl (LTL of the derived sentences from the official parser),
        <out>/reference_def.jsonl (the reference with the same rules applied and its LTL recompiled), <out>/term_report.json and <out>/substitution_report.json.
Options --no-substitute   copies the sentences unchanged (strict control with the same file layout; no alias, no substitution)
        --no-alias        applies the term substitution without the alias renaming
        --self-judge      writes units of the arm REFERENCE (the first version of every part of the reference) instead of the units of --inputs
        --terms-only      writes only term_report.json
usage (from bench/, python3 -I):
  python3 tools/make_def_inputs.py --inputs RUN/inputs_vf --reference ../data/reference/lm_reference_with_ltl.jsonl --dictionary ../data/dictionary/lm_dictionary.csv --out RUN/inputs_def_vf
"""
import argparse
import csv
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(BENCH, "fret_check", "tools"))
import fret_compile  # noqa: E402
import litnorm  # noqa: E402


def jl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def analyse_terms(rows, parser):
    """-> ({challenge: {term: definition}} of the substitutable terms, term report dict)"""
    defs = {}
    for r in rows:
        if r["kind"] == "defined" and r["definition"].strip():
            defs.setdefault(r["challenge"], {})[r["name"]] = r["definition"].strip()
    probes = {}
    for ch, d in defs.items():
        for n, t in d.items():
            probes[(ch, n)] = (f"X shall always satisfy ({t})", f"X shall always satisfy ({t}) < 0")
    texts = list(dict.fromkeys(x for v in probes.values() for x in v))
    ok = {r["fretish"]: bool(r["ok"]) for r in fret_compile.compile_list(texts, backend=parser)} if texts else {}
    subst, report = {}, {}
    for ch, d in sorted(defs.items()):
        parse_ok = {n: (ok[probes[(ch, n)][0]] or ok[probes[(ch, n)][1]]) for n in d}
        reason, good = litnorm.classify_terms(d, parse_ok)
        subst[ch] = good
        report[ch] = {"defined": len(d), "substitutable": len(good), "lustre_only": len(d) - len(good),
                      "lustre_only_parse_error": sum(1 for v in reason.values() if v == "parse_error"), "lustre_only_cycle": sum(1 for v in reason.values() if v == "cycle"),
                      "terms": [{"name": n, "reason": reason[n], "definition": d[n][:160]} for n in sorted(d)]}
    return subst, report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs")
    ap.add_argument("--reference", required=True)
    ap.add_argument("--dictionary", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--parser", default="docker", choices=["docker", "node"])
    ap.add_argument("--no-substitute", action="store_true")
    ap.add_argument("--no-alias", action="store_true")
    ap.add_argument("--self-judge", action="store_true")
    ap.add_argument("--terms-only", action="store_true")
    ap.add_argument("--only-challenge", nargs="*")
    a = ap.parse_args()
    refs = jl(a.reference)
    chal_of = {r["id"]: r["challenge"] for r in refs}
    drows = list(csv.DictReader(open(a.dictionary, encoding="utf-8-sig")))
    amap = {}
    for r in drows:
        if r.get("alias_of"):
            amap.setdefault(r["challenge"], {})[r["name"]] = r["alias_of"]
    subst, term_report = analyse_terms(drows, a.parser)
    os.makedirs(a.out, exist_ok=True)
    json.dump({"rule": "docs/V20_BATCH_DESIGN.md 7.5", "challenges": term_report,
               "total": {k: sum(v[k] for v in term_report.values()) for k in ("defined", "substitutable", "lustre_only", "lustre_only_parse_error", "lustre_only_cycle")}},
              open(os.path.join(a.out, "term_report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if a.terms_only:
        print(f"{a.out}: terms {sum(v['defined'] for v in term_report.values())}, lustre_only {sum(v['lustre_only'] for v in term_report.values())}")
        return
    if a.self_judge:
        units = []
        for r in refs:
            if a.only_challenge and r["challenge"] not in a.only_challenge:
                continue
            texts = [p[0]["fretish"] for p in r["gt_parts"] if p]
            units.append({"item": r["id"], "arm": "REFERENCE", "rep": 0, "status": "parsed", "status_code": "", "texts": texts, "n_sentences_final": len(texts), "n_feedback": 0,
                          "fallback": None, "cap_reached": False, "variant": "self", "rt_adopted": None, "n_rejected_sentence_attempts": 0, "pending": False})
    else:
        units = json.load(open(os.path.join(a.inputs, "units.json"), encoding="utf-8"))["units"]
    todo = []        # (kind, key, challenge, text)
    for u in units:
        for t in u["texts"]:
            todo.append(("gen", f'{u["item"]}|{u["arm"]}|{u["rep"]}', chal_of.get(u["item"]), t))
    for r in refs:
        for pi, part in enumerate(r["gt_parts"]):
            for vi, v in enumerate(part):
                todo.append(("ref", f'{r["id"]}|p{pi + 1}|v{vi + 1}', r["challenge"], v["fretish"]))
    orig = list(dict.fromkeys(t for _, _, _, t in todo))
    comp = {r["fretish"]: r for r in fret_compile.compile_list(orig, backend=a.parser)}
    def ensure(text):
        if text not in comp:
            comp.update({r["fretish"]: r for r in fret_compile.compile_list([text], backend=a.parser)})
        return comp[text]

    report = []
    for kind, key, ch, t in todo:
        info = {"substituted": [], "cycles": [], "depth_limit": [], "aliases": []}
        nt = t
        if not a.no_substitute and comp[t]["ok"]:
            if not a.no_alias and ch in amap:
                nt, info["aliases"] = litnorm.rename_aliases(t, comp[t]["sem"], amap[ch])
            if subst.get(ch):
                c = ensure(nt)          # after an alias renaming the text ranges moved: the renamed text is compiled to get its own ranges
                if c["ok"]:
                    nt, i2 = litnorm.substitute_defined(nt, c["sem"], subst[ch])
                    info.update({k: i2[k] for k in ("substituted", "cycles", "depth_limit")})
        report.append({"kind": kind, "key": key, "original": t, "new": nt, **info})
    new_texts = list(dict.fromkeys(r["new"] for r in report if r["new"] != r["original"]))
    comp.update({r["fretish"]: r for r in fret_compile.compile_list([t for t in new_texts if t not in comp], backend=a.parser)} if [t for t in new_texts if t not in comp] else {})
    final = {}
    for r in report:
        if r["new"] != r["original"] and not comp[r["new"]]["ok"]:
            r["parser_rejected"] = True
            r["new"] = r["original"]
        final[r["original"]] = r["new"]
    for r in report:
        r.setdefault("parser_rejected", False)
    out_units = []
    for u in units:
        u2 = dict(u)
        u2["texts"] = [final[t] for t in u["texts"]]
        out_units.append(u2)
    json.dump({"units": out_units}, open(os.path.join(a.out, "units.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    sent = list(dict.fromkeys(final[t] for u in units for t in u["texts"]))
    with open(os.path.join(a.out, "fret_ltl_gen.jsonl"), "w", encoding="utf-8") as f:
        for t in sent:
            r = comp[t]
            f.write(json.dumps({"sentence": t, "parser_ok": bool(r["ok"]), "ltl_pt": r.get("ltl_pt"), "ltl_ft": r.get("ltl_ft"), "error": r.get("error")}, ensure_ascii=False) + "\n")
    with open(os.path.join(a.out, "reference_def.jsonl"), "w", encoding="utf-8") as f:
        for r in refs:
            r2 = json.loads(json.dumps(r))
            for part in r2["gt_parts"]:
                for v in part:
                    nt = final[v["fretish"]]
                    if nt != v["fretish"]:
                        v["fretish_original"] = v["fretish"]
                        v["fretish"] = nt
                        v["ltl"] = {"past_time": comp[nt].get("ltl_pt"), "future_time": comp[nt].get("ltl_ft")}
                        v["ltl_source"] = "FRET parser (FretSemantics.js), after J+def (alias renaming and term substitution)"
            f.write(json.dumps(r2, ensure_ascii=False) + "\n")
    summ = {"mode": "no_substitute" if a.no_substitute else "def", "alias": not (a.no_alias or a.no_substitute), "sentences": len(report), "changed": sum(1 for r in report if r["new"] != r["original"]),
            "changed_gen": sum(1 for r in report if r["kind"] == "gen" and r["new"] != r["original"]), "changed_ref": sum(1 for r in report if r["kind"] == "ref" and r["new"] != r["original"]),
            "aliases_renamed": sum(1 for r in report if r["aliases"]), "parser_rejected": sum(1 for r in report if r["parser_rejected"]),
            "terms": term_report and {k: sum(v[k] for v in term_report.values()) for k in ("defined", "substitutable", "lustre_only")}}
    json.dump({"summary": summ, "sentences": report}, open(os.path.join(a.out, "substitution_report.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{a.out}: sentences {summ['sentences']}, changed {summ['changed']} (gen {summ['changed_gen']}, ref {summ['changed_ref']}), aliases renamed {summ['aliases_renamed']}, parser_rejected {summ['parser_rejected']}, lustre_only terms {summ['terms']['lustre_only']}/{summ['terms']['defined']}")


if __name__ == "__main__":
    main()
