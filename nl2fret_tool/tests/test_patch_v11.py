"""Tests of the v1.1.0 patch (sandbox: z3 engine or stub engines, no NuSMV needed). Run from judging/: python -m pytest ../tests -q

(a) an empty candidate list is UND            (b) candidates that all fail in _prepare stay N/M
(c) reference_trials and unchanged selection  (d) rlz hash in the run header
(e) resume after an interrupted write: Recorder and aggregate
"""
import hashlib
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "judging"))
import nl2fret_judge  # noqa: E402
from nl2fret_judge import aggregate as AG, cli, recorder  # noqa: E402
from nl2fret_judge.engines import Z3Engine  # noqa: E402
from nl2fret_judge.judge import best_over_references, judge_pair  # noqa: E402


def test_version():
    # the changes tested in this file came with 1.1.0 and stay in later versions; the exact version is asserted in test_patch_v12.py
    assert tuple(int(x) for x in nl2fret_judge.__version__.split(".")) >= (1, 1, 0)


# (a) -----------------------------------------------------------------------------------------------------------------------------------------
def test_no_injective_renaming_is_und():
    # generated x, y (booleans) have the same single same-type counterpart a in the reference (b is a number): align.candidates returns maps == []
    r = judge_pair("(H (x & y))", "(H (a & (b > 5)))", Z3Engine(8))
    assert r["role"] == "UND" and r["und_reason"] == "atomization_mismatch"
    assert r["nm"] is False and r["nm_reason"] is None
    assert r["nm_detail"] == {"message": "no injective renaming candidate"}
    assert r["alignment"]["n_candidates"] == 0 and r["alignment"]["n_tried"] == 0 and r["queries"] == []


def test_und_from_align_is_unchanged():
    r = judge_pair("(H (x & y & z))", "(H (a & b))", Z3Engine(8))
    assert r["role"] == "UND" and r["und_reason"] == "atomization_mismatch" and r["nm"] is False
    assert r["nm_detail"] == {"message": "unmatched gen vars 3 > unmatched ref vars 2"}


# (b) -----------------------------------------------------------------------------------------------------------------------------------------
def test_candidates_but_conversion_fails_is_nm():
    # identical names: one candidate exists, but the window 100 exceeds cap 10, so _prepare fails for every candidate
    r = judge_pair("(H[<=100] a)", "(H[<=100] a)", Z3Engine(8), cap=10)
    assert r["alignment"]["n_candidates"] == 1 and r["alignment"]["n_tried"] == 0
    assert r["nm"] is True and r["nm_reason"] == "converter_limit" and r["role"] is None and r["und_reason"] is None
    assert r["nm_detail"]["cap"] == 10


# (c) -----------------------------------------------------------------------------------------------------------------------------------------
class SmvStubEngine(Z3Engine):
    """z3 verdicts, but every query carries a made-up SMV text, so that the _smv merge can be tested without NuSMV."""
    name = "z3-with-fake-smv"

    def query(self, kind, gs, rs, atoms, **kw):
        q = super().query(kind, gs, rs, atoms, **kw)
        q.smv_text = f"MODULE main -- {kind} {gs} {rs}\n"
        q.smv_sha256 = hashlib.sha256(q.smv_text.encode()).hexdigest()
        return q


GEN = "(H (a -> b))"
REF_REFUTE = "(H (a & b))"                              # sound only (the reference is stronger than the generated formula)
REF_SAME = "(H (a -> b))"
REF_NEITHER = "(H (b -> a))"
REF_PROOF = "((H (a -> b)) | (O (! a)))"                # compl only (the generated formula is stronger)


def _parts(*refs):
    return [(f"P{i}#0", r, None) for i, r in enumerate(refs)]


def test_reference_trials_stop_at_same_and_keep_roles():
    parts = _parts(REF_REFUTE, REF_SAME, REF_NEITHER)
    rec = best_over_references(GEN, parts, SmvStubEngine(8), pair_id="t1", meta={})
    alone = [judge_pair(GEN, r, SmvStubEngine(8)) for r in (REF_REFUTE, REF_SAME)]
    assert rec["reference_part"] == "P1#0" and rec["role"] == "SAME" == alone[1]["role"]
    tr = rec["reference_trials"]
    assert [t["reference_part"] for t in tr] == ["P0#0", "P1#0"]            # the loop stops at the first SAME, P2 is not tried
    assert [t["role"] for t in tr] == [alone[0]["role"], alone[1]["role"]] == ["REFUTE", "SAME"]
    for t in tr:
        assert set(t) == {"reference_part", "role", "nm", "nm_reason", "und_reason", "n_queries", "smv_sha256", "queries"}
        assert t["n_queries"] == len(t["queries"]) == len(t["smv_sha256"])
        assert all(set(q) == {"kind", "verdict", "elapsed_sec"} for q in t["queries"])
    # the kept record keeps its full query output, and it is the only place that has it
    assert "stdout" in rec["queries"][0] and tr[1]["n_queries"] == len(rec["queries"])
    # SMV files of the unselected attempt are merged into _smv
    own_hashes = {q["smv_sha256"] for q in rec["queries"]}
    unselected = set(tr[0]["smv_sha256"])
    assert unselected and not (unselected & own_hashes)
    assert set(rec["_smv"]) == own_hashes | unselected


def test_selection_rule_is_unchanged():
    # PROOF and REFUTE have the same rank: the first one wins; NEITHER ranks lower than both
    rec = best_over_references(GEN, _parts(REF_REFUTE, REF_PROOF, REF_NEITHER), Z3Engine(8), pair_id="t2", meta={})
    assert rec["reference_part"] == "P0#0" and rec["role"] == "REFUTE"
    assert [t["role"] for t in rec["reference_trials"]] == ["REFUTE", "PROOF", "NEITHER"]
    rec = best_over_references(GEN, _parts(REF_NEITHER, REF_PROOF), Z3Engine(8), pair_id="t3", meta={})
    assert rec["reference_part"] == "P1#0" and rec["role"] == "PROOF"
    assert best_over_references(GEN, [], Z3Engine(8), pair_id="t4", meta={}) is None


def test_no_candidate_part_ranks_as_und_behind_an_nm_part():
    # v1.0.0 recorded the no-candidate part as N/M (rank 3) and kept the first of two N/M parts; it is UND (rank 4) now, so the N/M part is kept
    parts = [("P0#0", "(H (a & (b > 5)))", None), ("P1#0", "(H[<=100] (x & y))", None)]
    rec = best_over_references("(H (x & y))", parts, Z3Engine(8), pair_id="t5", meta={}, cap=10)
    assert [t["role"] for t in rec["reference_trials"]] == ["UND", None]
    assert rec["reference_part"] == "P1#0" and rec["nm"] is True and rec["nm_reason"] == "converter_limit"


# (d) -----------------------------------------------------------------------------------------------------------------------------------------
def _write_inputs(d):
    ref = {"id": "ITEM-1", "gt_parts": [[{"reqid": "R1", "ltl": {"past_time": "(H (a -> b))", "future_time": "G (a -> b)"}}]]}
    paths = {"ref": d / "ref.jsonl", "units": d / "units.json", "ltl": d / "ltl.jsonl", "rlz": d / "rlz.jsonl"}
    paths["ref"].write_text(json.dumps(ref) + "\n", encoding="utf-8")
    paths["units"].write_text(json.dumps({"units": [{"item": "ITEM-1", "arm": "DIRECT", "rep": 0, "status": "parsed", "texts": ["s1"]}]}), encoding="utf-8")
    paths["ltl"].write_text(json.dumps({"sentence": "s1", "parser_ok": True, "ltl_pt": "(H (a -> b))", "ltl_ft": "G (a -> b)"}) + "\n", encoding="utf-8")
    paths["rlz"].write_text(json.dumps({"item_id": "ITEM-1", "arm": "DIRECT", "rep": 0, "sentence": "s1", "result": "realizable"}) + "\n", encoding="utf-8")
    return {k: str(v) for k, v in paths.items()}


def _judge(p, out, with_rlz):
    argv = ["judge", "--engine", "z3", "--out", str(out), "--units", p["units"], "--ltl", p["ltl"], "--reference", p["ref"]]
    if with_rlz:
        argv += ["--rlz", p["rlz"]]
    assert cli.main(argv) == 0
    return json.load(open(os.path.join(str(out), "run_header.json"))), [json.loads(l) for l in open(os.path.join(str(out), "judge_records.jsonl"))]


def test_header_has_rlz_hash(tmp_path):
    p = _write_inputs(tmp_path)
    h, recs = _judge(p, tmp_path / "with_rlz", True)
    assert h["version"] == nl2fret_judge.__version__
    assert h["inputs"] == {"units": recorder.sha256_file(p["units"]), "ltl": recorder.sha256_file(p["ltl"]), "rlz": recorder.sha256_file(p["rlz"]),
                           "reference": recorder.sha256_file(p["ref"])}
    assert len(recs) == 1 and recs[0]["role"] == "SAME" and len(recs[0]["reference_trials"]) == 1
    h2, _ = _judge(p, tmp_path / "no_rlz", False)
    assert h2["inputs"]["rlz"] is None and h2["inputs"]["units"] == h["inputs"]["units"]


# (e) -----------------------------------------------------------------------------------------------------------------------------------------
def _rec(pid, text="plain"):
    return {"pair_id": pid, "role": "SAME", "nm": False, "nm_reason": None, "und_reason": None, "text": text}


def _lines(path):
    return [json.loads(l) for l in open(path, encoding="utf-8").read().split("\n") if l.strip()]


@pytest.mark.parametrize("keep", [20, 1, "multibyte"])
def test_recorder_drops_partial_last_line_and_resumes(tmp_path, keep):
    d = tmp_path / "run"
    r = recorder.Recorder(str(d), {"tool": "t"})
    r.write(_rec("p1"), {})
    r.write(_rec("p2", "한글 한글 한글"), {})
    path = d / "judge_records.jsonl"
    data = path.read_bytes()
    start = data.rfind(b"\n", 0, len(data) - 1) + 1                      # start of the second line
    if keep == "multibyte":                                             # cut inside a three byte character
        cut = start + data[start:].index("한".encode()) + 1
    else:
        cut = start + keep
    path.write_bytes(data[:cut])
    # reading the interrupted file (no resume yet): the aggregate reader skips the partial line, the file is not changed
    assert list(AG.read_records(str(path))) == ["p1"]
    assert path.read_bytes() == data[:cut]
    # resume: the partial line is removed and kept, the pair is not done, the new record starts on a fresh line
    r2 = recorder.Recorder(str(d))
    assert r2.has("p1") and not r2.has("p2")
    kept = (d / recorder.TAIL_FILE).read_bytes()
    assert data[start:cut] in kept
    r2.write(_rec("p2", "한글 한글 한글"), {})
    assert [x["pair_id"] for x in _lines(path)] == ["p1", "p2"]
    assert list(AG.read_records(str(path))) == ["p1", "p2"]
    assert path.read_bytes().count(b"\n") == 2
    assert recorder.Recorder(str(d)).done == {"p1", "p2"}               # a further resume changes nothing
    assert path.read_bytes().count(b"\n") == 2


def test_recorder_keeps_complete_record_without_newline(tmp_path):
    d = tmp_path / "run"
    r = recorder.Recorder(str(d), {"tool": "t"})
    r.write(_rec("p1"), {})
    path = d / "judge_records.jsonl"
    path.write_bytes(path.read_bytes().rstrip(b"\n"))                    # whole record, only the newline is missing
    r2 = recorder.Recorder(str(d))
    assert r2.has("p1") and not (d / recorder.TAIL_FILE).exists()
    r2.write(_rec("p2"), {})
    assert [x["pair_id"] for x in _lines(path)] == ["p1", "p2"]


def test_aggregate_reader_still_fails_on_a_damaged_middle_line(tmp_path):
    path = tmp_path / "judge_records.jsonl"
    path.write_text(json.dumps(_rec("p1")) + "\n" + '{"pair_id": "p2", "role"\n' + json.dumps(_rec("p3")) + "\n", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        AG.read_records(str(path))


def test_recorder_without_existing_file_and_empty_file(tmp_path):
    d = tmp_path / "run"
    r = recorder.Recorder(str(d), {"tool": "t"})
    assert r.done == set() and not (d / recorder.TAIL_FILE).exists()
    (d / "judge_records.jsonl").write_bytes(b"")
    assert recorder.Recorder(str(d)).done == set()
