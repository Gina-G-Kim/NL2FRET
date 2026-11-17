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
from nl2fret import fretparse
from nl2fret import units3 as U
from nl2fret import rt_stage as RT
from nl2fret import kc_stage as KC
from nl2fret import prompts3 as P
from nl2fret import tpl_rules as T
from nl2fret.common import load_jsonl


def apply_run_flags(results_dir):
    """Set the module flags that the run was made with (v1.4).

    units3.derive (used below) replays every unit from the call rows. For the +R2 arms that replay calls tpl_rules.assemble, whose result depends on tpl_rules.SOURCED_ONLY and
    tpl_rules.INTENT_COND. run_pipeline.main() sets them (and the prompts3 flags) from its command line (--sourced-rules-only, --intent-decl, ...). Without this call the replay uses the
    v1.3 defaults and does not reproduce the sentences that the run sent to the FRET parser (for example `no_source:` refusals and the keyword `whenever`), and a unit that went to the free
    path in the run is replayed as a slot unit (KeyError: 'slots').
    The flags are read from <results>/snapshot/run_info.json, which run_pipeline.py writes at the start of a run. A folder without that file, or a file without a key (a run made before
    v1.4), keeps the defaults. Returns the flags that were set."""
    p = os.path.join(results_dir, "snapshot", "run_info.json")
    if not os.path.exists(p):
        return {}
    info = json.load(open(p, encoding="utf-8"))
    flags = {k: bool(info.get(k, False)) for k in ("dict_all", "guide_sup", "fret_reference", "g_parity", "intent_decl", "tm_source_only", "sourced_rules_only")}
    P.DICT_ALL = flags["dict_all"]
    P.GUIDE_SUP = flags["guide_sup"]
    P.FRET_REFERENCE = flags["fret_reference"]
    from nl2fret import common as _C
    _C.TPL_V15 = bool(P.FRET_REFERENCE)
    T.SLOT_KW = bool(P.FRET_REFERENCE)
    P.G_PARITY = flags["g_parity"]
    P.INTENT_DECL = flags["intent_decl"]
    P.TM_SOURCE_ONLY = flags["tm_source_only"]
    P.SOURCED_ONLY = T.SOURCED_ONLY = flags["sourced_rules_only"]
    T.INTENT_COND = flags["intent_decl"]
    return flags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--parser", default="docker", choices=["docker", "node", "mock"])
    ap.add_argument("--arms", nargs="*")
    ap.add_argument("--reps", type=int)
    ap.add_argument("--variant", default="vf", choices=["v0", "vf", "kc", "rt"], help="v0 = first answer, vf = after the parser feedback (default), kc = after the keyword check when its answer is adopted (kc_stage.py), rt = after the round trip when its answer is adopted (rt_stage.py); the round trip starts from the kc answer when that was adopted")
    a = ap.parse_args()
    flags = apply_run_flags(a.results)
    print("run flags applied:", flags if flags else "none (no snapshot/run_info.json)")
    os.makedirs(a.out, exist_ok=True)
    rows = {r["stage_key"]: r for r in load_jsonl(os.path.join(a.results, "calls.jsonl"))}
    items = load_jsonl(a.data)
    st = json.load(open(os.path.join(a.results, "run_state.json"), encoding="utf-8"))
    arms = a.arms or st["arms"]
    reps = range(a.reps if a.reps is not None else st["reps"])
    cache = os.path.join(a.results, "parser_cache.jsonl")
    comp = fretparse._load_cache(cache)
    ch = KC.chain(rows, items, arms, reps, a.parser, cache, lambda: KC.cached_groups_of(os.path.join(a.results, "kc_fields.jsonl")))
    comp = fretparse._load_cache(cache)
    recs = {}
    for k, c in ch.items():
        if a.variant in ("v0", "vf"):
            recs[k] = c["base"]
        elif a.variant == "kc":
            recs[k] = c["kc"] if c["kc"].get("kc_adopted") else dict(c["base"], kc_adopted=False, kc_skipped=c["kc"].get("kc_skipped"))
        else:
            recs[k] = c["rt"] if c["rt"].get("rt_adopted") else dict(c["in"], rt_adopted=c["rt"].get("rt_adopted"))
            recs[k] = dict(recs[k], kc_adopted=c["kc"].get("kc_adopted"), kc_skipped=c["kc"].get("kc_skipped"), kc_changed=c["kc"].get("kc_changed") if c["kc"].get("kc_adopted") else None)
    final_sents = []
    units = []
    with open(os.path.join(a.out, "unit_state.jsonl"), "w", encoding="utf-8") as f:
        for (iid, arm, rep), rec in sorted(recs.items()):
            f.write(json.dumps(rec, ensure_ascii=False, default=str) + "\n")
            stat, code, detail, texts = U.variant(rec, "v0" if a.variant == "v0" else "vf")
            last = (rec["rounds"][0] if a.variant == "v0" else rec["rounds"][-1]) if rec["rounds"] else None
            allt = [s["text"] for s in (last["sentences"] if last else []) if s.get("text")]
            final_sents += allt
            rej = sum(1 for rr in rec["rounds"] for s in rr["sentences"] if s.get("official") is not None and not s["official"]["ok"])
            units.append({"item": iid, "arm": arm, "rep": rep, "status": stat, "status_code": code, "texts": texts, "n_sentences_final": len(allt),
                          "n_feedback": rec.get("n_feedback"), "fallback": rec.get("fallback"), "cap_reached": rec.get("cap_reached"), "variant": a.variant, "rt_adopted": rec.get("rt_adopted"), "kc_adopted": rec.get("kc_adopted"), "kc_skipped": rec.get("kc_skipped"), "kc_changed": rec.get("kc_changed"), "n_rejected_sentence_attempts": rej,
                          "pending": rec["pending"]})
    if a.variant in ("vf", "kc") and a.parser != "mock":       # keywords that the sentences use (distribution table of rt_effect.py)
        fl = KC.fields([t for u in units for t in u["texts"]], a.parser, os.path.join(a.results, "kc_fields.jsonl"))
        for u in units:
            u["keywords"] = [KC.keywords_of(t, fl.get(t)) for t in u["texts"]]
    json.dump({"units": units}, open(os.path.join(a.out, "units.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    from nl2fret.fret_check.tools import fret_compile
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
