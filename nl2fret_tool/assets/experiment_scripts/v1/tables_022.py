#!/usr/bin/env python3
"""Transition tables, controls and side-by-side tables of the 022 run (dictionary and alias applied inputs). Reads the merged judge records of the runs and the inputs; writes
tables_022.md and tables_022.json. No model call, no NuSMV; the only solver use is the bounded z3 comparison of judge4 for the symmetry flag of the swap control. Definitions:
notes/PRE_RUN_DEFINITIONS_022.md (pinned before the judge ran). The judge records are only read (slimmed while reading). The unit classes of the tool are not recomputed here: the
side-by-side unit success rates are read from the aggregate.json files the tool wrote.

usage:
  python3 -I -B tables_022.py --tool-dir T --units U --ltl L --reference REF --certs C --records-main M --records-anchor020 A --records-strict021 S --records-free021 F --skeleton021 K \
      [--records-ctrl X --control-sampling CS --records-alias AL --records-swap SW --swap-units SU] \
      [--aggregate-main f --aggregate-anchor020 f --aggregate-strict021 f --aggregate-free021 f] --out-md F --out-json F
"""
import argparse
import collections
import hashlib
import json
import os
import sys

sys.dont_write_bytecode = True

ROLES = ["SAME", "PROOF", "REFUTE", "NEITHER", "UND", "N/M"]
COMPARABLE = ["SAME", "PROOF", "REFUTE", "NEITHER"]
MAX_CASES = 200


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


def read_records(path):
    """pair_id -> slim record (the raw query output of a record is dropped while reading)"""
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


class Data:
    def __init__(self, a):
        self.a = a
        self.tool = a.tool_dir
        self.units = json.load(open(a.units, encoding="utf-8"))["units"]
        self.ltl = {r["sentence"]: r for r in jl(a.ltl)}
        self.ref_rows = {r["id"]: r for r in jl(a.reference)}
        self.certs = {(c["item"], c["sentence"]) for c in jl(a.certs)} if a.certs else set()
        self.pairs = []                                       # pair ids that the judge visits (parser ok and a past-time formula), in unit order
        for u in self.units:
            for i, t in enumerate(u["texts"]):
                L = self.ltl.get(t) or {}
                if L.get("parser_ok") and L.get("ltl_pt"):
                    self.pairs.append(f"{u['item']}|{u['arm']}|{u['rep']}|{i}")
        self.rec = {}
        for tag, path in (("main", a.records_main), ("anchor020", a.records_anchor020), ("strict021", a.records_strict021), ("free021", a.records_free021),
                          ("ctrl", a.records_ctrl), ("alias", a.records_alias), ("swap", a.records_swap)):
            self.rec[tag] = read_records(path) if path and os.path.exists(path) else None
        self.sk = {r["pair_id"]: r for r in jl(a.skeleton021)} if a.skeleton021 and os.path.exists(a.skeleton021) else None
        self.sampling = json.load(open(a.control_sampling, encoding="utf-8")) if a.control_sampling else None
        self.swap_units = json.load(open(a.swap_units, encoding="utf-8"))["units"] if a.swap_units and os.path.exists(a.swap_units) else None

    def label(self, tag, pid):
        if tag == "skeleton021":
            s = self.sk.get(pid)
            return None if s is None else (s["skel_role"], s.get("reason"), s.get("detail"))
        r = (self.rec.get(tag) or {}).get(pid)
        if r is None:
            return None
        L = lab(r)
        return (L, r.get("und_reason") if L == "UND" else (r.get("nm_reason") if L == "N/M" else None), r.get("message") if L == "UND" else None)


def t_inputs(D, R):
    a = D.a
    rows = []
    for name, p in (("units", a.units), ("ltl (main run)", a.ltl), ("reference", a.reference), ("alias certificates", a.certs), ("records main", a.records_main), ("records 020 anchor", a.records_anchor020),
                    ("records 021 strict", a.records_strict021), ("records 021 free", a.records_free021), ("skeleton 021", a.skeleton021), ("records ctrl", a.records_ctrl),
                    ("records alias_dictonly", a.records_alias), ("records swap", a.records_swap), ("swap units", a.swap_units)):
        if p and os.path.exists(p):
            rows.append([name, os.path.basename(p), sha256_file(p)])
    R.table("inputs", ["입력", "파일", "sha256"], rows, title="입력 파일")


def t_roles(D, R):
    cols = [("020 anchor (사전 없음)", "anchor020"), ("main (사전과 별칭)", "main"), ("021 free", "free021"), ("021 strict", "strict021"), ("021 골격", "skeleton021")]
    cols = [(c, t) for c, t in cols if (D.rec.get(t) is not None or (t == "skeleton021" and D.sk is not None))]
    n = len(D.pairs)
    lbl = {t: {pid: D.label(t, pid) for pid in D.pairs} for _, t in cols}
    count = lambda t, pred: sum(1 for v in lbl[t].values() if v is not None and pred(v))
    rows = []
    for role in ["SAME", "PROOF", "REFUTE", "NEITHER"]:
        rows.append([role] + [cell(count(t, lambda v, role=role: v[0] == role), n) for _, t in cols])
    for group in ("UND", "N/M"):
        rows.append([group + " (합)"] + [cell(count(t, lambda v, g=group: v[0] == g), n) for _, t in cols])
        for rs in sorted({v[1] for t in lbl for v in lbl[t].values() if v is not None and v[0] == group and v[1] is not None}):
            rows.append([f"  {group} 사유 {rs}"] + [cell(count(t, lambda v, g=group, rs=rs: v[0] == g and v[1] == rs), n) for _, t in cols])
        if group == "UND":
            for dt in sorted({und_detail(v[2]) for t in lbl for v in lbl[t].values() if v is not None and v[0] == "UND"}):
                rows.append([f"  UND 상세 {dt}"] + [cell(count(t, lambda v, dt=dt: v[0] == "UND" and und_detail(v[2]) == dt), n) for _, t in cols])
    rows.append(["기록 없음"] + [cell(sum(1 for v in lbl[t].values() if v is None), n) for _, t in cols])
    rows.append(["합계(전체 쌍)"] + [n for _ in cols])
    R.table("roles_side_by_side", ["역할"] + [c for c, _ in cols], rows, title="표 1. 쌍 역할 분포 나란히 (3999쌍)",
            note="분모는 전체 쌍(`parser_ok`이고 LTL이 있는 문장)이다. 열은 020 anchor(사전 없음), 이번 실행 main(사전과 별칭 적용), 021 free, 021 strict, 021 골격이다.")


def t_transition(D, R, prev, prev_name, key):
    if D.rec.get("main") is None or (D.rec.get(prev) is None):
        return
    M = collections.Counter()
    for pid in D.pairs:
        a, b = D.label(prev, pid), D.label("main", pid)
        if a is not None and b is not None:
            M[(a[0], b[0])] += 1
    rows = [[r] + [M[(r, c)] for c in ROLES] + [sum(M[(r, c)] for c in ROLES)] for r in ROLES]
    rows.append(["합"] + [sum(M[(r, c)] for r in ROLES) for c in ROLES] + [sum(M.values())])
    R.table(key, [f"{prev_name} 역할 \\ main 역할"] + ROLES + ["합"], rows, title=f"표 2. 이동표: {prev_name}에서 main으로")
    und_cmp = {c: M[("UND", c)] for c in COMPARABLE}
    nei = {c: M[("NEITHER", c)] for c in ("SAME", "PROOF", "REFUTE")}
    other = {r: sum(M[(r, c)] for c in ROLES if c != r) for r in ("SAME", "PROOF", "REFUTE")}
    R.table(key + "_special", ["이전 실행", "UND에서 비교 가능한 역할로", "(상세)", "NEITHER에서 SAME, PROOF, REFUTE로", "(상세)", "SAME에서 다른 역할로", "PROOF에서 다른 역할로", "REFUTE에서 다른 역할로"],
            [[prev_name, sum(und_cmp.values()), ", ".join(f"{c} {v}" for c, v in und_cmp.items()), sum(nei.values()), ", ".join(f"{c} {v}" for c, v in nei.items()),
              other["SAME"], other["PROOF"], other["REFUTE"]]], title=f"표 2. 따로 적는 이동 수 ({prev_name})")


def t_alias(D, R):
    if D.rec.get("alias") is None or D.rec.get("main") is None:
        return
    ids_all = sorted(D.rec["alias"], key=lambda p: D.pairs.index(p) if p in D.pairs else 10 ** 9)
    def matrix(ids):
        M = collections.Counter()
        for pid in ids:
            a, b = D.label("alias", pid), D.label("main", pid)
            if a is not None and b is not None:
                M[(a[0], b[0])] += 1
        return M
    def sentence_of(pid):
        item = pid.split("|")[0]
        return item, (D.rec["alias"][pid].get("sentence"))
    cert_ids = [pid for pid in ids_all if sentence_of(pid) in D.certs]
    for key, ids, title in (("alias_all", ids_all, "표 3. 별칭 이동표 (alias_dictonly의 쌍 전부)"), ("alias_cert", cert_ids, "표 3. 별칭 이동표 (증명서가 있는 문장의 쌍만)")):
        M = matrix(ids)
        rows = [[r] + [M[(r, c)] for c in ROLES] + [sum(M[(r, c)] for c in ROLES)] for r in ROLES]
        rows.append(["합"] + [sum(M[(r, c)] for r in ROLES) for c in ROLES] + [sum(M.values())])
        changed = sum(v for (r, c), v in M.items() if r != c)
        R.table(key, ["사전만 적용(alias_dictonly) 역할 \\ 별칭 적용(main) 역할"] + ROLES + ["합"], rows, title=title,
                note=f"쌍 {len(ids)}개, 역할이 바뀐 쌍 {changed}개. 쌍은 같은 `pair_id`의 main 기록과 짝지었다.")


def ref_text(D, item, part):
    row = D.ref_rows.get(item)
    if row and part:
        for i, grp in enumerate(row["gt_parts"]):
            for j, p in enumerate(grp):
                if f"{p.get('reqid', i)}#{j}" == part:
                    return p.get("fretish")
    return None


def t_ctrl(D, R):
    if D.rec.get("ctrl") is None:
        return
    ids = list(D.rec["ctrl"])
    n = len(ids)
    lab_of = lambda pid: lab(D.rec["ctrl"][pid])
    rows = []
    for role in ROLES:
        rows.append([role, cell(sum(1 for pid in ids if lab_of(pid) == role), n)])
    for rs in sorted({D.rec["ctrl"][pid].get("und_reason") for pid in ids if lab_of(pid) == "UND" and D.rec["ctrl"][pid].get("und_reason")}):
        rows.append([f"  UND 사유 {rs}", cell(sum(1 for pid in ids if lab_of(pid) == "UND" and D.rec["ctrl"][pid].get("und_reason") == rs), n)])
    for rs in sorted({D.rec["ctrl"][pid].get("nm_reason") for pid in ids if lab_of(pid) == "N/M" and D.rec["ctrl"][pid].get("nm_reason")}):
        rows.append([f"  N/M 사유 {rs}", cell(sum(1 for pid in ids if lab_of(pid) == "N/M" and D.rec["ctrl"][pid].get("nm_reason") == rs), n)])
    rows.append(["SAME 수(가짜 일치)", sum(1 for pid in ids if lab_of(pid) == "SAME")])
    rows.append(["SAME 또는 PROOF 비율", pct(sum(1 for pid in ids if lab_of(pid) in ("SAME", "PROOF")), n)])
    rows.append(["SAME, PROOF 또는 REFUTE 비율", pct(sum(1 for pid in ids if lab_of(pid) in ("SAME", "PROOF", "REFUTE")), n)])
    R.table("ctrl", ["역할", "ctrl(음성 대조, 사전과 별칭 적용 ltl)"], rows, title="표 4. 음성 대조", note=f"대조 판정 쌍 {n}개(분모). 기준을 다른 항목으로 바꾼 단위(021과 같은 입력)이다.")
    same = [pid for pid in ids if lab_of(pid) == "SAME"]
    orig = {}
    if D.sampling:
        for d in D.sampling["drawn_units"]:
            orig[(d["new_item"], d["arm"], str(d["rep"]))] = d["item"]
    cases = []
    for pid in same[:MAX_CASES]:
        r = D.rec["ctrl"][pid]
        item = pid.split("|")[0]
        cases.append({"pair_id": pid, "sentence": r.get("sentence"), "original_item": orig.get(tuple(pid.split("|")[:3])), "reference_item": item, "reference_part": r.get("reference_part"),
                      "reference_fretish": ref_text(D, item, r.get("reference_part")), "gen_pt": r.get("pred_pt"), "ref_pt": r.get("gt_pt"), "mapping": r.get("mapping")})
    md = ["", f"### 표 4. 음성 대조의 SAME 쌍 (전부 나열, {len(same)}쌍)", ""]
    if not same:
        md.append("SAME 쌍이 없다.")
    for c in cases:
        md.append(f"- `{c['pair_id']}` (원래 항목 {c['original_item']}, 기준 항목 {c['reference_item']}, 기준 부분 {c['reference_part']})\n  - 생성 문장: {c['sentence']}\n  - 기준 문장: {c['reference_fretish']}\n  - 생성 식: `{c['gen_pt']}`\n  - 기준 식: `{c['ref_pt']}`\n  - 대응: {c['mapping']}")
    R.text("ctrl_cases", "\n".join(md), {"same_pairs": same, "cases": cases})


def t_swap(D, R):
    if D.rec.get("swap") is None or D.swap_units is None or D.rec.get("main") is None:
        return
    sys.path.insert(0, os.path.join(D.tool, "judging", "legacy"))
    import judge4 as J4                                                # noqa: E402  (legacy code, read-only import)
    by_key = {(u["item"], u["arm"], int(u["rep"])): u for u in D.swap_units}
    ids = list(D.rec["swap"])
    n_main_same = sum(1 for pid in D.pairs if (D.rec["main"].get(pid) or {}).get("role") == "SAME" and not (D.rec["main"].get(pid) or {}).get("nm"))
    rows = [["main의 SAME 쌍 수", n_main_same], ["교환 단위 수", len(D.swap_units)], ["변수 하나뿐이라 건너뛴 쌍 수", n_main_same - len(D.swap_units)], ["교환 판정 쌍 수", len(ids)]]
    for role in ROLES:
        rows.append([f"교환 판정 {role}", cell(sum(1 for pid in ids if lab(D.rec["swap"][pid]) == role), len(ids))])
    cases = []
    for pid in ids:
        r = D.rec["swap"][pid]
        if lab(r) != "SAME":
            continue
        item, arm, rep, _ = pid.split("|")
        u = by_key.get((item, arm, int(rep))) or {}
        orig_pid = u.get("orig_pair_id")
        orig_pt = (D.rec["main"].get(orig_pid) or {}).get("pred_pt") if orig_pid else None
        try:
            cls = J4.compare(orig_pt, r.get("pred_pt")).get("cls") if orig_pt and r.get("pred_pt") else None
        except Exception as e:                                          # noqa: BLE001
            cls = "error " + type(e).__name__
        cases.append({"swap_pair_id": pid, "orig_pair_id": orig_pid, "swapped": u.get("swapped"), "orig_pt": orig_pt, "swapped_pt": r.get("pred_pt"), "compare_class": cls,
                      "symmetric": bool(cls and cls.startswith("equivalent")), "reference_part": r.get("reference_part")})
    sym = sum(1 for c in cases if c["symmetric"])
    rows.append(["교환 판정 SAME 중 대칭인 식(원 식과 교환 식이 judge4 비교에서 equivalent)", sym])
    rows.append(["교환 판정 SAME 중 대칭이 아닌 식(손으로 확인할 목록)", len(cases) - sym])
    R.table("swap", ["항목", "값"], rows, title="표 5. 이름 교환 대조")
    md = ["", f"### 표 5. 이름 교환 대조의 SAME 쌍 (전부 나열, {len(cases)}쌍)", ""]
    if not cases:
        md.append("SAME 쌍이 없다.")
    for c in cases[:MAX_CASES]:
        md.append(f"- `{c['swap_pair_id']}` (원래 쌍 `{c['orig_pair_id']}`, 교환한 변수 {c['swapped']}, 비교 클래스 {c['compare_class']}, 대칭 {'예' if c['symmetric'] else '아니오'})\n  - 원 식: `{c['orig_pt']}`\n  - 교환 식: `{c['swapped_pt']}`")
    R.text("swap_cases", "\n".join(md), {"cases": cases})


def t_units(D, R):
    srcs = [("020 anchor", D.a.aggregate_anchor020), ("main", D.a.aggregate_main), ("021 free", D.a.aggregate_free021), ("021 strict", D.a.aggregate_strict021)]
    srcs = [(n, p) for n, p in srcs if p and os.path.exists(p)]
    if not srcs:
        return
    agg = {n: {r["arm"]: r for r in json.load(open(p, encoding="utf-8"))["by_arm"]} for n, p in srcs}
    arms = []
    for n in agg:
        for a in agg[n]:
            if a not in arms:
                arms.append(a)
    order = ["DIRECT", "PARA", "MASTeR", "EARS", "Adv-EARS", "SPIDER", "Boilerplate", "MASTeR+R2", "EARS+R2", "Adv-EARS+R2", "SPIDER+R2", "Boilerplate+R2",
             "DIRECT+V", "MASTeR+V", "EARS+V", "Boilerplate+V", "DIRECT+D", "MASTeR+D", "EARS+D"]
    arms = [a for a in order if a in arms] + sorted(a for a in arms if a not in order)
    hdr = ["방식", "단위"] + [f"{n} 전체" for n, _ in srcs] + [f"{n} 판정된만" for n, _ in srcs]
    rows = []
    for arm in arms:
        any_n = next((agg[n][arm]["n_units"] for n, _ in srcs if arm in agg[n]), None)
        row = [arm, any_n]
        for n, _ in srcs:
            x = agg[n].get(arm)
            row.append(pct(x["success"], x["n_units"]) if x else "-")
        for n, _ in srcs:
            x = agg[n].get(arm)
            row.append(pct(x["success"], x["n_units"] - x["unjudged"]) if x else "-")
        rows.append(row)
    R.table("units_side_by_side", hdr, rows, title="표 6. 방식별 단위 성공률 나란히 (도구의 `aggregate.json`, 관대한 규칙)",
            note="success = SAME 또는 PROOF이면서 같은 문장이 realizable. 분모 전체 = 방식별 전체 단위(183 또는 153), 판정된 단위만 = unjudged가 아닌 단위만.")


def main():
    p = argparse.ArgumentParser()
    for k in ("tool-dir", "units", "ltl", "reference", "out-md", "out-json"):
        p.add_argument("--" + k, required=True)
    for k in ("certs", "records-main", "records-anchor020", "records-strict021", "records-free021", "skeleton021", "records-ctrl", "control-sampling", "records-alias", "records-swap",
              "swap-units", "aggregate-main", "aggregate-anchor020", "aggregate-strict021", "aggregate-free021"):
        p.add_argument("--" + k)
    a = p.parse_args()
    D = Data(a)
    R = Report()
    R.md.append("# 표 (022 사전과 별칭 적용 입력의 판정 실행)\n")
    R.md.append("사전과 별칭 적용 입력(이번 실험 한정 전처리)에 대한 동결 도구 판정 실행의 표이다. 정의는 `notes/PRE_RUN_DEFINITIONS_022.md`(판정 전에 고정). 판정 기록은 읽기만 했다.\n")
    R.section("입력")
    t_inputs(D, R)
    R.section("A. 나란히 표시와 이동표")
    t_roles(D, R)
    t_transition(D, R, "anchor020", "020 anchor(사전 없음)", "transition_020")
    t_transition(D, R, "strict021", "021 strict(`strict_merged`)", "transition_021_strict")
    t_alias(D, R)
    R.section("B. 대조")
    t_ctrl(D, R)
    t_swap(D, R)
    R.section("C. 방식별 단위 성공률")
    t_units(D, R)
    open(a.out_md, "w", encoding="utf-8").write("\n".join(R.md) + "\n")
    json.dump(R.js, open(a.out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote", a.out_md, a.out_json, "| tables:", len(R.js), "| pairs:", len(D.pairs))


if __name__ == "__main__":
    main()
