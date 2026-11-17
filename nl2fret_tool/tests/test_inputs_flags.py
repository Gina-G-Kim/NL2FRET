"""v1.4: tools/make_judge_inputs.py must replay a run with the flags the run was made with (read from <results>/snapshot/run_info.json).

Background: units3.derive replays every unit from the call rows; for the +R2 arms it calls tpl_rules.assemble, whose result depends on tpl_rules.SOURCED_ONLY and tpl_rules.INTENT_COND.
Only run_pipeline.main() used to set them, so `inputs` replayed a v1.4 run with the v1.3 defaults (KeyError: 'slots' for a unit that went to the free path, and +R2 sentences that the run never sent
to the FRET parser)."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

V14 = dict(dict_all=True, guide_sup=False, g_parity=True, intent_decl=True, tm_source_only=True, sourced_rules_only=True)
SPIDER_SENT = "Globally, it is always the case that if P holds, then S eventually holds."


def _flags():
    from nl2fret import prompts3 as P
    from nl2fret import tpl_rules as T
    return (P.DICT_ALL, P.GUIDE_SUP, P.G_PARITY, P.INTENT_DECL, P.TM_SOURCE_ONLY, P.SOURCED_ONLY, T.SOURCED_ONLY, T.INTENT_COND)


def _reset():
    from nl2fret import prompts3 as P
    from nl2fret import tpl_rules as T
    P.FRET_REFERENCE = P.DICT_ALL = P.GUIDE_SUP = P.G_PARITY = P.INTENT_DECL = P.TM_SOURCE_ONLY = P.SOURCED_ONLY = False
    T.SOURCED_ONLY = T.INTENT_COND = False


def _write_info(folder, **kw):
    os.makedirs(os.path.join(folder, "snapshot"), exist_ok=True)
    with open(os.path.join(folder, "snapshot", "run_info.json"), "w", encoding="utf-8") as f:
        json.dump(kw, f)


def test_run_flags_are_set_from_run_info(tmp_path):
    from nl2fret.tools import make_judge_inputs as M
    from nl2fret import tpl_rules as T
    _reset()
    try:
        _write_info(str(tmp_path), **V14)
        assert M.apply_run_flags(str(tmp_path)) == dict(V14, fret_reference=False)
        assert _flags() == (True, False, True, True, True, True, True, True)
        p = T.parse_template("SPIDER", SPIDER_SENT)
        a = T.assemble(p, {"p": {"expr": "x"}, "s": {"expr": "y"}}, r2=True)
        assert not a["ok"] and a["code"] == "rule_no_mapping" and a["detail"].startswith("no_source:")      # what the v1.4 run did
    finally:
        _reset()


def test_defaults_stay_without_run_info_or_without_the_v14_keys(tmp_path):
    from nl2fret.tools import make_judge_inputs as M
    from nl2fret import tpl_rules as T
    _reset()
    try:
        assert M.apply_run_flags(str(tmp_path)) == {}                    # no snapshot/run_info.json: nothing changes
        assert _flags() == (False,) * 8
        _write_info(str(tmp_path), model_arg="sonnet")                   # a run made before v1.4 has none of the v1.4 keys
        got = M.apply_run_flags(str(tmp_path))
        assert not any(got.values()) and _flags() == (False,) * 8
        p = T.parse_template("SPIDER", SPIDER_SENT)
        assert T.assemble(p, {"p": {"expr": "x"}, "s": {"expr": "y"}}, r2=True)["ok"]       # the v1.3 replay assembles a sentence here
    finally:
        _reset()
