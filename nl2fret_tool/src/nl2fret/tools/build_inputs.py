#!/usr/bin/env python3
"""Builds the bench inputs from the fixed dataset and dictionary (data/dataset, data/dictionary). No model call.

outputs
  src/nl2fret/data/lm_items.jsonl one item per NL requirement (id, raw_nl, challenge, family); all challenges
  src/nl2fret/data/lm_items_fsm.jsonl the 01_FSM items only (FSM test)
  src/nl2fret/data/sigdict.json   {challenge number: dictionary table text} given to the model at the FRETish stage
  data/reference/lm_reference_with_ltl.jsonl   reference parts and versions with their compiled LTL (answer key, judge side only)
usage: python3 -m nl2fret.tools.build_inputs   (run from the project root)
"""
import csv
import json
import os
import sys

from nl2fret.paths import PROJECT  # noqa: E402

ROOT = str(PROJECT)
KIND_ORDER = ["signal", "constant", "defined", "element", "component", "function"]


def dict_text(rows):
    rows = sorted(rows, key=lambda r: (KIND_ORDER.index(r["kind"]), r["name"].lower(), r["name"]))
    lines = ["name | kind | direction | type | description | definition"]
    for r in rows:
        lines.append(" | ".join([r["name"], r["kind"], r["direction"], r["type"], r["description"].strip(), r["definition"].strip()]))
    return "\n".join(lines)


def main():
    ds = [json.loads(l) for l in open(os.path.join(ROOT, "data/dataset/lm_dataset_final.jsonl"), encoding="utf-8") if l.strip()]
    items = [{"id": x["item_id"], "raw_nl": x["natural_language"], "family": x["challenge"], "challenge": x["challenge"]} for x in ds]
    for name, sel in (("lm_items.jsonl", items), ("lm_items_fsm.jsonl", [i for i in items if i["challenge"] == "01_FSM"])):
        with open(os.path.join(ROOT, "src/nl2fret/data", name), "w", encoding="utf-8") as f:
            for i in sel:
                f.write(json.dumps(i, ensure_ascii=False) + "\n")
    rows = list(csv.DictReader(open(os.path.join(ROOT, "data/dictionary/lm_dictionary.csv"), encoding="utf-8-sig")))
    by = {}
    for r in rows:
        by.setdefault(r["challenge"], []).append(r)
    sig = {ch.split("_")[0]: dict_text(rs) for ch, rs in sorted(by.items())}
    json.dump(sig, open(os.path.join(ROOT, "src/nl2fret/data/sigdict.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    json.dump(sig, open(os.path.join(ROOT, "data/reference/sigdict.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(ROOT, "data/reference/lm_reference_with_ltl.jsonl"), "w", encoding="utf-8") as f:
        for x in ds:
            parts = []
            for p in x["reference_parts"]:
                parts.append([{"reqid": v["reqid"], "fretish": v["fretish"], "source": v["source"],
                               "ltl": {"past_time": v["ltl_pt"], "future_time": v["ltl_ft"]}, "ltl_source": v["ltl_source"]} for v in p])
            f.write(json.dumps({"id": x["item_id"], "challenge": x["challenge"], "raw_nl": x["natural_language"], "mapping_basis": x["mapping_basis"],
                                "mapping_note": x["mapping_note"], "gt_parts": parts}, ensure_ascii=False) + "\n")
    print(f"items {len(items)} (fsm {sum(1 for i in items if i['challenge'] == '01_FSM')}); dictionary challenges {len(sig)}; reference items {len(ds)}")


if __name__ == "__main__":
    sys.exit(main())
