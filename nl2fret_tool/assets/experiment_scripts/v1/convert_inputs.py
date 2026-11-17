#!/usr/bin/env python3
"""Converter of the bench results of a Lockheed Martin run into the three input files of the frozen nl2fret_judge tool (package v1.2.0).
The rules are in notes/PRE_RUN_DEFINITIONS.md (written and pinned before the first run). Nothing is corrected and no unit, sentence or item is dropped except what
the rules name. The tool and the bench folders are only read.

  units   units.json: one unit per (item, arm, repetition), derived with the bench code that made the run (units3.derive, units3.variant(rec, "vf"))
  ltl     fret_ltl_gen.jsonl: the rows of the source LTL file whose sentence occurs in units.json, sorted by sentence
  rlz     fret_realizability_gen.jsonl: the generated rows of the final variant of the source realizability file, arm without the variant suffix, in unit order

usage:
  python -I -B convert_inputs.py units --results R --items F --code-dir D --out F [--stratum none|items] [--texts all|accepted] [--units-v3 F] [--summary F]
                                       [--subset-arm-suffix +D --subset-ids F]      (020: arms whose names end with the suffix were run only on the items listed in F)
  python -I -B convert_inputs.py ltl   --source F --units F --out F [--summary F]
  python -I -B convert_inputs.py rlz   --source F --units F --out F [--variant vf|none] [--summary F]
Serialization (the one of the v8 example files): units.json = json.dumps({"units": [...]}, ensure_ascii=False), no indent, no trailing newline; the jsonl files = one
json.dumps(row, ensure_ascii=False) per line, each line ended by a newline.
"""
import argparse
import collections
import json
import os
import sys

sys.dont_write_bytecode = True


def read_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def write_summary(path, obj):
    if path:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
            f.write("\n")


# ---------------------------------------------------------------------------------------------------------------------------------------------------------
def cmd_units(a):
    sys.path.insert(0, os.path.abspath(a.code_dir))          # the bench modules of the run: units3, prompts3, tpl_rules, fretlint, common
    import units3 as U                                          # noqa: E402
    rows = {}
    for r in read_jsonl(os.path.join(a.results, "calls.jsonl")):
        rows[r["stage_key"]] = r
    comp = {}
    for r in read_jsonl(os.path.join(a.results, "parser_cache.jsonl")):
        comp[r["t"]] = {"ok": r["ok"], "error": r["error"]}
    state = json.load(open(os.path.join(a.results, "run_state.json"), encoding="utf-8"))
    arms = state.get("arms") or sorted({r["arm"] for r in rows.values()})
    reps = sorted({r["rep"] for r in rows.values()})
    items = read_jsonl(a.items)
    subset_ids = None
    if a.subset_arm_suffix:
        subset_ids = {l.strip() for l in open(a.subset_ids, encoding="utf-8") if l.strip()}
    by_design = []                                              # (item, arm, rep) that were not run by design (020)
    v3 = {}
    if a.units_v3:
        for u in read_jsonl(a.units_v3):
            v3[(u["item_id"], u["arm"], u["rep"])] = u
    units, pending, status, mism = [], [], collections.Counter(), collections.defaultdict(list)
    n_rej_sent = 0
    for it in items:
        for arm in arms:
            for rep in reps:
                if subset_ids is not None and arm.endswith(a.subset_arm_suffix) and it["id"] not in subset_ids:
                    rec = U.derive(rows, it, arm, rep, comp)
                    if not rec["pending"]:
                        raise SystemExit(f"{it['id']}|{arm}|{rep} is outside the design subset but has rows in the results")
                    by_design.append(f"{it['id']}|{arm}|{rep}")
                    continue
                rec = U.derive(rows, it, arm, rep, comp)
                if rec["pending"]:
                    pending.append(f"{it['id']}|{arm}|{rep}")
                    continue
                st, code, _detail, accepted = U.variant(rec, "vf")
                last = rec["rounds"][-1] if rec["rounds"] else None
                all_texts = [s["text"] for s in last["sentences"] if s.get("text")] if last else []      # as score3.build: every sentence of the final round
                n_rej_sent += len(all_texts) - len(accepted)
                unit = {"item": it["id"], "arm": arm, "rep": rep, "status": st, "code": code, "texts": all_texts if a.texts == "all" else accepted, "n_rounds": len(rec["rounds"])}
                if a.stratum == "items":
                    if it.get("stratum") is None:
                        raise SystemExit(f"item {it['id']} has no stratum in {a.items}")
                    unit["stratum"] = it["stratum"]
                units.append(unit)
                status[st] += 1
                if v3:
                    ref = v3.get((it["id"], arm, rep))
                    d = (ref or {}).get("variants", {}).get("vf")
                    if d is None:
                        mism["missing in units_v3"].append(f"{it['id']}|{arm}|{rep}")
                        continue
                    for name, mine, theirs in (("pre", st, d["pre"]), ("code", code, d["code"]), ("texts", all_texts, d["texts"]), ("accepted_texts", accepted, d["accepted_texts"]),
                                               ("n_rounds", len(rec["rounds"]) - 1, ref["n_rounds"])):
                        if mine != theirs:
                            mism[name].append(f"{it['id']}|{arm}|{rep}")
    if pending:
        raise SystemExit(f"{len(pending)} units are pending in the results (the run is not finished): {pending[:5]}")
    with open(a.out, "w", encoding="utf-8") as f:
        f.write(json.dumps({"units": units}, ensure_ascii=False))
    summ = {"units": len(units), "items": len({u["item"] for u in units}), "arms": arms, "reps": reps, "status": dict(sorted(status.items())),
            "sentences_in_texts": sum(len(u["texts"]) for u in units), "units_with_empty_texts": sum(1 for u in units if not u["texts"]), "texts_mode": a.texts, "stratum_mode": a.stratum,
            "sentences_of_the_final_round_that_the_official_parser_rejected_or_did_not_accept": n_rej_sent,
            "units_v3_crosscheck": ({"units_compared": len(units), "differences": {k: len(v) for k, v in mism.items()}, "examples": {k: v[:3] for k, v in mism.items()}} if v3 else None),
            "not_run_by_design": ({"suffix": a.subset_arm_suffix, "subset_ids_file": a.subset_ids, "subset_items": len(subset_ids), "combinations_left_out": len(by_design),
                                   "items_left_out": sorted({x.split("|")[0] for x in by_design}), "arms": sorted({x.split("|")[1] for x in by_design}), "reps": sorted({x.split("|")[2] for x in by_design})} if subset_ids is not None else None),
            "code_dir": os.path.abspath(a.code_dir)}
    write_summary(a.summary, summ)
    print(json.dumps(summ, ensure_ascii=False))
    return 3 if mism else 0


def load_units(path):
    return json.load(open(path, encoding="utf-8"))["units"]


def cmd_ltl(a):
    units = load_units(a.units)
    sentences = {t for u in units for t in u["texts"]}
    src = read_jsonl(a.source)
    by, dup = {}, 0
    for r in src:
        if r["sentence"] in by:
            dup += 1
            continue
        by[r["sentence"]] = r
    out = [by[s] for s in sorted(sentences) if s in by]
    missing = sorted(s for s in sentences if s not in by)
    with open(a.out, "w", encoding="utf-8") as f:
        for r in out:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    summ = {"source_rows": len(src), "source_duplicate_sentences_ignored": dup, "distinct_sentences_in_units": len(sentences), "rows_written": len(out), "sentences_without_a_source_row": len(missing),
            "missing_examples": missing[:5], "source_rows_not_in_units": len(src) - sum(1 for r in src if r["sentence"] in sentences) , "rows_written_parser_ok_false": sum(1 for r in out if not r["parser_ok"])}
    write_summary(a.summary, summ)
    print(json.dumps(summ, ensure_ascii=False))
    return 0


def cmd_rlz(a):
    units = load_units(a.units)
    order = {(u["item"], u["arm"], u["rep"]): i for i, u in enumerate(units)}
    src = read_jsonl(a.source)
    suffix = "#" + a.variant if a.variant != "none" else None
    kept, skipped = [], collections.Counter()
    for r in src:
        if r.get("kind") != "gen":
            skipped["kind " + str(r.get("kind"))] += 1
            continue
        if r.get("mode") != "single_requirement":
            skipped["mode " + str(r.get("mode"))] += 1
            continue
        if r.get("rep") is None:
            skipped["rep null"] += 1
            continue
        arm = r["arm"]
        if suffix:
            if not arm.endswith(suffix):
                skipped["other variant " + (arm.split("#")[1] if "#" in arm else "none")] += 1
                continue
            arm = arm[:-len(suffix)]
        row = dict(r)
        row["arm"] = arm                                           # same key position as in the source row
        kept.append(row)
    unknown = [r for r in kept if (r["item_id"], r["arm"], r["rep"]) not in order]
    if unknown:
        raise SystemExit(f"{len(unknown)} rows belong to no unit of units.json, for example {(unknown[0]['item_id'], unknown[0]['arm'], unknown[0]['rep'])}")
    kept.sort(key=lambda r: (order[(r["item_id"], r["arm"], r["rep"])], r["sentence_idx"]))
    keys = collections.Counter((r["item_id"], r["arm"], r["rep"], r["sentence_idx"]) for r in kept)
    dups = [k for k, v in keys.items() if v > 1]
    if dups:
        raise SystemExit(f"duplicate rows for {dups[:3]}")
    have = {(r["item_id"], r["arm"], r["rep"], r["sentence"]) for r in kept}
    miss = collections.Counter()
    miss_examples = []
    for u in units:
        for t in u["texts"]:
            if (u["item"], u["arm"], u["rep"], t) not in have:
                miss[u["status"]] += 1
                if len(miss_examples) < 3:
                    miss_examples.append([u["item"], u["arm"], u["rep"], t[:80]])
    wrong = sum(1 for r in kept if units[order[(r["item_id"], r["arm"], r["rep"])]]["status"] == "parsed" and units[order[(r["item_id"], r["arm"], r["rep"])]]["texts"][r["sentence_idx"]] != r["sentence"])
    with open(a.out, "w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    summ = {"source_rows": len(src), "rows_written": len(kept), "source_rows_skipped": dict(sorted(skipped.items())), "unit_sentences_without_a_row_by_unit_status": dict(sorted(miss.items())),
            "unit_sentences_without_a_row": sum(miss.values()), "missing_examples": miss_examples, "rows_whose_sentence_differs_from_texts_at_sentence_idx_in_parsed_units": wrong,
            "results": dict(sorted(collections.Counter(r["result"] for r in kept).items()))}
    write_summary(a.summary, summ)
    print(json.dumps(summ, ensure_ascii=False))
    return 0 if not wrong else 3


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    u = sp.add_parser("units")
    u.add_argument("--results", required=True)
    u.add_argument("--items", required=True)
    u.add_argument("--code-dir", required=True)
    u.add_argument("--out", required=True)
    u.add_argument("--stratum", choices=["none", "items"], default="none")
    u.add_argument("--texts", choices=["all", "accepted"], default="all")
    u.add_argument("--units-v3")
    u.add_argument("--summary")
    u.add_argument("--subset-arm-suffix", help="020: arms with this name suffix were run on a subset of the items by design (their other units are not run, not pending)")
    u.add_argument("--subset-ids", help="020: file with the item ids (one per line) that the subset arms were run on (ids_B.txt)")
    u.set_defaults(f=cmd_units)
    l = sp.add_parser("ltl")
    l.add_argument("--source", required=True)
    l.add_argument("--units", required=True)
    l.add_argument("--out", required=True)
    l.add_argument("--summary")
    l.set_defaults(f=cmd_ltl)
    r = sp.add_parser("rlz")
    r.add_argument("--source", required=True)
    r.add_argument("--units", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--variant", choices=["vf", "none"], default="vf")
    r.add_argument("--summary")
    r.set_defaults(f=cmd_rlz)
    a = ap.parse_args()
    return a.f(a)


if __name__ == "__main__":
    sys.exit(main())
