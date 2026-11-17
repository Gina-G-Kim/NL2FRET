"""Extension modules of docs/V20_BATCH_DESIGN.md section 8: the extension `dictionary` on and off (prompts, user block, judge argument, run_batch.sh)."""
import csv, os, subprocess, sys, types
HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.join(HERE, "..")
BENCH = os.path.join(PKG, "src", "nl2fret")
import pytest  # noqa: E402
import nl2fret.ext as X
from nl2fret import prompts3 as P
from nl2fret import run_pipeline as RP
from nl2fret.ext.dictionary import attach, judge_input

HEADER = "name | kind | direction | type | description | definition"


def test_parse_names_alias_and_unknown():
    assert X.parse([]) == () and X.parse(None) == () and X.parse([""]) == ()
    assert X.parse(["dictionary"]) == ("dictionary",)
    assert X.parse(["dictionary", "dictionary"]) == ("dictionary",)
    assert X.parse([], dict_all=True) == ("dictionary",)      # the old flag --dict-all
    assert X.split("dictionary,x") == ["dictionary", "x"]
    with pytest.raises(SystemExit):
        X.parse(["nope"])


def test_attach_block_and_missing():
    t = attach.prompt_block("06_EB")
    assert t and t.startswith(HEADER)
    assert attach.prompt_block("99_XX") is None
    r = attach.rendered("06_EB")
    assert r.startswith("\nSIGNAL DICTIONARY") and t.strip() in r
    assert attach.missing([{"id": "a", "challenge": "06_EB"}, {"id": "b", "challenge": "99_XX"}]) == ["b"]


def _ctx(on):
    return types.SimpleNamespace(exts=("dictionary",) if on else ())


def test_sd_of_follows_the_extension_and_the_switch():
    old = P.DICT_ALL
    try:
        P.DICT_ALL = True
        it = {"id": "x", "challenge": "06_EB"}
        assert RP.sd_of(_ctx(True), it, "EARS+G") == attach.prompt_block("06_EB")
        assert RP.sd_of(_ctx(False), it, "EARS+G") is None          # extension off: no block, whatever the switch
        P.DICT_ALL = False
        assert RP.sd_of(_ctx(True), it, "EARS+G") is None
    finally:
        P.DICT_ALL = old


def test_system_prompts_carry_the_dictionary_rules_only_with_the_switch():
    old = P.DICT_ALL
    try:
        out = {}
        for on in (True, False):
            P.DICT_ALL = on
            ctx = types.SimpleNamespace(args=types.SimpleNamespace(arms=["DIRECT", "EARS+G", "EARS+R2"]))
            out[on] = {k: v[0] for k, v in RP.build_prompts(ctx).items()}
        assert {k[0] for k in out[True]} >= {"A", "B", "BF", "D"}
        for k in out[True]:
            if k[0] in ("B", "BF", "D"):
                assert "D-2:" in out[True][k] and "D-2:" not in out[False][k], k
    finally:
        P.DICT_ALL = old


def test_judge_argument_on_and_off(tmp_path):
    on = judge_input.judge_args(("dictionary",), tmp_path)
    assert on[0] == "--dictionary" and os.path.samefile(on[1], os.path.join(PKG, "data", "dictionary", "lm_dictionary.csv"))
    off = judge_input.judge_args((), tmp_path)
    rows = list(csv.reader(open(off[1], encoding="utf-8")))
    full = next(csv.reader(open(on[1], encoding="utf-8-sig")))
    assert rows == [full]                                              # same columns, no entry
    from nl2fret_judge import dict_align as DA
    assert DA.load_dictionary(off[1]) == {}
    assert DA.load_dictionary(on[1])["06_EB"]
    new, al = DA.align_formula("G (check_1_1 > 0)", set())
    assert al["aliased"] == {} and al["oov"] == ["check_1_1"]


def test_run_batch_uses_the_extension_variable():
    s = open(os.path.join(PKG, "scripts", "run_batch.sh")).read()
    assert 'EXT="${EXT-dictionary}"' in s and "--dict-all" not in s
    assert "nl2fret.ext.dictionary.judge_input" in s and '--dictionary "$DICT"' in s


def test_build_verify_passes_on_the_shipped_files():
    r = subprocess.run([sys.executable, "-B", "-m", "nl2fret.ext.dictionary.build", "verify"], capture_output=True, text=True)
    assert r.returncode == 0 and "DIFF" not in r.stdout, r.stdout
