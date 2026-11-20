#!/usr/bin/env python3
"""Result tables of a batch run for people (no model call, no judge call, nothing in the run folder is written).

Reads the stored results of a run folder (`readable/results_flat.csv` written by the `readable` step, `group_rlz.jsonl`, `gen/snapshot/items_used.jsonl`, the dataset items file and the NASA
reference file) and writes, for every challenge of the run, into <out>/<challenge>/:
  results_tables_<challenge>.xlsx  (5 sheets, needs `openpyxl`)
  summary_by_approach.csv, summary_by_item.csv, summary_groups.csv, per_item_approach.csv, all_results.csv, nasa_reference.csv, notes.csv  (UTF-8 with BOM, line end \\n)
Only variant `rt` (main variant) is used. All counts are written as values (no formulas). The judge information in the tables is the judgment role (SAME, PROOF, REFUTE, NEITHER) only; no success metric
(strict success, judge success, renamed) is read or written.
usage: python3 scripts/make_readable_tables.py --run RUN_DIR [--out OUT_DIR] [--only-challenge 01_FSM ...] [--name RUN_NAME] [--reference FILE] [--dataset FILE]
  --out default: RUN_DIR/readable/tables
  --name: run name used in titles and notes (default: the run folder name)
  --reference default: RUN_DIR/filtered/reference.jsonl if present, else data/reference/lm_reference_with_ltl.jsonl of the tool
  --dataset default (original sentences): RUN_DIR/filtered/items.jsonl if present, else src/nl2fret/data/lm_items.jsonl of the tool
The sentence that went into the tool is read from RUN_DIR/gen/snapshot/items_used.jsonl (field raw_nl).
"""
import argparse
import csv
import json
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
ROLES = ["SAME", "PROOF", "REFUTE", "NEITHER"]
NO_TEMPLATE = "(DIRECT: 없음)"

H_APPROACH = ["방식", "단위", "SAME", "PROOF", "REFUTE", "NEITHER"]
H_ITEM = ["항목", "원문 요구사항 (원본 데이터셋)", "SAME", "PROOF", "REFUTE", "NEITHER"]
H_GROUP = ["방식", "반복", "그룹 결과"]
H_PER = ["항목", "방식", "SAME", "PROOF", "REFUTE", "NEITHER"]
H_ALL = ["항목", "원문 요구사항 (원본 데이터셋)", "도구 입력 문장 (치환 후)", "방식", "반복", "템플릿 생성 문장", "FRETish 생성 문장", "NASA FRETish",
         "생성된 LTL (과거시제)", "NASA LTL (과거시제)", "판정", "비교한 NASA 버전"]
H_NASA = ["항목", "원문 요구사항", "버전", "NASA FRETish", "NASA LTL (과거시제)"]
LABELS = ["내용", "출처", "원문 요구사항 / 도구 입력 문장", "NASA 기준", "판정", "실현 가능성", "주의"]
TXT_NASA = '모델에는 주지 않은 값. 판정기가 가장 가깝다고 고른 버전을 "비교한 NASA 버전"에 적었다.'
TXT_ROLE = "SAME: LTL 동치. PROOF: 생성이 기준을 함의. REFUTE: 생성이 기준보다 약함. NEITHER: 서로 함의하지 않음."


def jl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def short_challenge(ch):
    return re.sub(r"^\d+_", "", ch)


def short_item(item, ch):
    return item.split(ch + "-", 1)[1] if (ch + "-") in item else item


def load_inputs(a):
    run = os.path.abspath(a.run)
    flat_path = os.path.join(run, "readable", "results_flat.csv")
    if not os.path.isfile(flat_path):
        raise SystemExit(f"missing {flat_path} (run the `readable` step first)")
    with open(flat_path, encoding="utf-8", newline="") as f:
        flat = [r for r in csv.DictReader(f) if r["variant"] == "rt"]
    if not flat:
        raise SystemExit("no variant rt rows in results_flat.csv")
    fi = os.path.join(run, "filtered", "items.jsonl")
    ds = a.dataset or (fi if os.path.isfile(fi) else os.path.join(ROOT, "src", "nl2fret", "data", "lm_items.jsonl"))
    fr = os.path.join(run, "filtered", "reference.jsonl")
    ref_path = a.reference or (fr if os.path.isfile(fr) else os.path.join(ROOT, "data", "reference", "lm_reference_with_ltl.jsonl"))
    used_path = os.path.join(run, "gen", "snapshot", "items_used.jsonl")
    if not os.path.isfile(used_path):
        raise SystemExit(f"missing {used_path} (the sentence that went into the tool is stored there)")
    items = {d["id"]: d for d in jl(ds)}
    used = {d["id"]: d["raw_nl"] for d in jl(used_path)}
    refs = {d["id"]: d for d in jl(ref_path)}
    gpath = os.path.join(run, "group_rlz.jsonl")
    groups = jl(gpath) if os.path.isfile(gpath) else []
    return run, flat, items, used, refs, groups, ds, ref_path


def build(ch, rows, items, used, refs, groups, name, ref_show):
    arms = list(dict.fromkeys(r["arm"] for r in rows))
    item_ids = sorted({r["item"] for r in rows})
    reps = sorted({int(r["rep"]) for r in rows})
    rows = sorted(rows, key=lambda r: (r["item"], arms.index(r["arm"]), int(r["rep"]), int(r["part"] or 1)))
    n_units = len(rows)
    sch = short_challenge(ch)
    vers = {}   # item -> list of (reqid, fretish, ltl past)
    for i in item_ids:
        vers[i] = [(v["reqid"], v["fretish"], (v.get("ltl") or {}).get("past_time", "")) for p in refs[i]["gt_parts"] for v in p]
    vmap = {(i, v[0]): v for i in item_ids for v in vers[i]}
    cnt_arm = {a_: {r_: 0 for r_ in ROLES} for a_ in arms}
    cnt_item = {i: {r_: 0 for r_ in ROLES} for i in item_ids}
    cnt_ia = {(i, a_): {r_: 0 for r_ in ROLES} for i in item_ids for a_ in arms}
    other = {}
    units_arm = {a_: 0 for a_ in arms}
    for r in rows:
        units_arm[r["arm"]] += 1
        if r["role"] in ROLES:
            cnt_arm[r["arm"]][r["role"]] += 1
            cnt_item[r["item"]][r["role"]] += 1
            cnt_ia[(r["item"], r["arm"])][r["role"]] += 1
        else:
            other[r["role"]] = other.get(r["role"], 0) + 1
    g = [x for x in groups if x.get("challenge") == ch and x.get("arm") in arms]
    g = sorted(g, key=lambda x: (arms.index(x["arm"]), -1 if x.get("rep") is None else x["rep"]))
    n_sent = sorted({x.get("n_sentences") for x in g if x.get("n_sentences") is not None})
    n_sent_txt = str(n_sent[0]) if len(n_sent) == 1 else (",".join(str(n) for n in n_sent) if n_sent else "알 수 없음")
    t = {}
    t["approach"] = [H_APPROACH] + [[a_, units_arm[a_]] + [cnt_arm[a_][r_] for r_ in ROLES] for a_ in arms]
    t["approach"].append(["전체", n_units] + [sum(cnt_arm[a_][r_] for a_ in arms) for r_ in ROLES])
    t["item"] = [H_ITEM] + [[i, items[i]["raw_nl"]] + [cnt_item[i][r_] for r_ in ROLES] for i in item_ids]
    t["item"].append(["전체", ""] + [sum(cnt_item[i][r_] for i in item_ids) for r_ in ROLES])
    t["group"] = [H_GROUP] + [[x["arm"], x.get("rep"), x.get("result")] for x in g]
    t["per"] = [H_PER] + [[i, a_] + [cnt_ia[(i, a_)][r_] for r_ in ROLES] for i in item_ids for a_ in arms]
    allr = [H_ALL]
    for r in rows:
        v = vmap.get((r["item"], r["reference_id"]))
        allr.append([r["item"], items[r["item"]]["raw_nl"], used[r["item"]], r["arm"], int(r["rep"]), r["template_sentences"] or NO_TEMPLATE, r["fretish"],
                     v[1] if v else "", r["ltl_past"], v[2] if v else "", r["role"], r["reference_id"]])
    t["all"] = allr
    t["nasa"] = [H_NASA] + [[i, items[i]["raw_nl"], v[0], v[1], v[2]] for i in item_ids for v in vers[i]]
    diff = [short_item(i, ch) for i in item_ids if used[i] != items[i]["raw_nl"]]
    same = [short_item(i, ch) for i in item_ids if used[i] == items[i]["raw_nl"]]
    if diff and same:
        sub = f"{', '.join(diff)}은 치환 후 문장이 다르고 {', '.join(same)}만 같다."
    elif diff:
        sub = f"{', '.join(diff)}은 모두 치환 후 문장이 다르다."
    else:
        sub = "모든 항목에서 두 문장이 같다."
    a_ok = sum(1 for x in g if x.get("result") == "realizable")
    b_ok = sum(1 for x in g if x.get("result") == "unrealizable")
    c_ok = len(g) - a_ok - b_ok
    n_items = len(item_ids)
    texts = [
        f"{name} {sch} {n_items}항목 x {len(arms)}방식 x {len(reps)}반복 = {n_units}단위의 최종 단계(rt, 주 변종) 결과.",
        f"{name}의 results_flat.csv(변종 rt), 그룹 realizability 파일, NASA 기준 파일 {ref_show}.",
        f"원문은 원본 데이터셋 문장, 도구 입력 문장은 도구에 들어간 문장이다. {sub}",
        TXT_NASA, TXT_ROLE,
        f"그룹 단위(방식 x 반복, {n_sent_txt}문장 한 묶음)로 확인. {name}은 {len(g)}그룹 중 {a_ok} 실현 가능, {b_ok} 불가능, {c_ok} 확인 불가.",
        f"독립 표본은 방식당 {len(reps)}그룹이다.",
    ]
    notes = [[l, x] for l, x in zip(LABELS, texts)]
    if other:
        notes.append(["기타 판정 역할", ", ".join(f"{k} {v}단위" for k, v in sorted(other.items()))])
    titles = {
        "main": f"{name} {sch} 결과 요약 (변종 rt, {n_items}항목 x {len(arms)}방식 x {len(reps)}반복 = {n_units}단위)",
        "item": f"요구사항별 판정 역할 개수 ({len(arms)}방식 x {len(reps)}반복 = {n_units // n_items if n_items else 0}단위)",
        "group": f"{name} 그룹별 (그룹 = 방식 x 반복, {n_sent_txt}단위)",
    }
    t["notes"] = notes
    return t, titles


def write_csv(path, rows):
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerows(rows)


def write_xlsx(path, t, titles):
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    F = Font(name="Arial", size=10)
    FB = Font(name="Arial", size=10, bold=True)
    fill = PatternFill("solid", fgColor="D9E1F2")
    side = Side(style="thin", color="BFBFBF")
    border = Border(left=side, right=side, top=side, bottom=side)
    wb = openpyxl.Workbook()

    def put(ws, r, c, v, bold=False, head=False, body=False, size=10, plain=False):
        cell = ws.cell(r, c, v)
        cell.font = Font(name="Arial", size=size, bold=bold or head)
        if head:
            cell.fill = fill
            cell.border = border
            cell.alignment = Alignment(wrap_text=True, vertical="center")
        elif body:
            cell.border = border
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        elif plain:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
        return cell

    def widths(ws, w):
        for k, v in w.items():
            ws.column_dimensions[k].width = v

    def table(ws, r0, rows, last_bold=False):
        for j, h in enumerate(rows[0], 1):
            put(ws, r0, j, h, head=True)
        for i, row in enumerate(rows[1:], 1):
            for j, v in enumerate(row, 1):
                put(ws, r0 + i, j, v, bold=(last_bold and i == len(rows) - 1), body=True)
        return r0 + len(rows) - 1

    ws = wb.active
    ws.title = "요약"
    put(ws, 1, 1, titles["main"], bold=True, size=12)
    end = table(ws, 3, t["approach"], last_bold=True)
    ws.row_dimensions[3].height = 30
    r = end + 2
    put(ws, r, 1, titles["item"], bold=True)
    end = table(ws, r + 1, t["item"], last_bold=True)
    r = end + 2
    put(ws, r, 1, titles["group"], bold=True)
    table(ws, r + 1, t["group"])
    widths(ws, {"A": 18, "B": 60, "C": 10, "D": 10, "E": 10, "F": 10})

    ws = wb.create_sheet("항목별 방식별")
    end = table(ws, 1, t["per"])
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:F{end}"
    widths(ws, {"A": 16, "B": 14, "C": 8, "D": 8, "E": 8, "F": 8})

    ws = wb.create_sheet("전체 결과")
    end = table(ws, 1, t["all"])
    ws.freeze_panes = "D2"
    ws.auto_filter.ref = f"A1:L{end}"
    widths(ws, dict(zip("ABCDEFGHIJKL", [16, 48, 52, 14, 6, 44, 48, 44, 48, 48, 10, 14])))

    ws = wb.create_sheet("NASA 기준")
    table(ws, 1, t["nasa"])
    ws.freeze_panes = "A2"
    widths(ws, {"A": 16, "B": 60, "C": 28, "D": 70, "E": 70})

    ws = wb.create_sheet("설명")
    for i, (k, v) in enumerate(t["notes"], 1):
        put(ws, i, 1, k, bold=True)
        put(ws, i, 2, v, plain=True)
    widths(ws, {"A": 22, "B": 120})
    wb.save(path)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--out")
    ap.add_argument("--only-challenge", nargs="*")
    ap.add_argument("--name")
    ap.add_argument("--reference")
    ap.add_argument("--dataset")
    a = ap.parse_args(argv)
    run, flat, items, used, refs, groups, ds, ref_path = load_inputs(a)
    out = a.out or os.path.join(run, "readable", "tables")
    name = a.name or os.path.basename(run)
    ref_show = os.path.relpath(ref_path, ROOT) if ref_path.startswith(ROOT + os.sep) else ref_path
    by_ch = {}
    for r in flat:
        by_ch.setdefault(items[r["item"]]["challenge"], []).append(r)
    try:
        import openpyxl  # noqa: F401
        have_xlsx = True
    except ImportError:
        have_xlsx = False
        print("openpyxl is not installed: only the CSV files are written", file=sys.stderr)
    for ch in sorted(by_ch):
        if a.only_challenge and ch not in a.only_challenge:
            continue
        t, titles = build(ch, by_ch[ch], items, used, refs, groups, name, ref_show)
        d = os.path.join(out, ch)
        os.makedirs(d, exist_ok=True)
        write_csv(os.path.join(d, "summary_by_approach.csv"), t["approach"])
        write_csv(os.path.join(d, "summary_by_item.csv"), t["item"])
        write_csv(os.path.join(d, "summary_groups.csv"), t["group"])
        write_csv(os.path.join(d, "per_item_approach.csv"), t["per"])
        write_csv(os.path.join(d, "all_results.csv"), t["all"])
        write_csv(os.path.join(d, "nasa_reference.csv"), t["nasa"])
        write_csv(os.path.join(d, "notes.csv"), t["notes"])
        if have_xlsx:
            write_xlsx(os.path.join(d, f"results_tables_{ch}.xlsx"), t, titles)
        print(f"readable tables: {ch}: {len(t['all']) - 1} units -> {d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
