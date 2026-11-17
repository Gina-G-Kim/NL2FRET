#!/usr/bin/env python3
"""Turns a generation results folder into the judge inputs and the per-unit state. No model call.

usage: python3 tools/make_judge_inputs.py --results RESULTS --data ITEMS.jsonl --out INPUTS [--parser docker|node]
outputs (in INPUTS)
  units.json            {"units": [{item, arm, rep, status, texts(final sentences accepted by FRET), n_feedback, fallback, cap_reached, n_rejected_attempts}]}
  fret_ltl_gen.jsonl    {sentence, parser_ok, ltl_pt, ltl_ft, error} for every sentence of the final round (accepted or not)
  unit_state.jsonl      the full derived record of every unit (all rounds, sentences, FRET verdicts, fallback)  -> input of tools/trace_report.py
The final answer of a unit is the last round of the FRET loop (variant vf). A sentence the parser still rejects after the last round keeps its place in the unit and has no LTL (it is judged as a failure, never removed).
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
sys.path.insert(0, BENCH)
sys.path.insert(0, os.path.join(BENCH, "fret_check", "tools"))
import fretparse  # noqa: E402
import units3 as U  # noqa: E402
import prompts3 as P  # noqa: E402
from common import load_jsonl  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--parser", default="docker", choices=["docker", "node", "mock"])
    ap.add_argument("--arms", nargs="*")
    ap.add_argument("--reps", type=int)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rows = {r["stage_key"]: r for r in load_jsonl(os.path.join(a.results, "calls.jsonl"))}
    items = load_jsonl(a.data)
    st = json.load(open(os.path.join(a.results, "run_state.json"), encoding="utf-8"))
    arms = a.arms or st["arms"]
    reps = range(a.reps if a.reps is not None else st["reps"])
    cache = os.path.join(a.results, "parser_cache.jsonl")
    comp = fretparse._load_cache(cache)
    recs = {(it["id"], arm, r): U.derive(rows, it, arm, r, comp) for it in items for arm in arms for r in reps}
    need = []
    for rec in recs.values():
        need += U.pending_compile(rec)
    if need:
        fretparse.compile_texts(list(dict.fromkeys(need)), a.parser, cache)
        comp = fretparse._load_cache(cache)
        recs = {(it["id"], arm, r): U.derive(rows, it, arm, r, comp) for it in items for arm in arms for r in reps}
    final_sents = []
    units = []
    with open(os.path.join(a.out, "unit_state.jsonl"), "w", encoding="utf-8") as f:
        for (iid, arm, rep), rec in sorted(recs.items()):
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
            stat, code, detail, texts = U.variant(rec, "vf")
            last = rec["rounds"][-1] if rec["rounds"] else None
            allt = [s["text"] for s in (last["sentences"] if last else []) if s.get("text")]
            final_sents += allt
            rej = sum(1 for rr in rec["rounds"] for s in rr["sentences"] if s.get("official") is not None and not s["official"]["ok"])
            units.append({"item": iid, "arm": arm, "rep": rep, "status": stat, "status_code": code, "texts": texts, "n_sentences_final": len(allt),
                          "n_feedback": rec.get("n_feedback"), "fallback": rec.get("fallback"), "cap_reached": rec.get("cap_reached"), "n_rejected_sentence_attempts": rej,
                          "pending": rec["pending"]})
    json.dump({"units": units}, open(os.path.join(a.out, "units.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    import fret_compile
    final_sents = list(dict.fromkeys(final_sents))
    ltl_path = os.path.join(a.out, "fret_ltl_gen.jsonl")
    done = {}
    if os.path.exists(ltl_path):
        done = {json.loads(l)["sentence"]: 1 for l in open(ltl_path, encoding="utf-8") if l.strip()}
    todo = [t for t in final_sents if t not in done]
    if todo:
        res = fret_compile.compile_list(todo, backend=("node" if a.parser == "node" else "docker")) if a.parser != "mock" else []
        with open(ltl_path, "a", encoding="utf-8") as f:
            for r in res:
                f.write(json.dumps({"sentence": r["fretish"], "parser_ok": bool(r["ok"]), "ltl_pt": r.get("ltl_pt"), "ltl_ft": r.get("ltl_ft"), "error": r.get("error")}, ensure_ascii=False) + "\n")
    print(f"units {len(units)} | pending {sum(1 for u in units if u['pending'])} | final sentences {len(final_sents)} | compiled now {len(todo)}")


if __name__ == "__main__":
    main()
