"""Part level judging (v9). One unit = item x arm x repetition. Every reference PART of the item is judged; a part may have several reference VERSIONS.
For one part the unit's accepted FRETish sentences are each compared with each version (all pairs are judged and recorded). The representative result of the part is the best
pair (SAME < PROOF < REFUTE < NEITHER < N/M < UND; a tie keeps the earliest sentence, then the earliest version). The other pairs stay in judge_records.jsonl as result records.
Part success = SAME or PROOF. Unit: n_parts_success / n_parts and all_parts_success. A unit without an accepted sentence fails every part (role NO_SENTENCE).
Before a pair is judged the identifiers of the generated formula are aligned to the dictionary of the challenge (dict_align.py); the record keeps the original formula."""
import json
import os

from . import dict_align as DA
from .judge import judge_pair

ORDER = {"SAME": 0, "PROOF": 1, "REFUTE": 2, "NEITHER": 3, "NM": 4, "UND": 5}
SUCCESS = ("SAME", "PROOF")


def load_reference_parts(path):
    """-> {item: {"challenge": str, "parts": [[(ref_id, ltl_pt, ltl_ft), ...versions...], ...]}}"""
    out = {}
    for line in open(path, encoding="utf-8"):
        if not line.strip():
            continue
        r = json.loads(line)
        parts = []
        for grp in r["gt_parts"]:
            parts.append([(p["reqid"], (p.get("ltl") or {}).get("past_time"), (p.get("ltl") or {}).get("future_time")) for p in grp])
        out[r["id"]] = {"challenge": r["challenge"], "parts": parts}
    return out


def role_key(rec):
    if rec.get("role"):
        return rec["role"]
    return "NM" if rec.get("nm") else "UND"


def pair_id(u, si, pi, vi):
    return f"{u['item']}|{u['arm']}|{u['rep']}|s{si}|p{pi}|v{vi}"


def judge_units(units, refs, dict_names, engine, recorder, cex_path, mode="anchor", cap=128, aux=False, run_id="", progress=None):
    n = 0
    for u in units:
        ref = refs.get(u["item"])
        if not ref:
            continue
        names = dict_names.get(ref["challenge"], set())
        for si, s in enumerate(u["sentences"]):
            if not s["parser_ok"] or not s["ltl_pt"]:
                continue
            gen_pt, al = DA.align_formula(s["ltl_pt"], names)
            gen_ft = s.get("ltl_ft")          # future-time form is recorded as generated; the judge works on the past-time form
            for pi, versions in enumerate(ref["parts"], 1):
                for vi, (rid, rpt, rft) in enumerate(versions, 1):
                    pid = pair_id(u, si, pi, vi)
                    if recorder.has(pid) or not rpt:
                        continue
                    r = judge_pair(gen_pt, rpt, engine, mode=mode, cap=cap, aux=aux, pair_id=pid, gen_ft=gen_ft, ref_ft=rft,
                                   meta={"group": "generated", "run_id": run_id})
                    smv = r.pop("_smv", {})
                    r.update({"item": u["item"], "arm": u["arm"], "rep": u["rep"], "sentence": s["text"], "sentence_index": si, "part": pi, "version": vi, "reference_id": rid,
                              "pred_pt_original": s["ltl_pt"], "dict_alignment": al,
                              "renamed_beyond_dictionary": any(k != v for k, v in ((r.get("alignment") or {}).get("mapping") or {}).items())})
                    recorder.write(r, smv)
                    if r.get("counterexample_required") or r.get("counterexamples"):
                        with open(cex_path, "a", encoding="utf-8") as f:
                            f.write(json.dumps({"pair_id": pid, "item": u["item"], "arm": u["arm"], "rep": u["rep"], "sentence": s["text"], "part": pi, "version": vi, "reference_id": rid,
                                                "role": role_key(r), "required": r.get("counterexample_required"), "status": r.get("counterexample_status"),
                                                "counterexamples": r.get("counterexamples"), "record": f"judge_records.jsonl#{pid}"}, ensure_ascii=False) + "\n")
                    n += 1
                    if progress and n % 25 == 0:
                        progress(n)
    return n


def assemble(units, refs, records):
    """records: {pair_id: record}. -> one row per unit with the representative result per part (recomputed from the raw records only)."""
    rows = []
    for u in units:
        ref = refs.get(u["item"])
        if not ref:
            continue
        parts = []
        for pi, versions in enumerate(ref["parts"], 1):
            cands = []
            for si, s in enumerate(u["sentences"]):
                for vi, (rid, _, _) in enumerate(versions, 1):
                    rec = records.get(pair_id(u, si, pi, vi))
                    if rec is not None:
                        cands.append((ORDER[role_key(rec)], si, vi, rec, rid))
            if not cands:
                parts.append({"part": pi, "n_versions": len(versions), "role": "NO_SENTENCE", "success": False, "representative": None, "pairs": []})
                continue
            cands.sort(key=lambda c: (c[0], c[1], c[2]))
            best = cands[0]
            parts.append({"part": pi, "n_versions": len(versions), "role": role_key(best[3]), "success": role_key(best[3]) in SUCCESS,
                          "representative": {"pair_id": best[3]["pair_id"], "sentence_index": best[1], "version": best[2], "reference_id": best[4]},
                          "pairs": [{"pair_id": c[3]["pair_id"], "sentence_index": c[1], "version": c[2], "reference_id": c[4], "role": role_key(c[3])} for c in sorted(cands, key=lambda c: (c[1], c[2]))]})
        ok = sum(1 for p in parts if p["success"])
        rows.append({"item": u["item"], "arm": u["arm"], "rep": u["rep"], "challenge": ref["challenge"], "n_sentences": len(u["sentences"]), "n_parts": len(parts), "n_parts_success": ok,
                     "all_parts_success": ok == len(parts), "any_part_success": ok > 0, "parts": parts})
    return rows
