"""v1.4 tools: resume flag pinning, launcher paths and copybase, rule_semantics_check workdir."""
import os
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.abspath(os.path.join(HERE, ".."))


def test_resume_with_other_flags_is_refused_and_old_state_gets_flags():
    from nl2fret import run_pipeline as RP
    f14 = dict(dict_all=True, guide_sup=False, g_parity=True, intent_decl=True, tm_source_only=True, sourced_rules_only=True)
    st = {"flags": dict(f14)}
    RP.check_flags(st, dict(f14))                                           # same flags: fine
    with pytest.raises(SystemExit):
        RP.check_flags({"flags": dict(f14)}, dict(f14, intent_decl=False))   # other flags on resume: refused
    old = {"start_epoch": 1}                                                # a run started before this check
    RP.check_flags(old, dict(f14))
    assert old["flags"] == f14


def test_launcher_resolves_relative_paths_and_copybase_skips_judge_records(tmp_path):
    src = tmp_path / "base"
    for d in ("gen", "inputs", "judge", "judge_selfcheck"):
        (src / d).mkdir(parents=True)
        (src / d / "f.txt").write_text("x")
    (src / "summary.json").write_text("{}")
    sh = os.path.join(PKG, "scripts", "run_intent.sh")
    env = dict(os.environ, SRC="base")
    r = subprocess.run(["bash", sh, "copybase", "fsm", "v13", "copy"], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert (tmp_path / "copy" / "gen" / "f.txt").exists() and (tmp_path / "copy" / "summary.json").exists()
    assert not (tmp_path / "copy" / "judge").exists() and not (tmp_path / "copy" / "judge_selfcheck").exists()
    assert not os.path.exists(os.path.join(PKG, "src", "nl2fret", "copy")) and not os.path.exists(os.path.join(PKG, "src", "nl2fret_judge", "copy"))
    r2 = subprocess.run(["bash", sh, "copybase", "fsm", "v13", "copy"], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert r2.returncode != 0                                                # never overwrites a folder that already has gen/


def test_rule_semantics_check_default_workdir_is_next_to_out():
    src = open(os.path.join(PKG, "src", "nl2fret", "tools", "rule_semantics_check.py"), encoding="utf-8").read()
    assert "/tmp/rsc_work" not in src and "--workdir" in src


def test_ntiming_is_the_semantic_class_from_the_official_parser_table():
    from nl2fret.tools.decision_points import decision_points as dp
    n = lambda f: dp(f)["ntiming"]
    assert n("whenever c the s shall immediately satisfy r") == n("the s shall always satisfy c => r")      # same LTL (S3)
    assert n("whenever c the s shall always satisfy r") != n("the s shall always satisfy c => r")           # stronger: r must hold from the trigger on
    assert n("whenever c the s shall satisfy r") == n("whenever c the s shall eventually satisfy r")        # omitted timing means eventually
    assert n("when c the s shall immediately satisfy r") != n("whenever c the s shall immediately satisfy r")   # edge vs every time


def test_timing_table_classes_match_pairwise_roles():
    import json
    d = json.load(open(os.path.join(PKG, "src", "nl2fret", "data", "timing_semantics.json")))
    for cl in d["equivalence_classes"]:
        for m in cl[1:]:
            assert d["roles"][f"{m} vs {cl[0]}"] == "SAME" and d["roles"][f"{cl[0]} vs {m}"] == "SAME"
    reps = [c[0] for c in d["equivalence_classes"]]
    for a in reps:
        for b in reps:
            if a != b:
                assert d["roles"][f"{a} vs {b}"] != "SAME"          # distinct classes are never equivalent
