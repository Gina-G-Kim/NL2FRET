import os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))


def test_v15_prompt_lint_passes():
    r = subprocess.run([sys.executable, "-m", "nl2fret.tools.prompt_v15_lint"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "V-LEAK compared 112" in r.stdout


def test_v15_slot_keywords_assemble():
    from nl2fret import tpl_rules as T
    T.SLOT_KW = True
    try:
        p = T.parse_template("EARS", "WHEN the start button is pressed the controller shall open the valve.")
        rq = T.slot_requests(p, r2=True)
        assert "ck" in rq and "tm" in rq
        ok = T.lint_slots(rq, {"c1": "start_pressed", "r": "valve_open", "ck": "whenever", "tm": "finally"})
        assert T.assemble(p, ok, r2=True)["fretish"] == "whenever start_pressed controller shall finally satisfy valve_open"
        bad = T.lint_slots(rq, {"c1": "a", "r": "b", "ck": "unless", "tm": "soon"})
        assert bad["ck"]["violations"] and bad["tm"]["violations"]
    finally:
        T.SLOT_KW = False
