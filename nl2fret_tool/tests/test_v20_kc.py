"""Keyword check step KC (kc_stage.py, KC_STAGE_SPEC.md, experiment 030): groups of a sentence, adoption rule, message assembly, reference documents, run record, keyword table.
Unit tests only: no model call and no parser run. The parser fields of the sentences are recorded in tests/data/kc_parser_fields.json (official parser, docker image fret-lab, 2026-11-17)."""
import json
import os
import re

import pytest

from nl2fret import kc_stage as KC
from nl2fret import rt_stage as RT
from nl2fret import units3 as U
from nl2fret.paths import PACKAGE

HERE = os.path.dirname(os.path.abspath(__file__))
FX = json.load(open(os.path.join(HERE, "data", "kc_parser_fields.json"), encoding="utf-8"))["sentences"]

# expected groups of the specification (the values were set by hand from the examples of the FRETish guide); sentence 3 is rejected by the official parser (`count` is a reserved word)
EXPECTED = [
    ("whenever intruder the alarm shall immediately satisfy sound", "COND (whenever), TIMING_POINT (immediately)"),
    ("In landing mode the system shall eventually satisfy decrease_speed", "SCOPE (in), TIMING_POINT (eventually)"),
    ("the system shall always satisfy count >= 0", "TIMING_POINT (always)"),
    ("When errorCondition, the system shall, for 4 seconds, satisfy alarmOn", "COND (when), TIMING_DURATION (for)"),
    ("The system shall satisfy x", "TIMING_POINT (timing omitted)"),
    ("The system shall, until Count = 0, satisfy Count > 0", "TIMING_STOP (until)"),
]


def norm(line):
    return re.sub(r"\s+", " ", line).strip()


def test_reference_documents_equal_lines_of_the_guide():
    """every line of a KC document equals a line of the FRETish guide, except the added headings (title line, 'Keywords of this group', 'Source', 'EXAMPLES', 'Formulas of FRET', 'Condition with each timing')"""
    guide = {norm(l) for l in open(os.path.join(PACKAGE, "prompts", "fretish_reference.md"), encoding="utf-8").read().split("\n")}
    heading = re.compile(r"^(KEYWORD REFERENCE:|Keywords of this group:|Source:|#+ ?EXAMPLES$|EXAMPLES$|Formulas of FRET|Condition with each timing)")
    missing = {}
    for g in KC.GROUPS:
        for i, line in enumerate(KC.doc_text(g).split("\n"), 1):
            n = norm(line)
            if n and not heading.match(n) and n not in guide:
                missing.setdefault(g, []).append((i, n[:90]))
    assert not missing, missing


@pytest.mark.parametrize("sentence, expected", EXPECTED)
def test_groups_of_the_specified_sentences(sentence, expected):
    fl = FX[sentence]
    gs = KC.groups_for(sentence, fl)
    assert KC.group_line(gs) == expected
    if sentence.startswith("the system shall always satisfy count"):
        assert fl is None and all(g["via"] == "lexical" for g in gs)      # no parser fields: the groups come from the tokens of the sentence and say so
    else:
        assert fl is not None and all(g["via"] == "fields" for g in gs)


def test_lexical_fallback_gives_the_same_groups_as_the_fields():
    for s, fl in FX.items():
        if fl:
            assert KC.group_line(KC.groups_for(s, fl)) == KC.group_line(KC.groups_for(s, None)), s


def test_every_keyword_of_the_guide_is_read_from_the_written_sentence():
    kws = {"Upon powered_on the component shall immediately satisfy bootup": "COND (upon)",
           "unless p the system shall always satisfy q": "COND (unless)",
           "Only after arming mode shall the system eventually satisfy fired": "SCOPE (only after)",
           "When not in initialization mode the system shall always satisfy commands_accepted": "SCOPE (when not in)",
           "During landing mode the system shall always satisfy q": "SCOPE (during)",
           "When currentOverload the circuitBreaker shall, at the next timepoint, satisfy shutoff": "TIMING_POINT (at the next timepoint)",
           "The system shall initially satisfy z": "TIMING_POINT (initially)",
           "The system shall, before TakeOff, satisfy CheckListTasksCompleted": "TIMING_STOP (before)",
           "The system shall within 2 seconds satisfy y": "TIMING_DURATION (within)"}
    for s, want in kws.items():
        assert want in KC.group_line(KC.groups_for(s, FX[s])), (s, KC.group_line(KC.groups_for(s, FX[s])))
    # a scope omitted does not fire; a timing omitted fires TIMING_POINT
    assert [g["group"] for g in KC.groups_for("The system shall satisfy x", FX["The system shall satisfy x"])] == ["TIMING_POINT"]


# ------------------------------------------------------------------ adoption rule and unit state
ITEM = {"id": "I1", "challenge": "00_X"}
S0 = "whenever p the s shall immediately satisfy q"
S1 = "whenever p the s shall always satisfy q"
BAD = "whenever p the s shall bogus satisfy q"


def row(stage, texts):
    return {"stage_key": U.skey("I1", "DIRECT", 0, stage), "stage": stage, "status": "ok", "parsed": {"fretish": texts, "unmapped_content": []}, "raw_result": json.dumps({"fretish": texts})}


def comp_for(**verdict):
    return {t: {"ok": ok, "error": None if ok else "syntax"} for t, ok in verdict.items()}


def rows_for(*extra):
    r = {U.skey("I1", "DIRECT", 0, "D"): row("D", [S0])}
    for stage, texts in extra:
        r[U.skey("I1", "DIRECT", 0, stage)] = row(stage, texts)
    return r


def test_kc_answer_is_adopted_only_when_the_parser_accepts_every_sentence():
    rows = rows_for((KC.KC_STAGE, [S1]))
    comp = {S0: {"ok": True, "error": None}, S1: {"ok": True, "error": None}}
    rec = U.derive(rows, ITEM, "DIRECT", 0, comp)
    rec2, adopted = KC.with_kc(rec, rows, ITEM, "DIRECT", 0, comp)
    assert adopted and rec2["kc_adopted"] and rec2["rounds"][-1]["stage"] == KC.KC_STAGE and RT.last_texts(rec2) == [S1] and rec2["kc_changed"] == [True]
    rows = rows_for((KC.KC_STAGE, [BAD]))
    comp = {S0: {"ok": True, "error": None}, BAD: {"ok": False, "error": "syntax"}}
    rec = U.derive(rows, ITEM, "DIRECT", 0, comp)
    rec2, adopted = KC.with_kc(rec, rows, ITEM, "DIRECT", 0, comp)
    assert not adopted and rec2["kc_adopted"] is False          # vf stays, the variant kc equals vf (make_judge_inputs strips the round)
    # unchanged sentence: adopted and not changed
    rows = rows_for((KC.KC_STAGE, [S0]))
    comp = {S0: {"ok": True, "error": None}}
    rec = U.derive(rows, ITEM, "DIRECT", 0, comp)
    rec2, adopted = KC.with_kc(rec, rows, ITEM, "DIRECT", 0, comp)
    assert adopted and rec2["kc_changed"] == [False]


def test_kc_skipped_marks_a_unit_without_any_group_and_no_row():
    rows = rows_for()
    comp = {S0: {"ok": True, "error": None}}
    rec = U.derive(rows, ITEM, "DIRECT", 0, comp)
    rec2, adopted = KC.with_kc(rec, rows, ITEM, "DIRECT", 0, comp, lambda texts: [[] for _ in texts])
    assert not adopted and rec2["kc_skipped"] is True
    rec3, _ = KC.with_kc(rec, rows, ITEM, "DIRECT", 0, comp, lambda texts: [[{"group": "COND"}] for _ in texts])
    assert rec3["kc_skipped"] is False


def test_chain_round_trip_starts_from_the_adopted_kc_answer(tmp_path):
    cache = tmp_path / "parser_cache.jsonl"
    lines = [{"t": S0, "ok": True, "error": None}, {"t": S1, "ok": True, "error": None}, {"t": "whenever p the s shall never satisfy q", "ok": True, "error": None}]
    cache.write_text("\n".join(json.dumps(x) for x in lines) + "\n", encoding="utf-8")
    rows = rows_for((KC.KC_STAGE, [S1]), (RT.RT_STAGE, ["whenever p the s shall never satisfy q"]))
    ch = KC.chain(rows, [ITEM], ["DIRECT"], [0], "mock", str(cache))[("I1", "DIRECT", 0)]
    assert ch["base"]["rounds"][-1]["stage"] == "D" and ch["kc"]["kc_adopted"] and ch["in"]["rounds"][-1]["stage"] == KC.KC_STAGE
    assert ch["rt"]["rt_adopted"] and RT.last_texts(ch["rt"]) == ["whenever p the s shall never satisfy q"] and [r["stage"] for r in ch["rt"]["rounds"]] == ["D", KC.KC_STAGE, RT.RT_STAGE]
    # a KC answer that is not accepted: the round trip starts from the vf answer
    cache.write_text("\n".join(json.dumps(x) for x in [{"t": S0, "ok": True, "error": None}, {"t": BAD, "ok": False, "error": "syntax"}]) + "\n", encoding="utf-8")
    rows = rows_for((KC.KC_STAGE, [BAD]))
    ch = KC.chain(rows, [ITEM], ["DIRECT"], [0], "mock", str(cache))[("I1", "DIRECT", 0)]
    assert not ch["kc"]["kc_adopted"] and ch["in"]["rounds"][-1]["stage"] == "D"


# ------------------------------------------------------------------ message
def test_plan_lists_only_sentences_with_groups_and_skips_a_unit_without_any():
    pl = KC.plan("I1", "NATURAL LANGUAGE REQUIREMENT:\nx", [S0, "The system shall satisfy x"], {})
    body, groups = pl
    assert body.startswith("ITEM I1\ninput: NATURAL LANGUAGE REQUIREMENT:") and body.count("sentence ") == 2 and "groups: " in body and len(groups) == 2
    assert KC.plan("I1", "x", [S0], {S0: {"scope": "null", "condition": "null", "qualifier": None, "timing": "null", "timing_range": None, "scope_range": None}}) is not None   # timing omitted still fires TIMING_POINT
    assert KC.plan("I1", "x", [], {}) is None


def test_message_holds_the_reference_text_of_the_fired_groups_once():
    def task(i, names):
        return {"it": {"id": i}, "body": f"ITEM {i}\ninput: x\n", "extra": {"kc_group_names": names}}
    msg = KC.block_text([task("A", ["COND", "TIMING_POINT"]), task("B", ["COND", "SCOPE"])], None, lambda s: "")
    assert msg.startswith("ITEMS: 2\n\n" + KC.KC_HEAD) and msg.rstrip().endswith(KC.KC_TAIL)
    for g in ("COND", "TIMING_POINT", "SCOPE"):
        assert msg.count(f"== {g} ==\n") == 1 and KC.doc_text(g).strip() in msg
    for g in ("TIMING_DURATION", "TIMING_STOP"):
        assert f"== {g} ==" not in msg
    assert msg.index("== COND ==") < msg.index("== TIMING_POINT ==") < msg.index("== SCOPE ==")        # order of the table of the specification
    assert msg.count("### id: ") == 2 and msg.index("### id: A") < msg.index("== COND ==")
    sig = KC.block_text([task("A", ["COND"])], "name | kind", lambda s: "\nSIGNAL DICTIONARY (x)\n" + s)
    assert sig.rstrip().endswith("name | kind") and "SIGNAL DICTIONARY" in sig                           # the dictionary comes last, as in the other stages


def test_document_hashes_cover_every_group_and_equal_the_files():
    import hashlib
    sh = KC.doc_sha()
    assert sorted(sh) == sorted(KC.GROUPS)
    for g, h in sh.items():
        assert h == hashlib.sha256(open(os.path.join(KC.KC_DIR, KC.GROUP_FILES[g]), "rb").read()).hexdigest()


def test_sources_file_names_the_reference_documents():
    d = json.load(open(os.path.join(PACKAGE, "prompts", "sources_v15.json"), encoding="utf-8"))
    assert d["keyword_reference"]["status"] == "official_verbatim with headings" and len(d["keyword_reference"]["files"]) == 5


# ------------------------------------------------------------------ variants and tables
def test_rt_effect_counts_kc_and_the_keyword_distribution(tmp_path):
    import subprocess
    import sys
    for v, kw in (("vf", [{"condition": "when", "timing": "always", "scope": None}]), ("kc", [{"condition": "whenever", "timing": "always", "scope": "in"}])):
        d = tmp_path / f"inputs_{v}"
        d.mkdir()
        (d / "units.json").write_text(json.dumps({"units": [{"item": "LM-06_EB-N1", "texts": ["x"], "keywords": kw}]}), encoding="utf-8")
        j = tmp_path / f"judge_{v}"
        j.mkdir()
        (j / "part_results.jsonl").write_text(json.dumps({"item": "LM-06_EB-N1", "arm": "DIRECT", "rep": 0, "challenge": "06_EB", "parts": [{"part": 1, "success": v == "kc"}]}) + "\n", encoding="utf-8")
    out = subprocess.run([sys.executable, "-m", "nl2fret.tools.rt_effect", "--judge", f"vf={tmp_path}/judge_vf", f"kc={tmp_path}/judge_kc", "--keyword-inputs", f"vf={tmp_path}/inputs_vf", f"kc={tmp_path}/inputs_kc"],
                         capture_output=True, text=True)
    assert out.returncode == 0, out.stderr
    rep = json.loads(out.stdout)
    assert rep["pairs"]["vf->kc"]["DIRECT"] == {"common_parts": 1, "gain": 1, "loss": 0}
    assert rep["keyword_distribution"]["vf"]["condition"] == {"when": 1} and rep["keyword_distribution"]["kc"]["condition"] == {"whenever": 1} and rep["keyword_distribution"]["kc"]["scope"] == {"in": 1}


def test_run_batch_has_the_kc_switch():
    s = open(os.path.join(HERE, "..", "scripts", "run_batch.sh")).read()
    assert 'VARIANTS="v0 vf kc rt"' in s and "NO_KC" in s and "--no-kc" in s and "keyword-inputs" in s
