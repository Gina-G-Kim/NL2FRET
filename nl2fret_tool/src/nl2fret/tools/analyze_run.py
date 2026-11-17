#!/usr/bin/env python3
"""Post-run analysis with the metrics fixed BEFORE a run (archive/nl2fret_tool_docs/v1.4/docs/ANALYSIS_PLAN.md). Reads only files of the run folder, the reference, the item audit and (optional) the judge controls.
No model call. Every number is computed; the report states definitions, not conclusions.

usage: python3 tools/analyze_run.py --run RUN [--controls CTRLDIR] [--out RUN/analysis] [--engine z3|nusmv]
Metrics (per arm; unit = item x arm x rep; part = reference part of the item):
  lenient   judge success: SAME or PROOF (as in the judge)                                       [identical to summary.md; checked]
  strict    lenient AND the generated formula is satisfiable AND no identifier was renamed beyond the dictionary
            (the controls show an unsatisfiable formula is scored PROOF; free renaming is a judge convenience)
  ceiling   parts whose reference version(s) the judge can compare with themselves (controls C+ID); success is impossible on the others
  dp        decision-point agreement of the representative pair (scope, condition kind, timing) read from the FRETish texts
  cause     every non-strict part gets exactly ONE primary cause by the fixed order below; all matching causes are also kept (labels_all)
            PIPELINE (no accepted sentence) > INSTRUMENT_CEILING > INSTRUMENT_UND_NM > INSTRUMENT_STRICT (lenient success removed by strict)
            > DATA (audit: no NL-linked reference row, or conflicting duplicate definition) > TEMPLATE_INFO_LOSS (stage A recorded unmapped_content)
            > DECISION:<points that differ> > EXPRESSION (all decision points agree, formulas differ)
"""
import argparse, collections, json, os, sys, csv
HERE = os.path.dirname(os.path.abspath(__file__))
from nl2fret.paths import PROJECT  # noqa: E402

ROOT = str(PROJECT)
from nl2fret.tools.decision_points import decision_points
from nl2fret_judge.judge import judge_pair           # noqa: E402
from nl2fret_judge.engines import NuSMVEngine, Z3Engine   # noqa: E402

SUCCESS = ("SAME", "PROOF")


def jl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()] if os.path.exists(p) else []


def pct(a, b):
    return f"{a}/{b} = {a / b:.3f}" if b else f"{a}/0"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--controls")
    ap.add_argument("--reference", default=os.path.join(ROOT, "data/reference/lm_reference_with_ltl.jsonl"))
    ap.add_argument("--audit", default=os.path.join(ROOT, "data/audit/item_validity_audit.csv"))
    ap.add_argument("--engine", choices=["z3", "nusmv"], default="z3")
    ap.add_argument("--nusmv", default="NuSMV")
    ap.add_argument("--out")
    a = ap.parse_args()
    out = a.out or os.path.join(a.run, "analysis")
    os.makedirs(out, exist_ok=True)
    eng = Z3Engine(8) if a.engine == "z3" else NuSMVEngine(a.nusmv.split(), timeout=120, workdir=os.path.join(out, "work"))

    refs = {}
    for r in jl(a.reference):
        refs[r["id"]] = r["gt_parts"]
    audit = {r["id"]: r for r in csv.DictReader(open(a.audit, encoding="utf-8-sig"))}
    records = {r["pair_id"]: r for r in jl(f"{a.run}/judge/judge_records.jsonl")}
    parts = jl(f"{a.run}/judge/part_results.jsonl")
    units = {(u["item"], u["arm"], u["rep"]): u for u in json.load(open(f"{a.run}/inputs/units.json", encoding="utf-8"))["units"]}
    calls = {r["stage_key"]: r for r in jl(f"{a.run}/gen/calls.jsonl")}

    # ceiling from controls: reference rows the judge cannot compare with themselves
    not_self = set()
    ctrl = None
    if a.controls and os.path.exists(f"{a.controls}/controls.jsonl"):
        for r in jl(f"{a.controls}/controls.jsonl"):
            if r["control"] == "C+ID" and r.get("role") != "SAME":
                not_self.add((r["item"], r["part"], r["version"]))
        ctrl = json.load(open(f"{a.controls}/controls_summary.json"))

    sat_cache = {}

    def strict_flags(rec):
        """-> (unsat, renamed). Satisfiability of the generated formula by the judge's own engine (aux query)."""
        flags = {"unsat": False, "renamed": bool(rec.get("renamed_beyond_dictionary"))}
        key = (rec["pred_pt"], rec["gt_pt"])
        if key not in sat_cache:
            r = judge_pair(rec["pred_pt"], rec["gt_pt"], eng, aux=True, pair_id="sat")
            sat_cache[key] = r.get("gen_sat")
        flags["unsat"] = sat_cache[key] is False
        flags["sat_unknown"] = sat_cache[key] is None
        return flags

    rows = []
    for p in parts:
        item, arm, rep = p["item"], p["arm"], p["rep"]
        base = arm.split("+")[0]
        u = units.get((item, arm, rep)) or {}
        for pt in p["parts"]:
            ver_ids = list(range(1, pt["n_versions"] + 1))
            ceiling_ok = any((item, pt["part"], v) not in not_self for v in ver_ids) if ctrl else None
            rec = records.get(pt["representative"]["pair_id"]) if pt.get("representative") else None
            role = pt["role"]
            row = {"item": item, "arm": arm, "rep": rep, "part": pt["part"], "role": role, "lenient": bool(pt["success"]), "ceiling_ok": ceiling_ok,
                   "strict": False, "flags": {}, "dp_gen": None, "dp_ref": None, "dp_diff": None, "labels_all": [], "cause": None}
            if rec:
                vi = pt["representative"]["version"]
                ref_f = refs[item][pt["part"] - 1][vi - 1]["fretish"]
                gen_f = (u.get("texts") or [None])[pt["representative"]["sentence_index"]]
                row["dp_ref"] = decision_points(ref_f)
                row["dp_gen"] = decision_points(gen_f) if gen_f else None
                if row["dp_gen"]:
                    row["dp_diff"] = [k for k in ("scope", "reading", "ntiming") if row["dp_gen"][k] != row["dp_ref"][k]]
                if pt["success"]:
                    fl = strict_flags(rec)
                    row["flags"] = fl
                    row["strict"] = not fl["unsat"] and not fl["renamed"]
            # causes (only parts that are not strict successes)
            if not row["strict"]:
                L = []
                if role == "NO_SENTENCE":
                    L.append("PIPELINE")
                if ctrl and not ceiling_ok:
                    L.append("INSTRUMENT_CEILING")
                if role in ("UND", "NM"):
                    L.append("INSTRUMENT_UND_NM")
                if row["lenient"]:
                    L.append("INSTRUMENT_STRICT")
                au = audit.get(item, {})
                if au.get("no_nl_linked_row_heuristic") == "True" or au.get("conflicting_duplicate_lhs"):
                    L.append("DATA")
                if base != "DIRECT" and role not in ("NO_SENTENCE",):
                    ar = calls.get(f"{item}|{base}|{rep}|A") or {}
                    if ((ar.get("parsed") or {}).get("unmapped_content")):
                        L.append("TEMPLATE_INFO_LOSS")
                if row["dp_diff"]:
                    L.append("DECISION:" + "+".join(row["dp_diff"]))
                elif row["dp_gen"] is not None and role not in ("UND", "NM", "NO_SENTENCE") and not row["lenient"]:
                    L.append("EXPRESSION")
                row["labels_all"] = L
                row["cause"] = L[0] if L else "UNLABELED"
            rows.append(row)
    with open(f"{out}/part_analysis.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    arms = sorted({r["arm"] for r in rows}, key=lambda x: (not x.startswith("DIRECT"), x))
    md = ["# Run analysis (metrics fixed in archive/nl2fret_tool_docs/v1.4/docs/ANALYSIS_PLAN.md)", "", f"run: {a.run}; engine for the satisfiability check: {eng.name}; parts analysed: {len(rows)}", ""]
    if ctrl:
        md += ["## Instrument controls (judge_controls.py)", "", "| control | n | flagged | meaning |", "|---|---|---|---|"]
        for k, v in ctrl.items():
            md.append(f"| {k} | {v['n']} | {v['flag_count']}/{v['n']} = {v['flag_rate']} | {v['flag']} |")
        md.append("")
    md += ["## Success per arm (parts)", "", "| arm | parts | lenient | SAME | PROOF | strict | PROOF removed: unsat | removed: renamed | parts with judgeable reference |", "|---|---|---|---|---|---|---|---|---|"]
    for ar in arms:
        R = [r for r in rows if r["arm"] == ar]
        n = len(R)
        same = sum(1 for r in R if r["role"] == "SAME")
        proof = sum(1 for r in R if r["role"] == "PROOF")
        md.append(f"| {ar} | {n} | {pct(sum(r['lenient'] for r in R), n)} | {same} | {proof} | {pct(sum(r['strict'] for r in R), n)} | "
                  f"{sum(1 for r in R if r['lenient'] and r['flags'].get('unsat'))} | {sum(1 for r in R if r['lenient'] and r['flags'].get('renamed'))} | "
                  f"{pct(sum(1 for r in R if r['ceiling_ok']), n) if ctrl else 'n/a'} |")
    md += ["", "## Decision-point agreement with the representative reference version (parts with a generated sentence)", "",
           "reading = EDGE / EVERY_TIME / UNCOND / UNLESS (decision_points.py); ntiming = semantic equivalence class of (condition form, timing) from data/timing_semantics.json (official parser + engine)", "",
           "| arm | n | scope same | reading same | ntiming same | all three same | gen EDGE | gen EVERY_TIME | ref EDGE | ref EVERY_TIME |", "|---|---|---|---|---|---|---|---|---|---|"]
    for ar in arms:
        R = [r for r in rows if r["arm"] == ar and r["dp_gen"]]
        n = len(R)
        md.append(f"| {ar} | {n} | {pct(sum('scope' not in r['dp_diff'] for r in R), n)} | {pct(sum('reading' not in r['dp_diff'] for r in R), n)} | "
                  f"{pct(sum('ntiming' not in r['dp_diff'] for r in R), n)} | {pct(sum(not r['dp_diff'] for r in R), n)} | "
                  f"{pct(sum(r['dp_gen']['reading'] == 'EDGE' for r in R), n)} | {pct(sum(r['dp_gen']['reading'] == 'EVERY_TIME' for r in R), n)} | "
                  f"{pct(sum(r['dp_ref']['reading'] == 'EDGE' for r in R), n)} | {pct(sum(r['dp_ref']['reading'] == 'EVERY_TIME' for r in R), n)} |")
    md += ["", "## Primary cause of every part that is not a strict success (exactly one cause per part)", ""]
    causes = sorted({r["cause"] for r in rows if r["cause"]})
    md += ["| arm | non-strict parts | " + " | ".join(causes) + " |", "|---|---|" + "---|" * len(causes)]
    for ar in arms:
        R = [r for r in rows if r["arm"] == ar and not r["strict"]]
        c = collections.Counter(r["cause"] for r in R)
        md.append(f"| {ar} | {len(R)} | " + " | ".join(str(c.get(k, 0)) for k in causes) + " |")
    md += ["", "## Strata (all arms pooled; parts)", "", "| stratum | parts | lenient | strict |", "|---|---|---|---|"]

    def stratum(name, fn):
        R = [r for r in rows if fn(r)]
        md.append(f"| {name} | {len(R)} | {pct(sum(r['lenient'] for r in R), len(R))} | {pct(sum(r['strict'] for r in R), len(R))} |")
    stratum("item mapping_basis = rationale", lambda r: audit.get(r["item"], {}).get("mapping_basis") == "rationale")
    stratum("item mapping_basis = id_order", lambda r: audit.get(r["item"], {}).get("mapping_basis") == "id_order")
    stratum("item has no NL-linked reference row (heuristic)", lambda r: audit.get(r["item"], {}).get("no_nl_linked_row_heuristic") == "True")
    stratum("item has conflicting duplicate definition", lambda r: bool(audit.get(r["item"], {}).get("conflicting_duplicate_lhs")))
    if ctrl:
        stratum("judge cannot compare the reference with itself", lambda r: r["ceiling_ok"] is False)
        stratum("judge can compare the reference with itself", lambda r: r["ceiling_ok"] is True)
    md += ["", "## Check against the run's own summary", ""]
    sj = os.path.join(a.run, "summary.json")
    if os.path.exists(sj):
        s = json.load(open(sj))
        md.append("summary.json present; compare the lenient column with its part success counts (printed below by arm).")
        for ar in arms:
            md.append(f"- {ar}: recomputed lenient = {sum(r['lenient'] for r in rows if r['arm'] == ar)}")
    open(f"{out}/analysis.md", "w").write("\n".join(md) + "\n")
    print("\n".join(md))


if __name__ == "__main__":
    main()
