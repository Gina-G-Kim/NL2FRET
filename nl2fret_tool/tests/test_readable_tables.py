"""scripts/make_readable_tables.py: small fake run (6 result rows, 2 groups): (a) the role counts add up to the number of units, (b) the headers are the specified wording."""
import csv
import importlib.util
import json
import os
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "scripts", "make_readable_tables.py")


def w(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def jl(rows):
    return "".join(json.dumps(r) + "\n" for r in rows)


def test_readable_tables_counts_and_headers():
    spec = importlib.util.spec_from_file_location("make_readable_tables", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    with tempfile.TemporaryDirectory() as tmp:
        run = os.path.join(tmp, "run")
        items = [{"id": "CH-X1", "raw_nl": "first original", "family": "CH", "challenge": "CH"}, {"id": "CH-X2", "raw_nl": "second original", "family": "CH", "challenge": "CH"}]
        used = [dict(items[0]), dict(items[1], raw_nl="second substituted")]
        ref = [{"id": i["id"], "challenge": "CH", "raw_nl": i["raw_nl"], "gt_parts": [[{"reqid": i["id"] + "v1", "fretish": "S shall always satisfy a", "ltl": {"past_time": "(H a)"}}]]} for i in items]
        w(os.path.join(run, "filtered", "items.jsonl"), jl(items))
        w(os.path.join(run, "filtered", "reference.jsonl"), jl(ref))
        w(os.path.join(run, "gen", "snapshot", "items_used.jsonl"), jl(used))
        w(os.path.join(run, "group_rlz.jsonl"), jl([{"arm": "DIRECT", "challenge": "CH", "rep": 0, "result": "realizable", "n_sentences": 2},
                                                   {"arm": "MASTeR+G", "challenge": "CH", "rep": 0, "result": "unrealizable", "n_sentences": 2}]))
        cols = ["item", "arm", "rep", "variant", "part", "original_requirement", "template_sentences", "fretish", "ltl_past", "role", "success", "reference_id"]
        roles = {("CH-X1", "DIRECT"): "SAME", ("CH-X2", "DIRECT"): "REFUTE", ("CH-X1", "MASTeR+G"): "PROOF", ("CH-X2", "MASTeR+G"): "NEITHER", ("CH-X1", "SPIDER+G"): "REFUTE", ("CH-X2", "SPIDER+G"): "SAME"}
        os.makedirs(os.path.join(run, "readable"))
        with open(os.path.join(run, "readable", "results_flat.csv"), "w", encoding="utf-8", newline="") as f:
            cw = csv.writer(f, lineterminator="\n")
            cw.writerow(cols)
            for (it, arm), role in roles.items():
                cw.writerow([it, arm, 0, "rt", 1, "x", "" if arm == "DIRECT" else "tpl", "a", "(H a)", role, "False", it + "v1"])
                cw.writerow([it, arm, 0, "v0", 1, "x", "", "a", "(H a)", "REFUTE", "False", it + "v1"])   # other variants must be ignored
        out = os.path.join(tmp, "out")
        assert m.main(["--run", run, "--out", out, "--name", "test run"]) == 0
        d = os.path.join(out, "CH")
        read = lambda n: list(csv.reader(open(os.path.join(d, n), encoding="utf-8-sig")))
        a = read("summary_by_approach.csv")
        assert a[0] == ["방식", "단위", "SAME", "PROOF", "REFUTE", "NEITHER"]
        total = a[-1]
        assert total[0] == "전체" and int(total[1]) == 6 and sum(int(x) for x in total[2:]) == 6      # (a) role counts add up to the units
        assert all(sum(int(x) for x in r[2:]) == int(r[1]) for r in a[1:])
        assert read("summary_by_item.csv")[0] == ["항목", "원문 요구사항 (원본 데이터셋)", "SAME", "PROOF", "REFUTE", "NEITHER"]   # (b) headers
        assert read("summary_groups.csv")[0] == ["방식", "반복", "그룹 결과"]
        assert read("per_item_approach.csv")[0] == ["항목", "방식", "SAME", "PROOF", "REFUTE", "NEITHER"]
        allr = read("all_results.csv")
        assert allr[0] == ["항목", "원문 요구사항 (원본 데이터셋)", "도구 입력 문장 (치환 후)", "방식", "반복", "템플릿 생성 문장", "FRETish 생성 문장", "NASA FRETish", "생성된 LTL (과거시제)", "NASA LTL (과거시제)", "판정", "비교한 NASA 버전"]
        assert len(allr) == 7 and allr[1][5] == "(DIRECT: 없음)" and allr[4][2] == "second substituted" and allr[4][1] == "second original" and allr[1][2] == "first original"
        assert read("nasa_reference.csv")[0] == ["항목", "원문 요구사항", "버전", "NASA FRETish", "NASA LTL (과거시제)"]
        assert [r[0] for r in read("notes.csv")] == ["내용", "출처", "원문 요구사항 / 도구 입력 문장", "NASA 기준", "판정", "실현 가능성", "주의"]
        try:
            import openpyxl
        except ImportError:
            return
        wb = openpyxl.load_workbook(os.path.join(d, "results_tables_CH.xlsx"))
        assert wb.sheetnames == ["요약", "항목별 방식별", "전체 결과", "NASA 기준", "설명"]
        assert [c.value for c in wb["전체 결과"][1]] == allr[0]
