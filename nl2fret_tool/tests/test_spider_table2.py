"""SPIDER Table 2 (Autili et al., TSE 2015) forms are parsed and assembled; forms without a FRETish counterpart are recorded as no mapping."""
import os, sys
from nl2fret import tpl_rules as T


def build(sentence, vals=None):
    T.SLOT_KW = True
    try:
        p = T.parse_spider(sentence)
        assert p["ok"], p
        rq = T.slot_requests(p, r2=True)
        raw = {k: (vals or {}).get(k, k + "_x") for k in rq}
        return T.assemble(p, T.lint_slots(rq, raw), r2=True)["fretish"]
    finally:
        T.SLOT_KW = False


def test_table2_forms_assemble():
    assert build("Globally, it is always the case that {the valve is open} holds.") == "system shall always satisfy p_x"
    assert build("Globally, if {a} has occurred then in response {b} eventually holds within 5 seconds.", {"ck": "whenever"}).startswith("whenever p_x system shall within 5 seconds satisfy s_x")
    assert build("Globally, {the fan is off} holds after 3 seconds.") == "system shall after 3 seconds satisfy p_x"
    assert build("Globally, if {a} has occurred then in response {b} holds continually.", {"ck": "when", "tm": "always"}) == "when p_x system shall always satisfy s_x"
    assert build("Globally, {x} holds eventually with a probability greater than 0.9.") == "system shall with probability > 0.9 eventually satisfy p_x"


def test_table2_forms_without_fretish_counterpart_are_recorded():
    for s, what in [("Globally, {x} holds repeatedly every 3 seconds.", "periodic recurrence"),
                    ("Globally, if {a} has occurred then in response {b} eventually holds followed by {c} within 2 seconds.", "chain"),
                    ("Globally, {x} holds in the long run.", "steady state")]:
        p = T.parse_spider(s)
        assert p["ok"] and what in p["nomap"], (s, p.get("nomap"))


def test_last_json_object_of_a_reply_is_the_answer():
    from nl2fret import common as C
    assert C.extract_json('{"a":1}\n\nWait, correction.\n\n{"sentences":["x"]}') == {"sentences": ["x"]}
    assert C.extract_json('{"a":1}') == {"a": 1} and C.extract_json("no json here") is None
