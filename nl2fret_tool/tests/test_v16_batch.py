import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.join(HERE, "..", "src", "nl2fret")
from nl2fret import agent_call as A


def test_env_whitelist(monkeypatch):
    monkeypatch.setenv("CLAUDE_CODE_SSE_PORT", "1")
    monkeypatch.setenv("CCR_SESSION", "x")
    monkeypatch.setenv("MY_LOGIN", "tok")
    e = A.AgentConfig(env_pass=["MY_LOGIN"]).env()
    assert "CLAUDE_CODE_SSE_PORT" not in e and "CCR_SESSION" not in e
    assert e["MY_LOGIN"] == "tok" and "PATH" in e


def test_command_flags():
    c = A.AgentConfig(model="sonnet", extra="--effort medium").command("SYS", A.BATCH_SCHEMA)
    for f in ("--tools", "--no-session-persistence", "--disable-slash-commands", "--strict-mcp-config", "--json-schema", "--effort"):
        assert f in c
    assert c[c.index("--tools") + 1] == "" and c[c.index("--setting-sources") + 1] == ""
    assert c[c.index("--system-prompt") + 1] == "SYS"


def test_answer_object():
    assert A.answer_object({"structured_output": {"a": 1}}) == {"a": 1}
    assert A.answer_object({"result": '{"b": 2}'}) == {"b": 2}
    assert A.answer_object({"result": "chatter"}) is None
    assert A.answer_object(None) is None
    assert A._result_object('[{"type":"system"},{"type":"result","result":"{}"}]')["type"] == "result"


def test_batch_system_and_declined():
    from nl2fret import batch_pipeline as B
    s = B.batch_system("BASE")
    assert s.startswith("BASE") and "### id:" in s
    assert B.declined("B", ["schema_fretish"], {"fretish": []})
    assert not B.declined("B", [], {"fretish": ["x"]})
    assert B.declined("A", ["schema_sentences"], {"sentences": []})
    assert not B.declined("B", ["schema_fretish"], None)


def test_extract_json():
    from nl2fret import common as C
    assert C.extract_json('{"a": 1}') == {"a": 1}
    assert C.extract_json('```json\n{"a": 2}\n```') == {"a": 2}


def test_rt_clean_and_applicable():
    from nl2fret import rt_stage as R
    assert R.clean("In <b>x</b><br>then y") == "In x | then y"
    ok = {"pending": False, "pipeline": None, "rounds": [{"pending": False, "sentences": [{"text": "t", "official": {"ok": True}}]}]}
    assert R.applicable(ok)
    bad = json.loads(json.dumps(ok)); bad["rounds"][0]["sentences"][0]["official"]["ok"] = False
    assert not R.applicable(bad)
    assert not R.applicable({"pending": True, "pipeline": None, "rounds": []})


def test_group_rlz_set_job():
    from nl2fret.fret_check import group_rlz as G
    sem = {"component_name": "c", "scope": {"type": "null"}, "condition": "null", "timing": "always", "response": "satisfaction", "post_condition": "(x)", "variables": []}
    comp = {"a": {"ok": True, "sem": sem, "ltl_ft": "x", "ltl_pt": "x", "fretish": "a"}, "b": {"ok": False, "error": "e"}}
    job, meta = G.set_job("T", ["b"], comp)
    assert job is None and meta["n_rejected"] == 1 and meta["n_sentences"] == 0


def test_isolation_allowed_items(monkeypatch):
    assert A.ALLOWED_VISIBLE == {"StructuredOutput", "userEmail"}
    def probe(vis, cwd_empty=True):
        monkeypatch.setattr(A, "call_agent", lambda cfg, s, u, sc: {"answer": {"visible": vis}, "cwd_empty": cwd_empty, "obj": {}, "rc": 0, "stderr": ""})
        return A.isolation_probe(A.AgentConfig())
    assert probe(["StructuredOutput", "userEmail"])[0] is True
    assert probe(["userEmail"])[0] is True
    assert probe([])[0] is True
    assert probe(["StructuredOutput", "userEmail", "Skill"])[0] is False
    assert probe(["Read"])[0] is False
    assert probe(["userEmail"], cwd_empty=False)[0] is False


def test_isolation_record_has_no_email(monkeypatch):
    monkeypatch.setattr(A, "call_agent", lambda cfg, s, u, sc: {"answer": {"visible": ["userEmail: someone@example.org"]}, "cwd_empty": True, "obj": {}, "rc": 0, "stderr": "x someone@example.org"})
    ok, rec = A.isolation_probe(A.AgentConfig())
    assert ok is False and "@" not in json.dumps(rec)


def test_rt_effect_only_filters(tmp_path):
    import subprocess
    rows = [{"arm": "DIRECT", "item": "LM-06_EB-N1", "challenge": "06_EB", "rep": 0, "parts": [{"part": 1, "success": True}]},
            {"arm": "DIRECT", "item": "LM-01_FSM-N01", "challenge": "01_FSM", "rep": 0, "parts": [{"part": 1, "success": False}, {"part": 2, "success": False}]}]
    d = tmp_path / "j"; d.mkdir()
    (d / "part_results.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    def run(*extra):
        out = subprocess.run([sys.executable, "-m", "nl2fret.tools.rt_effect", "--judge", f"v0={d}", f"vf={d}", *extra], capture_output=True, text=True, check=True).stdout
        return json.loads(out)["per_arm"]["DIRECT"]["v0"]
    assert run() == {"parts": 3, "success": 1}
    assert run("--only-challenge", "06_EB") == {"parts": 1, "success": 1}
    assert run("--only-item", "LM-01_FSM-N01") == {"parts": 2, "success": 0}

