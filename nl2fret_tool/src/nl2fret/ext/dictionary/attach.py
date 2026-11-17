"""Extension `dictionary`, attach side: the signal dictionary that the FRETish stage gets as an additional block (docs/V20_BATCH_DESIGN.md 0.1 and 8).
Wraps `common.sigdict_block` (the user prompt block) and the `prompts3.DICT_ALL` switch (the dictionary rules in the system prompts of the FRETish stage).

prompt_block(challenge)  -> the dictionary table text of the challenge (the text that `common.user_prompt_B/D` and `prompts3.user_prompt_S` pass to `sigdict_block`), or None when the challenge has no entry
rendered(challenge)      -> the complete block as it appears in the user message (`common.sigdict_block(prompt_block(challenge))`)
missing(items)           -> ids of the items whose challenge has no dictionary entry
switch_on(P)             -> sets P.DICT_ALL (the module `prompts3`) so that the system prompts carry the dictionary rules
The table text is the file data/sigdict.json of the package (built from data/dictionary/lm_dictionary.csv by tools/build_inputs.py, checked by build.py verify)."""
import json
from pathlib import Path

from nl2fret.paths import PACKAGE  # noqa: E402

SIGDICT = PACKAGE / "data" / "sigdict.json"
_cache = {}


def table():
    if "t" not in _cache:
        _cache["t"] = json.loads(SIGDICT.read_text(encoding="utf-8"))
    return _cache["t"]


def prompt_block(challenge):
    return table().get(str(challenge).split("_")[0]) or None


def rendered(challenge):
    from nl2fret import common
    return common.sigdict_block(prompt_block(challenge))


def missing(items):
    return sorted({it["id"] for it in items if not prompt_block(it["challenge"])})


def switch_on(P):
    P.DICT_ALL = True
