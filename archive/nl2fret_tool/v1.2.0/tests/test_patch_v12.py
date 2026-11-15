"""Tests of the v1.2.0 patch (sandbox: z3 engine, no NuSMV needed). Run from judging/: python -m pytest ../tests -q

(a) run header: interpreter and z3 versions, code hashes, SMV template identifier and query templates; docs/DESIGN.md section 7 names exactly the keys the code writes
(b) freeze device: release writes the manifest once, judge checks it (match, changed file, --allow-unfrozen, no manifest, unreadable manifest), make release
(c) selection rank of the reference parts: explicit RANK, unchanged behaviour, NEITHER before N/M before UND

The freeze tests work on a copy of the judging code in a temporary directory; they never write a manifest into, or change a file of, the real package tree.
"""
import hashlib
import importlib.metadata
import json
import os
import platform
import re
import shutil
import subprocess
import sys

import pytest

PKG = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(PKG, "judging"))
import nl2fret_judge  # noqa: E402
from nl2fret_judge import cli, engines, freeze  # noqa: E402
from nl2fret_judge.engines import Z3Engine  # noqa: E402
from nl2fret_judge.judge import RANK, best_over_references, rank_of  # noqa: E402

MANIFEST = freeze.MANIFEST_NAME


def test_version():
    assert nl2fret_judge.__version__ == "1.2.0"


# inputs and helpers --------------------------------------------------------------------------------------------------------------------------------
def _write_inputs(d):
    ref = {"id": "ITEM-1", "gt_parts": [[{"reqid": "R1", "ltl": {"past_time": "(H (a -> b))", "future_time": "G (a -> b)"}}]]}
    paths = {"ref": d / "ref.jsonl", "units": d / "units.json", "ltl": d / "ltl.jsonl"}
    paths["ref"].write_text(json.dumps(ref) + "\n", encoding="utf-8")
    paths["units"].write_text(json.dumps({"units": [{"item": "ITEM-1", "arm": "DIRECT", "rep": 0, "status": "parsed", "texts": ["s1"]}]}), encoding="utf-8")
    paths["ltl"].write_text(json.dumps({"sentence": "s1", "parser_ok": True, "ltl_pt": "(H (a -> b))", "ltl_ft": "G (a -> b)"}) + "\n", encoding="utf-8")
    return {k: str(v) for k, v in paths.items()}


def _copy_pkg(dst):
    """Copy of the judging code and the Makefile in a temporary directory (the copy has no manifest, whatever the state of the real tree)."""
    shutil.copytree(os.path.join(PKG, "judging"), os.path.join(str(dst), "judging"), ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"))
    shutil.copy(os.path.join(PKG, "Makefile"), str(dst))
    return str(dst)


def _cli(root, *args):
    """python -m nl2fret_judge ... in a fresh interpreter whose code comes from the copy (cwd = judging/ of the copy, as in the Makefile)."""
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run([sys.executable, "-m", "nl2fret_judge", *args], cwd=os.path.join(root, "judging"), env=env, capture_output=True, text=True, timeout=300)


def _judge_args(p, out, *extra):
    return ["judge", "--engine", "z3", "--out", str(out), "--units", p["units"], "--ltl", p["ltl"], "--reference", p["ref"], *extra]


def _header(out):
    return json.load(open(os.path.join(str(out), "run_header.json"), encoding="utf-8"))


def _sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def _append_comment(root, rel):
    with open(os.path.join(root, *rel.split("/")), "a", encoding="utf-8") as f:
        f.write("# changed by a test\n")


# (a) header ----------------------------------------------------------------------------------------------------------------------------------------
EXPECTED_TEMPLATES = {"equiv": "G ((RS) <-> (GS))", "sound": "G ((RS) -> (GS))", "compl": "G ((GS) -> (RS))", "sat": "G (! (GS))", "valid": "G (GS)"}


def _independent_code_list():
    out = []
    for d in ("judging/nl2fret_judge", "judging/legacy"):
        for n in sorted(os.listdir(os.path.join(PKG, *d.split("/")))):
            if n.endswith(".py"):
                out.append((f"{d}/{n}", _sha(os.path.join(PKG, d, n))))
    return sorted(out)


N_CODE = len(_independent_code_list())


def test_header_has_provenance_fields(tmp_path):
    p = _write_inputs(tmp_path)
    assert cli.main(_judge_args(p, tmp_path / "run")) == 0
    h = _header(tmp_path / "run")
    assert h["version"] == "1.2.0"
    assert h["python_version"] == platform.python_version() == h["python"]
    assert h["z3_version"] == importlib.metadata.version("z3-solver")
    want = _independent_code_list()
    assert [(e["file"], e["sha256"]) for e in h["code_sha256"]] == want                       # every code file, ascending path order, content hashes
    assert all(set(e) == {"file", "sha256"} for e in h["code_sha256"])
    assert any(e["file"] == "judging/legacy/judge4.py" for e in h["code_sha256"]) and any(e["file"] == "judging/nl2fret_judge/freeze.py" for e in h["code_sha256"])
    assert h["code_tree_sha256"] == hashlib.sha256("".join(f"{s}  {f}\n" for f, s in want).encode()).hexdigest()
    assert h["smv_template_id"] == "single_ltlspec_v1"
    assert h["query_templates"] == EXPECTED_TEMPLATES
    # the frozen fields describe the real tree: no manifest before the release, a matching one after it (a mismatching one would have refused the run)
    released = os.path.exists(os.path.join(PKG, MANIFEST))
    assert h["frozen_check"] == ("match" if released else "absent") and h["frozen"] is released and h["allow_unfrozen"] is False
    assert h["frozen_manifest_sha256"] == (_sha(os.path.join(PKG, MANIFEST)) if released else None)
    assert "frozen_diff" not in h


def test_smv_template_id_pins_the_file_structure_and_query_templates():
    assert engines.SMV_TEMPLATE_ID == "single_ltlspec_v1"
    assert engines.smv_file_text("SPEC_X", ["b", "a"]) == "MODULE main\nVAR\n  a : boolean;\n  b : boolean;\nLTLSPEC SPEC_X\n"
    assert engines.smv_file_text("SPEC_X", []) == "MODULE main\nVAR\n  dummy_ap : boolean;\nLTLSPEC SPEC_X\n"
    assert {k: engines.spec_text(k, "GS", "RS") for k in engines.KINDS + engines.AUX} == EXPECTED_TEMPLATES


# docs/DESIGN.md section 7 lists the record and header fields; it must name exactly the keys that the code writes (v1.1.0 listed header fields that did not exist)
def _section7_rows():
    text = open(os.path.join(PKG, "docs", "DESIGN.md"), encoding="utf-8").read()
    sec = text[text.index("## 7. "):text.index("## 8. ")]
    rows = []
    for line in sec.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("|") else []
        if len(cells) == 2 and not set(cells[0]) <= set("-"):
            rows.append(cells)
    return sec, rows


def _names(cell, inside=False):
    """Backticked identifiers of a table cell, outside (default) or inside its parentheses."""
    if inside:
        return set(re.findall(r"`([A-Za-z_0-9]+)`", " ".join(re.findall(r"\(([^)]*)\)", cell))))
    return set(re.findall(r"`([A-Za-z_0-9]+)`", re.sub(r"\([^)]*\)", "", cell)))


def test_design_section7_names_exactly_the_keys_the_code_writes(tmp_path):
    p = _write_inputs(tmp_path)
    assert cli.main(_judge_args(p, tmp_path / "run")) == 0
    h = _header(tmp_path / "run")
    r = json.loads(open(tmp_path / "run" / "judge_records.jsonl", encoding="utf-8").readline())
    code = {"header": set(h) | {"frozen_diff"}, "record": set(r), "query": set(r["queries"][0]), "alignment": set(r["alignment"]), "ap_check": set(r["ap_check"])}
    sec, rows = _section7_rows()
    # every key of the code is named in the section
    for group, keys in code.items():
        assert not [k for k in keys if f"`{k}`" not in sec], (group, [k for k in keys if f"`{k}`" not in sec])
    # and the section names nothing that the code does not write
    header_rows = rows[rows.index(["헤더 필드", "내용"]) + 1:]
    record_rows = rows[rows.index(["구분", "필드"]) + 1:rows.index(["헤더 필드", "내용"])]
    doc_header = set().union(*[_names(c[0]) for c in header_rows])
    assert doc_header == code["header"], sorted(doc_header ^ code["header"])
    for label, cell in record_rows:
        want = code["query"] if label.startswith("질의") else code["record"]
        assert _names(cell) <= want, (label, sorted(_names(cell) - want))
    cells = {label: cell for label, cell in record_rows}
    assert _names(cells["정렬과 선택"], inside=True) == code["alignment"] and _names(cells["AP 규칙"], inside=True) == code["ap_check"]


# (b) freeze device ---------------------------------------------------------------------------------------------------------------------------------
def test_manifest_format_and_roundtrip(tmp_path):
    root = _copy_pkg(tmp_path / "pkg")
    path, entries, sha = freeze.write_manifest(root)
    text = open(path, encoding="utf-8", newline="").read()
    lines = text.split("\n")
    assert lines[-1] == "" and len(lines) - 1 == len(entries) == N_CODE == 18
    assert [l.split("  ", 1)[1] for l in lines[:-1]] == sorted(l.split("  ", 1)[1] for l in lines[:-1])      # ascending paths
    for l in lines[:-1]:                                                                                       # sha256sum -c format, content really hashed
        h, rel = l.split("  ", 1)
        assert len(h) == 64 and h == _sha(os.path.join(root, *rel.split("/")))
    assert sha == _sha(path) == freeze.tree_sha256(entries) == freeze.provenance(root)["code_tree_sha256"]
    assert freeze.check_manifest(root) == {"status": "match", "manifest": path, "manifest_sha256": sha, "diff": None}


def test_manifest_is_never_overwritten(tmp_path):
    root = _copy_pkg(tmp_path / "pkg")
    path, _, _ = freeze.write_manifest(root)
    before = open(path, "rb").read()
    _append_comment(root, "judging/nl2fret_judge/judge.py")
    with pytest.raises(FileExistsError):
        freeze.write_manifest(root)
    assert open(path, "rb").read() == before


def test_check_reports_modified_missing_and_extra_files(tmp_path):
    root = _copy_pkg(tmp_path / "pkg")
    freeze.write_manifest(root)
    _append_comment(root, "judging/legacy/judge2.py")
    os.remove(os.path.join(root, "judging", "nl2fret_judge", "units.py"))
    with open(os.path.join(root, "judging", "nl2fret_judge", "added.py"), "w") as f:
        f.write("X = 1\n")
    chk = freeze.check_manifest(root)
    assert chk["status"] == "mismatch"
    assert chk["diff"] == {"modified": ["judging/legacy/judge2.py"], "missing": ["judging/nl2fret_judge/units.py"], "extra": ["judging/nl2fret_judge/added.py"]}
    assert "modified: judging/legacy/judge2.py" in freeze.describe(chk) and "extra: judging/nl2fret_judge/added.py" in freeze.describe(chk)
    # files that are not code files do not matter: a note and a cache directory next to the code
    root2 = _copy_pkg(tmp_path / "pkg2")
    freeze.write_manifest(root2)
    open(os.path.join(root2, "judging", "nl2fret_judge", "notes.txt"), "w").write("x")
    os.makedirs(os.path.join(root2, "judging", "nl2fret_judge", "__pycache__"))
    assert freeze.check_manifest(root2)["status"] == "match"


@pytest.mark.parametrize("content", ["", "not a manifest line\n", "0" * 64 + " judging/legacy/judge2.py\n",                 # empty, free text, one space
                                     ("0" * 64 + "  judging/legacy/judge2.py\n") * 2])                                       # a path listed twice
def test_check_reports_an_unreadable_manifest_as_invalid(tmp_path, content):
    root = _copy_pkg(tmp_path / "pkg")
    with open(os.path.join(root, MANIFEST), "w", encoding="utf-8") as f:
        f.write(content)
    chk = freeze.check_manifest(root)
    assert chk["status"] == "invalid" and "error" in chk["diff"]


def test_judge_runs_with_a_matching_manifest(tmp_path):
    root, p = _copy_pkg(tmp_path / "pkg"), _write_inputs(tmp_path)
    r = _cli(root, "release")
    assert r.returncode == 0 and r.stdout.startswith(f"released: {N_CODE} code files")
    r = _cli(root, *_judge_args(p, tmp_path / "run"))
    assert r.returncode == 0, r.stderr
    h, msha = _header(tmp_path / "run"), _sha(os.path.join(root, MANIFEST))
    assert h["frozen"] is True and h["frozen_check"] == "match" and h["allow_unfrozen"] is False and "frozen_diff" not in h
    assert h["frozen_manifest_sha256"] == msha == h["code_tree_sha256"]
    assert len([l for l in open(tmp_path / "run" / "judge_records.jsonl")]) == 1


def test_judge_refuses_changed_code_and_creates_nothing(tmp_path):
    root, p = _copy_pkg(tmp_path / "pkg"), _write_inputs(tmp_path)
    assert _cli(root, "release").returncode == 0
    _append_comment(root, "judging/nl2fret_judge/engines.py")
    r = _cli(root, *_judge_args(p, tmp_path / "run"))
    assert r.returncode == 2 and r.stdout == ""
    assert "refused" in r.stderr and "judging/nl2fret_judge/engines.py" in r.stderr and "--allow-unfrozen" in r.stderr
    assert not (tmp_path / "run").exists()                                                  # nothing was created, not even the record directory


def test_allow_unfrozen_runs_and_records_the_header(tmp_path):
    root, p = _copy_pkg(tmp_path / "pkg"), _write_inputs(tmp_path)
    assert _cli(root, "release").returncode == 0
    msha = _sha(os.path.join(root, MANIFEST))
    _append_comment(root, "judging/nl2fret_judge/engines.py")
    r = _cli(root, *_judge_args(p, tmp_path / "run", "--allow-unfrozen"))
    assert r.returncode == 0, r.stderr
    assert "warning" in r.stderr and "judging/nl2fret_judge/engines.py" in r.stderr
    h = _header(tmp_path / "run")
    assert h["frozen"] is False and h["frozen_check"] == "mismatch" and h["allow_unfrozen"] is True
    assert h["frozen_diff"] == {"modified": ["judging/nl2fret_judge/engines.py"], "missing": [], "extra": []}
    assert h["frozen_manifest_sha256"] == msha and h["code_tree_sha256"] != msha              # the header still shows which code actually ran
    assert len([l for l in open(tmp_path / "run" / "judge_records.jsonl")]) == 1


def test_allow_unfrozen_with_matching_code_still_records_frozen_false(tmp_path):
    root, p = _copy_pkg(tmp_path / "pkg"), _write_inputs(tmp_path)
    assert _cli(root, "release").returncode == 0
    assert _cli(root, *_judge_args(p, tmp_path / "run", "--allow-unfrozen")).returncode == 0
    h = _header(tmp_path / "run")
    assert h["frozen"] is False and h["frozen_check"] == "match" and h["allow_unfrozen"] is True and "frozen_diff" not in h


def test_judge_without_manifest_runs_unfrozen(tmp_path):
    root, p = _copy_pkg(tmp_path / "pkg"), _write_inputs(tmp_path)
    r = _cli(root, *_judge_args(p, tmp_path / "run"))
    assert r.returncode == 0, r.stderr
    h = _header(tmp_path / "run")
    assert h["frozen"] is False and h["frozen_check"] == "absent" and h["frozen_manifest_sha256"] is None and h["allow_unfrozen"] is False


def test_judge_refuses_an_unreadable_manifest(tmp_path):
    root, p = _copy_pkg(tmp_path / "pkg"), _write_inputs(tmp_path)
    open(os.path.join(root, MANIFEST), "w").write("garbage\n")
    r = _cli(root, *_judge_args(p, tmp_path / "run"))
    assert r.returncode == 2 and "refused" in r.stderr and "not readable" in r.stderr and not (tmp_path / "run").exists()
    r = _cli(root, *_judge_args(p, tmp_path / "run2", "--allow-unfrozen"))
    assert r.returncode == 0 and _header(tmp_path / "run2")["frozen_check"] == "invalid"


def test_release_twice_is_refused_and_keeps_the_manifest(tmp_path):
    root = _copy_pkg(tmp_path / "pkg")
    assert _cli(root, "release").returncode == 0
    before = open(os.path.join(root, MANIFEST), "rb").read()
    _append_comment(root, "judging/legacy/judge5.py")
    r = _cli(root, "release")
    assert r.returncode == 2 and "refused" in r.stderr and "already exists" in r.stderr
    assert open(os.path.join(root, MANIFEST), "rb").read() == before


@pytest.mark.skipif(shutil.which("make") is None, reason="make is not installed")
def test_make_release_and_judge_args(tmp_path):
    root = _copy_pkg(tmp_path / "pkg")

    def make(*args):
        return subprocess.run(["make", *args], cwd=root, capture_output=True, text=True, timeout=300)

    r = make("release", f"PY={sys.executable}")
    assert r.returncode == 0 and f"released: {N_CODE} code files" in r.stdout, r.stderr
    assert os.path.exists(os.path.join(root, MANIFEST))
    r = make("release", f"PY={sys.executable}")
    assert r.returncode != 0 and "already exists" in r.stderr
    # --allow-unfrozen (and the other judge options) can be passed through make; without JUDGE_ARGS the command line is the one of v1.1.0
    r = make("-n", "judge", "OUT=runs/x", "JUDGE_ARGS=--allow-unfrozen")
    assert r.returncode == 0 and r.stdout.strip().endswith("--allow-unfrozen")
    r = make("-n", "judge", "OUT=runs/x")
    assert r.returncode == 0 and r.stdout.strip().endswith("--rlz ../inputs/fret_realizability_gen.jsonl")


def test_released_code_matches_the_manifest():
    """In a released package (the manifest exists) this fails as soon as a code file differs; before the release there is nothing to compare."""
    if not os.path.exists(os.path.join(PKG, MANIFEST)):
        pytest.skip("no manifest: the package is not released")
    chk = freeze.check_manifest()
    assert chk["status"] == "match", freeze.describe(chk)


# (c) selection rank ----------------------------------------------------------------------------------------------------------------------------------
def test_rank_table_is_explicit():
    assert RANK == {"SAME": 0, "PROOF": 1, "REFUTE": 1, "NEITHER": 2, "N/M": 3, "UND": 4}


@pytest.mark.parametrize("role,nm,expected", [("SAME", False, 0), ("PROOF", False, 1), ("REFUTE", False, 1), ("NEITHER", False, 2), (None, True, 3), ("UND", False, 4)])
def test_rank_of_equals_the_v1_1_formula_for_every_reachable_state(role, nm, expected):
    v11 = {"SAME": 0, "PROOF": 1, "REFUTE": 1, "NEITHER": 2}                                # RANK of v1.1.0, applied as RANK.get(role, 3 if role is None else 4)
    assert v11.get(role, 3 if role is None else 4) == expected == rank_of({"role": role, "nm": nm})


def _best(gen, *refs):
    parts = [(f"P{i}#0", r, None) for i, r in enumerate(refs)]
    rec = best_over_references(gen, parts, Z3Engine(8), pair_id="t", meta={}, cap=10)
    return rec["reference_part"], [("N/M" if t["nm"] else t["role"]) for t in rec["reference_trials"]]


# generated (x & y): UND = x and y have a single same-type counterpart (no injective renaming), N/M = window 100 above cap 10, NEITHER = same names, both directions fail
G1, G1_UND, G1_NM, G1_NEITHER = "(H (x & y))", "(H (a & (b > 5)))", "(H[<=100] (x & y))", "(H (! (x & y)))"
# generated (a -> b): the same three kinds, plus REFUTE (rank 1) as a judged role that must win against N/M and UND
G2, G2_UND, G2_NM, G2_REFUTE = "(H (a -> b))", "(H (c & (d > 5)))", "(H[<=100] (a -> b))", "(H (a & b))"


def test_selection_over_reference_parts_prefers_neither_then_nm_then_und():
    assert _best(G1, G1_UND, G1_NM, G1_NEITHER) == ("P2#0", ["UND", "N/M", "NEITHER"])    # NEITHER wins against N/M and UND although it comes last
    assert _best(G1, G1_NEITHER, G1_NM, G1_UND) == ("P0#0", ["NEITHER", "N/M", "UND"])
    assert _best(G1, G1_UND, G1_NEITHER) == ("P1#0", ["UND", "NEITHER"])
    assert _best(G1, G1_NM, G1_NEITHER) == ("P1#0", ["N/M", "NEITHER"])
    assert _best(G1, G1_UND, G1_NM) == ("P1#0", ["UND", "N/M"])                            # N/M wins against UND although UND comes first
    assert _best(G1, G1_NM, G1_UND) == ("P0#0", ["N/M", "UND"])
    assert _best(G2, G2_UND, G2_NM, G2_REFUTE) == ("P2#0", ["UND", "N/M", "REFUTE"])        # a judged role beats both
