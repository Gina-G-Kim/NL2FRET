"""v2.0 measurement rule of docs/V20_BATCH_DESIGN.md section 7: N-LIT (integer literals of the realizability input). The J+def tests were moved to archive/removed_features/ on 2026-11-17."""
import json, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.join(HERE, "..", "src", "nl2fret")
from nl2fret.fret_check.tools import litnorm as L


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


def test_run_batch_script_syntax_and_no_judgedef_step():
    p = os.path.join(HERE, "..", "scripts", "run_batch.sh")
    assert subprocess.run(["bash", "-n", p]).returncode == 0
    s = open(p).read()
    assert "judgedef" not in s and "make_def_inputs" not in s and "rt_effect_strict" not in s
