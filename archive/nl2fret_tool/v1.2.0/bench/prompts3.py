"""Prompts and parsers of the v3 bench: arms, stage A with surface rules, slot filling for the rule arms, feedback prompts for all arms.

Arms (11):
  DIRECT        raw NL -> FRETish (model)                                          [as v2]
  <TPL>         raw NL -> template (model) -> FRETish (model, free)                [as v2, stage A has two surface rules more]
  PARA          raw NL -> plain English rewrite (model, no template) -> FRETish (model, free)    [control: same two steps, no template structure]
  <TPL>+R       raw NL -> template (model, the SAME stage A row as <TPL>) -> parse by script -> phrases to expressions (model, slots only)
                -> FRETish assembled by script (tpl_rules.assemble)
Feedback (variant F): after the first answer ALL arms get the same kind of message from the OFFICIAL parser (rejected sentence, parser text, hint), at most
MAX_ROUNDS times. Realizability, the reference FRETish and any score are never fed back.
"""
import json
import re

import tpl_rules as T
from common import RULES_COMMON, TEMPLATES, build_system, extract_json, user_prompt_A, user_prompt_B, user_prompt_D  # noqa: F401
import fretlint as L

TPLS = list(TEMPLATES)   # v7 dev: all five templates, Boilerplate included
ARM_D = "DIRECT"
RULE_SUFFIX = "+R"
GUIDE_SUFFIX = "+G"
U_SUFFIX = "+U"
V_SUFFIX = "+V"
D_SUFFIX = "+D"         # v8: signal dictionary given at the FRETish stage (D for DIRECT, B for template arms); stage A is shared with the base arm
V6_SUFFIX = "+V6"       # v7: +V plus principle V-6 (state versus event condition)
R2_SUFFIX = "+R2"       # v7: rule arm without R-DEFTIME; the timing is a slot answered by the model under V-1..V-4
ARM_P = "PARA"        # control arm: raw NL -> plain English rewrite (no template) -> FRETish (free)
ARMS_MAIN = [ARM_D] + TPLS + [t + RULE_SUFFIX for t in TPLS]
ARMS_G = [t + GUIDE_SUFFIX for t in ("MASTeR", "EARS", "Adv-EARS")]
ARMS_U = [t + U_SUFFIX for t in TPLS]
ARMS_U2 = [t + U_SUFFIX for t in ("MASTeR", "EARS")]
ARMS_V5 = [ARM_D, ARM_P] + TPLS + [t + RULE_SUFFIX for t in TPLS] + ARMS_U2    # the 12 arms of the v5 main run
ARMS_V = [ARM_D + V_SUFFIX] + [t + V_SUFFIX for t in TPLS]                      # all +V arms (principled timing inference, the same principles for every arm)
ARMS_V6 = [ARM_D, ARM_P] + TPLS + [t + RULE_SUFFIX for t in TPLS] + [ARM_D + V_SUFFIX, "MASTeR" + V_SUFFIX, "EARS" + V_SUFFIX]    # the 13 arms of the v6 main run
ARMS_R2 = [t + R2_SUFFIX for t in TPLS]
ARMS_VV6 = [ARM_D + V6_SUFFIX] + [t + V6_SUFFIX for t in TPLS]
ARMS_DEV1 = ARMS_R2 + [ARM_D + V_SUFFIX, "MASTeR" + V_SUFFIX, "EARS" + V_SUFFIX, "Boilerplate" + V_SUFFIX] + [ARM_D + V6_SUFFIX, "MASTeR" + V6_SUFFIX, "EARS" + V6_SUFFIX, "Boilerplate" + V6_SUFFIX]
ARMS_D8 = [ARM_D, ARM_D + D_SUFFIX, "MASTeR", "MASTeR" + D_SUFFIX, "EARS", "EARS" + D_SUFFIX]    # v8 dictionary smoke: three paired arms
ARMS3 = list(dict.fromkeys(ARMS_D8 + ARMS_MAIN + [ARM_P] + ARMS_G + ARMS_U + ARMS_V + ARMS_R2 + ARMS_VV6 + ["Boilerplate" + V_SUFFIX]))
MAX_ROUNDS = 2


def base_of(arm):
    for sfx in (D_SUFFIX, R2_SUFFIX, V6_SUFFIX, RULE_SUFFIX, GUIDE_SUFFIX, U_SUFFIX, V_SUFFIX):
        if arm.endswith(sfx):
            return arm[:-len(sfx)]
    return arm


def is_dict(arm):
    return arm.endswith(D_SUFFIX)


def is_rule(arm):
    return arm.endswith(RULE_SUFFIX) or arm.endswith(R2_SUFFIX)


def is_r2(arm):
    return arm.endswith(R2_SUFFIX)


def is_guide(arm):
    return arm.endswith(GUIDE_SUFFIX)


def is_unspec(arm):
    return arm.endswith(U_SUFFIX)


def is_infer(arm):
    return arm.endswith(V_SUFFIX) or arm.endswith(V6_SUFFIX)


def is_v6(arm):
    return arm.endswith(V6_SUFFIX)


def is_direct(arm):
    """DIRECT and DIRECT+V: raw NL -> FRETish in one stage (stage D)."""
    return base_of(arm) == ARM_D


def dkey(arm):
    """key of the stage D system prompt: None for plain DIRECT (file name system_prompt_D_none.txt), the arm name for DIRECT+V."""
    return None if arm == ARM_D else arm


def akey(arm):
    """key of the stage A row: +U arms have their own stage A (different system prompt); every other arm (also +V) shares the stage A row of its template."""
    return arm if is_unspec(arm) else base_of(arm)


U_RULES_A = """NO-COMPLETION RULES (test bench rules of this arm; they are not part of the template source)
U-1: Use only information that is stated in the input. Do not add a condition, a mode, a trigger, a time bound, a number, a threshold or a name that the input does not state, and do not drop one that it states.
U-2: When the template requires a decision that the input does not settle (for example which keyword fits, or what the response phrase is), make the decision that adds the least information and list the decision in "choices". Do not present an assumption as stated information."""

U_RULES_B = """NO-COMPLETION RULES (test bench rules of this arm; they are not part of the FRETish source)
U-1: Use only information that is stated in the template sentence. Do not add a condition, a mode, a trigger, a time bound, a number, a threshold or a variable that the sentence does not state, and do not drop one that it states.
U-2: When FRETish requires a decision that the sentence does not settle (for example whether a condition is a trigger or a state, which timing word to use, or what an identifier should be), make the decision that adds the least information and list the decision in "choices". Do not present an assumption as stated information.
U-3: Source fact for timing (Adam et al. 2023, FRETish description): FRET reads a requirement with the timing left out as 'eventually'. Leaving the timing out is therefore also a decision. Decide on purpose and list it in "choices"."""


V_COMMON = """TIMING INFERENCE PRINCIPLES (test bench principles of this arm; they are not part of the {src} source)
V-1: Fact (Adam et al. 2023, FRETish description): FRET reads a requirement whose timing is left out as 'eventually', which only asks that the response holds at some time point. Leaving the timing out is therefore a decision with a meaning.
V-2: Decide the timing from the content of the {inp} only, in this order.
  (a) A time word that the {inp} states (within, for, after, until, before, never, immediately, always, eventually) is kept.
  (b) If there is no trigger and no state clause, and the response states a relation, a bound or a limit on quantities or states (a comparison, a range, 'remain', 'not exceed', 'be bounded', 'equal'), it describes something that must hold whenever the system runs: use 'always'. 'eventually' would accept a system that violates the bound at all but one time point.
  (c) If a condition starts an action or a change (an event, or a response that is an action or a state change), decide between 'immediately' and 'eventually' by asking whether the {inp} would still forbid the violation it describes when the response happens only at some later time point. If a late response would be a violation, use 'immediately' (or the stated time bound); otherwise use 'eventually'.
V-3: Violation check before you answer: write in one line the situation that the {inp} forbids, and check that your FRETish rejects exactly that situation. A timing that would accept the forbidden situation is wrong; choose the stronger timing.
V-4: V-2 and V-3 settle the timing only. Do not add a condition, scope, number or name that the {inp} does not state, and do not drop one that it states.
V-5: The OUTPUT SCHEMA of this task contains one more field, "timing_basis", as its LAST field inside the same single JSON object (do not close the object before it, and write the key without a leading space). Always give a rule, also when the timing is stated: "rule" is one of stated, V-2b, V-2c; "words" are the words of the {inp} that triggered the rule (at most 10 words); "forbidden_situation" is the one line of V-3 (at most 25 words)."""

V6_ADD = """
V-6: Fact (Adam et al. 2023, FRETish description, and the RE 2020 FRET paper as listed in the FRETish guide): a condition (when, upon, if) is a trigger. It fires at the time points where its expression becomes true from false, and the response is required from that point on. A scope (in <mode>, or while <expression>) applies at every time point where the mode or the expression is true.
  Decide from the content of the {inp}, not from the keyword it uses, which one it states.
  (a) A situation that persists while the requirement applies (a mode, an operating state, 'while', 'as long as', 'during', 'in <mode>', 'when the system is in ...', 'when <state variable> is true' meaning a continuing state) is a scope: use 'in <mode>' for one named mode, otherwise 'while <expression>'.
  (b) Something that happens at a moment (receives, detects, is pressed, becomes, has occurred, is started) is a condition: use 'when'.
  (c) If the {inp} states both a persisting situation and a moment, write both.
  (d) 'when', 'if' and 'while' in the {inp} are hints. 'when the vehicle is in standby' states a state."""


D_RULES = """SIGNAL DICTIONARY RULES (test bench rules of this arm; they are not part of the {src} source)
D-1: The user message ends with a SIGNAL DICTIONARY copied from the requirement document of this requirement. It is a table of signal names with type and description. It is not a statement of what the requirement says: use only the entries that the {inp} needs, and do not add a condition, scope, number or response because an entry exists.
D-2: When a phrase of the {inp} denotes a signal of the dictionary, write the dictionary name exactly (spelling and case) as the FRETish identifier. Do not rename, abbreviate or rebuild it.
D-3: When a phrase has no signal in the dictionary (for example a constant, a state value or a mode name), build the identifier as before (lower snake_case words of the phrase).
D-4: Keep the type of the dictionary entry: a Boolean name is used as a Boolean expression, a numeric name in a comparison or in arithmetic."""


TB_OLD = '"unmapped_content": ["<content of the input that FRETish cannot carry>"]}'
TB_NEW = '"unmapped_content": ["<content of the input that FRETish cannot carry>"],\n "timing_basis": {"rule": "stated | V-2b | V-2c", "words": "<words of the input>", "forbidden_situation": "<one line>"}}'


def with_tb_schema(s):
    assert s.count(TB_OLD) == 1, s.count(TB_OLD)
    return s.replace(TB_OLD, TB_NEW)


V_RULES_B = V_COMMON.format(src="FRETish", inp="template sentence")
V_RULES_D = V_COMMON.format(src="FRETish", inp="natural language requirement")
V6_RULES_B = V_RULES_B.rstrip() + "\n" + V6_ADD.format(inp="template sentence")
V6_RULES_D = V_RULES_D.rstrip() + "\n" + V6_ADD.format(inp="natural language requirement")


GUIDE_HEAD = """MECHANICAL MAPPING RULES (test bench). The same rules a script applies in the rule arm of this bench. Follow them when you write the FRETish; they decide the
mapping from template parts to FRETish fields. Where a rule says nothing, decide yourself as before.
Assembly order of one FRETish requirement: [scope] [condition] component shall [timing] satisfy response.
Component: the subject phrase of the template sentence without article, as one snake_case identifier (the flight control system -> flight_control_system).
Response: the verb phrase as an expression; state and event phrases become ONE snake_case identifier made of the words in their original order; a quantity compared with a value becomes a comparison.
Expression syntax accepted by the official parser: identifiers (letters digits underscore), numbers without units or % signs, ! & | => <=> = != < <= > >= + - * / ( ), absReal(x) for the absolute value.
Not accepted: units inside expressions, abs max min previous, a variable named mode, the words and or not is as operators, Unicode symbols, spaces or hyphens in names.
Time units after within / for / after: ticks, milliseconds, seconds, minutes, hours (not ms, s, sec). The word every is not accepted.
Rules for this template:"""


def guide_rules_text(base):
    lines = [GUIDE_HEAD]
    for rid, (tpl, desc, status, ev) in T.RULES.items():
        if tpl in (base, "*") and not rid.startswith("L-"):
            lines.append(f"- {rid}: " + re.sub(r",? failure code recorded", "", re.sub(r"\s*\((?:mechanical, no model|script)\)", "", desc)))
    return "\n".join(lines) + "\n"


def build_system_B3(arm):
    """FRETish stage of the free arms. +G adds the rule text above to the same system prompt."""
    s, st = build_system("B", base_of(arm))
    if is_guide(arm):
        s = s.rstrip() + "\n\n" + guide_rules_text(base_of(arm))
        st = dict(st, rules="bench_rules")
    if is_unspec(arm):
        s = s.rstrip() + "\n\n" + U_RULES_B + "\n"
        st = dict(st, rules="no_completion")
    if is_infer(arm):
        s = with_tb_schema(s).rstrip() + "\n\n" + (V6_RULES_B if is_v6(arm) else V_RULES_B) + "\n"
        st = dict(st, rules="timing_state_inference" if is_v6(arm) else "timing_inference")
    if is_dict(arm):
        s = s.rstrip() + "\n\n" + D_RULES.format(src="FRETish", inp="template sentence") + "\n"
        st = dict(st, rules="signal_dictionary")
    return s, st


def build_system_D3(arm):
    """FRETish stage of DIRECT and DIRECT+V (raw NL -> FRETish)."""
    s, st = build_system("D")
    if is_infer(arm):
        s = with_tb_schema(s).rstrip() + "\n\n" + (V6_RULES_D if is_v6(arm) else V_RULES_D) + "\n"
        st = dict(st, rules="timing_state_inference" if is_v6(arm) else "timing_inference")
    if is_dict(arm):
        s = s.rstrip() + "\n\n" + D_RULES.format(src="FRETish", inp="natural language requirement") + "\n"
        st = dict(st, rules="signal_dictionary")
    return s, st


SURFACE_RULE = """SURFACE RULES (test bench, apply to every template, not part of the template source)
SA-1: put a comma between the last condition clause and the subject of the sentence (for example "WHEN the door is opened, the alarm shall sound").
SA-2: write each time phrase (within N units, for N units, after N units, until ..., before ...) once, directly after the verb phrase it belongs to; do not repeat it elsewhere."""


def build_system_A3(key):
    """key = template name, or template name + '+U' for the no-completion arm."""
    if base_of(key) == ARM_P:                       # control arm: no template, so no template surface rules either
        return build_system("A", ARM_P)
    s, st = build_system("A", base_of(key))
    s = s.rstrip() + "\n\n" + SURFACE_RULE + "\n"
    if is_unspec(key):
        s = s.rstrip() + "\n\n" + U_RULES_A + "\n"
        st = dict(st, rules="no_completion")
    return s, st


# ------------------------------------------------------------------ slot filling (rule arms)
SLOT_SYSTEM = """TASK: A script has split requirement sentences written in a requirement template into named phrases. Write every phrase as a Boolean or arithmetic expression in
FRETish expression syntax. You do NOT choose scope, condition keywords, timing, component or structure: the script does that and assembles the FRETish sentence itself.

EXPRESSION SYNTAX (all of it was observed to be accepted by the official FRET parser)
- identifiers: letters, digits and underscore, first character a letter or underscore, no spaces, no hyphens
- numbers: digits with an optional decimal point (write 10, not "10 V"; remove units and percent signs, keep the number)
- operators: ! & | => <=> = != < <= > >= + - * /  and parentheses; true false; absReal(x) for an absolute value
NOT accepted: units or % inside an expression, the functions abs max min previous, the word mode as an identifier, the words and or not is the of than as operators,
Unicode symbols (use <= >= != =>), a single bar |x| as magnitude, identifiers that start with a digit or contain spaces.

NAMING (test bench rule NM-1): a state or an event becomes ONE identifier made of the words of the phrase in their original order, lower snake_case, articles left out
(the start button is pressed -> start_button_pressed; open the inlet valve -> open_inlet_valve). A quantity compared with a value becomes a comparison
(the supply voltage is below 10 V -> supply_voltage < 10; at most 2 W -> power_consumption <= 2). Words in parentheses in the phrase are variable names, keep them
((not standby) -> !standby). Several conditions joined by and/or become & and |. Never invent numbers, thresholds or names that are not in the phrase.
STATE SLOTS (slot names starting with s): if the phrase names ONE operating mode or state (standby, the state maintenance, maintenance mode), answer {"mode": "<identifier>"}
(for example {"mode": "maintenance"}); otherwise answer {"expr": "<expression>"}.

OUTPUT: exactly one JSON object and nothing else:
{"items": [{"i": 1, "slots": {"c1": "<expression>", "s1": {"mode": "<identifier>"}, "r": "<expression>"}}], "unmapped_content": ["<content of a phrase that no expression can carry>"]}
Give every slot that is listed for an item. Keep the order and numbering of the items."""


R2_ADD = """
TIMING SLOT (slot name tm, only for items that list it): the template sentence states no timing word, and the script does NOT leave the timing out. Answer one word: always, immediately or eventually.
Decide with these principles (test bench principles of this arm; they are not part of the FRETish source):
V-1: Fact (Adam et al. 2023, FRETish description): FRET reads a requirement whose timing is left out as 'eventually', which only asks that the response holds at some time point. Leaving the timing out is therefore a decision with a meaning.
V-2: (b) If the item has no trigger and no state clause, and the response states a relation, a bound or a limit on quantities or states (a comparison, a range, 'remain', 'not exceed', 'be bounded', 'equal'), it describes something that must hold whenever the system runs: answer always.
     (c) If a condition starts an action or a change, decide between immediately and eventually by asking whether the requirement would still forbid the violation it describes when the response happens only at some later time point. If a late response would be a violation, answer immediately; otherwise eventually.
V-3: Check before you answer: the situation that the requirement forbids must be rejected by the timing you choose.
For items that do not list tm, give no timing."""
SLOT_SYSTEM_R2 = SLOT_SYSTEM.replace("You do NOT choose scope, condition keywords, timing, component or structure", "You do NOT choose scope, condition keywords, component or structure (the timing only where the item lists a tm slot)") + R2_ADD


def slot_payload(parses, reqs):
    items = []
    for i, (p, rq) in enumerate(zip(parses, reqs), 1):
        ctx = {}
        if p["template"] != "SPIDER":
            ctx["subject"] = p["subject"]
            ctx["verb_phrase_is_slot_r"] = True
        if "tm" in rq:
            ctx["has_trigger"] = any(not c["kind"].startswith("state") for c in p.get("clauses", []))
            ctx["has_state"] = any(c["kind"].startswith("state") for c in p.get("clauses", []))
        items.append({"i": i, "template": p["template"], "context": ctx, "slots": {k: v["phrase"] for k, v in rq.items()},
                      "state_slots": [k for k, v in rq.items() if v["kind"] == "state"]})
    return items


def user_prompt_S(parses, reqs):
    return "ITEMS (JSON):\n" + json.dumps(slot_payload(parses, reqs), ensure_ascii=False, indent=1) + "\n"


def parse_slot_output(text, n):
    """-> (dict i -> {slot: str|dict}, errors)"""
    o = extract_json(text)
    if o is None:
        return None, ["no_json"]
    its = o.get("items")
    if not isinstance(its, list):
        return None, ["schema_items"]
    out = {}
    for x in its:
        if isinstance(x, dict) and isinstance(x.get("slots"), dict):
            try:
                out[int(x.get("i"))] = x["slots"]
            except Exception:
                pass
    errs = [] if all(i in out for i in range(1, n + 1)) else ["schema_items_missing"]
    return {"slots": out, "unmapped_content": [str(u) for u in (o.get("unmapped_content") or []) if isinstance(u, (str, int, float))]}, errs


# ------------------------------------------------------------------ feedback
def _status_lines(statuses):
    lines = []
    for i, st in enumerate(statuses, 1):
        if st["verdict"] == "accepted":
            lines.append(f"{i}. ACCEPTED by the official FRET parser: {st['text']}")
        else:
            lines.append(f"{i}. REJECTED: {st['text']!r}\n   message: {st['message']}")
            for h in st["hints"]:
                lines.append(f"   hint: {h}")
    return "\n".join(lines)


FEEDBACK_TAIL = """
OFFICIAL FRET PARSER RESULT FOR YOUR PREVIOUS ANSWER (only syntax is judged; the meaning is not):
{status}

Return the corrected answer in exactly the same JSON schema as before, for ALL items. Keep accepted items unchanged. Change only what is needed to remove the
rejection, and do not change the meaning, names or numbers of the input. If something truly cannot be expressed, list it in "unmapped_content"."""


def user_prompt_feedback(original_user, previous_text, statuses):
    return (original_user.rstrip() + "\n\nYOUR PREVIOUS ANSWER:\n" + previous_text.strip() + "\n" + FEEDBACK_TAIL.format(status=_status_lines(statuses)))


def statuses_from_round(rnd):
    """rnd = round record of units3; -> list of status dicts for the feedback text"""
    out = []
    for s in rnd["sentences"]:
        if s.get("pre"):
            out.append({"verdict": "rejected", "text": s.get("text") or "(no sentence)", "message": s["pre"]["code"] + ": " + s["pre"]["detail"],
                        "hints": [HINT_PRE.get(s["pre"]["code"], "")] if HINT_PRE.get(s["pre"]["code"]) else []})
        elif s.get("official") and not s["official"]["ok"]:
            msg = s["official"]["error"] or ""
            out.append({"verdict": "rejected", "text": s["text"], "message": msg, "hints": [h for _, _, h in L.hints_for(msg)]})
        else:
            out.append({"verdict": "accepted", "text": s["text"], "message": "", "hints": []})
    return out


HINT_PRE = {
    "slot_lint": "A slot value breaks the expression syntax listed in the task (see the message: E-WORD = a word instead of an operator, E-UNITINEXPR = a unit after a number, "
                 "E-FUNC = a function that does not exist, E-BADCHAR = a character that is not allowed, E-MISSING = a slot was not answered). Fix the named slot only.",
}
