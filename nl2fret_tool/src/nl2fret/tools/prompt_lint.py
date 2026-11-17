#!/usr/bin/env python3
"""v1.4 pre-run prompt lints P-1..P-6 (design: archive/nl2fret_tool_docs/v1.4/docs/V14_GUIDE_SUPPLEMENT.md, rules Q-1..Q-7).

Usage: python3 -m nl2fret.tools.prompt_lint --fret-docs DIR [--reference data/reference/lm_reference_with_ltl.jsonl] [--out report.json]
  DIR = fret-electron/docs/_media/user-interface/examples of the FRET repository (commit cf0f913).
Exit code 1 if any lint FAILS. A lint that cannot run is reported as SKIPPED and also fails the run unless --allow-skip is given
(a check that is skipped must never read as a pass).
"""
import argparse, inspect, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
from nl2fret import tpl_rules as T
from nl2fret import prompts3 as P
from nl2fret.paths import PROJECT

STATUSES = {"DEFAULT", "OBSERVED", "SOURCE", "FRET"}
NORM = lambda s: re.sub(r"\s+", " ", re.sub(r"[*_`]", "", s)).strip().lower()


def rules_for_g(base, parity):
    old = P.G_PARITY
    P.G_PARITY = parity
    try:
        txt = P.guide_rules_text(base)
    finally:
        P.G_PARITY = old
    return set(re.findall(r"^- (R-[A-Z0-9-]+):", txt, re.M))


def p1():
    """Every rule has a provenance status; counts reported; DEFAULT rules are the ones that must be audited."""
    bad = [k for k, v in T.RULES.items() if v[2] not in STATUSES]
    cnt = {s: sum(1 for v in T.RULES.values() if v[2] == s) for s in STATUSES}
    return {"ok": not bad, "n_rules": len(T.RULES), "counts": cnt, "no_status": bad}


def p1b(docs):
    """Every quote in data/rule_sources.json occurs verbatim in the FRET docs; every rule is assigned to a decision point (tools/ownership_table.py)."""
    from nl2fret.tools import ownership_table as O
    if not docs or not os.path.isdir(docs):
        return {"ok": False, "skipped": True, "reason": "--fret-docs directory missing"}
    import subprocess
    _, bad = O.evidence(docs)
    un = [r for r in T.RULES if r not in O.POINT_OF]
    r = subprocess.run([sys.executable, os.path.join(HERE, "ownership_table.py"), "--fret-docs", docs], capture_output=True, text=True)
    no_ev = [l for l in r.stdout.splitlines() if "with NO evidence" in l]
    return {"ok": not bad and not un and r.returncode == 0, "quotes_or_parser_checks_failed": bad, "rules_without_decision_point": un, "ownership_exit": r.returncode, "line": no_ev}


def p2():
    """+G rule text vs code of the assembly arm: rule IDs only in the text (not in code) and only in code (not in text)."""
    lines = inspect.getsource(T).splitlines()
    i0 = next(i for i, l in enumerate(lines) if l.startswith("RULES = {"))
    i1 = next(i for i in range(i0, len(lines)) if lines[i].startswith("}"))
    code_ids = set(re.findall(r'"(R-[A-Z0-9-]+)"', "\n".join(lines[:i0] + lines[i1 + 1:])))   # ids used by the code outside the RULES table
    out, ok = {}, True
    for base in P.TPLS:
        g_v13 = rules_for_g(base, False)
        g_v14 = rules_for_g(base, True)
        r = {"text_only_v13": sorted(g_v13 - code_ids), "text_only_v14": sorted(g_v14 - code_ids), "deftime_in_g_v14": "R-DEFTIME" in g_v14}
        if r["deftime_in_g_v14"]:
            ok = False
        out[base] = r
    return {"ok": ok, "per_template": out,
            "note": "text_only_* = rules the +G text states but the assembly code of R2 does not apply (parity gap). R-DEFTIME must not be in the v1.4 +G text."}


def sentences(md):
    parts = re.split(r"(?<=[.;:])\s+|\n", md)
    return [NORM(x) for x in parts if len(NORM(x)) > 40]


def p3():
    sup = open(os.path.join(BENCH, "prompts/fretish_guide_supplement.md"), encoding="utf-8").read()
    gd = open(os.path.join(BENCH, "prompts/fretish_guide.md"), encoding="utf-8").read()
    gset = set(sentences(gd))
    dup = [s for s in sentences(sup) if s in gset]
    bad_words = [w for w in ("observation of the official parser", "compiled in this bench", "not a documentation quote") if w in NORM(sup)]
    no_src = [l[:60] for l in sup.splitlines() if l.startswith("- ") and not re.search(r'"', l)]
    return {"ok": not dup and not bad_words and not no_src, "duplicates_with_guide": dup, "tool_observation_phrases": bad_words, "bullets_without_quote": no_src}


def p4(docs):
    """Each quoted string of the supplement must occur verbatim (whitespace and markdown markup normalized) in the file named in its section header."""
    if not docs or not os.path.isdir(docs):
        return {"ok": False, "skipped": True, "reason": "--fret-docs directory missing"}
    sup = open(os.path.join(BENCH, "prompts/fretish_guide_supplement.md"), encoding="utf-8").read()
    sec, miss, n = None, [], 0
    cache = {}
    for line in sup.splitlines():
        m = re.match(r"## .*\[([A-Za-z_]+\.md)\]", line)
        if m:
            sec = m.group(1)
            continue
        if sec is None or not line.startswith("- "):
            continue
        if sec not in cache:
            cache[sec] = NORM(open(os.path.join(docs, sec), encoding="utf-8").read())
        for q in re.findall(r'"([^"]{12,})"', line):
            n += 1
            parts = [NORM(x) for x in re.split(r'\s*\.\.\.\s*', q) if x.strip()]
            if not all(p.rstrip(".") in cache[sec] for p in parts):
                miss.append({"file": sec, "quote": q[:90]})
    return {"ok": not miss and n > 0, "n_quotes": n, "not_found": miss}


def p4b(paper_raw):
    """The quoted sentence of the intent declaration must occur verbatim in the NASA paper text (pdftotext raw order of the NTRS PDF)."""
    if not paper_raw or not os.path.exists(paper_raw):
        return {"ok": False, "skipped": True, "reason": "--paper-raw file missing"}
    t = NORM(re.sub(r"-\n", "", open(paper_raw, encoding="utf-8", errors="ignore").read()))
    t = re.sub(r"\s+", " ", t)
    d = open(os.path.join(BENCH, "prompts/intent_declaration.md"), encoding="utf-8").read()
    qs = [q for q in re.findall(r'"([^"]{30,})"', d)]
    miss = [q[:80] for q in qs if NORM(q) not in t]
    return {"ok": bool(qs) and not miss, "n_quotes": len(qs), "not_found": miss}


def p5(ref):
    """Reading profile of the reference corpus from the FRETish text (regex on keyword and timing field). Informational, never fails."""
    if not ref or not os.path.exists(ref):
        return {"ok": False, "skipped": True, "reason": "reference file missing"}
    rows = []
    for l in open(ref, encoding="utf-8"):
        d = json.loads(l)
        for part in d.get("gt_parts", []):
            for r in part:
                rows.append(r["fretish"])
    cond = {"none": 0, "upon/when/if/where": 0, "whenever": 0, "unless": 0}
    tim = {}
    for f in rows:
        head = f.split(" shall ")[0].lower()
        c = "whenever" if re.search(r"\bwhenever\b", head) else "unless" if re.search(r"\bunless\b", head) else \
            "upon/when/if/where" if re.search(r"\b(upon|when|if|where)\b", head) else "none"
        cond[c] += 1
        tail = f.split(" shall ", 1)[1] if " shall " in f else ""
        m = re.match(r"(?:,\s*)?(immediately|always|never|eventually|finally|at the next timepoint|within|for|after|until|before)\b", tail.strip())
        tim[m.group(1) if m else "(omitted)"] = tim.get(m.group(1) if m else "(omitted)", 0) + 1
    return {"ok": True, "n_rows": len(rows), "condition_kind": cond, "timing": dict(sorted(tim.items(), key=lambda x: -x[1])),
            "note": "dataset-wide convention, reported so that prompt supplements are not read as correcting it"}


def p6(ref, n=6):
    """No prompt text may contain a word n-gram of a reference FRETish row (answer leak), apart from quotes of the official documents."""
    if not ref or not os.path.exists(ref):
        return {"ok": False, "skipped": True, "reason": "reference file missing"}
    grams = {}
    for l in open(ref, encoding="utf-8"):
        d = json.loads(l)
        for part in d.get("gt_parts", []):
            for r in part:
                w = re.findall(r"[A-Za-z0-9_]+", r["fretish"].lower())
                for i in range(len(w) - n + 1):
                    grams.setdefault(" ".join(w[i:i + n]), d["id"])
    texts = {"fretish_guide.md": open(os.path.join(BENCH, "prompts/fretish_guide.md"), encoding="utf-8").read(),
             "fretish_guide_supplement.md": open(os.path.join(BENCH, "prompts/fretish_guide_supplement.md"), encoding="utf-8").read(),
             "intent_declaration.md": open(os.path.join(BENCH, "prompts/intent_declaration.md"), encoding="utf-8").read(),
             "D5_RULE": P.D5_RULE}
    hits = []
    for name, t in texts.items():
        w = re.findall(r"[A-Za-z0-9_]+", t.lower())
        for i in range(len(w) - n + 1):
            g = " ".join(w[i:i + n])
            if g in grams:
                hits.append({"file": name, "ngram": g, "ref_id": grams[g]})
    return {"ok": not hits, "n": n, "hits": hits[:20]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fret-docs")
    ap.add_argument("--reference", default=os.path.join(str(PROJECT), "data/reference/lm_reference_with_ltl.jsonl"))
    ap.add_argument("--paper-raw", help="pdftotext raw-order text of NTRS 20205000433 (needed by P-4b when the intent declaration is used)")
    ap.add_argument("--out")
    ap.add_argument("--allow-skip", action="store_true")
    a = ap.parse_args()
    res = {"P-1 rule provenance": p1(), "P-1b rule evidence quotes and decision points": p1b(a.fret_docs), "P-2 +G vs R2 rule parity": p2(), "P-3 guide duplication and tool observations": p3(),
           "P-4 citation verbatim check": p4(a.fret_docs), "P-4b intent declaration quote": p4b(a.paper_raw), "P-5 reference reading profile": p5(a.reference), "P-6 answer-leak n-gram": p6(a.reference)}
    bad = 0
    for k, v in res.items():
        st = "SKIPPED" if v.get("skipped") else ("PASS" if v["ok"] else "FAIL")
        if st == "FAIL" or (st == "SKIPPED" and not a.allow_skip):
            bad += 1
        print(f"{st:8s} {k}")
        if st != "PASS":
            print("         ", json.dumps(v, ensure_ascii=False)[:600])
    if a.out:
        json.dump(res, open(a.out, "w"), ensure_ascii=False, indent=1)
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
