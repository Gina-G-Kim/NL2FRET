#!/usr/bin/env python3
"""Build the input-case files in data/cases/ from the experiment data in experiments/.

The script reads experiments/ and writes input-only files (natural-language requirements and their
provenance) to data/cases/. Reference (ground-truth) FRETish is never copied.

Groups
- nasa_papers/      NASA technical reports, NTRS papers and slides, and public-repository case
                    studies (told apart by the `origin` field).
- lockheed_martin/  Original natural-language requirements of the Lockheed Martin Cyber-Physical
                    Challenge problems.
- fsm/              The 12 FSM cases whose text is character-identical in the two groups above.
                    Each case is stored once; its original membership is recorded in
                    fsm/ORIGIN_MAP.csv (lockheed_martin 49 + fsm 12 = 61,
                    nasa_papers 183 + fsm 12 = 195).

Rules
- Reference FRETish fields (gt*, ref_*) are not copied. The originals stay in experiments/, which
  this script only reads.
- One case is one distinct natural-language text (raw_nl). A text that occurs in several experiment
  sets becomes a single record, and every membership is listed in `used_in`.
- Provenance fields are copied only from fields of the source data and from facts confirmed in the
  project documents. Nothing is inferred or invented.
- On every run the script checks that the counts before and after the split are consistent
  (nasa_papers 195, lockheed_martin 61, overlap 12), that the 12 overlapping cases are
  character-identical in both originals, and that no output contains reference fields. Any
  mismatch stops the run with an AssertionError.

Usage (from the repository root):
    python3 -I -B tools/build_cases.py
"""
import collections
import csv
import hashlib
import json
import os
import re
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXP = os.path.join(ROOT, "experiments")
OUT = os.path.join(ROOT, "data", "cases")

# Expected counts before the split; the baseline for the consistency checks below.
PRE_A, PRE_B, PRE_OVERLAP = 195, 61, 12


def rows(rel):
    p = os.path.join(EXP, rel)
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def write_jsonl(path, items):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as w:
        for r in items:
            w.write(json.dumps(r, ensure_ascii=False) + "\n")


def gold_keys(obj, found=None):
    """Recursively collect the keys that start with gt or ref_ (reference fields)."""
    found = [] if found is None else found
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).startswith(("gt", "ref_")):
                found.append(k)
            gold_keys(v, found)
    elif isinstance(obj, list):
        for v in obj:
            gold_keys(v, found)
    return found


stats = {}

# ---------------- Group A (full set before the split): NASA reports, other papers, public repositories ----------------
V1 = "nl2fret/data/pairs_v1.jsonl"
POOL = "nl2fret_v2/data/pool_v2.json"
V2 = "nl2fret_v2/data/pairs_v2.jsonl"
CAL = "nl3/data/calib_items.jsonl"
DEV = "v7_dev0/bench/data/dev_items.jsonl"

pool = json.load(open(os.path.join(EXP, POOL), encoding="utf-8"))
v1, v2, cal, dev = rows(V1), rows(V2), rows(CAL), rows(DEV)
v1_by_id = {r["id"]: r for r in v1}

cases = collections.OrderedDict()  # normalized raw_nl -> case record


def get(raw, cid):
    k = norm(raw)
    if k not in cases:
        cases[k] = {"case_id": cid, "raw_nl": raw.strip(), "used_in": {}}
    return cases[k]


# Source code -> (title, NTRS id), as recorded in the SRC table of nl2fret/NL2FRET_PROMPT_v1.md and in the
# source_title field of pairs_v1.
v1_title = {r["source_doc"]: (r["source_title"], r["ntrs"]) for r in v1}

for r in pool:
    c = get(r["raw_nl"], r["pid"])
    c["source_code"] = r["src"]
    c["origin"] = r["origin"]
    c["provenance"] = r["prov"]
    c["used_in"]["pool_v2"] = r["pid"]
for r in v1:
    c = get(r["raw_nl"], r["id"])
    c.setdefault("source_code", r["source_doc"])
    if "provenance" not in c:
        t, n = v1_title[r["source_doc"]]
        c["origin"] = "nasa_tr" if t.startswith("NASA/TM") else "paper_or_slides"
        c["provenance"] = {"title": t, "ntrs": n, "location": r["source_location"], "pdf_page": r.get("pdf_page"), "verify": r.get("verify_method")}
    c["used_in"]["v1_pairs"] = r["id"]
for r in v2:
    c = get(r["raw_nl"], r["pid"])
    c["used_in"]["v2_main"] = r["id"]
    if r.get("nl_fretish_like"):
        c["nl_fretish_like"] = True
for r in cal:
    c = get(r["raw_nl"], r["pid"])
    c["used_in"]["nl3_calib"] = r["id"]
for r in dev:
    c = get(r["raw_nl"], r["id"])
    c["used_in"]["v7_dev"] = {"id": r["id"], "role": r["role"]}
    c["stratum"] = r["stratum"]
    c["family"] = r["family"]

A_full = []
for c in cases.values():
    A_full.append({"case_id": c["case_id"], "raw_nl": c["raw_nl"], "source_code": c.get("source_code"), "origin": c.get("origin"),
                   **({"stratum": c["stratum"]} if "stratum" in c else {}), **({"nl_fretish_like": True} if c.get("nl_fretish_like") else {}),
                   "provenance": c.get("provenance"), "used_in": c["used_in"]})

# ---------------- Group B (full set before the split): NASA Lockheed Martin cases ----------------
lm8 = rows("v8_dict8/bench/data/lm_items.jsonl")             # natural-language-only version (no references)
lm4_rows = rows("nl4/data/lm_items.jsonl")
lm4 = {r["id"]: r for r in lm4_rows}                          # used for the provenance field nl_source
assert [r["raw_nl"] for r in lm8] == [lm4[r["id"]]["raw_nl"] for r in lm8]
lm8_by_id = {r["id"]: r for r in lm8}
used = collections.defaultdict(list)
USED_DIRS = ["nl4/results_smoke", "nl5/results_smoke2", "nl6/results_pre", "nl7/results_pre", "nl7/results_lm", "v8_dict8/bench/results_dict8"]
for rel in USED_DIRS:
    for r in rows(rel + "/snapshot/items_used.jsonl"):
        used[r["id"]].append(rel)
B_full = []
for r in lm8:
    B_full.append({"case_id": r["id"], "challenge": r["challenge"], "raw_nl": r["raw_nl"], "stratum": r["stratum"],
                   "nl_source": lm4[r["id"]]["nl_source"], "used_in": sorted(used[r["id"]])})

assert len(A_full) == PRE_A and len(B_full) == PRE_B, (len(A_full), len(B_full))

# ---------------- Overlap: cases whose text is character-identical in both groups -> fsm/ ----------------
bmap = {norm(r["raw_nl"]): r["id"] for r in lm8}
overlap = [(a, bmap[norm(a["raw_nl"])]) for a in A_full if norm(a["raw_nl"]) in bmap]
assert len(overlap) == PRE_OVERLAP, len(overlap)

F, ORIGIN_MAP = [], []
for a, lm_id in overlap:
    # Compare the raw text of the two original files directly, without relying on normalization
    # (for these cases, case_id is the pairs_v1 id).
    rc_raw = v1_by_id[a["case_id"]]["raw_nl"]
    lm_raw = lm8_by_id[lm_id]["raw_nl"]
    assert rc_raw == lm_raw == lm4[lm_id]["raw_nl"], (a["case_id"], lm_id)
    assert a["source_code"] == "RC22" and lm8_by_id[lm_id]["challenge"] == "01_FSM", (a["case_id"], lm_id)
    F.append({"case_id": lm_id, "raw_nl": lm_raw, "challenge": "01_FSM", "stratum": lm8_by_id[lm_id]["stratum"],
              "origins": [{"original_group": "lockheed_martin", "original_id": lm_id, "nl_source": lm4[lm_id]["nl_source"]},
                          {"original_group": "nasa_papers", "original_id": a["case_id"], "source_code": a["source_code"],
                           "origin": a["origin"], "provenance": a["provenance"]}],
              "used_in": {"lockheed_martin": sorted(used[lm_id]), "nasa_papers": a["used_in"]}})
    ORIGIN_MAP.append([lm_id, "lockheed_martin", lm_id, "01_FSM", "nasa_papers:" + a["case_id"], "exact"])
    ORIGIN_MAP.append([lm_id, "nasa_papers", a["case_id"], "RC22", "lockheed_martin:" + lm_id, "exact"])

fsm_a_ids = {a["case_id"] for a, _ in overlap}
fsm_lm_ids = {lm for _, lm in overlap}
A = [a for a in A_full if a["case_id"] not in fsm_a_ids]
B = [b for b in B_full if b["case_id"] not in fsm_lm_ids]

# ---------------- Write outputs ----------------
write_jsonl(os.path.join(OUT, "nasa_papers", "cases.jsonl"), A)
write_jsonl(os.path.join(OUT, "lockheed_martin", "cases.jsonl"), B)
write_jsonl(os.path.join(OUT, "fsm", "cases.jsonl"), F)
with open(os.path.join(OUT, "fsm", "ORIGIN_MAP.csv"), "w", newline="", encoding="utf-8") as w:
    cw = csv.writer(w)
    cw.writerow(["case_id", "original_group", "original_id", "original_source", "same_case_as", "text_match"])
    cw.writerows(ORIGIN_MAP)
shutil.copyfile(os.path.join(EXP, "v8_dict8/bench/data/sigdict.json"), os.path.join(OUT, "lockheed_martin", "sigdict.json"))

# Inputs of the legacy experiments (FRETish sentences rather than natural language). ref_* fields are not
# copied. These records stay in nasa_papers.
leg = []
for r in rows("fret_template_bench/data/requirements.jsonl"):
    leg.append({"set": "fret_template_bench", "id": r["id"], "text_kind": "fretish", "text": r["fretish"], "source": r["source"],
                "pdf_page": r.get("pdf_page"), "verified": r.get("verified")})
for r in rows("fret_retest_v2/data/requirements_v2.jsonl"):
    leg.append({"set": "fret_retest_v2", "id": r["id"], "text_kind": "fretish", "text": r["fretish"], "source_code": r["source_doc"],
                "source_location": r["source_location"], "stratum": r["stratum"], "kind": r["kind"]})
write_jsonl(os.path.join(OUT, "nasa_papers", "legacy_fretish_inputs.jsonl"), leg)

# ---------------- Consistency checks (stop on any mismatch) ----------------
# 1) The counts after the split are consistent with the counts before it (the 12 overlapping cases appear
#    once, in fsm).
assert (len(A), len(B), len(F)) == (PRE_A - PRE_OVERLAP, PRE_B - PRE_OVERLAP, PRE_OVERLAP)
assert len(A) + len(B) + len(F) == PRE_A + PRE_B - PRE_OVERLAP
# 2) ORIGIN_MAP is sufficient to reconstruct both pre-split groups exactly.
lm_rebuilt = {b["case_id"] for b in B} | {r[2] for r in ORIGIN_MAP if r[1] == "lockheed_martin"}
a_rebuilt = {a["case_id"] for a in A} | {r[2] for r in ORIGIN_MAP if r[1] == "nasa_papers"}
assert lm_rebuilt == {b["case_id"] for b in B_full} and len(lm_rebuilt) == PRE_B
assert a_rebuilt == {a["case_id"] for a in A_full} and len(a_rebuilt) == PRE_A
# 3) No natural-language text occurs twice across the three groups.
allnl = [norm(x["raw_nl"]) for x in A + B + F]
assert len(allnl) == len(set(allnl)), "duplicate natural-language text across groups"
# 4) No output record contains reference (ground-truth) fields.
for name, items in (("nasa_papers", A), ("lockheed_martin", B), ("fsm", F), ("legacy", leg)):
    assert not gold_keys(items), (name, gold_keys(items))
# 5) The 12 fsm cases are character-identical to both originals (checked by the == comparison in the loop above).
stats["checks"] = {"pre_split": {"nasa_papers": PRE_A, "lockheed_martin": PRE_B, "overlap": PRE_OVERLAP, "distinct_total": PRE_A + PRE_B - PRE_OVERLAP},
                   "post_split": {"nasa_papers": len(A), "lockheed_martin": len(B), "fsm": len(F), "distinct_total": len(A) + len(B) + len(F)},
                   "fsm_exact_match_with_both_originals": True, "gold_keys_in_outputs": 0, "reconstructed_lockheed_martin": len(lm_rebuilt),
                   "reconstructed_nasa_papers": len(a_rebuilt), "duplicate_nl_across_groups": 0}

stats["A_cases"] = len(A)
stats["A_by_origin"] = dict(collections.Counter(a["origin"] for a in A))
stats["A_by_source_code"] = dict(collections.Counter(a["source_code"] for a in A))
stats["A_set_membership"] = {s: sum(1 for a in A if s in a["used_in"]) for s in ("v1_pairs", "pool_v2", "v2_main", "nl3_calib", "v7_dev")}
stats["A_dev_roles"] = dict(collections.Counter(r["role"] for r in dev))
stats["A_legacy"] = dict(collections.Counter(x["set"] for x in leg))
stats["B_cases"] = len(B)
stats["B_by_challenge"] = dict(collections.Counter(b["challenge"] for b in B))
stats["B_by_stratum"] = dict(collections.Counter(b["stratum"] for b in B))
stats["B_files"] = dict(collections.Counter(b["nl_source"]["file"] for b in B))
dirs = sorted({x for v in used.values() for x in v})
stats["used_in_result_dirs"] = {rel: {"lockheed_martin": sum(1 for b in B if rel in b["used_in"]),
                                      "fsm": sum(1 for f in F if rel in f["used_in"]["lockheed_martin"]),
                                      "original_61_basis": sum(1 for b in B_full if rel in b["used_in"])} for rel in dirs}
stats["F_cases"] = len(F)
stats["F_set_membership_nasa_papers"] = {s: sum(1 for f in F if s in f["used_in"]["nasa_papers"]) for s in ("v1_pairs", "pool_v2", "v2_main", "nl3_calib", "v7_dev")}
stats["sigdict_sha256"] = sha(os.path.join(OUT, "lockheed_martin", "sigdict.json"))

json.dump(stats, open(os.path.join(OUT, "_build_stats.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps(stats, ensure_ascii=False, indent=1))
