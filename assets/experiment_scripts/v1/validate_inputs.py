#!/usr/bin/env python3
"""Validation of the three converted input files (instruction step 4 and "data separation"). Read only; the tool and the bench folders are only read.

  1. counts: units, items, arms, repetitions, sentences; per status; units with empty texts; stratum
  2. every (item, arm, repetition) of the run is in units.json exactly once
  3. coverage: sentences of units.json without a row in fret_ltl_gen.jsonl and in fret_realizability_gen.jsonl (by unit status); rows of the files that belong to no unit
  4. the tool's own loader (judging/nl2fret_judge/units.py of the unzipped package, imported read only): units.load_units reads the three files without an error
  5. unit status after the realizability check recomputed from the converted files with the rule of bench/score3.py (worst result of the sentences) and compared, unit by unit, with the
     run's own units_scored.jsonl (variants.vf.status) and with the counts of RUN_RECORD.md
  6. the effect of texts = all versus accepted on the tool's unit outcome (aggregate with no judge record), for the units where the two differ
  7. data separation: ids, development set, source folder, sentences that do not belong to units
usage: python -I -B validate_inputs.py --units F --ltl F --rlz F --pkg D --results R --items F --dev-items F --ref F --out F [--units-accepted F] [--pre-ltl F ...]
"""
import argparse
import collections
import json
import os
import sys

sys.dont_write_bytecode = True
ORDER = ["pipeline", "parse_error", "not_run", "unknown", "unrealizable", "realizable"]       # bench/score3.py


def read_jsonl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def norm(s):
    return " ".join((s or "").split()).lower()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--units", required=True)
    ap.add_argument("--ltl", required=True)
    ap.add_argument("--rlz", required=True)
    ap.add_argument("--pkg", required=True, help="unzipped package (judging/nl2fret_judge is imported read only)")
    ap.add_argument("--results", help="bench results folder of the run (run_state.json, units_scored.jsonl, fret_ltl.jsonl)")
    ap.add_argument("--items", help="items file of the run")
    ap.add_argument("--pkg-items", help="bench/data/lm_items.jsonl of the unzipped package (cross-check of the stratum source)")
    ap.add_argument("--dev-items", help="development item set (data/dev_items.jsonl)")
    ap.add_argument("--ref", help="reference file of the package (data/reference/lm_reference_with_ltl.jsonl)")
    ap.add_argument("--units-accepted", help="the same conversion with --texts accepted (what-if, not delivered)")
    ap.add_argument("--other-ltl", nargs="*", default=[], help="LTL files of pre-check, mock and development runs (informational overlap)")
    ap.add_argument("--subset-arm-suffix", help="020: arms with this suffix were run on a subset of the items by design")
    ap.add_argument("--subset-ids", help="020: file with the item ids of the design subset (ids_B.txt)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res = {}
    units = json.load(open(a.units, encoding="utf-8"))["units"]
    ltl = read_jsonl(a.ltl)
    rlz = read_jsonl(a.rlz)

    # 1 counts
    items = []
    for u in units:
        if u["item"] not in items:
            items.append(u["item"])
    arms = []
    for u in units:
        if u["arm"] not in arms:
            arms.append(u["arm"])
    sents = [t for u in units for t in u["texts"]]
    res["counts"] = {"units": len(units), "items": len(items), "arms": len(arms), "arm_list": arms, "reps": sorted({u["rep"] for u in units}), "sentences": len(sents), "distinct_sentences": len(set(sents)),
                     "status": dict(sorted(collections.Counter(u["status"] for u in units).items())), "units_with_empty_texts": sum(1 for u in units if not u["texts"]),
                     "units_with_stratum": sum(1 for u in units if "stratum" in u), "stratum": dict(sorted(collections.Counter(u.get("stratum") for u in units).items(), key=lambda x: str(x[0]))),
                     "n_rounds": dict(sorted(collections.Counter(u["n_rounds"] for u in units).items())), "unit_keys": sorted({tuple(sorted(u)) for u in units})[:3]}
    # 2 completeness
    keys = collections.Counter((u["item"], u["arm"], u["rep"]) for u in units)
    expected = None
    if a.results and a.items:
        st = json.load(open(os.path.join(a.results, "run_state.json"), encoding="utf-8"))
        its = [r["id"] for r in read_jsonl(a.items)]
        reps = sorted({u["rep"] for u in units})
        subset = {l.strip() for l in open(a.subset_ids, encoding="utf-8") if l.strip()} if a.subset_arm_suffix else None
        expected = {(i, ar, rp) for i in its for ar in st["arms"] for rp in range(st["reps"])
                    if not (subset is not None and ar.endswith(a.subset_arm_suffix) and i not in subset)}      # 020: the by-design combinations are not units
        res["completeness"] = {"expected_units": len(expected), "missing": len(expected - set(keys)), "unexpected": len(set(keys) - expected), "duplicates": sum(1 for v in keys.values() if v > 1),
                               "run_state_status": st.get("status"), "run_state_n_items": st.get("n_items")}
    else:
        res["completeness"] = {"duplicates": sum(1 for v in keys.values() if v > 1)}
    if a.pkg_items and a.items:
        run_items = [json.loads(l) for l in open(a.items, encoding="utf-8") if l.strip()]
        pk = read_jsonl(a.pkg_items)
        by_run = {r["id"]: r for r in run_items}
        res["stratum_source"] = {"items_file_of_the_run": a.items, "package_items_file": a.pkg_items, "same_ids_in_the_same_order": [r["id"] for r in run_items] == [r["id"] for r in pk],
                                 "items_whose_stratum_differs": sum(1 for r in pk if by_run.get(r["id"], {}).get("stratum") != r.get("stratum")),
                                 "items_whose_raw_nl_differs": sum(1 for r in pk if by_run.get(r["id"], {}).get("raw_nl") != r.get("raw_nl"))}
    # 3 coverage
    ltl_s = {r["sentence"] for r in ltl}
    rlz_k = {(r["item_id"], r["arm"], r["rep"], r["sentence"]) for r in rlz}
    miss_l, miss_r = collections.Counter(), collections.Counter()
    miss_l_distinct = set()
    for u in units:
        for t in u["texts"]:
            if t not in ltl_s:
                miss_l[u["status"]] += 1
                miss_l_distinct.add(t)
            if (u["item"], u["arm"], u["rep"], t) not in rlz_k:
                miss_r[u["status"]] += 1
    unit_keys = set(keys)
    res["coverage"] = {"ltl_rows": len(ltl), "ltl_rows_not_in_units": sum(1 for r in ltl if r["sentence"] not in set(sents)), "ltl_parser_ok_false": sum(1 for r in ltl if not r["parser_ok"]),
                       "unit_sentences_without_ltl_row": sum(miss_l.values()), "by_unit_status_ltl": dict(sorted(miss_l.items())), "distinct_sentences_without_ltl_row": len(miss_l_distinct),
                       "rlz_rows": len(rlz), "rlz_rows_with_rep_null": sum(1 for r in rlz if r.get("rep") is None), "rlz_rows_of_no_unit": sum(1 for r in rlz if (r["item_id"], r["arm"], r["rep"]) not in unit_keys),
                       "unit_sentences_without_rlz_row": sum(miss_r.values()), "by_unit_status_rlz": dict(sorted(miss_r.items())), "rlz_results": dict(sorted(collections.Counter(r["result"] for r in rlz).items()))}
    # 4 the tool's loader
    sys.path.insert(0, os.path.join(os.path.abspath(a.pkg), "judging"))
    from nl2fret_judge import units as TU, aggregate as AG          # noqa: E402
    try:
        loaded = TU.load_units(a.units, a.ltl, a.rlz)
        res["tool_loader"] = {"ok": True, "units": len(loaded), "sentences": sum(len(u["sentences"]) for u in loaded), "parser_ok_sentences": sum(1 for u in loaded for s in u["sentences"] if s["parser_ok"]),
                              "sentences_with_ltl_pt": sum(1 for u in loaded for s in u["sentences"] if s["ltl_pt"]),
                              "realizability": dict(sorted(collections.Counter(s["realizability"] for u in loaded for s in u["sentences"]).items()))}
    except Exception as e:  # noqa: BLE001
        res["tool_loader"] = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        loaded = None
    # 5 unit status after the realizability check
    by = collections.defaultdict(dict)
    for r in rlz:
        by[(r["item_id"], r["arm"], r["rep"])][r["sentence_idx"]] = r["result"]
    mine = {}
    for u in units:
        k = (u["item"], u["arm"], u["rep"])
        if u["status"] in ("pipeline", "parse_error"):
            mine[k] = u["status"]
        else:
            rs = list(by.get(k, {}).values())
            mine[k] = "not_run" if not rs else next(o for o in ORDER if o in rs)
    res["unit_status_after_realizability"] = {"recomputed": dict(sorted(collections.Counter(mine.values()).items()))}
    if a.results and os.path.exists(os.path.join(a.results, "units_scored.jsonl")):
        sc = {(u["item_id"], u["arm"], u["rep"]): u["variants"]["vf"]["status"] for u in read_jsonl(os.path.join(a.results, "units_scored.jsonl"))}
        diff = [k for k in mine if sc.get(k) != mine[k]]
        res["unit_status_after_realizability"].update({"run_units_scored": dict(sorted(collections.Counter(sc.values()).items())), "units_compared": len(mine), "units_that_differ": len(diff),
                                                      "examples": [[list(k), mine[k], sc.get(k)] for k in diff[:3]]})
    # 6 texts all versus accepted
    if a.units_accepted and loaded is not None:
        acc = json.load(open(a.units_accepted, encoding="utf-8"))["units"]
        loaded_acc = TU.load_units(a.units_accepted, a.ltl, a.rlz)
        o_all = {(r["item"], r["arm"], r["rep"]): r["outcome"] for r in AG.aggregate(loaded, {})}
        o_acc = {(r["item"], r["arm"], r["rep"]): r["outcome"] for r in AG.aggregate(loaded_acc, {})}
        differ_units = [k for k in o_all if o_all[k] != o_acc.get(k)]
        n_text_diff = sum(1 for u, v in zip(units, acc) if u["texts"] != v["texts"])
        res["texts_all_vs_accepted"] = {"units_whose_texts_differ": n_text_diff, "sentences_all": sum(len(u["texts"]) for u in units), "sentences_accepted": sum(len(u["texts"]) for u in acc),
                                       "units_whose_tool_outcome_differs_with_no_judge_record": len(differ_units), "outcomes_all": dict(sorted(collections.Counter(o_all.values()).items())),
                                       "outcomes_accepted": dict(sorted(collections.Counter(o_acc.values()).items()))}
    # 7 data separation
    ds = {}
    ds["1_item_ids"] = {"all_start_with_LM-": all(i.startswith("LM-") for i in items), "distinct_items": len(items), "exactly_61": len(items) == 61}
    if a.dev_items:
        dev = read_jsonl(a.dev_items)
        dev_ids = {r["id"] for r in dev}
        lm_texts = {}
        if a.items:
            lm_texts = {r["id"]: norm(r.get("raw_nl")) for r in read_jsonl(a.items)}
        dev_texts = {norm(r.get("raw_nl")): r["id"] for r in dev}
        same_text = [(i, dev_texts[t]) for i, t in lm_texts.items() if t and t in dev_texts]
        ds["2_dev_set"] = {"dev_items_file": a.dev_items, "dev_items": len(dev), "dev_id_prefixes": dict(collections.Counter(r["id"].split("-")[0] for r in dev)), "item_ids_starting_with_N-_or_X-": [i for i in items if i[:2] in ("N-", "X-")],
                           "id_intersection": sorted(set(items) & dev_ids), "raw_nl_exact_match_after_normalisation_intersection": same_text, "lm_items_with_raw_nl": len(lm_texts)}
    if a.results:
        st = json.load(open(os.path.join(a.results, "run_state.json"), encoding="utf-8"))
        folder = os.path.basename(os.path.abspath(a.results))
        ds["3_source_folder"] = {"folder": folder, "is_dev_pre_or_mock_name": any(x in folder for x in ("dev", "pre", "mock")), "run_state_status": st.get("status"), "run_state_n_items": st.get("n_items"),
                                 "items_of_the_run_equal_the_items_of_units": (sorted(r["id"] for r in read_jsonl(a.items)) == sorted(items)) if a.items else None}
    ref_sents = set()
    if a.ref:
        for r in read_jsonl(a.ref):
            for g in r["gt_parts"]:
                for p in g:
                    ref_sents.add(p["fretish"])
    src_ltl = read_jsonl(os.path.join(a.results, "fret_ltl.jsonl")) if a.results and os.path.exists(os.path.join(a.results, "fret_ltl.jsonl")) else []
    sset = set(sents)
    ds["4_foreign_sentences"] = {"rows_of_fret_ltl_gen_whose_sentence_is_not_in_units": sum(1 for r in ltl if r["sentence"] not in sset),
                                 "source_ltl_rows": len(src_ltl), "source_rows_not_in_units_and_not_a_reference_sentence": sum(1 for r in src_ltl if r["sentence"] not in sset and r["sentence"] not in ref_sents),
                                 "source_rows_that_are_reference_sentences": sum(1 for r in src_ltl if r["sentence"] in ref_sents), "reference_sentences_in_units_texts": len(sset & ref_sents)}
    other = {}
    for p in a.other_ltl:
        o = {r["sentence"] for r in read_jsonl(p)}
        other[p] = {"rows": len(o), "sentences_also_in_units": len(o & sset)}
    ds["4_foreign_sentences"]["informational_overlap_with_other_runs_by_identical_text"] = other
    res["data_separation"] = ds
    json.dump(res, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))
    ok = (res["tool_loader"]["ok"] and res["completeness"].get("duplicates") == 0 and res["completeness"].get("missing", 0) == 0 and res["completeness"].get("unexpected", 0) == 0
          and res["coverage"]["rlz_rows_with_rep_null"] == 0 and res["coverage"]["rlz_rows_of_no_unit"] == 0 and res["coverage"]["ltl_rows_not_in_units"] == 0)
    print("VALIDATION CORE CHECKS:", "ok" if ok else "NOT OK")
    return 0 if ok else 3


if __name__ == "__main__":
    sys.exit(main())
