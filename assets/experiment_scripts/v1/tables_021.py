#!/usr/bin/env python3
"""Tables 1 to 8 of the 021 comparability test (instruction section 5). Reads the merged judge records of the runs, the skeleton records and the inputs; writes tables_021.md
and tables_021.json. No model call, no solver, no judgement of meaning. Definitions: notes/PRE_RUN_DEFINITIONS_021.md (pinned before the judge ran).
The judge records are only read (slimmed while reading: a record keeps pair id, role, nm flag, reasons, message, sentence, reference part, formulas, mapping). The per-sentence and
per-unit classes and the rank order come from the code of the frozen tool (nl2fret_judge.aggregate, nl2fret_judge.judge), imported read-only; the bootstrap, the comparison list and
the arm order come from the 020 script rq_aggregate.py, imported read-only (it has no side effect on import).

usage:
  python3 -I -B tables_021.py --tool-dir T --units U --ltl L --rlz R --reference REF --records-anchor A --records-free F --records-strict S --skeleton K \
      [--records-ctrl-anchor CA --records-ctrl-free CF --control-units CU --control-sampling CS] [--aggregate-anchor f --aggregate-free f --aggregate-strict f] \
      --rq020 <020 scripts/rq_aggregate.py> --out-md F --out-json F [--seed 20261112] [--boot 5000]
"""
import argparse
import collections
import hashlib
import importlib.util
import json
import os
import sys

sys.dont_write_bytecode = True

ROLES = ["SAME", "PROOF", "REFUTE", "NEITHER", "UND", "N/M"]
COMPARABLE = ["SAME", "PROOF", "REFUTE", "NEITHER"]
STRATA = ["conditional", "invariant", "timed", "scoped"]
MAX_CASES = 20


def jl(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def pct(n, d):
    return "-" if not d else f"{100.0 * n / d:.1f}%"


def cell(n, d):
    return f"{n} ({pct(n, d)})"


def md_table(headers, rows):
    out = ["| " + " | ".join(str(h) for h in headers) + " |", "|" + "---|" * len(headers)]
    for r in rows:
        out.append("| " + " | ".join("" if c is None else str(c) for c in r) + " |")
    return "\n".join(out)


class Report:
    def __init__(self):
        self.md, self.js = [], {}

    def section(self, title, note=None):
        self.md.append(f"\n## {title}\n")
        if note:
            self.md.append(note + "\n")

    def table(self, key, headers, rows, note=None, title=None):
        if title:
            self.md.append(f"\n### {title}\n")
        self.md.append(md_table(headers, rows) + "\n")
        if note:
            self.md.append(note + "\n")
        self.js[key] = {"headers": headers, "rows": rows}

    def text(self, key, md, js):
        self.md.append(md + "\n")
        self.js[key] = js


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def read_records(path):
    """pair_id -> slim record (the heavy parts of a record, the raw query output, are dropped while reading)"""
    out = {}
    with open(path, encoding="utf-8") as f:
        for ln in f:
            if not ln.strip():
                continue
            r = json.loads(ln)
            al = r.get("alignment") or {}
            out[r["pair_id"]] = {"pair_id": r["pair_id"], "role": r.get("role"), "nm": bool(r.get("nm")), "nm_reason": r.get("nm_reason"), "und_reason": r.get("und_reason"),
                                 "message": (r.get("nm_detail") or {}).get("message") if isinstance(r.get("nm_detail"), dict) else None, "sentence": r.get("sentence"),
                                 "reference_part": r.get("reference_part"), "pred_pt": r.get("pred_pt"), "gt_pt": r.get("gt_pt"), "mapping": al.get("mapping")}
    return out


def lab(r):
    """pair label of a judge record: N/M when the engine could not decide, else the role"""
    return "N/M" if r.get("nm") else r.get("role")


def und_detail(msg):
    m = msg or ""
    if m.startswith("unmatched gen vars"):
        return "unmatched_gen_gt_unmatched_ref"
    if m.startswith("gen vars"):
        return "gen_vars_gt_ref_vars"
    if m.startswith("reference has"):
        return "ref_3plus_more_vars"
    if m == "type":
        return "type"
    if m.startswith("too many renamings"):
        return "too_many_renamings"
    if m.startswith("no lexically supported"):
        return "no_lexical_counterpart"
    if m.startswith("no injective renaming candidate"):
        return "no_injective_candidate"
    return "other"


def sk_label(s):
    return s["skel_role"]


class Data:
    def __init__(self, a):
        sys.path.insert(0, os.path.join(a.tool_dir, "judging"))
        from nl2fret_judge import aggregate as AG, judge as JD, units as U      # noqa: E402  (frozen tool code, read-only import)
        self.AG, self.JD, self.U = AG, JD, U
        self.rq = load_module(a.rq020, "rq020")
        self.a = a
        self.tool_units = U.load_units(a.units, a.ltl, a.rlz)
        self.ltl = {r["sentence"]: r for r in jl(a.ltl)}
        ref = jl(a.reference)
        self.ref_rows = {r["id"]: r for r in ref}
        self.n_parts = {r["id"]: r.get("n_parts") or len(r["gt_parts"]) for r in ref}
        self.arms = self.rq.order_arms({u["arm"] for u in self.tool_units})
        self.pairs = []                                    # (pair_id, unit, sentence index, sentence dict): the pairs that nl2fret_judge judge visits
        for u in self.tool_units:
            for i, s in enumerate(u["sentences"]):
                if s["parser_ok"] and s["ltl_pt"]:
                    self.pairs.append((f"{u['item']}|{u['arm']}|{u['rep']}|{i}", u, i, s))
        self.pair_ids = [p[0] for p in self.pairs]
        self.rec = {}
        for tag, path in (("anchor", a.records_anchor), ("free", a.records_free), ("strict", a.records_strict)):
            self.rec[tag] = read_records(path) if path else None
        self.sk = {r["pair_id"]: r for r in jl(a.skeleton)} if a.skeleton else None
        self.ctrl_units = json.load(open(a.control_units, encoding="utf-8"))["units"] if a.control_units else None
        self.ctrl_sampling = json.load(open(a.control_sampling, encoding="utf-8")) if a.control_sampling else None
        self.ctrl_rec = {}
        for tag, path in (("ctrl_anchor", a.records_ctrl_anchor), ("ctrl_free", a.records_ctrl_free)):
            self.ctrl_rec[tag] = read_records(path) if path else None
        self.ctrl_pairs = []
        if self.ctrl_units is not None:
            for u in U.load_units(a.control_units, a.ltl, a.rlz):
                for i, s in enumerate(u["sentences"]):
                    if s["parser_ok"] and s["ltl_pt"]:
                        self.ctrl_pairs.append((f"{u['item']}|{u['arm']}|{u['rep']}|{i}", u, i, s))
        self.tool_unit_key = {(u["item"], u["arm"], u["rep"]): u for u in self.tool_units}

    # ---- pair labels of a run, as (label, reason, detail) ----------------------------------------------------------------------------------------------------
    def labels(self, tag, pair_ids=None):
        out = {}
        for pid in pair_ids or self.pair_ids:
            if tag == "skeleton":
                s = self.sk.get(pid)
                out[pid] = None if s is None else (sk_label(s), s.get("reason"), s.get("detail"))
            else:
                r = (self.rec.get(tag) or self.ctrl_rec.get(tag) or {}).get(pid)
                if r is None:
                    out[pid] = None
                else:
                    L = lab(r)
                    out[pid] = (L, r.get("und_reason") if L == "UND" else (r.get("nm_reason") if L == "N/M" else None), r.get("message") if L == "UND" else None)
        return out


# ------------------------------------------------------------------------------------------------------------------------------------------------------------
def t_inputs(D, R):
    a = D.a
    rows = []
    for name, p in (("units", a.units), ("ltl", a.ltl), ("rlz", a.rlz), ("reference", a.reference), ("records anchor (020)", a.records_anchor), ("records free", a.records_free),
                    ("records strict", a.records_strict), ("skeleton records", a.skeleton), ("control units", a.control_units), ("records ctrl_anchor", a.records_ctrl_anchor),
                    ("records ctrl_free", a.records_ctrl_free)):
        if p:
            rows.append([name, os.path.basename(p), sha256_file(p)])
    R.table("inputs", ["입력", "파일", "sha256"], rows, title="입력 파일")


def t1(D, R):
    cols = [("anchor (020)", "anchor"), ("free", "free"), ("strict", "strict"), ("골격", "skeleton")]
    lbl = {t: D.labels(t) for _, t in cols if (D.rec.get(t) is not None or (t == "skeleton" and D.sk is not None))}
    n = len(D.pair_ids)
    def count(t, pred):
        return sum(1 for v in lbl[t].values() if v is not None and pred(v))
    rows = []
    for role in ["SAME", "PROOF", "REFUTE", "NEITHER"]:
        rows.append([role] + [cell(count(t, lambda v, role=role: v[0] == role), n) if t in lbl else "-" for _, t in cols])
    for group in ("UND", "N/M"):
        rows.append([group + " (합)"] + [cell(count(t, lambda v, g=group: v[0] == g), n) if t in lbl else "-" for _, t in cols])
        reasons = sorted({v[1] for t in lbl for v in lbl[t].values() if v is not None and v[0] == group and v[1] is not None})
        for rs in reasons:
            rows.append([f"  {group} 사유 {rs}"] + [cell(count(t, lambda v, g=group, rs=rs: v[0] == g and v[1] == rs), n) if t in lbl else "-" for _, t in cols])
        if group == "UND":
            dets = sorted({und_detail(v[2]) for t in lbl for v in lbl[t].values() if v is not None and v[0] == "UND"})
            for dt in dets:
                rows.append([f"  UND 상세 {dt}"] + [cell(count(t, lambda v, dt=dt: v[0] == "UND" and und_detail(v[2]) == dt), n) if t in lbl else "-" for _, t in cols])
    rows.append(["기록 없음"] + [cell(sum(1 for v in lbl[t].values() if v is None), n) if t in lbl else "-" for _, t in cols])
    rows.append(["합계(전체 쌍)"] + [n for _ in cols])
    R.table("table1", ["역할"] + [c for c, _ in cols], rows, title="표 1. 모드별 쌍 역할 분포",
            note="분모는 전체 쌍(`parser_ok`이고 LTL이 있는 문장)이다. 골격의 UND는 미판정(UND 쪽, `atomization_mismatch`), N/M은 미판정(N/M 쪽, `solver_unknown` 또는 `unsupported`)이다. "
                 "UND 상세는 `nm_detail.message`(골격은 `detail`)의 분류다. free는 상한이며 가짜 일치 가능성이 있다(표 3). 골격 결과는 짝지어진 불투명 원자가 같은 상태 술어를 뜻한다는 "
                 "검증되지 않은 전제 위에 있다. 골격 비교는 유한 구간 z3이고 NuSMV 판정과 엔진이 다르다.")


def t2(D, R):
    base = D.labels("anchor")
    special = []
    for tag, title in (("free", "anchor 대 free"), ("strict", "anchor 대 strict")):
        if D.rec.get(tag) is None:
            continue
        other = D.labels(tag)
        M = collections.Counter()
        for pid in D.pair_ids:
            if base[pid] is not None and other[pid] is not None:
                M[(base[pid][0], other[pid][0])] += 1
        rows = []
        for r in ROLES:
            row = [r] + [M[(r, c)] for c in ROLES] + [sum(M[(r, c)] for c in ROLES)]
            rows.append(row)
        rows.append(["합"] + [sum(M[(r, c)] for r in ROLES) for c in ROLES] + [sum(M.values())])
        R.table(f"table2_{tag}", ["anchor 역할 \\ " + tag + " 역할"] + ROLES + ["합"], rows, title=f"표 2. 전이 행렬 ({title})")
        und_to_cmp = sum(M[("UND", c)] for c in COMPARABLE)
        nei_to = {c: M[("NEITHER", c)] for c in ("SAME", "PROOF", "REFUTE")}
        same_to = {c: M[("SAME", c)] for c in ROLES if c != "SAME"}
        proof_to = {c: M[("PROOF", c)] for c in ROLES if c != "PROOF"}
        refute_to = {c: M[("REFUTE", c)] for c in ROLES if c != "REFUTE"}
        special.append([title, und_to_cmp, ", ".join(f"{c} {M[('UND', c)]}" for c in COMPARABLE), sum(nei_to.values()), ", ".join(f"{c} {v}" for c, v in nei_to.items()),
                        sum(same_to.values()), ", ".join(f"{c} {v}" for c, v in same_to.items()), sum(proof_to.values()), sum(refute_to.values())])
    R.table("table2_special", ["비교", "UND에서 비교 가능한 역할로", "(상세)", "NEITHER에서 SAME, PROOF, REFUTE로", "(상세)", "SAME에서 다른 역할로", "(상세)",
                               "PROOF에서 다른 역할로", "REFUTE에서 다른 역할로"], special, title="표 2. 따로 적는 전이 수",
            note="비교 가능한 역할 = SAME, PROOF, REFUTE, NEITHER. 쌍은 `pair_id`로 짝지었다.")


def case_texts(D, tag, pid):
    r = D.ctrl_rec[tag][pid]
    item = pid.split("|")[0]
    ref_text = None
    row = D.ref_rows.get(item)
    if row and r.get("reference_part"):
        for i, grp in enumerate(row["gt_parts"]):
            for j, p in enumerate(grp):
                if f"{p.get('reqid', i)}#{j}" == r["reference_part"]:
                    ref_text = p.get("fretish")
    orig = None
    if D.ctrl_sampling:
        key = tuple(pid.split("|")[:3])
        for d in D.ctrl_sampling["drawn_units"]:
            if (d["new_item"], d["arm"], str(d["rep"])) == key:
                orig = d["item"]
    return {"pair_id": pid, "sentence": r.get("sentence"), "original_item": orig, "reference_item": item, "reference_part": r.get("reference_part"), "reference_fretish": ref_text,
            "gen_pt": r.get("pred_pt"), "ref_pt": r.get("gt_pt"), "mapping": r.get("mapping"), "role": r.get("role")}


def t3(D, R):
    if not D.ctrl_units or not any(D.ctrl_rec.values()):
        R.section("표 3. 음성 대조", "(대조 입력이나 기록이 없음)")
        return
    ids = [p[0] for p in D.ctrl_pairs]
    n = len(ids)
    units_with = len({tuple(pid.split("|")[:3]) for pid in ids})
    cols = [("anchor", "ctrl_anchor"), ("free", "ctrl_free")]
    L = {t: D.labels(t, ids) for _, t in cols if D.ctrl_rec.get(t) is not None}
    rows = []
    for role in ["SAME", "PROOF", "REFUTE", "NEITHER"]:
        rows.append([role] + [cell(sum(1 for v in L[t].values() if v and v[0] == role), n) if t in L else "-" for _, t in cols])
    for group in ("UND", "N/M"):
        rows.append([group + " (합)"] + [cell(sum(1 for v in L[t].values() if v and v[0] == group), n) if t in L else "-" for _, t in cols])
        for rs in sorted({v[1] for t in L for v in L[t].values() if v and v[0] == group and v[1]}):
            rows.append([f"  {group} 사유 {rs}"] + [cell(sum(1 for v in L[t].values() if v and v[0] == group and v[1] == rs), n) if t in L else "-" for _, t in cols])
    rows.append(["기록 없음"] + [cell(sum(1 for v in L[t].values() if v is None), n) if t in L else "-" for _, t in cols])
    rows.append(["가짜 일치율 = SAME / 대조 쌍"] + [pct(sum(1 for v in L[t].values() if v and v[0] == "SAME"), n) if t in L else "-" for _, t in cols])
    rows.append(["SAME 또는 PROOF / 대조 쌍"] + [pct(sum(1 for v in L[t].values() if v and v[0] in ("SAME", "PROOF")), n) if t in L else "-" for _, t in cols])
    rows.append(["SAME, PROOF 또는 REFUTE / 대조 쌍"] + [pct(sum(1 for v in L[t].values() if v and v[0] in ("SAME", "PROOF", "REFUTE")), n) if t in L else "-" for _, t in cols])
    R.table("table3", ["역할"] + [c for c, _ in cols], rows, title="표 3. 음성 대조의 역할 분포",
            note=f"대조 단위 {len(D.ctrl_units)}개(시드 20261112, 항목은 정렬한 id 번호 + 31 mod 61로 바꿈), 판정 쌍이 있는 단위 {units_with}개, 대조 판정 쌍 {n}개(분모). "
                 "기준이 틀린 짝이라 SAME이 나오면 가짜 일치다. 대조 단위의 realizability는 `not_run`이 되며 역할에는 영향이 없다.")
    cases, extra = {}, {}
    for _, t in cols:
        if t in L:
            same = [pid for pid in ids if L[t][pid] and L[t][pid][0] == "SAME"]
            cases[t] = [case_texts(D, t, pid) for pid in same[:MAX_CASES]]
    if sum(len([pid for pid in ids if L[t][pid] and L[t][pid][0] == "SAME"]) for t in L) < 5:
        for _, t in cols:
            if t in L:
                proof = [pid for pid in ids if L[t][pid] and L[t][pid][0] == "PROOF"]
                extra[t] = [case_texts(D, t, pid) for pid in proof[:5]]
    md = ["", "### 표 3. 가짜 일치 사례 (모드별 SAME 쌍, 최대 %d개)" % MAX_CASES, ""]
    for _, t in cols:
        if t in cases:
            md.append(f"**{t}**: SAME {sum(1 for pid in ids if L[t][pid] and L[t][pid][0] == 'SAME')}개 중 {len(cases[t])}개")
            for c in cases[t]:
                md.append(f"- `{c['pair_id']}` (원래 항목 {c['original_item']}, 기준 항목 {c['reference_item']}, 기준 부분 {c['reference_part']})\n  - 생성 문장: {c['sentence']}\n  - 기준 문장: {c['reference_fretish']}\n  - 생성 식: `{c['gen_pt']}`\n  - 기준 식: `{c['ref_pt']}`\n  - 대응: {c['mapping']}")
    if extra:
        md.append("")
        md.append("SAME 쌍이 두 모드 합쳐 5개 미만이라 정의대로 PROOF 쌍을 모드별 앞에서 5개까지 더한다(PROOF 사례).")
        for _, t in cols:
            for c in extra.get(t, []):
                md.append(f"- [{t}, PROOF] `{c['pair_id']}` (원래 항목 {c['original_item']}, 기준 항목 {c['reference_item']})\n  - 생성 문장: {c['sentence']}\n  - 기준 문장: {c['reference_fretish']}")
    R.text("table3_cases", "\n".join(md), {"same_cases": cases, "proof_cases": extra})


def rank(D, rec):
    return D.JD.rank_of({"nm": rec["nm"], "role": rec["role"]})


def agg_by_arm(D, records):
    """tool rule: aggregate.aggregate over all units, then aggregate.table by arm. records: pair_id -> record with a 'role'"""
    rows = D.AG.aggregate(D.tool_units, records)
    return rows, {r["arm"]: r for r in D.AG.table(rows, "arm")}


def t4(D, R):
    groups = []
    for tag, title in (("anchor", "anchor (020)"), ("free", "free"), ("strict", "strict")):
        if D.rec.get(tag) is not None:
            groups.append((tag, title, D.rec[tag]))
    if D.rec.get("anchor") is not None and D.rec.get("free") is not None:
        best = {}
        for pid in D.pair_ids:
            ra, rf = D.rec["anchor"].get(pid), D.rec["free"].get(pid)
            if ra is None or rf is None:
                best[pid] = ra or rf
                continue
            best[pid] = rf if rank(D, rf) < rank(D, ra) else ra          # ties keep the anchor record
        best = {k: v for k, v in best.items() if v is not None}
        groups.append(("best", "anchor와 free 중 좋은 쪽", best))
    tabs = {}
    for tag, title, recs in groups:
        rows, by = agg_by_arm(D, recs)
        tabs[tag] = (title, by, rows)
        R.table(f"table4_{tag}", ["방식", "단위", "success", "partial", "failure", "unjudged", "성공률(분모 전체)", "성공률(판정된 단위만)"],
                [[a, by[a]["n_units"], by[a]["success"], by[a]["partial"], by[a]["failure"], by[a]["unjudged"], pct(by[a]["success"], by[a]["n_units"]),
                  pct(by[a]["success"], by[a]["n_units"] - by[a]["unjudged"])] for a in D.arms if a in by],
                title=f"표 4. 방식별 단위 성공률 ({title})",
                note="도구의 `aggregate`(관대한 규칙: 단위 안 가장 좋은 문장, success = SAME 또는 PROOF이면서 같은 문장이 realizable). 분모는 전체 단위(방식별 183 또는 153), 판정된 단위만 = unjudged가 아닌 단위만"
                     + (" . 좋은 쪽 = 쌍마다 도구의 순위(N/M 3, UND 4, 그 밖은 역할 순위)가 더 좋은 기록(같으면 anchor)." if tag == "best" else "."))
    if tabs:
        hdr = ["방식"] + [f"{t[0]} 전체" for t in tabs.values()] + [f"{t[0]} 판정된만" for t in tabs.values()]
        rows = []
        for a in D.arms:
            row = [a]
            for _, (_, by, _) in tabs.items():
                row.append(pct(by[a]["success"], by[a]["n_units"]) if a in by else "-")
            for _, (_, by, _) in tabs.items():
                row.append(pct(by[a]["success"], by[a]["n_units"] - by[a]["unjudged"]) if a in by else "-")
            rows.append(row)
        R.table("table4_summary", hdr, rows, title="표 4. 방식별 단위 성공률 (나란히)")
    # cross-check with the tool's own aggregate.json of every run
    chk = []
    for tag, path in (("anchor", D.a.aggregate_anchor), ("free", D.a.aggregate_free), ("strict", D.a.aggregate_strict)):
        if path and tag in tabs:
            tool = {r["arm"]: r for r in json.load(open(path, encoding="utf-8"))["by_arm"]}
            by = tabs[tag][1]
            bad = [a for a in by if (tool.get(a, {}).get("n_units"), tool.get(a, {}).get("success"), tool.get(a, {}).get("partial"), tool.get(a, {}).get("failure"), tool.get(a, {}).get("unjudged"))
                   != (by[a]["n_units"], by[a]["success"], by[a]["partial"], by[a]["failure"], by[a]["unjudged"])]
            chk.append([tag, os.path.basename(os.path.dirname(path)), len(by), len(bad), ", ".join(bad)])
    if chk:
        R.table("table4_crosscheck", ["실행", "도구 aggregate.json 폴더", "방식 수", "다른 방식 수", "다른 방식"], chk, title="표 4. 도구 aggregate.json과의 대조",
                note="단위 수, success, partial, failure, unjudged를 방식별로 비교했다(도구의 값은 바꾸지 않음).")


def sk_class(role):
    return {"SAME": "success", "PROOF": "success", "REFUTE": "partial", "NEITHER": "failure"}.get(role, "unjudged")


def sk_units(D):
    """(item, arm, rep) -> skeleton unit outcome (the rule of aggregate.unit_outcome over the skeleton sentence classes)"""
    out = {}
    for u in D.tool_units:
        cl = []
        for i, s in enumerate(u["sentences"]):
            if not s["parser_ok"] or not s["ltl_pt"]:
                cl.append("failure")
                continue
            r = D.sk.get(f"{u['item']}|{u['arm']}|{u['rep']}|{i}")
            cl.append(sk_class(r["skel_role"]) if r else "unjudged")
        out[(u["item"], u["arm"], u["rep"])] = D.AG.unit_outcome(cl)
    return out


def outcome_rows(D, SU, group_fn, groups, group_name):
    rows = []
    for arm in D.arms:
        for g in groups:
            us = [u for u in D.tool_units if u["arm"] == arm and group_fn(u) == g]
            if not us:
                continue
            c = collections.Counter(SU[(u["item"], u["arm"], u["rep"])] for u in us)
            n = len(us)
            rows.append([arm, g, len({u["item"] for u in us}), n, c["success"], c["partial"], c["failure"], c["unjudged"], pct(c["success"], n), pct(c["success"], n - c["unjudged"])])
    return rows


def t5(D, R):
    if D.sk is None:
        return
    SU = sk_units(D)
    D.sk_unit = SU
    hdr = ["방식", "구분", "항목 수", "단위", "success", "partial", "failure", "unjudged", "성공률(분모 전체)", "성공률(판정된 단위만)"]
    note = ("골격 단위 결과: 문장 클래스 = 골격 SAME 또는 PROOF success, REFUTE partial, NEITHER failure, 미판정 unjudged, 파서 거부 failure; 단위는 도구의 `unit_outcome`(단위 안 가장 좋은 문장). "
            "분모는 전체 단위. 실현가능성은 넣지 않았다(구조만). 부분이 여러 개인 항목에서 \"어느 한 문장이라도 일치\"는 모든 부분을 만족한다는 뜻이 아니다. "
            "골격 결과는 짝지어진 불투명 원자가 같은 상태 술어를 뜻한다는 검증되지 않은 전제 위에 있고, 유한 구간 z3로 비교했으며 NuSMV 판정과 엔진이 다르다.")
    R.table("table5_all", hdr, outcome_rows(D, SU, lambda u: "전체", ["전체"], "전체"), title="표 5. 방식별 골격 단위 결과 (전체)", note=note)
    np_of = lambda u: "n_parts=1" if D.n_parts[u["item"]] == 1 else "n_parts>=2"
    R.table("table5_nparts", hdr, outcome_rows(D, SU, np_of, ["n_parts=1", "n_parts>=2"], "n_parts"), title="표 5. 방식별 골격 단위 결과 (n_parts별)", note=note)
    R.table("table5_stratum", hdr, outcome_rows(D, SU, lambda u: u.get("stratum"), STRATA, "stratum"), title="표 5. 방식별 골격 단위 결과 (stratum별)",
            note=note + " 항목 수가 작은 칸(scoped는 항목 2개)은 `항목 수` 열을 함께 본다.")


def nz(v):
    return None if v in (None, "null", "") else v


def refs_fields(D, item):
    out = []
    row = D.ref_rows.get(item)
    for part in (row or {}).get("gt_parts", []):
        for v in part:
            f = v.get("fields") or {}
            out.append({"scope": nz(f.get("scope")), "condition": nz(f.get("condition")), "timing": nz(f.get("timing")) or "eventually"})
    return out


def pattern_of(D, pid, sentence, item):
    """True when the pair shows the trigger-versus-holding pattern (the RQ1c rule of 020 applied to one pair); None when the fields are not available"""
    c = D.ltl.get(sentence)
    refs = refs_fields(D, item)
    if not c or not refs:
        return None
    g = {"scope": nz(c.get("scope")), "condition": nz(c.get("condition")), "timing": nz(c.get("timing")) or "eventually"}
    best = None
    for r in refs:
        e = []
        if bool(g["scope"]) != bool(r["scope"]):
            e.append("scope")
        elif g["scope"] != r["scope"]:
            e.append("scope")
        if bool(g["condition"]) != bool(r["condition"]):
            e.append("cond")
        if g["timing"] != r["timing"]:
            e.append("timing")
        if best is None or len(e) < len(best[0]):
            best = (e, g, r)
    e, g, r = best
    return "cond" in e and r["timing"] == "always" and g["timing"] != "always"


def t6(D, R):
    if D.sk is None:
        return
    rows = []
    tot = collections.Counter()
    for arm in D.arms + ["전체"]:
        c = collections.Counter()
        for pid, u, i, s in D.pairs:
            if arm != "전체" and u["arm"] != arm:
                continue
            sk = D.sk.get(pid)
            if sk is None or sk["skel_role"] != "NEITHER":
                continue
            pat = pattern_of(D, pid, s["text"], u["item"])
            if pat is None:
                c["no_fields"] += 1
                continue
            c["all_n"] += 1
            c["all_p"] += 1 if pat else 0
            if u.get("stratum") == "conditional":
                c["cond_n"] += 1
                c["cond_p"] += 1 if pat else 0
        if arm != "전체" and not c:
            continue
        rows.append([arm, c["cond_n"], c["cond_p"], pct(c["cond_p"], c["cond_n"]), c["all_n"], c["all_p"], pct(c["all_p"], c["all_n"]), c["no_fields"]])
    R.table("table6", ["방식", "골격 NEITHER 쌍(conditional 항목)", "패턴 쌍", "비율", "골격 NEITHER 쌍(모든 stratum)", "패턴 쌍", "비율", "필드 없음으로 뺀 쌍"], rows,
            title="표 6. 골격 NEITHER 쌍 중 trigger 대 holding 패턴",
            note="020 `rq_aggregate.py`의 RQ1c 규칙을 쌍에 적용: 문장 x 기준 버전 중 필드(scope, condition 유무, timing) 어긋남이 가장 적은 쌍(같으면 먼저 본 것)에서 condition 유무가 다르고 기준 timing이 "
                 "`always`이며 생성 timing이 `always`가 아니면 패턴이다. 분모 = 골격 NEITHER 쌍.")


def t7(D, R):
    if D.sk is None or D.rec.get("anchor") is None:
        return
    sk = D.labels("skeleton")
    an = D.labels("anchor")
    M = collections.Counter()
    for pid in D.pair_ids:
        if sk[pid] is not None and an[pid] is not None:
            M[(sk[pid][0], an[pid][0])] += 1
    rows = [[f"골격 {r}"] + [M[(r, c)] for c in ROLES] + [sum(M[(r, c)] for c in ROLES)] for r in ROLES]
    rows.append(["합"] + [sum(M[(r, c)] for r in ROLES) for c in ROLES] + [sum(M.values())])
    R.table("table7", ["골격 역할 \\ anchor 역할"] + ROLES + ["합"], rows, title="표 7. 골격 결과와 anchor 역할의 교차표 (전체 쌍)",
            note="골격의 UND, N/M은 미판정(UND 쪽, N/M 쪽)이다.")


def item_success(D, SU, arm, items):
    """item -> (mean over the repetitions of the unit success (all units in the denominator), all units of the item judged?)"""
    if not hasattr(D, "sk_ia"):
        D.sk_ia = collections.defaultdict(list)
        for (it, ar, rep), v in SU.items():
            D.sk_ia[(it, ar)].append(v)
    out = {}
    for it in items:
        us = D.sk_ia.get((it, arm))
        if not us:
            continue
        out[it] = (sum(1 for v in us if v == "success") / len(us), all(v != "unjudged" for v in us))
    return out


def t8(D, R):
    if D.sk is None:
        return
    SU = D.sk_unit
    seed, B = D.a.seed, D.a.boot
    items_of = collections.defaultdict(set)
    for (it, arm, rep) in SU:
        items_of[arm].add(it)
    rows, rows_j = [], []
    for a, b in D.rq.comparisons(D.arms):
        items = sorted(items_of[a] & items_of[b])
        sa, sb = item_success(D, SU, a, items), item_success(D, SU, b, items)
        d = {i: sa[i][0] - sb[i][0] for i in items if i in sa and i in sb}
        pt, lo, hi = D.rq.boot(d, f"{seed}:{a}:{b}:all", B)
        better = sum(1 for x in d.values() if x > 0)
        worse = sum(1 for x in d.values() if x < 0)
        rows.append([f"{a} - {b}", len(d), f"{100 * pt:+.1f}", f"[{100 * lo:+.1f}, {100 * hi:+.1f}]", better, len(d) - better - worse, worse])
        dj = {i: sa[i][0] - sb[i][0] for i in items if i in sa and i in sb and sa[i][1] and sb[i][1]}
        if dj:
            ptj, loj, hij = D.rq.boot(dj, f"{seed}:{a}:{b}:judged", B)
            rows_j.append([f"{a} - {b}", len(dj), len(d), f"{100 * ptj:+.1f}", f"[{100 * loj:+.1f}, {100 * hij:+.1f}]"])
        else:
            rows_j.append([f"{a} - {b}", 0, len(d), "-", "-"])
    note = (f"골격 단위 성공률(골격 success의 비율, 분모 전체)에 020과 같은 항목 단위 부트스트랩: 항목이 재표집 단위, 항목 안에서 반복을 평균, {B}회 복원 재표집(요청 횟수), 시드 `{seed}`와 비교 이름으로 "
            "고정(`random.Random(\"시드:A:B:구분\")`), 구간 = 정렬한 통계량의 2.5%와 97.5% 위치. `+D` 비교는 51항목, 그 밖은 61항목. 골격 결과의 전제와 한계는 표 5의 주석과 같다.")
    R.table("table8_all", ["비교 (A - B)", "항목 수", "성공률 차이(%p)", "95% 구간", "A가 나은 항목", "같은 항목", "A가 나쁜 항목"], rows, title="표 8. 방식 쌍 비교 (골격 단위 성공률, 모든 항목)", note=note)
    R.table("table8_judged", ["비교 (A - B)", "남은 항목 수", "모든 항목 수", "성공률 차이(%p)", "95% 구간"], rows_j,
            title="표 8. 방식 쌍 비교 (골격 단위 성공률, 모든 방식이 판정된 항목만)",
            note="별도 표: 두 방식의 모든 단위(반복 포함)가 골격에서 판정된(unjudged가 아닌) 항목만 쓴 짝 비교. 남은 항목 수를 적었다. 같은 부트스트랩 규칙.")


def main():
    p = argparse.ArgumentParser()
    for k in ("tool-dir", "units", "ltl", "rlz", "reference", "rq020", "out-md", "out-json"):
        p.add_argument("--" + k, required=True)
    for k in ("records-anchor", "records-free", "records-strict", "skeleton", "records-ctrl-anchor", "records-ctrl-free", "control-units", "control-sampling",
              "aggregate-anchor", "aggregate-free", "aggregate-strict"):
        p.add_argument("--" + k)
    p.add_argument("--seed", default="20261112")
    p.add_argument("--boot", type=int, default=5000)
    a = p.parse_args()
    D = Data(a)
    R = Report()
    R.md.append("# 표 (021 비교 가능성 시험, 탐색적 보조 실행)\n")
    R.md.append("이 실행은 본 실험(019)의 판정 결과(020, 모드 anchor)를 본 뒤에 하는 탐색적 보조 실행이다. 020의 결과는 사전 정의된 주 결과이고 이 실행으로 바뀌지 않는다. "
                "정의는 `notes/PRE_RUN_DEFINITIONS_021.md`(판정 전에 고정). 해석 문장은 쓰지 않았다. 판정 기록은 읽기만 했다.\n")
    R.section("입력")
    t_inputs(D, R)
    R.section("A. 이름 대응 모드와 음성 대조")
    t1(D, R)
    t2(D, R)
    t3(D, R)
    t4(D, R)
    R.section("B. 골격 비교")
    t5(D, R)
    t6(D, R)
    t7(D, R)
    t8(D, R)
    open(a.out_md, "w", encoding="utf-8").write("\n".join(R.md) + "\n")
    json.dump(R.js, open(a.out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote", a.out_md, a.out_json, "| tables:", len(R.js), "| pairs:", len(D.pair_ids))


if __name__ == "__main__":
    main()
