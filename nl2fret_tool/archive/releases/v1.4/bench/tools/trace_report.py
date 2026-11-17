#!/usr/bin/env python3
"""Per unit trace of one run: how the requirement changed at every stage and where the log of each stage is. Reads only files of the run folder. No model call.

usage: python3 tools/trace_report.py --run RUN        RUN has gen/ inputs/ judge/ (see exp/fsm/README.md); writes RUN/trace/ and RUN/summary.md, RUN/summary.json
stages written for every unit (item x arm x repetition)
  S0 input             natural language, challenge, dictionary location
  S1 template          natural language -> template sentence (arms with a template)
  S2 FRETish           template or natural language -> FRETish (Direct: one step; rule text: free step with the rule text; rule assembly: phrases, slot values, assembled sentence, fallback)
  S3 FRET loop         every attempt, the FRET parser verdict and message of every sentence, the number of rejections
  S4 LTL               final sentence -> past time and future time LTL (official FRET compile)
  S5 dictionary        generated names -> dictionary names (exact, aliased, out of vocabulary)
  S6 judge             every pair (sentence x reference version) per part, the representative, equiv/sound/compl, counterexamples
Each stage block names the log files and keys (relative to RUN) in which the raw record is stored.
"""
import argparse
import collections
import json
import os


def jl(path):
    if not os.path.exists(path):
        return []
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def short(t, n=400):
    t = "" if t is None else str(t)
    return t if len(t) <= n else t[:n] + " ..."


def build(run):
    calls = {r["stage_key"]: r for r in jl(f"{run}/gen/calls.jsonl")}
    states = jl(f"{run}/inputs/unit_state.jsonl")
    units = {(u["item"], u["arm"], u["rep"]): u for u in json.load(open(f"{run}/inputs/units.json", encoding="utf-8"))["units"]}
    ltl = {r["sentence"]: r for r in jl(f"{run}/inputs/fret_ltl_gen.jsonl")}
    records = {r["pair_id"]: r for r in jl(f"{run}/judge/judge_records.jsonl")}
    parts = {(r["item"], r["arm"], r["rep"]): r for r in jl(f"{run}/judge/part_results.jsonl")}
    cex = collections.defaultdict(list)
    for r in jl(f"{run}/judge/counterexamples.jsonl"):
        cex[r["pair_id"]].append(r)
    items = {}
    for line in jl(f"{run}/gen/snapshot/items_used.jsonl"):
        items[line["id"]] = line
    out = []
    for rec in states:
        iid, arm, rep = rec["item_id"], rec["arm"], rec["rep"]
        it = items.get(iid, {})
        base = arm.split("+")[0]
        st = []
        calls_ref = lambda k: {"file": "gen/calls.jsonl", "key": k}
        st.append({"stage": "S0", "name": "input", "output": {"natural_language": it.get("raw_nl"), "challenge": it.get("challenge")}, "changed": None,
                   "logs": [{"file": "gen/snapshot/items_used.jsonl", "key": iid}, {"file": "data/dictionary/lm_dictionary.csv", "key": f"challenge {it.get('challenge')}"},
                            {"file": "gen/snapshot/run_info.json", "key": "prompt_hashes"}]})
        akey = f"{iid}|{base}|{rep}|A"
        if rec.get("A") is not None:
            arow = calls.get(akey, {})
            sents = rec["A"]["sentences"]
            st.append({"stage": "S1", "name": "template", "input": it.get("raw_nl"), "output": {"template": base, "sentences": sents, "choices": (arow.get("parsed") or {}).get("choices"),
                                                                                              "unmapped_content": (arow.get("parsed") or {}).get("unmapped_content")},
                       "changed": [sents[0] != it.get("raw_nl")] if sents else None,
                       "conformance": rec.get("conformance"), "logs": [calls_ref(akey)]})
        rounds = rec["rounds"]
        s2 = {"stage": "S2", "name": "fretish", "arm": arm, "attempts": [], "logs": []}
        if rec.get("fallback"):
            s2["fallback"] = rec["fallback"]
            s2["note"] = "the rule layer could not build a sentence (" + str(rec["fallback"]["code"]) + "); the template sentences went through the free path with the rule text"
        if rec.get("parses") and not rec.get("fallback") or (rec.get("parses") and rounds and rounds[0].get("stage") in ("S",)):
            s2["phrases"] = [{k: v for k, v in p.items() if k in ("template", "subject", "clauses", "response", "timing", "rules")} for p in rec["parses"]]
        for rr in rounds:
            row = rr.get("row") or {}
            k = f"{iid}|{arm}|{rep}|{rr['stage']}"
            e = {"round": rr["round"], "stage": rr["stage"], "sentences": [s.get("text") for s in rr["sentences"]],
                 "rules_applied": [s.get("rules") for s in rr["sentences"]], "rule_layer_failure": [s["pre"] for s in rr["sentences"] if s.get("pre")],
                 "model_output": short(row.get("raw_result"), 1500), "log": calls_ref(k) if row else None}
            if row.get("parsed") and rr["stage"] == "S" or (row.get("parsed") and "slots" in (row.get("parsed") or {})):
                e["slot_values"] = row["parsed"].get("slots")
            s2["attempts"].append(e)
            if row:
                s2["logs"].append(calls_ref(k))
        st.append(s2)
        s3 = {"stage": "S3", "name": "fret_loop", "attempts": [], "logs": [{"file": "gen/parser_cache.jsonl", "key": "sentence text"}]}
        n_rej = 0
        for rr in rounds:
            for s in rr["sentences"]:
                o = s.get("official")
                if o is not None and not o["ok"]:
                    n_rej += 1
                s3["attempts"].append({"round": rr["round"], "stage": rr["stage"], "sentence": s.get("text"), "reached_fret": o is not None,
                                       "verdict": None if o is None else ("accepted" if o["ok"] else "REJECTED"), "fret_message": None if o is None or o["ok"] else short(o["error"], 600),
                                       "error_class": None if o is None or o["ok"] else o.get("cls")})
        s3["n_rejected_sentence_attempts"] = n_rej
        s3["n_feedback_calls"] = rec.get("n_feedback")
        s3["cap_reached"] = rec.get("cap_reached")
        s3["feedback_log_given_to_model"] = [{"stage": r["stage_key"].split("|")[-1], "log": calls_ref(r["stage_key"])} for r in
                                             (calls.get(f"{iid}|{arm}|{rep}|F{k}") for k in range(1, 12)) if r]
        st.append(s3)
        u = units.get((iid, arm, rep), {})
        final = (rounds[-1]["sentences"] if rounds else [])
        s4 = {"stage": "S4", "name": "ltl", "sentences": [], "logs": [{"file": "inputs/fret_ltl_gen.jsonl", "key": "sentence"}]}
        for s in final:
            l = ltl.get(s.get("text") or "", {})
            s4["sentences"].append({"fretish": s.get("text"), "parser_ok": l.get("parser_ok"), "ltl_past": l.get("ltl_pt"), "ltl_future": l.get("ltl_ft")})
        st.append(s4)
        pr = parts.get((iid, arm, rep))
        s5 = {"stage": "S5", "name": "dictionary_alignment", "pairs": {}, "logs": [{"file": "judge/judge_records.jsonl", "key": "pair_id -> dict_alignment"}]}
        s6 = {"stage": "S6", "name": "judge", "parts": [], "logs": [{"file": "judge/judge_records.jsonl", "key": "pair_id"}, {"file": "judge/smv/<smv_sha256>.smv", "key": "query files"},
                                                           {"file": "judge/counterexamples.jsonl", "key": "pair_id"}, {"file": "judge/part_results.jsonl", "key": f"{iid}|{arm}|{rep}"}]}
        if pr:
            for p in pr["parts"]:
                pe = {"part": p["part"], "role": p["role"], "representative": p["representative"], "pairs": []}
                for q in p["pairs"]:
                    r = records.get(q["pair_id"], {})
                    s5["pairs"].setdefault(r.get("sentence_index"), r.get("dict_alignment"))
                    pe["pairs"].append({"pair_id": q["pair_id"], "sentence_index": q["sentence_index"], "reference_id": q["reference_id"], "role": q["role"], "equiv": r.get("equiv"),
                                        "sound": r.get("sound"), "compl": r.get("compl"), "nm_reason": r.get("nm_reason"), "und_reason": r.get("und_reason"),
                                        "renamed_beyond_dictionary": r.get("renamed_beyond_dictionary"), "counterexample_status": r.get("counterexample_status"),
                                        "counterexample_required": r.get("counterexample_required"),
                                        "counterexample_traces": [{"kind": c["kind"], "meaning": c["meaning"], "states": (c["trace"] or {}).get("n_states"), "smv": c.get("smv_path")}
                                                                  for c in (r.get("counterexamples") or [])]})
                s6["parts"].append(pe)
            s6["n_parts_success"], s6["n_parts"], s6["all_parts_success"] = pr["n_parts_success"], pr["n_parts"], pr["all_parts_success"]
        else:
            s6["note"] = "no sentence accepted by FRET, nothing to judge: every part is a failure (NO_SENTENCE)"
        st.append(s5)
        st.append(s6)
        out.append({"item": iid, "arm": arm, "rep": rep, "stages": st, "n_rejected_sentence_attempts": n_rej, "status": u.get("status"),
                    "fallback": rec.get("fallback"), "cap_reached": rec.get("cap_reached"), "part_result": pr})
    return out


def md_unit(t):
    L = [f"# {t['item']} | {t['arm']} | rep {t['rep']}", ""]
    for s in t["stages"]:
        L.append(f"## {s['stage']} {s['name']}")
        if s["stage"] == "S0":
            L += [f"- natural language: {s['output']['natural_language']}", f"- challenge: {s['output']['challenge']}"]
        elif s["stage"] == "S1":
            L += [f"- natural language: {s['input']}", f"- template ({s['output']['template']}): " + " / ".join(s["output"]["sentences"])]
            if s["output"].get("unmapped_content"):
                L.append(f"- content the template could not carry: {s['output']['unmapped_content']}")
            if s["output"].get("choices"):
                L.append(f"- choices made at this stage: {json.dumps(s['output']['choices'], ensure_ascii=False)}")
        elif s["stage"] == "S2":
            if s.get("note"):
                L.append(f"- {s['note']}")
            for ph in s.get("phrases", []):
                L.append(f"- phrases read by the rule layer: {json.dumps(ph, ensure_ascii=False)}")
            for a in s["attempts"]:
                L.append(f"- attempt {a['round']} ({a['stage']}): " + (" / ".join(x for x in a["sentences"] if x) or "(no sentence)"))
                if a.get("slot_values"):
                    L.append(f"  - slot values from the model: {json.dumps(a['slot_values'], ensure_ascii=False)}")
                if a.get("rule_layer_failure"):
                    L.append(f"  - rule layer failure: {a['rule_layer_failure']}")
        elif s["stage"] == "S3":
            for a in s["attempts"]:
                L.append(f"- round {a['round']} ({a['stage']}): {a['verdict'] or 'did not reach FRET'}: {a['sentence']}" + (f"\n  - FRET: {a['fret_message']}" if a["fret_message"] else ""))
            L.append(f"- rejected sentence attempts: {s['n_rejected_sentence_attempts']}; feedback calls: {s['n_feedback_calls']}; cap reached: {s['cap_reached']}")
        elif s["stage"] == "S4":
            for x in s["sentences"]:
                L += [f"- {x['fretish']}", f"  - past time: {x['ltl_past']}", f"  - future time: {x['ltl_future']}"]
        elif s["stage"] == "S5":
            for k, v in s["pairs"].items():
                L.append(f"- sentence {k}: {json.dumps(v, ensure_ascii=False)}")
        elif s["stage"] == "S6":
            if s.get("note"):
                L.append(f"- {s['note']}")
            for p in s["parts"]:
                L.append(f"- part {p['part']}: representative role {p['role']} ({p['representative']['pair_id'] if p['representative'] else '-'})")
                for q in p["pairs"]:
                    L.append(f"  - {q['pair_id']} ({q['reference_id']}): {q['role']} equiv={q['equiv']} sound={q['sound']} compl={q['compl']} counterexample={q['counterexample_status']}"
                             + (f" traces={q['counterexample_traces']}" if q["counterexample_traces"] else ""))
        L.append("- logs: " + "; ".join(f"`{x['file']}` ({x['key']})" for x in s.get("logs", [])))
        L.append("")
    return "\n".join(L)


def summarize(trace):
    by = collections.defaultdict(list)
    for t in trace:
        by[t["arm"]].append(t)
    rows = []
    for arm, ts in sorted(by.items()):
        n = len(ts)
        prs = [t["part_result"] for t in ts]
        parts = [p for pr in prs if pr for p in pr["parts"]]
        n_parts = sum((pr["n_parts"] if pr else 1) for pr in prs)
        roles = collections.Counter(p["role"] for p in parts)
        roles["NO_SENTENCE"] += sum(1 for pr in prs if not pr)
        succ = sum(p["success"] for p in parts)
        rows.append({"arm": arm, "units": n, "parts": n_parts, "part_success": succ, "part_success_rate": round(succ / n_parts, 3) if n_parts else None,
                     "unit_all_parts_success": sum(1 for pr in prs if pr and pr["all_parts_success"]), "roles": dict(roles),
                     "units_with_reject": sum(1 for t in ts if t["n_rejected_sentence_attempts"] >= 1), "units_with_2plus_rejects": sum(1 for t in ts if t["n_rejected_sentence_attempts"] >= 2),
                     "cap_reached": sum(1 for t in ts if t["cap_reached"]), "fallback_to_free_path": sum(1 for t in ts if t["fallback"])})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    a = ap.parse_args()
    trace = build(a.run)
    td = f"{a.run}/trace"
    os.makedirs(f"{td}/units", exist_ok=True)
    with open(f"{td}/unit_trace.jsonl", "w", encoding="utf-8") as f:
        for t in trace:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    idx = ["# Trace index", "", "One file per unit (item x arm x repetition). Each stage block lists the log file and key that hold the raw record.", "",
           "| item | arm | rep | rejected attempts | fallback | all parts success | file |", "|---|---|---|---|---|---|---|"]
    for t in trace:
        fn = f"units/{t['item']}__{t['arm'].replace('+', '_')}__rep{t['rep']}.md"
        open(f"{td}/{fn}", "w", encoding="utf-8").write(md_unit(t))
        pr = t["part_result"]
        idx.append(f"| {t['item']} | {t['arm']} | {t['rep']} | {t['n_rejected_sentence_attempts']} | {(t['fallback'] or {}).get('code', '')} | {pr['all_parts_success'] if pr else False} | [{fn}]({fn}) |")
    open(f"{td}/INDEX.md", "w", encoding="utf-8").write("\n".join(idx) + "\n")
    rows = summarize(trace)
    json.dump(rows, open(f"{a.run}/summary.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    md = ["# FSM run summary (observations only, no interpretation)", "", "| arm | units | parts | part success | rate | units all parts | units with reject | with 2+ rejects | cap reached | fallback | roles |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['arm']} | {r['units']} | {r['parts']} | {r['part_success']} | {r['part_success_rate']} | {r['unit_all_parts_success']} | {r['units_with_reject']} | {r['units_with_2plus_rejects']} | {r['cap_reached']} | {r['fallback_to_free_path']} | {r['roles']} |")
    open(f"{a.run}/summary.md", "w", encoding="utf-8").write("\n".join(md) + "\n")
    print(f"trace: {len(trace)} units -> {td}/INDEX.md ; summary -> {a.run}/summary.md")


if __name__ == "__main__":
    main()
