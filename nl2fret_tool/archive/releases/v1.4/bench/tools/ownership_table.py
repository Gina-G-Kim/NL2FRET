#!/usr/bin/env python3
"""Decision ownership of the 11 approaches (DIRECT, 5 templates +G, 5 templates +R2): for every decision point, WHO decides (model, rule text read by the model, script) and which rules touch it.
Built from the code (tpl_rules.RULES, prompts3.guide_rules_text, the rule ids used by the assembly code), not typed by hand, except RULE_POINT below (the decision point each rule acts on), which is a reviewable list.
A rule that picks one of several documented FRETish alternatives for a template phrase is a CHOICE. A CHOICE without official-document evidence for the choice itself is UNSOURCED and is listed
(the evidence in data/rule_sources.json only documents that a construct exists and what it means). usage: python3 tools/ownership_table.py [--fret-docs DIR] [--out DIR]"""
import argparse, inspect, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
sys.path.insert(0, BENCH)
import tpl_rules as T   # noqa: E402
import prompts3 as P    # noqa: E402

POINTS = ["condition kind", "scope", "timing", "response phrase", "component", "form (surface syntax)", "unmapped template feature"]
RULE_POINT = {
    "condition kind": ["R-EARS-WHEN", "R-EARS-IF", "R-MAS-IF", "R-MAS-SOON", "R-ADV-WHEN", "R-ADV-IF", "R-BP-IF", "R-BP-UNLESS", "R-MULTI", "R2-COND-INTENT", "R-SP-RESP"],
    "scope": ["R-EARS-WHILE", "R-EARS-WHERE", "R-EARS-UB", "R-MAS-LONG", "R-ADV-WHILE", "R-ADV-WHERE", "R-ADV-HY", "R-BP-WHILE", "R-SP-GLOBAL", "R-SP-BEFORE", "R-SP-AFTER", "R-SP-AFTERUNTIL"],
    "timing": ["R-TIME-WITHIN", "R-TIME-FOR", "R-TIME-AFTER", "R-TIME-UNTIL", "R-TIME-BEFORE", "R-TIME-ADV", "R-TIME-NEXT", "R-TIME-PROB", "R-DEFTIME", "R2-TIME", "R-NEG", "R-BP-SUFFIX",
               "R-SP-UNIV", "R-SP-ABS", "R-SP-EXIST", "R-SP-PREC", "R-SP-BRESP", "R-SP-BINV", "R-SP-MINDUR"],
    "response phrase": ["R-MAS-ABLE", "R-MAS-PROVIDE", "R-ADV-PERFORM"],
    "component": ["R-COMP", "R-SP-COMP"],
    "form (surface syntax)": ["L-UNIT", "L-ABS", "L-SYM"],
    "unmapped template feature": ["R-SP-NOMAP", "R-TIME-EVERY"],
}
POINT_OF = {r: k for k, v in RULE_POINT.items() for r in v}
NORM = lambda s: re.sub(r"\s+", " ", re.sub(r"[*_`]", "", s)).strip().lower()


def code_ids():
    lines = inspect.getsource(T).splitlines()
    i0 = next(i for i, l in enumerate(lines) if l.startswith("RULES = {"))
    i1 = next(i for i in range(i0, len(lines)) if lines[i].startswith("}"))
    return set(re.findall(r'"(R2?-[A-Z0-9-]+|L-[A-Z]+)"', "\n".join(lines[:i0] + lines[i1 + 1:])))


def g_ids(base):
    old = (P.G_PARITY, P.INTENT_DECL)
    P.G_PARITY = True
    try:
        txt = P.guide_rules_text(base)
    finally:
        P.G_PARITY, P.INTENT_DECL = old
    return set(re.findall(r"^- ([RL]-[A-Z0-9-]+):", txt, re.M))


def evidence(docs):
    """quotes (main and 'also') must occur verbatim in the FRET docs; a parser_check must have passed in data/rule_semantics_results.json (tools/rule_semantics_check.py)."""
    src = json.load(open(os.path.join(BENCH, "data/rule_sources.json"), encoding="utf-8"))
    src.pop("_comment", None)
    rs_path = os.path.join(BENCH, "data/rule_semantics_results.json")
    checks = json.load(open(rs_path))["checks"] if os.path.exists(rs_path) else {}
    res, bad = {}, []
    cache = {}
    for rid, e in src.items():
        ok = None
        if docs:
            ok = True
            for q in [{"file": e["file"], "quote": e["quote"]}] + e.get("also", []):
                f = os.path.join(docs, q["file"])
                if f not in cache:
                    cache[f] = NORM(open(f, encoding="utf-8").read())
                ok = ok and NORM(q["quote"]).rstrip(".") in cache[f]
        pc = e.get("parser_check")
        if pc and not checks.get(pc, {}).get("pass"):
            ok = False
        if ok is False:
            bad.append(rid)
        res[rid] = dict(e, verified=ok)
    return res, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fret-docs")
    ap.add_argument("--out")
    a = ap.parse_args()
    ev, bad = evidence(a.fret_docs)
    cids = code_ids()
    base_t = list(P.TPLS)
    gset = {b: g_ids(b) for b in base_t}
    rows = []
    for rid, v in T.RULES.items():
        tpl, text, status = v[0], v[1], v[2]
        in_g = sorted(b for b in base_t if rid in gset[b])
        rows.append({"rule": rid, "template": tpl, "point": POINT_OF.get(rid, "UNCLASSIFIED"), "status": status, "in_G_text": bool(in_g), "in_R2_code": rid in cids,
                     "doc_evidence": (ev.get(rid) or {}).get("file"), "evidence_verified": (ev.get(rid) or {}).get("verified")})
    unclassified = [r["rule"] for r in rows if r["point"] == "UNCLASSIFIED"]
    owner = {
        "condition kind": ("model", "model, rule text constrains", "script (assembly keyword map R-*-WHEN/IF, R2-COND-INTENT)"),
        "scope": ("model", "model, rule text constrains", "script (assembly scope map)"),
        "timing": ("model", "model, rule text constrains", "model slot when no timing is given (R2-TIME), else script (R-TIME-*)"),
        "response phrase": ("model", "model, rule text constrains", "model (slot text)"),
        "component": ("model", "model", "script (R-COMP)"),
        "form (surface syntax)": ("model, FRETish guide", "model, FRETish guide", "script (L-*)"),
        "unmapped template feature": ("not applicable", "model", "script (failure code recorded, free path fallback)"),
    }
    md = ["# Decision ownership (generated from the code)", "", "| decision point | DIRECT | +G (free FRETish) | +R2 (script assembly) | rules touching it (id:status; G=in +G text, R=in R2 code) |", "|---|---|---|---|---|"]
    for p in POINTS:
        rs = [r for r in rows if r["point"] == p]
        lst = ", ".join(f"{r['rule']}:{r['status']}{'/G' if r['in_G_text'] else ''}{'/R' if r['in_R2_code'] else ''}" for r in rs)
        o = owner[p]
        md.append(f"| {p} | {o[0]} | {o[1]} | {o[2]} | {lst} |")
    choice_points = {"condition kind", "scope", "timing"}
    off = set(T.DISABLED_RULES)
    for r in rows:
        r["disabled_in_v14"] = r["rule"] in off
    unsourced = [r for r in rows if r["status"] == "DEFAULT" and not r["doc_evidence"] and not r["disabled_in_v14"]]
    construct_only = [r for r in rows if r["status"] == "DEFAULT" and r["doc_evidence"] and not r["disabled_in_v14"]]
    disabled = [r["rule"] for r in rows if r["disabled_in_v14"]]
    md += ["", "## Provenance counts", "", f"rules: {len(rows)}; by status: " + ", ".join(f"{s} {sum(1 for r in rows if r['status'] == s)}" for s in ("DEFAULT", "OBSERVED", "SOURCE", "FRET")),
           f"DEFAULT rules on a decision the script or the rule text hands to the tool (condition kind, scope, timing): {len([r for r in rows if r['point'] in choice_points and r['status'] == 'DEFAULT'])}",
           f"- active in v1.4 with evidence (official document quote and/or official parser check): {len(construct_only)}",
           f"- switched off in v1.4 (--sourced-rules-only; the model decides these phrases): {len(disabled)}: " + ", ".join(disabled),
           f"- active in v1.4 with NO evidence (must be 0): {len(unsourced)}: " + ", ".join(r["rule"] for r in unsourced),
           f"DEFAULT rules in total: {len([r for r in rows if r['status'] == 'DEFAULT'])} (all points; the counts below cover all of them)",
           f"unclassified rules (must be 0): {len(unclassified)} {unclassified}"]
    if a.fret_docs:
        md.append(f"evidence quotes verified verbatim in the FRET docs: {sum(1 for r in rows if r['evidence_verified'])}; not found: {bad}")
    print("\n".join(md))
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        open(os.path.join(a.out, "ownership.md"), "w").write("\n".join(md) + "\n")
        json.dump({"rules": rows, "unsourced_choice_rules": [r["rule"] for r in unsourced], "unclassified": unclassified, "evidence_not_found": bad}, open(os.path.join(a.out, "ownership.json"), "w"), indent=1)
    sys.exit(1 if (unclassified or bad or unsourced) else 0)


if __name__ == "__main__":
    main()
