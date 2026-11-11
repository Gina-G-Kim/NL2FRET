#!/usr/bin/env python3
"""Rule probe: sends the output shapes of the rule table and a list of open syntax questions to the OFFICIAL FRET parser (or the mock parser) and records accept / reject.

python3 -I tools/rule_probe.py --parser docker --out results_calib/rule_probe.jsonl
Only syntax is probed. Whether a shape means what the rule says is NOT tested (추측입니다). Part A re-uses the golden cases of tools/selftest.py, so the probe sees
exactly what the assembler writes. Part B asks questions the previous runs could not answer (unless, where, between-like scopes, unit words, next, before/after timing).
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import fretparse  # noqa: E402
import selftest  # noqa: E402
import tpl_rules as T  # noqa: E402

PART_B = [
    ("B-unless", "unless override_active controller shall satisfy valve_closed"),
    ("B-where", "where feature_a controller shall satisfy valve_closed"),
    ("B-while-expr", "while pump_running controller shall always satisfy pressure < 5"),
    ("B-while-and", "while (a) & (b) controller shall always satisfy y"),
    ("B-in-mode", "in standby mode controller shall always satisfy y"),
    ("B-in-nomode", "in standby controller shall always satisfy y"),
    ("B-after-scope", "after takeoff controller shall always satisfy y"),
    ("B-before-scope", "before landed controller shall always satisfy y"),
    ("B-after-until", "after takeoff controller shall until landed satisfy y"),
    ("B-timing-before", "controller shall before landed satisfy y"),
    ("B-timing-next", "when a controller shall next satisfy y"),
    ("B-unit-ticks", "controller shall within 5 ticks satisfy y"),
    ("B-unit-tick", "controller shall within 5 tick satisfy y"),
    ("B-unit-second", "controller shall within 1 second satisfy y"),
    ("B-unit-days", "controller shall within 2 days satisfy y"),
    ("B-unit-micro", "controller shall within 2 microseconds satisfy y"),
    ("B-for", "when a controller shall for 5 seconds satisfy y"),
    ("B-after-timing", "when a controller shall after 5 seconds satisfy y"),
    ("B-prob", "controller shall with probability <= 0.01 eventually satisfy y"),
    ("B-both", "in standby mode when a controller shall within 5 seconds satisfy y"),
    ("B-cond-and", "when (a) & (b) controller shall satisfy y"),
    ("B-neg-resp", "when a controller shall within 5 seconds satisfy !(y)"),
    ("B-absReal", "controller shall always satisfy absReal(x) <= 3"),
    ("B-the-comp", "when a the controller shall satisfy y"),
    ("B-if-resp", "when a controller shall satisfy if b then c"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parser", default="docker", choices=["docker", "mock"])
    ap.add_argument("--out", default="rule_probe.jsonl")
    a = ap.parse_args()
    probes = []
    for tpl, sent, slots, want in selftest.CASES:
        if isinstance(want, tuple):
            continue
        probes.append(("A-" + tpl, want, sent))
    for pid, s in PART_B:
        probes.append((pid, s, ""))
    cache = os.path.splitext(a.out)[0] + "_cache.jsonl"
    res = fretparse.compile_texts([p[1] for p in probes], a.parser, cache)
    rows = [{"probe": pid, "sentence": s, "from_template_sentence": src, "accepted": res[s]["ok"], "message": res[s]["error"]} for pid, s, src in probes]
    with open(a.out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    for r in rows:
        print(("ACCEPT " if r["accepted"] else "REJECT "), r["probe"].ljust(18), r["sentence"][:80], "" if r["accepted"] else "| " + str(r["message"])[:90])


if __name__ == "__main__":
    main()
