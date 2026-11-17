#!/usr/bin/env python3
"""Build prompts/fretish_reference.md from the official FRET field documents, verbatim (v1.5).

Rule Q-1 of the retest design: every meaning sentence of the prompt is a quotation of an official document. Instead of choosing sentences by hand (which
produced the v1.4 supplement that covers only part of the documents), the whole text of every FRETish field document is included, in the order of the
FRETish fields. Nothing is paraphrased and no sentence is added; the only change is that the documents' markdown emphasis is kept as in the source.

usage: python3 tools/build_fretish_reference.py --docs <fret-electron/docs/_media/user-interface/examples> --commit <git commit> --grammar <Requirement.g4> --writing <writingReqs.md> --fret-parser <FretSemantics.js> --out prompts/fretish_reference.md
"""
import argparse
import hashlib
import os
import json
import re
import subprocess

ORDER = [("scope", "Scope"), ("condition", "Condition"), ("component", "Component"), ("timing", "Timing"), ("probability", "Probability"),
         ("response", "Response"), ("builtin_functions_explanations", "Built-in functions"), ("temporal_condition_explanations", "Temporal conditions")]


SCOPES = [("in m mode", "in"), ("while s", "while"), ("before m mode", "before"), ("after m mode", "after"), ("when not in m mode", "not in")]
CONDS = [("upon p", "regular condition"), ("whenever p", "holding condition"), ("unless p", "unless")]
TIMINGS = ["immediately", "at the next timepoint", "finally", "eventually", "always", "never", "within 3 ticks", "for 3 ticks", "after 3 ticks", "until r", "before r"]


def sentence(scope="", cond="", timing=""):
    return " ".join(x for x in (scope, cond, "the system shall", timing, "satisfy q") if x)


def semantics_section(parser_js):
    """FRET's own description and future-time formula of probe sentences, produced by the official parser (FretSemantics.compile)."""
    probes = [sentence(timing="always")]
    probes += [sentence(scope=sc, timing="always") for sc, _ in SCOPES]
    probes += [sentence(cond=c, timing="always") for c, _ in CONDS]
    probes += [sentence()] + [sentence(timing=t) for t in TIMINGS]
    probes += [sentence(cond=c, timing=t) for c in ("upon p", "whenever p") for t in [""] + TIMINGS]
    probes = list(dict.fromkeys(probes))
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_probes.json")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(probes, fh)
    try:
        r = subprocess.run(["node", os.path.join(os.path.dirname(os.path.abspath(__file__)), "fret_semantics_probe.js"), parser_js, tmp], capture_output=True, text=True, check=True)
    finally:
        os.remove(tmp)
    res = {x["sentence"]: x for x in json.loads(r.stdout)}
    bad = [k for k, v in res.items() if not v["ok"]]
    assert not bad, bad

    def part(sent, name):
        m = re.search(name + r": (.*?)(?= \| [A-Z ]+: |$)", res[sent]["description"])
        return m.group(1).strip()

    out = ["Each entry: a FRETish sentence, the description FRET gives for it, and its future-time formula. p and r are conditions, s is a Boolean expression, m is a mode, q is the response.", ""]
    out.append("### Scope\n")
    for sc, name in SCOPES:
        sn = sentence(scope=sc, timing="always")
        out.append(f"* `{sn}`\n  * Scope: {part(sn, 'SCOPE')}\n  * Formula (infinite traces): {res[sn]['ft_inf']}")
    out.append("* `" + sentence(timing="always") + "`\n  * Scope: " + part(sentence(timing="always"), "SCOPE") + "\n  * Formula (infinite traces): " + res[sentence(timing="always")]["ft_inf"])
    out.append("\n### Condition\n")
    for c, name in CONDS:
        sn = sentence(cond=c, timing="always")
        out.append(f"* `{sn}`\n  * Trigger: {part(sn, 'TRIGGER')}\n  * Formula (infinite traces): {res[sn]['ft_inf']}")
    out.append("* `" + sentence(timing="always") + "`\n  * Trigger: " + part(sentence(timing="always"), "TRIGGER"))
    out.append("\n### Timing\n")
    for t in [""] + TIMINGS:
        sn = sentence(timing=t)
        out.append(f"* `{sn}`\n  * Required behavior: {part(sn, 'REQUIRED BEHAVIOR')}\n  * Formula (infinite traces): {res[sn]['ft_inf']}\n  * Formula (finite traces): {res[sn]['ft_finite']}")
    out.append("\n### Condition and timing\n")
    for c in ("upon p", "whenever p"):
        for t in [""] + [x for x in TIMINGS if x != "finally"]:
            sn = sentence(cond=c, timing=t)
            out.append(f"* `{sn}`: {res[sn]['ft_inf']}")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", required=True)
    ap.add_argument("--commit", required=True)
    ap.add_argument("--grammar", required=True, help="fret-electron/app/parser/Requirement.g4")
    ap.add_argument("--writing", required=True, help="fret-electron/docs/_media/user-interface/writingReqs.md")
    ap.add_argument("--fret-parser", required=True, help="fret-electron/app/parser/FretSemantics.js (node dependencies of FRET reachable through NODE_PATH)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    parts = ["# FRETISH FIELD DOCUMENTATION\n"]
    shas = []
    g = open(a.grammar, encoding="utf-8").read().strip()
    g = g[g.index("grammar Requirement"):]      # the license header comment is not part of the grammar
    shas.append(f"Requirement.g4 {hashlib.sha256(g.encode()).hexdigest()[:12]}")
    parts.append("\n## FRETish grammar [Requirement.g4]\n\n```antlr\n" + g + "\n```\n")
    w = open(a.writing, encoding="utf-8").read()
    w = w[:w.index("### Templates tab")]                                   # the sections after the optional fields describe the editor tabs
    w = w.split("\n", 1)[1]                                                   # the document title line
    w = re.sub(r"^## ", "### ", w, flags=re.M)
    w = re.sub(r"<img[^>]*>\n?", "", w)
    w = re.sub(r"<span[^>]*>(.*?)</span>", r"\1", w)                           # markup of the manual page
    w = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", w)                          # links to files that are not part of the prompt: keep the link text
    for pat in (r" There is a grammar for the allowable sentences\. The grammar, displayed as \"railroad diagrams\", is accessible from this view by clicking on the question mark\. Mind you, this is not for the faint-hearted\.",
                r" You can switch between them using the toggle button \(\*Activate probabilistic FRETish\*\)\.",
                r" For more details, see the [A-Za-z ]+ Help Menu",
                r" See [A-Za-z\- ]+ Help for more\.",
                r" See Temporal Condition Help\."):                 # pointers to the editor window and to help pages
        w = re.sub(pat, "", w)
    w = re.sub(r"^While typing the body of a requirement.*\n", "", w, flags=re.M)   # editor behaviour of the FRET window
    w = re.sub(r"^\*\*\*\s*$", "", w, flags=re.M)
    w = re.sub(r"\n{3,}", "\n\n", w).strip()
    shas.append(f"writingReqs.md {hashlib.sha256(w.encode()).hexdigest()[:12]}")
    parts.append("\n## Writing requirements [writingReqs.md]\n\n" + w + "\n")
    for f, title in ORDER:
        t = open(os.path.join(a.docs, f + ".md"), encoding="utf-8").read().strip()
        shas.append(f"{f}.md {hashlib.sha256(t.encode()).hexdigest()[:12]}")
        parts.append(f"\n## {title} [{f}.md]\n\n{t}\n")
    sem = semantics_section(a.fret_parser)
    shas.append(f"FretSemantics.compile probes {hashlib.sha256(sem.encode()).hexdigest()[:12]}")
    parts.append("\n## Semantics of the fields [FRET parser output]\n\n" + sem + "\n")
    open(a.out, "w", encoding="utf-8").write("\n".join(parts))
    print("wrote", a.out, "| sources:", "; ".join(shas))


if __name__ == "__main__":
    main()
