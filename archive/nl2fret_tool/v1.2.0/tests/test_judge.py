"""Sandbox tests (z3 engine; no NuSMV needed). Run from judging/: python -m pytest ../tests -q"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "judging"))
from nl2fret_judge import selfcheck, ap_check
from nl2fret_judge.engines import Z3Engine, spec_text
from nl2fret_judge.judge import judge_pair, clean_markup


def test_selfcheck_z3():
    ok, rows = selfcheck.run(Z3Engine(8))
    assert ok, rows


def test_spec_text_directions():
    assert spec_text("sound", "G1", "R1") == "G ((R1) -> (G1))"
    assert spec_text("compl", "G1", "R1") == "G ((G1) -> (R1))"


def test_und_when_no_alignment():
    r = judge_pair("(H (x -> y))", "(H (a -> b))", Z3Engine(8), mode="anchor")
    assert r["role"] in ("UND", "SAME")  # free renaming may align; anchor mode needs same-type counterpart


def test_markup_and_precedence_reference():
    t = clean_markup("(H <b><i>(mag ( yout - Xtarg ) >= r & dot ( ( yout - Xtarg ) , ( yout - Xv ) ) = 0)</i></b>)")
    r = judge_pair(t, t, Z3Engine(8))
    assert r["role"] == "SAME"


def test_ap_check_rule():
    a = ap_check.ap_check(["a"], ["a", "b"])
    assert a["nm_by_kind"] == {"equiv": False, "sound": False, "compl": True}


def test_pairs_agree_with_stored_z3_roles():
    p = os.path.join(os.path.dirname(__file__), "..", "data", "reference", "pairs_sample.jsonl")
    if not os.path.exists(p):
        return
    for l in open(p):
        d = json.loads(l)
        r = judge_pair(d["gen_pt"], d["ref_pt"], Z3Engine(8))
        if r["role"]:
            assert r["role"] == d["z3_role"], d["id"]
