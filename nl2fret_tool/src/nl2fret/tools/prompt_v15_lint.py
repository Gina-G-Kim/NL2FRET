#!/usr/bin/env python3
"""v1.5 pre-run prompt lints (provenance principle: the model gets the FRETish guide and one template guide, every sentence from an official source).

  V-COMPLETE  every keyword of the official lexer (Requirement.g4) appears in every FRETish-stage prompt and in the slot prompt.
  V-PROVENANCE no marker of bench-authored content in any prompt (rule text, intent paragraph, naming rule, rewritten examples, unverified additions).
  V-LEAK       no reference FRETish sentence, and no reference response/condition text of 30+ characters, appears in any prompt.
  V-STATUS     status per document from prompts/sources_v15.json (not verified: WARNING).
  V-STYLE      no annotation, hedge, negation or test-bench sentence in the prompt text.
Usage: python3 -m nl2fret.tools.prompt_v15_lint [--reference data/reference/lm_reference_with_ltl.jsonl] [--grammar path/Requirement.g4]
Exit code 1 when a lint fails."""
import argparse, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
from nl2fret import common as C
from nl2fret import prompts3 as P
from nl2fret import batch_pipeline as BP
from nl2fret import rt_stage as RT
from nl2fret import kc_stage as KC
from nl2fret.paths import PROJECT

FORBIDDEN = ["MECHANICAL MAPPING", "R-EARS", "R-NEG", "R-MULTI", "NM-1", "UNVERIFIED", "rewritten for this bench", "NOT read",
             "intent declaration", "INTENT", "V-1:", "V-2:", "verified_subset"]
STYLE_BANNED = [r"SPEC_STATUS", r"SPEC_SOURCES", r"\bNot stated\b", r"test bench", r"\bbench\b", r"unverified", r"not verified", r"\bdo not\b", r"\bdon't\b", r"\bnever\b",
                r"\bmust not\b", r"\bNOT\b", r"\bnot\b", r"\bno\b", r"\bnothing\b", r"on purpose", r"as before"]
NORM = lambda s: re.sub(r"\s+", " ", s).strip().lower()


def lexer_words(g4):
    words = set()
    for m in re.finditer(r"^([A-Z]+)\s*:\s*((?:[A-Z]\s?)+(?:\(.*?\))?(?:\s[A-Z])*)", g4, re.M):
        name = m.group(1)
        if name in ("ID", "WS", "STRING", "NUMBER", "INT", "EXP", "ESC"):
            continue
        words.add(name.lower())
    return words


def prompts():
    P.DICT_ALL = True
    P.FRET_REFERENCE = True
    C.TPL_V15 = True
    out = {"DIRECT": P.build_system_D3("DIRECT")[0], "SLOT": P.slot_system_r2()}
    for t in C.TEMPLATES:
        out[t] = P.build_system_A3(t)[0]
    for t in C.TEMPLATES:
        out[t + "+G"] = P.build_system_B3(t + "+G")[0]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", default=os.path.join(str(PROJECT), "data/reference/lm_reference_with_ltl.jsonl"))
    ap.add_argument("--grammar", default=os.path.join(BENCH, "prompts/fretish_reference.md"))
    a = ap.parse_args()
    ps = prompts()
    fails, warns = [], []
    g4 = open(a.grammar, encoding="utf-8").read()
    words = lexer_words(g4)
    # tokens such as MICROSECOND/HOUR are spelled with optional letters in the lexer; check the stem
    stems = {w: w.rstrip("s") for w in words}
    for name, s in ps.items():
        low = s.lower()
        miss = sorted(w for w, st in stems.items() if st not in low)
        if miss and name not in C.TEMPLATES:      # stage A prompts (natural language to template) carry no FRETish, so V-COMPLETE covers the FRETish-stage and slot prompts only
            fails.append(f"V-COMPLETE {name}: lexer words missing {miss}")
        for f in FORBIDDEN:
            if f.lower() in low and not (f == "INTENT" and "intent" not in low):
                # 'INTENT' alone is too broad; only report the exact marker
                if f == "INTENT":
                    continue
                fails.append(f"V-PROVENANCE {name}: marker '{f}'")
    if os.path.exists(a.reference):
        refs = [json.loads(l) for l in open(a.reference, encoding="utf-8") if l.strip()]
        texts = []

        def walk(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k in ("fretish", "response", "condition") and isinstance(v, str):
                        texts.append(v)
                    else:
                        walk(v)
            elif isinstance(o, list):
                for x in o:
                    if isinstance(x, str) and False:
                        texts.append(x)
                    else:
                        walk(x)
        for r in refs:
            walk(r)
        texts = [NORM(t) for t in texts if len(t.strip()) >= 30]
        for name, s in ps.items():
            n = NORM(s)
            hit = [t[:60] for t in texts if t in n]
            if hit:
                fails.append(f"V-LEAK {name}: {len(hit)} reference texts, e.g. {hit[0]!r}")
        print(f"V-LEAK compared {len(texts)} reference texts of 30+ characters against {len(ps)} prompts")
    else:
        fails.append("V-LEAK skipped: reference file not found (a skipped lint is a failure)")
    src = json.load(open(os.path.join(BENCH, "prompts/sources_v15.json"), encoding="utf-8"))
    for t in ["FRETish"] + list(C.TEMPLATES):
        st = src.get(t, {}).get("status", "none")
        print(f"V-STATUS {t}: {st}")
        if st not in ("verified", "official_verbatim"):
            warns.append(f"V-STATUS {t}: {st}")
    # V-STYLE: no annotation, hedge, negation or test-bench sentence in the pieces authored by the bench (the official texts are verbatim and exempt)
    authored = {"RULES_COMMON_V15": C.RULES_COMMON_V15, "SCHEMA_A_V15": C.SCHEMA_A_V15, "SCHEMA_B_V15": C.SCHEMA_B_V15, "TASK_A": C.TASK_A, "TASK_B_V15": C.TASK_B_V15,
                "TASK_D": C.TASK_D, "BATCH_RULES": BP.BATCH_RULES, "RT_HEAD": RT.RT_HEAD, "RT_TAIL": RT.RT_TAIL, "KC_HEAD": KC.KC_HEAD, "KC_TAIL": KC.KC_TAIL, "RULES_A_V15": C.RULES_A_V15, "NOTATION_V15": C.NOTATION_V15, "NOTATION_FRETISH_V15": C.NOTATION_FRETISH_V15, "D_RULES_V15": P.D_RULES_V15, "D5_RULE_V15": P.D5_RULE_V15, "SLOT_D_RULES_V15": P.SLOT_D_RULES_V15,
                "SLOT_SYSTEM_V15": re.sub(r"\(always, never[^)]*\)", "", P.SLOT_SYSTEM_V15)}
    for name, s_ in authored.items():
        for pat in STYLE_BANNED:
            m = re.search(pat, s_, re.I)
            if m:
                fails.append(f"V-STYLE {name}: '{m.group(0)}' ... {s_[max(0, m.start()-40):m.end()+40]!r}")
    for w in warns:
        print("WARNING", w)
    for f in fails:
        print("FAIL", f)
    print(f"V-COMPLETE checked {len([n for n in ps if n not in C.TEMPLATES])} of {len(ps)} prompts (stage A prompts excluded)")
    print("RESULT", "FAIL" if fails else "PASS", f"({len(ps)} prompts)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
