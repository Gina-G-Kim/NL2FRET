"""v9 tests (no NuSMV, no docker, no model): counterexample plumbing with a stub engine, dictionary alignment, part level assembly, the no-drop rules of the generation units."""
import json
import re
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "judging"))
sys.path.insert(0, os.path.join(HERE, "..", "bench"))

from nl2fret_judge import dict_align as DA, parts as PT  # noqa: E402
from nl2fret_judge.engines import QueryResult, parse_nusmv_trace, spec_text, smv_file_text  # noqa: E402
from nl2fret_judge.judge import judge_pair  # noqa: E402

TRACE = """-- specification G (a -> b)  is false
-- as demonstrated by the following execution sequence
Trace Description: LTL Counterexample
Trace Type: Counterexample
-- Loop starts here
-> State: 1.1 <-
  a = TRUE
  b = FALSE
-> State: 1.2 <-
  a = FALSE
"""


class StubEngine:
    """answers every query with false and a canned NuSMV trace (role NEITHER)"""
    name = "stub"

    def query(self, kind, gs, rs, atoms, **_):
        spec = spec_text(kind, gs, rs)
        text = smv_file_text(spec, atoms)
        return QueryResult(kind=kind, spec_text=spec, verdict=False, stdout=TRACE, exit_code=0, smv_text=text, smv_sha256="deadbeef" + kind)


def test_trace_parser():
    t = parse_nusmv_trace(TRACE)
    assert t["n_states"] == 2 and t["loop_start_state"] == "1.1"
    assert t["states"][1]["values"] == {"a": "FALSE", "b": "FALSE"}      # the unchanged variable is carried over


def test_neither_records_counterexamples():
    r = judge_pair("(H (b -> a))", "(H (a -> b))", StubEngine(), pair_id="t1")
    assert r["role"] == "NEITHER"
    assert r["counterexample_required"] is True and r["counterexample_status"] == "recorded"
    kinds = {c["kind"] for c in r["counterexamples"]}
    assert {"sound", "compl", "equiv"} <= kinds
    assert all(c["trace"]["n_states"] == 2 for c in r["counterexamples"])
    assert all(q["counterexample"] is not None for q in r["queries"] if q["verdict"] is False)


def test_dictionary_alignment():
    new, al = DA.align_formula("(H ((Pull_Up & foo) -> (! standby)))", {"pullup", "standby"})
    assert new == "(H ((pullup & foo) -> (! standby)))"
    assert al == {"exact": ["standby"], "aliased": {"Pull_Up": "pullup"}, "oov": ["foo"]}
    new2, al2 = DA.align_formula("(H (x -> y))", {"X1", "x1", "y"})
    assert al2["oov"] == ["x"] and new2 == "(H (x -> y))"


def _rec(pid, role, nm=False):
    return {"pair_id": pid, "role": None if nm else role, "nm": nm}


def test_part_representative_and_tiebreak():
    u = {"item": "I", "arm": "A", "rep": 0, "sentences": [{"text": "s0"}, {"text": "s1"}]}
    refs = {"I": {"challenge": "01_FSM", "parts": [[("r1", "x", None), ("r2", "x", None)], [("q1", "x", None)]]}}
    recs = {PT.pair_id(u, 0, 1, 1): _rec("a", "NEITHER"), PT.pair_id(u, 0, 1, 2): _rec("b", "PROOF"), PT.pair_id(u, 1, 1, 1): _rec("c", "PROOF"), PT.pair_id(u, 1, 1, 2): _rec("d", "SAME"),
            PT.pair_id(u, 0, 2, 1): _rec("e", "REFUTE"), PT.pair_id(u, 1, 2, 1): _rec("f", "NEITHER")}
    row = PT.assemble([u], refs, recs)[0]
    p1, p2 = row["parts"]
    assert p1["role"] == "SAME" and p1["representative"]["sentence_index"] == 1 and p1["representative"]["version"] == 2
    assert p2["role"] == "REFUTE" and not p2["success"]
    assert row["n_parts_success"] == 1 and not row["all_parts_success"] and len(p1["pairs"]) == 4     # the non representative pairs stay in the row
    recs[PT.pair_id(u, 0, 1, 2)] = _rec("b", "SAME")                      # tie with (1, 2): the earliest sentence wins
    assert PT.assemble([u], refs, recs)[0]["parts"][0]["representative"]["pair_id"] == "b"


def test_no_sentence_part_fails():
    u = {"item": "I", "arm": "A", "rep": 0, "sentences": []}
    refs = {"I": {"challenge": "01_FSM", "parts": [[("r1", "x", None)]]}}
    row = PT.assemble([u], refs, {})[0]
    assert row["parts"][0]["role"] == "NO_SENTENCE" and row["n_parts_success"] == 0


def test_rule_arm_falls_back_instead_of_dropping():
    import units3 as U
    item = {"id": "X", "challenge": "01_FSM", "raw_nl": "x"}
    rows = {U.skey("X", "MASTeR+R2", 0, "A"): {"status": "ok", "parsed": {"sentences": ["this is not a template sentence at all"]}, "total_tokens": 0}}
    rec = U.derive(rows, item, "MASTeR+R2", 0, {})
    assert rec["pipeline"] is None and rec["fallback"]["reason"] == "rule_parse" and rec["pending"]      # waits for the free-path call, never dropped
    rows[U.skey("X", "MASTeR+R2", 0, "B")] = {"status": "ok", "parsed": {"fretish": ["controller shall always satisfy x"]}}
    rec = U.derive(rows, item, "MASTeR+R2", 0, {})
    assert rec["offset"] == 1 and len(rec["rounds"]) == 2 and rec["rounds"][0]["stage"] == "rule"


def test_feedback_log_is_cumulative():
    import prompts3 as P
    h = [{"attempt": 1, "stage": "D", "answer": "ANSWER ONE", "statuses": [{"verdict": "rejected", "text": "bad one", "message": "MSG ONE", "hints": ["HINT"]}], "note": ""},
         {"attempt": 2, "stage": "F1", "answer": "ANSWER TWO", "statuses": [{"verdict": "rejected", "text": "bad two", "message": "MSG TWO", "hints": []}], "note": ""}]
    s = P.user_prompt_feedback_log("ORIGINAL", h)
    for k in ("ORIGINAL", "ANSWER ONE", "MSG ONE", "ANSWER TWO", "MSG TWO", "rejected 2 of your answers", "ATTEMPT 1", "ATTEMPT 2"):
        assert k in s, k


def test_g_rule_text_has_no_r2_rule():
    import prompts3 as P
    for t in P.TPLS:
        assert "R2-" not in P.guide_rules_text(t)


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
            print("ok", n)


def test_guide_supplement_flag_only_in_free_and_direct_prompts():
    import prompts3 as P
    P.DICT_ALL = True
    try:
        P.GUIDE_SUP = False
        base_d, _ = P.build_system_D3("DIRECT")
        base_b, _ = P.build_system_B3("MASTeR+G")
        assert "SEMANTICS SUPPLEMENT" not in base_d and "SEMANTICS SUPPLEMENT" not in base_b and "D-5:" not in base_d
        P.GUIDE_SUP = True
        sup_d, st = P.build_system_D3("DIRECT")
        sup_b, _ = P.build_system_B3("MASTeR+G")
        for s in (sup_d, sup_b):
            assert "SEMANTICS SUPPLEMENT" in s and "D-5:" in s and "whenever" in s
        assert st.get("guide_supplement") == "v1.4"
    finally:
        P.GUIDE_SUP = False
        P.DICT_ALL = False


def test_g_parity_removes_only_deftime_and_default_is_v13():
    import prompts3 as P
    assert P.G_PARITY is False
    for t in P.TPLS:
        off = P.guide_rules_text(t)
        P.G_PARITY = True
        try:
            on = P.guide_rules_text(t)
        finally:
            P.G_PARITY = False
        assert "R-DEFTIME:" in off and "R-DEFTIME:" not in on
        assert [l for l in off.splitlines() if not l.startswith("- R-DEFTIME:")] == on.splitlines()
        assert P.guide_rules_text(t) == off


def test_supplement_has_no_tool_observation_and_no_selection_rule():
    import prompts3 as P
    s = P.guide_supplement().lower()
    for w in ("parser compiled", "observation of the official parser", "not a documentation quote", "you should", "choose", "use whenever"):
        assert w not in s, w


def test_prompt_lint_p3_p6_pass():
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bench", "tools"))
    import prompt_lint as L
    assert L.p3()["ok"] and L.p6(os.path.join(os.path.dirname(__file__), "..", "data/reference/lm_reference_with_ltl.jsonl"))["ok"] and L.p1()["ok"] and L.p2()["ok"]


def test_default_prompts_equal_v13_hashes():
    """Flags off: the free-arm and Direct prompts must be byte-identical to the v1.3 FSM run (hashes from its run_info.json)."""
    import hashlib, prompts3 as P
    P.DICT_ALL = True
    try:
        P.GUIDE_SUP = False
        P.G_PARITY = False
        exp = {("B", "MASTeR+G"): "7fcef80f4e296266", ("D", None): "df9d43b6b87459c7", ("B", "SPIDER+G"): "b514b62d18cb1193"}
        for (stg, arm), h in exp.items():
            s, _ = P.build_system_D3("DIRECT") if stg == "D" else P.build_system_B3(arm)
            assert hashlib.sha256(s.encode()).hexdigest()[:16] == h, (stg, arm)
    finally:
        P.DICT_ALL = False


def test_intent_decl_only_appended_and_default_unchanged():
    import hashlib, prompts3 as P
    P.DICT_ALL = True
    try:
        for build, arg in ((P.build_system_D3, "DIRECT"), (P.build_system_B3, "MASTeR+G")):
            P.INTENT_DECL = False
            base, st0 = build(arg)
            P.INTENT_DECL = True
            on, st1 = build(arg)
            P.INTENT_DECL = False
            assert on.replace("\n\n" + P.intent_declaration(), "", 1) == base      # nothing else differs
            assert "INTENT OF THE REQUIREMENTS" in on and "INTENT OF THE REQUIREMENTS" not in base
            assert "Instead of a trigger we wanted the response to hold every time the condition is true and not only when it becomes true from false." in on
            assert st1.get("intent_decl") == "v1.4" and "intent_decl" not in st0
        assert P.INTENT_DECL is False
    finally:
        P.DICT_ALL = False
        P.INTENT_DECL = False


def test_runner_has_exactly_the_11_approaches_and_no_condition_branches():
    import os, re, prompts3 as P
    sh = open(os.path.join(os.path.dirname(__file__), "..", "exp/fsm/run_intent.sh"), encoding="utf-8").read()
    arms = re.search(r"^ARMS=\((.*)\)$", sh, re.M).group(1).split()
    assert arms == P.ARMS_FSM and len(arms) == 11
    assert "A0" not in sh and "A1" not in sh and "A2" not in sh


def test_intent_cond_maps_every_trigger_to_whenever_and_default_is_v13():
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bench", "tools"))
    import selftest as S
    import tpl_rules as T
    assert T.INTENT_COND is False
    S.run()                                    # v1.3 mapping unchanged: golden outputs with when / if
    T.INTENT_COND = True
    try:
        n = 0
        for tpl, sent, slots, want in S.CASES:
            p = T.parse_template(tpl, sent)
            req = T.slot_requests(p)
            a = T.assemble(p, T.lint_slots(req, slots if slots is not None else {k: "x" for k in req}))
            if isinstance(want, tuple) or not a["ok"]:
                continue
            if want.startswith(("when ", "if ")) or " when " in " " + want or " if " in " " + want:
                head = a["fretish"].split(" shall ")[0]
                assert "whenever " in head and not re.search(r"\b(when|if)\b", head.replace("whenever", "")), (sent, a["fretish"])
                assert "R2-COND-INTENT" in a["rules"]
                n += 1
        assert n >= 4
    finally:
        T.INTENT_COND = False


def test_stage_a_reuse_copies_only_matching_hash_and_refuses_mismatch(tmp_path):
    import json as _j
    import types
    sys.path.insert(0, os.path.join(HERE, "..", "bench"))
    import run_pipeline as RP
    src = tmp_path / "src"
    src.mkdir()
    row = {"stage_key": "I1|MASTeR|0|A", "stage": "A", "item_id": "I1", "arm": "MASTeR", "rep": 0, "status": "ok", "prompt_hash": "H1", "raw_result": "x"}
    (src / "calls.jsonl").write_text(_j.dumps(row) + "\n")
    dst = tmp_path / "dst"
    dst.mkdir()
    ctx = types.SimpleNamespace(rows={}, calls_path=dst / "calls.jsonl", prompts={("A", "MASTeR"): ("sys", "H1", "st")}, args=types.SimpleNamespace(), results=dst)
    RP.log = lambda c, m: None
    RP.reuse_stage_a(ctx, src, [{"id": "I1"}], ["MASTeR+G", "MASTeR+R2", "DIRECT"], 1)
    assert list(ctx.rows) == ["I1|MASTeR|0|A"] and ctx.rows["I1|MASTeR|0|A"]["reused_from"].endswith("calls.jsonl")
    ctx2 = types.SimpleNamespace(rows={}, calls_path=tmp_path / "c2.jsonl", prompts={("A", "MASTeR"): ("sys", "H2", "st")}, args=types.SimpleNamespace(), results=dst)
    import pytest
    with pytest.raises(SystemExit):
        RP.reuse_stage_a(ctx2, src, [{"id": "I1"}], ["MASTeR+G"], 1)


def _tools():
    sys.path.insert(0, os.path.join(HERE, "..", "bench", "tools"))


def test_decision_points_reading_classes_follow_fret_semantics():
    _tools()
    from decision_points import decision_points as dp
    a = dp("whenever c the sys shall immediately satisfy r")
    b = dp("the sys shall always satisfy c => r")
    assert a["reading"] == b["reading"] == "EVERY_TIME" and a["ntiming"] == b["ntiming"] == "now"      # same LTL, official parser check (H(c -> r))
    e = dp("when c the sys shall immediately satisfy r")
    assert e["reading"] == "EDGE" and e["ntiming"] == "immediately"
    assert dp("the sys shall always satisfy x > 0")["reading"] == "UNCOND"
    s = dp("In landing mode, when c, the sys shall eventually satisfy r")
    assert s["scope"] == "scoped" and s["reading"] == "EDGE" and s["timing"] == "eventually"
    assert dp("while mode = 4 the watch shall always satisfy alarm_icon_on")["scope"] == "scoped"


def test_sign_test_threshold_13_items():
    _tools()
    from compare_runs import sign_p
    assert sign_p(10, 3) < 0.05 and sign_p(9, 4) > 0.05 and sign_p(0, 0) == 1.0


def test_ownership_table_classifies_every_rule_and_quotes_exist_in_rule_sources():
    import subprocess
    r = subprocess.run([sys.executable, os.path.join(HERE, "..", "bench", "tools", "ownership_table.py")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "unclassified rules (must be 0): 0" in r.stdout


def test_controls_unsatisfiable_formula_is_scored_proof_by_the_judge_and_strict_flag_catches_it():
    from nl2fret_judge.engines import Z3Engine
    f = "(H (a -> b))"
    eng = Z3Engine(6)
    r = judge_pair(f"(({f}) & (! ({f})))", f, eng, aux=True)
    assert r["role"] == "PROOF" and r["gen_sat"] is False                 # documents the instrument flaw the strict metric removes
    assert judge_pair(f, f, eng)["role"] == "SAME"


def test_tm_source_only_removes_selection_procedure_and_default_is_v13():
    import prompts3 as P
    base = P.slot_system_r2()
    assert base == P.SLOT_SYSTEM_R2 and "V-2" in base and "test bench principles" in base
    P.TM_SOURCE_ONLY = True
    try:
        on = P.slot_system_r2()
        assert "V-2" not in on and "V-3" not in on and "test bench principles" not in on
        assert "immediately, initially, at the first timepoint, at the same timepoint (synonyms)" in on
        pl = P.slot_payload([{"template": "EARS", "subject": "s", "clauses": [{"kind": "trigger"}]}], [{"tm": {"phrase": "", "kind": "timing"}, "r": {"phrase": "x", "kind": "resp"}}])
        assert "has_trigger" not in pl[0]["context"]
    finally:
        P.TM_SOURCE_ONLY = False
    assert P.slot_system_r2() == base


def test_sourced_rules_only_refuses_unsourced_mappings_and_omits_them_from_g_text():
    import prompts3 as P
    import tpl_rules as T
    base = P.guide_rules_text("EARS")
    assert "R-EARS-WHERE" in base
    P.SOURCED_ONLY = T.SOURCED_ONLY = True
    try:
        on = P.guide_rules_text("EARS")
        assert "R-EARS-WHERE" not in on and "R-EARS-WHEN" in on
        assert all(r not in P.guide_rules_text("SPIDER") for r in ("R-SP-RESP", "R-SP-BRESP", "R-SP-PREC", "R-SP-BINV", "R-SP-MINDUR", "R-SP-AFTERUNTIL"))
        p = T.parse_template("SPIDER", "Globally, it is always the case that if P holds, then S eventually holds.")
        assert p["ok"]
        a = T.assemble(p, {"p": {"expr": "x"}, "s": {"expr": "y"}}, r2=True)
        assert not a["ok"] and a["code"] == "rule_no_mapping" and a["detail"].startswith("no_source:")
        e = T.parse_template("EARS", "When the button is pressed the system shall start.")
        T.slot_requests(e, r2=True)
        assert e["ok"] and T.assemble(e, {"c1": {"expr": "pressed"}, "r": {"expr": "start"}, "tm": {"expr": "immediately"}}, r2=True)["ok"]   # a sourced mapping still assembles
    finally:
        P.SOURCED_ONLY = T.SOURCED_ONLY = False
    assert P.guide_rules_text("EARS") == base
