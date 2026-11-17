"""v2.0 measurement rules of docs/V20_BATCH_DESIGN.md section 7: N-LIT (integer literals of the realizability input) and J+def (defined dictionary terms)."""
import json, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.join(HERE, "..", "bench")
sys.path.insert(0, os.path.join(BENCH, "fret_check", "tools"))
sys.path.insert(0, os.path.join(BENCH, "fret_check"))
sys.path.insert(0, os.path.join(BENCH, "tools"))
import litnorm as L  # noqa: E402


def sem_for(t):
    c = re.search(r"^(when|whenever|if|upon|unless)\b.*?(?= \S+ shall)", t)
    r = t.index("satisfy")
    d = {"responseTextRange": [r, len(t) - 1]}
    if c:
        d["conditionTextRange"] = [0, c.end() - 1]
    return d


def norm(t, dv):
    return L.normalize_sentence(t, sem_for(t), dv)


def test_nlit_converts_integer_literals_next_to_double_variables():
    t = "Whenever ridge_on the EB shall always satisfy absReal(check_1_1 - 1) <= eps6 & absReal(check_1_2 - 0) <= eps6"
    assert norm(t, {"check_1_1", "check_1_2", "eps6"}) == (t.replace("- 1)", "- 1.0)").replace("- 0)", "- 0.0)"), 2)
    assert norm("the EB shall always satisfy x <= 3 & k = 2", {"x"}) == ("the EB shall always satisfy x <= 3.0 & k = 2", 1)


def test_nlit_leaves_other_text_alone():
    t = "the EB shall within 3 ticks satisfy x_real <= 3"
    assert norm(t, {"x_real"}) == ("the EB shall within 3 ticks satisfy x_real <= 3.0", 1)            # the timing bound stays an integer
    assert norm("the EB shall always satisfy (count + 1) <= limit", {"limit"})[1] == 0                  # integer variable with an integer literal
    assert norm("the EB shall always satisfy absReal(y - 1) <= eps", set())[1] == 0                     # no double variable known
    assert norm("the EB shall always satisfy f(2) & q", {"q"})[1] == 0                                  # function argument is not an operand
    t2 = "the EB shall always satisfy absReal(y - 1.0) <= 5"
    assert norm(t2, {"y"}) == (t2.replace("<= 5", "<= 5.0"), 1)


def test_nlit_reads_only_condition_and_response_regions():
    t = "when x_real > 10 the EB shall always satisfy x_real < 2"
    sem = {"conditionTextRange": [0, 15], "responseTextRange": [t.index("satisfy"), len(t) - 1]}
    assert L.normalize_sentence(t, sem, {"x_real"}) == ("when x_real > 10.0 the EB shall always satisfy x_real < 2.0", 2)
    assert L.normalize_sentence(t, {"responseTextRange": sem["responseTextRange"]}, {"x_real"})[0].startswith("when x_real > 10 the EB")


def test_jdef_substitution_recursive_with_parentheses_cycle_and_depth():
    defs = {"A": "B * B + C", "B": "D + 1", "C": "A", "D": "x * x"}
    t = "the EB shall always satisfy A < 5 & E = 2"
    new, info = L.substitute_defined(t, sem_for(t), defs)
    assert new == "the EB shall always satisfy (((x * x) + 1) * ((x * x) + 1) + (A)) < 5 & E = 2"
    assert info["cycles"] == ["A"] and info["substituted"] == ["A", "B", "C", "D"]
    chain = {f"T{i}": f"T{i + 1} + 1" for i in range(30)}
    chain["T30"] = "z"
    t2 = "the EB shall always satisfy T0 > 0"
    new2, info2 = L.substitute_defined(t2, sem_for(t2), chain)
    assert info2["depth_limit"] and "(" in new2
    assert L.substitute_defined("the EB shall always satisfy Q > 0", sem_for("the EB shall always satisfy Q > 0"), {"A": "1"})[0] == "the EB shall always satisfy Q > 0"


def test_jdef_does_not_touch_component_or_timing_text():
    t = "the A shall within 3 ticks satisfy A > 0"
    new, _ = L.substitute_defined(t, sem_for(t), {"A": "x + 1"})
    assert new == "the A shall within 3 ticks satisfy (x + 1) > 0"


def test_make_def_inputs_with_a_fake_parser(tmp_path, monkeypatch):
    import make_def_inputs as M
    import fret_compile

    def fake(texts, backend="docker", chunk=400):
        out = []
        for t in texts:
            out.append({"fretish": t, "ok": "REJECT" not in t, "ltl_pt": "PT(" + t + ")", "ltl_ft": "FT(" + t + ")", "error": None, "sem": sem_for(t)})
        return out
    monkeypatch.setattr(fret_compile, "compile_list", fake)
    ref = [{"id": "I1", "challenge": "C1", "raw_nl": "x", "gt_parts": [[{"reqid": "R1", "fretish": "the S shall always satisfy (a * a + b * b) < 1", "ltl": {"past_time": "p", "future_time": "f"}}]]}]
    (tmp_path / "ref.jsonl").write_text(json.dumps(ref[0]) + "\n")
    (tmp_path / "dict.csv").write_text("challenge,name,direction,type,dims,description,sources,components,kind,definition,model_signal\nC1,nrm,Internal,real,,,x,,defined,a * a + b * b,\nC1,a,Input,double,,,x,,signal,,\n")
    (tmp_path / "in").mkdir()
    units = [{"item": "I1", "arm": "DIRECT", "rep": 0, "status": "parsed", "texts": ["the S shall always satisfy nrm < 1"], "pending": False},
             {"item": "I1", "arm": "EARS+G", "rep": 0, "status": "pending", "texts": [], "pending": True}]
    (tmp_path / "in" / "units.json").write_text(json.dumps({"units": units}))
    sys.argv = ["make_def_inputs", "--inputs", str(tmp_path / "in"), "--reference", str(tmp_path / "ref.jsonl"), "--dictionary", str(tmp_path / "dict.csv"), "--out", str(tmp_path / "out")]
    M.main()
    u = json.load(open(tmp_path / "out" / "units.json"))["units"]
    assert u[0]["texts"] == ["the S shall always satisfy (a * a + b * b) < 1"] and u[1]["texts"] == []
    rep = json.load(open(tmp_path / "out" / "substitution_report.json"))
    assert rep["summary"]["changed"] == 1 and rep["summary"]["parser_rejected"] == 0
    ltl = [json.loads(l) for l in open(tmp_path / "out" / "fret_ltl_gen.jsonl")]
    assert ltl[0]["ltl_pt"] == "PT(the S shall always satisfy (a * a + b * b) < 1)"
    ref2 = json.loads(open(tmp_path / "out" / "reference_def.jsonl").readline())
    assert ref2["gt_parts"][0][0]["ltl"] == {"past_time": "p", "future_time": "f"}     # the reference sentence without a defined term keeps its stored LTL


def test_run_batch_script_has_the_new_step():
    p = os.path.join(HERE, "..", "exp", "fsm", "run_batch.sh")
    assert subprocess.run(["bash", "-n", p]).returncode == 0
    assert "judgedef)" in open(p).read()


def test_classify_terms_parse_error_and_cycles():
    defs = {"ok1": "a * a", "bad": "x and y", "self": "self + 1", "p": "q + 1", "q": "p + 1", "uses_bad": "bad | z", "plain": "b + 1"}
    reason, good = L.classify_terms(defs, {"ok1": True, "bad": False, "self": True, "p": True, "q": True, "uses_bad": True, "plain": True})
    assert reason == {"ok1": None, "bad": "parse_error", "self": "cycle", "p": "cycle", "q": "cycle", "uses_bad": None, "plain": None}
    assert set(good) == {"ok1", "uses_bad", "plain"}


def test_rename_aliases_only_in_condition_and_response():
    t = "when old_1 > 3 the old_1 shall always satisfy old_1 < 2"
    sem = {"conditionTextRange": [0, 15], "responseTextRange": [t.index("satisfy"), len(t) - 1]}
    new, names = L.rename_aliases(t, sem, {"old_1": "cur_1"})
    assert new == "when cur_1 > 3 the old_1 shall always satisfy cur_1 < 2" and names == ["old_1"]


def test_make_def_inputs_term_level_alias_and_term_report(tmp_path, monkeypatch):
    import make_def_inputs as M
    import fret_compile

    def fake(texts, backend="docker", chunk=400):
        return [{"fretish": t, "ok": " and " not in t and "->" not in t, "ltl_pt": "PT(" + t + ")", "ltl_ft": "FT(" + t + ")", "error": None, "sem": sem_for(t)} for t in texts]
    monkeypatch.setattr(fret_compile, "compile_list", fake)
    ref = [{"id": "I1", "challenge": "C1", "raw_nl": "x", "gt_parts": [[{"reqid": "R1", "fretish": "the S shall always satisfy nrm < 1 & lus > 0", "ltl": {"past_time": "p", "future_time": "f"}}]]}]
    (tmp_path / "ref.jsonl").write_text(json.dumps(ref[0]) + "\n")
    header = "challenge,name,direction,type,dims,description,sources,components,kind,definition,model_signal,alias_of,alias_evidence\n"
    (tmp_path / "dict.csv").write_text(header + "C1,nrm,Internal,real,,,x,,defined,a * a + b * b,,,\nC1,lus,Internal,real,,,x,,defined,x and y,,,\nC1,cyc,Internal,real,,,x,,defined,cyc + 1,,,\n"
                                       "C1,old_1,Input,real,,,x,,signal,,,cur_1,REQ-1\nC1,cur_1,Input,real,,,x,,signal,,,,\n")
    (tmp_path / "in").mkdir()
    units = [{"item": "I1", "arm": "DIRECT", "rep": 0, "status": "parsed", "texts": ["the S shall always satisfy nrm < 1 & lus > 0 & old_1 = 2"], "pending": False}]
    (tmp_path / "in" / "units.json").write_text(json.dumps({"units": units}))
    sys.argv = ["make_def_inputs", "--inputs", str(tmp_path / "in"), "--reference", str(tmp_path / "ref.jsonl"), "--dictionary", str(tmp_path / "dict.csv"), "--out", str(tmp_path / "out")]
    M.main()
    u = json.load(open(tmp_path / "out" / "units.json"))["units"][0]["texts"][0]
    assert u == "the S shall always satisfy (a * a + b * b) < 1 & lus > 0 & cur_1 = 2"          # term substituted, lustre_only term and the alias handled
    r = json.loads(open(tmp_path / "out" / "reference_def.jsonl").readline())["gt_parts"][0][0]["fretish"]
    assert r == "the S shall always satisfy (a * a + b * b) < 1 & lus > 0"                          # the same terms on the reference side
    tr = json.load(open(tmp_path / "out" / "term_report.json"))
    assert tr["total"]["defined"] == 3 and tr["total"]["lustre_only"] == 2 and tr["total"]["lustre_only_cycle"] == 1 and tr["total"]["lustre_only_parse_error"] == 1
    assert tr["challenges"]["C1"]["substitutable"] == 1
    # strict control: no alias, no substitution
    sys.argv += ["--no-substitute"]
    sys.argv[sys.argv.index("--out") + 1] = str(tmp_path / "out_strict")
    M.main()
    assert json.load(open(tmp_path / "out_strict" / "units.json"))["units"][0]["texts"] == units[0]["texts"]


def test_dictionary_v2_alias_rows_have_evidence_and_the_model_text_has_none():
    import csv
    rows = list(csv.DictReader(open(os.path.join(HERE, "..", "data", "dictionary", "lm_dictionary.csv"), encoding="utf-8-sig")))
    assert {"alias_of", "alias_evidence"} <= set(rows[0])
    names = {(r["challenge"], r["name"]) for r in rows}
    alias = [r for r in rows if r["alias_of"]]
    assert alias and all(r["alias_evidence"] and (r["challenge"], r["alias_of"]) in names and "nasa_req:" in r["sources"] for r in alias)
    sig = open(os.path.join(BENCH, "data", "sigdict.json"), encoding="utf-8").read()
    assert "alias" not in sig.lower() and "nasa_req" not in sig                                      # the dictionary text that the model sees has no alias information
