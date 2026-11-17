#!/usr/bin/env python3
"""Compile the dev sentences (generated and reference) with the official FRET parser in docker and write fret_ltl_dev.jsonl.
Records only. No comparison, no feedback.
usage (from the bench folder): python3 tools/compile_dev.py data/dev_ltl_sentences.json results_dev/fret_ltl_dev.jsonl
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "fret_check", "tools"))
import fret_compile as FC  # noqa: E402
src, dst = sys.argv[1], sys.argv[2]
texts = json.load(open(src, encoding="utf-8"))
res = FC.compile_list(texts)
with open(dst, "w", encoding="utf-8") as f:
    for c in res:
        sem = c.get("sem") or {}
        f.write(json.dumps({"sentence": c["fretish"], "parser_ok": bool(c["ok"]), "error": c.get("error"), "ltl_ft": c.get("ltl_ft"), "ltl_pt": c.get("ltl_pt"),
                            "scope": (sem.get("scope") or {}).get("type") if isinstance(sem.get("scope"), dict) else sem.get("scope"), "condition": sem.get("condition"),
                            "timing": sem.get("timing"), "response": sem.get("response"), "component": sem.get("component_name"),
                            "post_condition": sem.get("post_condition"), "variables": sem.get("variables")}, ensure_ascii=False) + "\n")
print("sentences", len(texts), "ok", sum(1 for c in res if c["ok"]), "wrote", dst)
