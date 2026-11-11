#!/usr/bin/env python3
"""Deterministic preflight gate (stdlib only). Runs the checks P1..P25 on the preflight results folder and writes
PREFLIGHT_CHECK.md and preflight_values.json into it. Exit code 0 = no gate check failed, 1 = at least one gate check failed.
Checks marked INFO never fail the gate; they only report values. The script never judges meaning (no equivalence)."""
import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--results", default="results_pre")
ap.add_argument("--data", default="data/lm_preflight.jsonl")
ap.add_argument("--all-items", default="data/lm_items.jsonl")
ap.add_argument("--annotation", default="data/lm_slot_annotation.jsonl")
ap.add_argument("--review", default="data/lm_mapping_review.json")
ap.add_argument("--main", default="results_lm", help="folder of the main run; must not be the preflight folder")
ap.add_argument("--reps", type=int, default=2)
a = ap.parse_args()

R = Path(a.results)
M = R / "metrics"
SNAP = R / "snapshot"
rows_out = []   # (id, title, gate, verdict, evidence)
vals = {}


def jl(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def rd(p):
    return list(csv.DictReader(open(p, encoding="utf-8")))


def rec(pid, title, gate, ok, evidence, value=None):
    verdict = "INFO" if gate == "info" else ("PASS" if ok else "FAIL")
    rows_out.append((pid, title, gate, verdict, evidence))
    if value is not None:
        vals[pid] = value


def safe(fn, pid, title, gate):
    try:
        fn()
    except Exception as e:  # a crashed check is a failed check for gate rows
        rec(pid, title, gate, False, "check crashed: %s: %s" % (type(e).__name__, e))


data = jl(a.data)
all_items = jl(a.all_items)
info = json.loads((SNAP / "run_info.json").read_text(encoding="utf-8"))
arms = info["arms"]
n_arms = len(arms)
n_items = len(data)
exp_units = n_items * n_arms * a.reps
calls = jl(R / "calls.jsonl")
ref_texts = {v["fretish"] for d in data for part in d["gt_parts"] for v in part}


def norm(s):
    return re.sub(r"\s+", "", s).lower()


def p01():
    units = jl(R / "units_scored.jsonl")
    keys = {(u["item_id"], u["arm"], u["rep"]) for u in units}
    vs = Counter(",".join(sorted(u["variants"])) for u in units)
    ok = len(keys) == exp_units and set(vs) == {"v0,vf,vn"}
    rec("P1", "all units recorded with 3 variants", "gate", ok, "distinct units %d (expected %d = %d items x %d arms x %d reps); variant sets %s" % (len(keys), exp_units, n_items, n_arms, a.reps, dict(vs)))


def p02():
    um = rd(M / "lm_unit_metrics.csv")
    c = defaultdict(lambda: [0, 0])
    for r in um:
        if r["variant"] == "vf":
            c[r["arm"]][1] += 1
            if r["no_output"] != "1":
                c[r["arm"]][0] += 1
    ok = set(c) == set(arms) and all(v[0] >= 1 for v in c.values())
    rec("P2", "every arm produced output", "gate", ok, "; ".join("%s %d/%d" % (k, v[0], v[1]) for k, v in sorted(c.items())))


def p03():
    ltl = jl(R / "fret_ltl.jsonl")
    ref_rows = [r for r in ltl if r["sentence"] in ref_texts]
    gen_rows = [r for r in ltl if r["sentence"] not in ref_texts]
    acc = [r for r in gen_rows if r["parser_ok"]]
    ok3 = len({r["sentence"] for r in ref_rows}) == len(ref_texts)
    rec("P3", "reference sentences have parser/LTL records", "gate", ok3,
        "distinct reference texts %d, rows found %d, parser_ok %d, ltl_ft non-empty %d" % (len(ref_texts), len(ref_rows), sum(1 for r in ref_rows if r["parser_ok"]), sum(1 for r in ref_rows if r.get("ltl_ft"))))
    ok4 = len(acc) > 0 and any(r.get("ltl_ft") for r in acc)
    rec("P4", "generated sentences have parser/LTL records", "gate", ok4, "distinct generated sentences %d, parser accepted %d, accepted with ltl_ft %d" % (len(gen_rows), len(acc), sum(1 for r in acc if r.get("ltl_ft"))))


def p05():
    pat = re.compile(r"equiv|stronger|weaker|implies|entail", re.I)
    hits = []
    for f in sorted(M.glob("*.csv")):
        hits += [(f.name, c) for c in next(csv.reader(open(f, encoding="utf-8"))) if pat.search(c)]
    keys = set()

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if pat.search(k):
                    keys.add(k)
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    for f in sorted(M.glob("*.jsonl")):
        for r in jl(f):
            walk(r)
    gl = [l.strip()[:160] for l in open(M / "METRICS_GLOSSARY.md", encoding="utf-8") if pat.search(l)]
    rec("P5", "the tool does not judge (no judgment column or key)", "gate", not hits and not keys,
        "csv column hits %s; jsonl key hits %s; glossary lines mentioning the words (disclaimer allowed) %d" % (hits, sorted(keys), len(gl)), {"glossary_lines": gl})


def p06():
    need = ["lm_unit_metrics.csv", "lm_summary.csv", "lm_paired_vs_direct.csv", "lm_consistency.csv", "lm_item_features.csv", "lm_failures.csv",
            "lm_judgment_queue.jsonl", "lm_pairs.jsonl", "METRICS_GLOSSARY.md"]
    miss = [n for n in need if not (M / n).exists()]
    rec("P6", "all metric files exist", "gate", not miss, "missing: %s" % (miss or "none"))


def p07():
    pr = rd(M / "lm_paired_vs_direct.csv")
    pc = Counter((r["arm"], r["versus"]) for r in pr)
    want = [("MASTeR+R", "MASTeR"), ("MASTeR", "DIRECT"), ("MASTeR", "PARA"), ("PARA", "DIRECT")]
    if "MASTeR+V" in arms:
        want += [("MASTeR+V", "MASTeR"), ("EARS+V", "EARS"), ("DIRECT+V", "DIRECT")]
    if "MASTeR+U" in arms:
        want += [("MASTeR+U", "MASTeR")]
    miss = [w for w in want if pc[w] == 0]
    rec("P7", "paired comparisons present (C1, C3, PARA control, V and U vs the same arm without the rule)", "gate", not miss, "rows per pair %s; missing %s" % ({"%s vs %s" % k: v for k, v in sorted(pc.items())}, miss or "none"))


def p08():
    co = rd(M / "lm_consistency.csv")
    c = Counter(r["n_reps"] for r in co)
    rec("P8", "repetition consistency computed", "gate", c.get(str(a.reps), 0) > 0, "n_reps distribution %s" % dict(c))


def p09():
    q = jl(M / "lm_judgment_queue.jsonl")
    full = [r for r in q if (r.get("generated_ltl") or {}).get("ft") and (r.get("reference_ltl") or {}).get("future_time")]
    rec("P9", "judgment queue usable", "info", True, "rows %d, both ltl filled %d" % (len(q), len(full)))


def p10():
    um = rd(M / "lm_unit_metrics.csv")
    s = {}
    for r in um:
        if r["item_id"] == "LM-09_EUL-N2" and r["variant"] == "vf":
            s.setdefault(r["arm"], []).append((r["rep"], r["n_pred_accepted"], r["count_diff"], r["n_parts"]))
    rec("P10", "split into parts visible (LM-09_EUL-N2, 3 parts)", "info", True, "values (rep, n_pred_accepted, count_diff, n_parts) per arm: %s" % {k: sorted(v) for k, v in sorted(s.items())})


def p11():
    pairs = [p for p in jl(M / "lm_pairs.jsonl") if p["item_id"] == "LM-01_FSM-N01"]
    vers = Counter()
    for p in pairs:
        for x in p["alignment"]:
            vers[(p["variant"], x.get("ref_version"))] += 1
    rec("P11", "alternative reference versions handled (LM-01_FSM-N01)", "info", True, "alignments by (variant, ref_version) %s" % {"%s|%s" % k: v for k, v in sorted(vers.items(), key=lambda x: str(x))})


def p12():
    all_ref = set(ref_texts)
    for d in all_items:
        for part in d["gt_parts"]:
            for v in part:
                all_ref.add(v["fretish"])
        if isinstance(d.get("gt"), str):
            all_ref.add(d["gt"])
        for k in ("gt_alts", "gt_list"):
            if isinstance(d.get(k), list):
                all_ref.update(x for x in d[k] if isinstance(x, str))
    nref = {norm(t): t for t in all_ref if len(norm(t)) >= 25}
    fr = [c for c in calls if c["stage"] in ("F1", "F2")]
    hits_f = [(c["stage_key"], t[:60]) for c in fr for t in all_ref if t and t in (c.get("user_prompt") or "")]
    hits_any = [(c["stage_key"], t[:60]) for c in calls for t in all_ref if t and t in (c.get("user_prompt") or "")]
    rec("P12", "no reference FRETish in feedback prompts", "gate", not hits_f, "feedback rows %d, strings searched %d, hits %s" % (len(fr), len(all_ref), hits_f[:5]))
    rec("P12b", "no reference FRETish in any user prompt", "gate", not hits_any, "hits %s" % hits_any[:5])
    files = sorted(list(SNAP.glob("system_prompt_*.txt")) + list((SNAP / "prompts").glob("*.md")) + list((SNAP / "templates").glob("*.md")))
    hits = []
    for f in files:
        t = f.read_text(encoding="utf-8", errors="replace")
        w = norm(t)
        for nt, orig in nref.items():
            if nt in w:
                hits.append((str(f.relative_to(SNAP)), orig[:70]))
    rec("P13", "no reference FRETish in system prompts, guide or template specs", "gate", not hits, "files searched %d, reference strings (len>=25) %d, hits %s" % (len(files), len(nref), hits[:5]))


def p14():
    pa, pb = R / "fret_realizability.jsonl", R / "fret_realizability_double.jsonl"
    if not pb.exists():
        rec("P14", "type policy probe (optional file absent)", "info", True, "fret_realizability_double.jsonl not found")
        return
    A = {r["sentence_sha"]: r for r in jl(pa)}
    B = {r["sentence_sha"]: r for r in jl(pb)}
    c = Counter()
    for k, x in A.items():
        y = B.get(k)
        if y is not None:
            c[(x["kind"], x["result"], y["result"])] += 1
    rec("P14", "type policy probe (informational)", "info", True, "changed distinct sentences %d; unknown in both (gen) %d; table %s" % (sum(v for (kd, x, y), v in c.items() if x != y), c.get(("gen", "unknown", "unknown"), 0), {"%s|%s|%s" % k: v for k, v in sorted(c.items())}))


def p15():
    dtxt = (SNAP / "system_prompt_D_none.txt").read_text(encoding="utf-8")
    need = ['timing is omitted it is "eventually"', "persisted(n, p)", "absReal"]
    rec("P15", "FRETish guide content is in the DIRECT prompt", "gate", all(s in dtxt for s in need), "%s" % {s: (s in dtxt) for s in need})


def p16():
    ok = True
    ev = []
    for arm in [x for x in arms if x.endswith("+U")]:
        rr = [c for c in calls if c["stage"] == "A" and c["arm"] == arm]
        st = Counter(c["status"] for c in rr)
        ev.append("%s A rows %d status %s" % (arm, len(rr), dict(st)))
        ok = ok and len(rr) == n_items * a.reps and set(st) == {"ok"}
        base = arm[:-2]
        pu = SNAP / ("system_prompt_A_%s.txt" % arm)
        pb = SNAP / ("system_prompt_A_%s.txt" % base)
        has_u = "NO-COMPLETION RULES" in pu.read_text(encoding="utf-8")
        has_b = "NO-COMPLETION RULES" in pb.read_text(encoding="utf-8")
        ev.append("rules in %s: %s; in %s: %s" % (pu.name, has_u, pb.name, has_b))
        ok = ok and has_u and not has_b
    rec("P16", "+U arms have their own stage A with the no-completion rules", "gate", ok, "; ".join(ev))


def p17():
    s = defaultdict(lambda: [0, 0])
    for c in calls:
        if c["stage"] in ("B", "D"):
            s[c["arm"]][1] += 1
            if (c.get("parsed") or {}).get("choices"):
                s[c["arm"]][0] += 1
    rec("P17", "choices recorded (informational)", "info", True, "; ".join("%s %d/%d" % (k, v[0], v[1]) for k, v in sorted(s.items())))


def p18():
    um = rd(M / "lm_unit_metrics.csv")
    s = defaultdict(lambda: [0.0, 0.0, 0])
    for r in um:
        if r["variant"] == "vf":
            s[r["arm"]][0] += float(r["ip_num_invented"] or 0)
            s[r["arm"]][1] += float(r["ip_num_dropped"] or 0)
            s[r["arm"]][2] += 1
    rec("P18", "invented/dropped numbers (informational)", "info", True, "; ".join("%s inv %.0f drop %.0f n %d" % (k, v[0], v[1], v[2]) for k, v in sorted(s.items())))


def p19():
    ok = True
    ev = []
    for st in ("A", "B"):
        f = SNAP / ("system_prompt_%s_PARA.txt" % st)
        ev.append("%s exists %s" % (f.name, f.exists()))
        ok = ok and f.exists()
    ta = (SNAP / "system_prompt_A_PARA.txt").read_text(encoding="utf-8") if (SNAP / "system_prompt_A_PARA.txt").exists() else ""
    ok = ok and "PLAIN ENGLISH REWRITE" in ta
    ev.append("PLAIN ENGLISH REWRITE in A prompt: %s" % ("PLAIN ENGLISH REWRITE" in ta))
    for st in ("A", "B"):
        rr = [c for c in calls if c["stage"] == st and c["arm"] == "PARA"]
        stt = Counter(c["status"] for c in rr)
        ev.append("PARA stage %s rows %d status %s" % (st, len(rr), dict(stt)))
        ok = ok and len(rr) == n_items * a.reps and set(stt) == {"ok"}
    rb = [c for c in calls if c["stage"] == "B" and c["arm"] == "PARA"]
    nl = {d["id"]: d["raw_nl"].strip() for d in data}
    leak = [c["stage_key"] for c in rb if nl[c["item_id"]] in (c.get("user_prompt") or "") and "REWRITTEN SENTENCES:" not in (c.get("user_prompt") or "")]
    marker = all("REWRITTEN SENTENCES:" in (c.get("user_prompt") or "") for c in rb)
    ev.append("stage B user prompts carry REWRITTEN SENTENCES marker: %s" % marker)
    ok = ok and marker
    rec("P19", "PARA control arm is wired (own prompts, A and B rows ok)", "gate", ok, "; ".join(ev))


def p20():
    ann = jl(a.annotation)
    ids = {d["id"] for d in all_items}
    aid = [r["id"] for r in ann]
    bad = [r["id"] for r in ann if r.get("scope") not in ("S", "U", "A") or r.get("condition") not in ("S", "U", "A") or r.get("timing") not in ("S", "U", "A")]
    ok = set(aid) == ids and len(aid) == len(ids) and not bad
    cnt = {k: dict(Counter(r[k] for r in ann)) for k in ("scope", "condition", "timing")}
    st = dict(Counter(r.get("status") for r in ann))
    rec("P20", "slot annotation file is valid (61 ids, values S/U/A)", "gate", ok, "rows %d, ids equal to item ids %s, invalid rows %s, counts %s, status %s" % (len(aid), set(aid) == ids, bad[:5], cnt, st), {"counts": cnt, "status": st})


def p21():
    um = rd(M / "lm_unit_metrics.csv")
    cols = set(um[0].keys())
    need = ["aud_fill_rate", "aud_drop_rate", "aud_fill_n", "aud_drop_n", "aud_timing_fill_nonalways", "aud_cond_fill_kw", "aud_cond_fill_impl", "aud_scope_has", "aud_condition_has", "aud_timing_has"]
    miss = [c for c in need if c not in cols]
    aud_cols = [c for c in cols if c.startswith("aud_")]
    filled = sum(1 for r in um if r.get("aud_n_slots_present") not in ("", None))
    rec("P21", "audit columns exist and are filled in some rows", "gate", not miss and filled > 0, "aud_ columns %d, missing %s, rows with aud_n_slots_present %d of %d" % (len(aud_cols), miss or "none", filled, len(um)))


def p22():
    f = rd(M / "lm_item_features.csv")
    cols = set(f[0].keys())
    need = ["map_review", "ann_scope", "ann_condition", "ann_timing"]
    miss = [c for c in need if c not in cols]
    mr = Counter(r.get("map_review") for r in f)
    ok = not miss and all(r.get("ann_timing") in ("S", "U", "A") for r in f)
    rec("P22", "item features carry map_review and annotation", "gate", ok, "missing %s; map_review counts %s" % (miss or "none", dict(mr)))


def p23():
    ann = jl(a.annotation)
    bad = []
    texts = set()
    for r in ann:
        for k in ("cue_scope", "cue_condition", "cue_timing", "note"):
            t = (r.get(k) or "").strip()
            if len(t) >= 12:
                texts.add(t)
    rv = json.load(open(a.review, encoding="utf-8"))["items"]
    for v in rv.values():
        t = (v.get("note") or "").strip()
        if len(t) >= 12:
            texts.add(t)
    files = sorted(list(SNAP.glob("system_prompt_*.txt")) + list((SNAP / "prompts").glob("*.md")) + list((SNAP / "templates").glob("*.md")))
    for f in files:
        txt = f.read_text(encoding="utf-8", errors="replace")
        for t in texts:
            if t in txt:
                bad.append((f.name, t[:50]))
    for c in calls:
        up = (c.get("user_prompt") or "")
        for t in texts:
            if t in up and t not in (nl_text(c) or ""):
                bad.append((c["stage_key"], t[:50]))
    names = [x for x in ("lm_slot_annotation", "lm_mapping_review", "slot annotation", "mapping review") if any(x in (c.get("user_prompt") or "") for c in calls)]
    rec("P23", "annotation and review text never reach a prompt", "gate", not bad and not names, "strings searched %d, hits %s, file-name mentions in prompts %s" % (len(texts), bad[:5], names or "none"))


_nl = {d["id"]: d["raw_nl"] for d in all_items}


def nl_text(c):
    return _nl.get(c["item_id"])


def p25():
    varms = [x for x in arms if x.endswith("+V")]
    ok = True
    ev = []
    for arm in varms:
        base = arm[:-2]
        st = "D" if base == "DIRECT" else "B"
        pv = SNAP / ("system_prompt_%s_%s.txt" % (st, "DIRECT+V" if base == "DIRECT" else arm))
        pb = SNAP / ("system_prompt_%s_%s.txt" % (st, "none" if base == "DIRECT" else base))
        has_v = pv.exists() and "TIMING INFERENCE PRINCIPLES" in pv.read_text(encoding="utf-8")
        has_b = pb.exists() and "TIMING INFERENCE PRINCIPLES" in pb.read_text(encoding="utf-8")
        rr = [c for c in calls if c["stage"] in ("B", "D") and c["arm"] == arm]
        sta = Counter(c["status"] for c in rr)
        filled = sum(1 for c in rr if ((c.get("parsed") or {}).get("timing_basis") or {}).get("rule"))
        own_a = [c for c in calls if c["stage"] == "A" and c["arm"] == arm]
        ev.append("%s: V text in own prompt %s, in base prompt %s, first-stage rows %d status %s, timing_basis.rule filled %d, own stage A rows %d" % (arm, has_v, has_b, len(rr), dict(sta), filled, len(own_a)))
        ok = ok and has_v and not has_b and len(rr) == n_items * a.reps and set(sta) == {"ok"} and filled > 0 and not own_a
    rec("P25", "+V arms: principles only in their own prompt, shared stage A with the base arm, timing_basis recorded", "gate", ok, "; ".join(ev) or "no +V arm in this run")


def p24():
    um = rd(M / "lm_unit_metrics.csv")
    pr = rd(M / "lm_paired_vs_direct.csv")
    paired_para = sum(1 for r in pr if r["versus"] == "PARA")
    same = Path(a.main).resolve() == R.resolve()
    main_started = (Path(a.main) / "run_state.json").exists()
    rs = json.load(open(R / "run_state.json", encoding="utf-8")) if (R / "run_state.json").exists() else {}
    ok = (not same) and paired_para > 0 and rs.get("status") == "finished_all"
    rec("P24", "folder isolation, PARA paired rows, run finished", "gate", ok, "preflight folder is not the main folder %s; PARA paired rows %d; run status %s; main folder already has a run_state.json (informational) %s" % (not same, paired_para, rs.get("status"), main_started))


def p26():
    by = defaultdict(lambda: [0, 0, 0.0, 0, 0])
    for c in calls:
        if c.get("status") != "ok":
            continue
        k = c["stage"]
        by[k][0] += 1; by[k][1] += int(c.get("output_tokens") or 0); by[k][2] += float(c.get("wall_s") or 0); by[k][3] = max(by[k][3], int(c.get("output_tokens") or 0)); by[k][4] += 1
    parts = ["%s: calls %d, mean output tokens %.0f, max %d, mean wall %.1f s" % (k, v[0], v[1] / max(1, v[0]), v[3], v[2] / max(1, v[0])) for k, v in sorted(by.items())]
    tot_wall = sum(v[2] for v in by.values())
    pairs = max(1, n_items * a.reps)
    proj = tot_wall / pairs * 183 / 3600
    rec("P26", "output tokens and wall time per stage (record only; main run projection = preflight wall time per item-rep pair x 183 pairs, feedback rounds included, limit waits excluded)", "info", True, "; ".join(parts) + "; projected main-run hours (excluding waits) %.1f" % proj, value={"by_stage": {k: v[:4] for k, v in by.items()}, "projected_main_hours": proj})


for fn, pid, title, gate in [(p01, "P1", "units", "gate"), (p02, "P2", "arms", "gate"), (p03, "P3", "ref ltl", "gate"), (p05, "P5", "no judge", "gate"), (p06, "P6", "files", "gate"),
                             (p07, "P7", "pairs", "gate"), (p08, "P8", "consistency", "gate"), (p09, "P9", "queue", "info"), (p10, "P10", "split", "info"), (p11, "P11", "versions", "info"),
                             (p12, "P12", "leak", "gate"), (p14, "P14", "type probe", "info"), (p15, "P15", "guide", "gate"), (p16, "P16", "+U", "gate"), (p17, "P17", "choices", "info"),
                             (p18, "P18", "numbers", "info"), (p19, "P19", "PARA", "gate"), (p20, "P20", "annotation", "gate"), (p21, "P21", "audit columns", "gate"),
                             (p22, "P22", "item features", "gate"), (p23, "P23", "annotation leak", "gate"), (p24, "P24", "isolation", "gate"), (p25, "P25", "+V", "gate"), (p26, "P26", "tokens and time", "info")]:
    safe(fn, pid, title, gate)

order = lambda r: (int(re.match(r"P(\d+)", r[0]).group(1)), r[0])
rows_out.sort(key=order)
n_fail = sum(1 for r in rows_out if r[3] == "FAIL")
lines = ["# PREFLIGHT CHECK", "", "results folder: `%s`; items %d; arms %d; reps %d; expected units %d" % (R, n_items, n_arms, a.reps, exp_units), "",
         "| # | check | type | verdict | evidence |", "|---|---|---|---|---|"]
for pid, title, gate, verdict, ev in rows_out:
    lines.append("| %s | %s | %s | %s | %s |" % (pid, title, gate, verdict, str(ev).replace("|", "/").replace("\n", " ")))
lines += ["", "gate result: %s (%d failed gate checks)" % ("FAIL" if n_fail else "PASS", n_fail), "", "INFO rows never fail the gate. This script reads files only and judges nothing about meaning."]
(R / "PREFLIGHT_CHECK.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
(R / "preflight_values.json").write_text(json.dumps(vals, ensure_ascii=False, indent=1), encoding="utf-8")
print("\n".join(lines))
sys.exit(1 if n_fail else 0)
