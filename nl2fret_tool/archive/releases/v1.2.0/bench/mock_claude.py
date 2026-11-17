#!/usr/bin/env python3
"""Fake `claude` CLI for offline tests of the NL2FRET bench. It is NOT a model: the outputs are rule based and only exercise the code paths.

Usage: python3 run_pipeline.py --claude-bin ./mock_claude.py ...
Environment:
  MOCK_STATE_DIR        directory for the call counter (default: ./.mock_state)
  MOCK_LIMIT_AFTER      emit a session limit after this many calls, once per N (default: off)
  MOCK_LIMIT_SECONDS    seconds the fake limit lasts (default 6)
  MOCK_SEED             base seed (default 1)
"""
import json
import os
import random
import re
import sys
import time
from pathlib import Path


def snake(s, n=4):
    w = re.findall(r"[A-Za-z0-9]+", s.lower())
    w = [x for x in w if x not in {"the", "a", "an", "shall", "is", "are", "be", "to", "of", "when", "while", "if", "and", "or", "then"}]
    return "_".join(w[:n]) or "x"


def main():
    argv = sys.argv[1:]
    if "--version" in argv:
        print("0.0.0-mock (Claude Code mock)")
        return
    system = ""
    if "--system-prompt" in argv:
        system = argv[argv.index("--system-prompt") + 1]
    user = sys.stdin.read()
    sd = Path(os.environ.get("MOCK_STATE_DIR", ".mock_state"))
    sd.mkdir(exist_ok=True)
    cnt_file = sd / "count"
    n = int(cnt_file.read_text()) + 1 if cnt_file.exists() else 1
    cnt_file.write_text(str(n))
    lim_after = int(os.environ.get("MOCK_LIMIT_AFTER", "0") or 0)
    lim_s = int(os.environ.get("MOCK_LIMIT_SECONDS", "6"))
    lim_file = sd / "limit_until"
    if lim_after and n % lim_after == 0 and not lim_file.exists():
        lim_file.write_text(str(time.time() + lim_s))
    if lim_file.exists():
        until = float(lim_file.read_text())
        if time.time() < until:
            msg = f"You've hit your session limit · resets in {max(1, int(until - time.time()))} seconds"
            print(json.dumps({"type": "result", "subtype": "success", "is_error": True, "result": msg}))
            sys.exit(1)
        lim_file.unlink()
    rnd = random.Random(int(os.environ.get("MOCK_SEED", "1")) * 100003 + n)
    time.sleep(rnd.uniform(0.01, 0.05))
    if "Reply with the single word OK" in system:
        text = "OK"
    elif system.startswith("You continue a text."):
        text = " ".join(user.split()[-3:])
    elif system.startswith("You are a blind, strict evaluator"):
        items = json.loads(user)
        text = json.dumps([{"id": it["id"], "equivalent": rnd.choice([0.25, 0.5, 0.75, 1.0]), "verdict": rnd.choice(["close", "different", "equivalent"]),
                            "meaning_changed": rnd.random() < 0.5, "issue": "mock"} for it in items])
    elif system.startswith("TASK: A script has split"):
        body = user.split("ITEMS (JSON):", 1)[1].split("YOUR PREVIOUS ANSWER:")[0].strip()
        fb = "OFFICIAL FRET PARSER RESULT" in user
        items = json.loads(body)
        outs = []
        for it in items:
            sl = {}
            for k, ph in it["slots"].items():
                e = snake(ph, 4)
                if k == "tm":
                    sl[k] = rnd.choice(["always", "immediately", "eventually"])
                    continue
                if rnd.random() < (0.05 if fb else 0.18):
                    e = rnd.choice([e + " 10 V", "abs(" + e + ") <= 5", e + " is true", "max(" + e + ", 3) > 1"])
                sl[k] = {"mode": snake(ph, 2)} if k in it["state_slots"] and rnd.random() < 0.5 else e
            outs.append({"i": it["i"], "slots": sl})
        text = json.dumps({"items": outs, "unmapped_content": []})
    elif system.startswith("TASK: PLAIN ENGLISH REWRITE"):
        raw = user.split("NATURAL LANGUAGE REQUIREMENT:", 1)[1].strip().rstrip(".")
        s = [raw[0].upper() + raw[1:] + "."] if rnd.random() < 0.9 else [raw[0].upper() + raw[1:] + ".", "The system shall log the event."]
        text = json.dumps({"sentences": s, "requirement_type": "mock plain", "split_reason": "" if len(s) == 1 else "mock split", "choices": [], "unmapped_content": [], "spec_confidence": "medium"})
    elif system.startswith("TASK: Rewrite the natural language"):
        raw = user.split("NATURAL LANGUAGE REQUIREMENT:", 1)[1].strip()
        m = re.search(r"# TEMPLATE: ([A-Za-z\-]+)", system)
        tpl = m.group(1) if m else "MASTeR"
        body = raw.rstrip(".")
        low = body[0].lower() + body[1:]
        if tpl == "MASTeR":
            kw = rnd.choice(["AS SOON AS", "IF", "AS LONG AS"])
            s = [f"{kw} {low}, the controller SHALL comply."]
        elif tpl == "EARS":
            kw = rnd.choice(["WHEN", "IF", "WHILE"])
            s = [f"{kw} {low}{', THEN' if kw == 'IF' else (',' if rnd.random() < 0.6 else '')} the system shall respond."]
        elif tpl == "Adv-EARS":
            kw = rnd.choice(["When", "WHILE", "IF"])
            s = [f"{kw} {low}{' THEN' if kw == 'IF' else ''} the entity shall perform the functionality."]
        elif tpl == "SPIDER":
            s = [rnd.choice(["Globally, it is always the case that if (" + low + ") holds, then (done) holds after at most 5 time units.",
                             "After (" + low + "), it is always the case that (done) holds until (reset) holds."])]
        else:
            s = [rnd.choice(["While " + low + ", the system shall respond.", "If " + low + ", the operator shall be able to react."])]
        if rnd.random() < 0.1:
            s.append("The system shall log the event.")
        text = json.dumps({"sentences": s, "requirement_type": "mock", "split_reason": "" if len(s) == 1 else "mock split",
                           "choices": [{"point": "condition keyword", "chosen": "mock", "alternatives": ["x"]}], "unmapped_content": [],
                           "spec_confidence": rnd.choice(["high", "medium"])})
    else:  # stage B or D
        src = user
        if "TEMPLATE SENTENCES:" in user:
            src = user.split("TEMPLATE SENTENCES:", 1)[1]
        elif "REWRITTEN SENTENCES:" in user:
            src = user.split("REWRITTEN SENTENCES:", 1)[1]
        else:
            src = user.split("NATURAL LANGUAGE REQUIREMENT:", 1)[1]
        first = re.sub(r"^\s*\d+\.\s*", "", src.strip().splitlines()[0])
        cond = snake(first, 3)
        resp = snake(first[len(first) // 2:], 3)
        form = rnd.choice([0, 1, 2])
        if form == 0:
            f = f"when {cond} the controller shall immediately satisfy {resp}"
            fld = {"scope": "", "condition": "when " + cond, "component": "the controller", "timing": "immediately", "response": resp}
        elif form == 1:
            f = f"in {cond} mode the controller shall always satisfy {resp}"
            fld = {"scope": f"in {cond} mode", "condition": "", "component": "the controller", "timing": "always", "response": resp}
        else:
            f = f"controller shall always satisfy ({cond}) => {resp}"
            fld = {"scope": "", "condition": "", "component": "controller", "timing": "always", "response": f"({cond}) => {resp}"}
        fb = "OFFICIAL FRET PARSER RESULT" in user
        if rnd.random() < (0.08 if fb else 0.3):
            bad = rnd.choice([f.replace("immediately", "within 5 ms"), f.replace("satisfy ", "satisfy abs(") + ") <= 3", f + ". This is a note.", f.replace("the controller", "the flight control system")])
            f = bad
        text = json.dumps({"fretish": [f], "fields": [fld], "choices": [{"point": "scope or condition", "chosen": "mock", "alternatives": ["x"]}],
                           "unmapped_content": [], "confidence": rnd.choice(["high", "medium"])})
        if "TIMING INFERENCE PRINCIPLES" in system:
            o = json.loads(text)
            o["timing_basis"] = {"rule": rnd.choice(["stated", "V-2b", "V-2c"]), "words": cond, "forbidden_situation": "mock situation"}
            text = json.dumps(o)
    it = rnd.randint(2, 9)
    ot = max(5, len(text) // 4)
    out = {"type": "result", "subtype": "success", "is_error": False, "duration_ms": rnd.randint(900, 3000), "duration_api_ms": rnd.randint(700, 2500),
           "num_turns": 1, "result": text, "stop_reason": "end_turn", "session_id": "mock", "total_cost_usd": 0.0,
           "usage": {"input_tokens": it, "output_tokens": ot, "cache_creation_input_tokens": rnd.randint(0, 3000), "cache_read_input_tokens": rnd.randint(0, 3000)},
           "modelUsage": {"mock-model": {"inputTokens": it, "outputTokens": ot}}}
    print(json.dumps(out))


if __name__ == "__main__":
    main()
