"""Round trip step (v2.0): FRET describes, in English, every sentence that the official parser accepted; the agent reads each description next to the input it came from and
returns the answer again in the same schema. One round, the same for every approach. The first answer, the answer after the parser feedback and the answer after the round trip are all
kept; the round trip answer replaces the answer after the parser feedback only when the official parser accepts every one of its sentences (adoption rule, fixed before any run).
No score, no reference sentence and no realizability result is part of the text.
"""
import json
import os
import re
import sys

from nl2fret import units3 as U

HERE = os.path.dirname(os.path.abspath(__file__))
RT_STAGE = "RT1"

RT_HEAD = """ROUND TRIP
FRET writes an English description of every FRETish sentence that it accepts; this is the text that FRET shows to a user who types the sentence. Below are your answer to the input above and the description of each sentence of it."""
RT_TAIL = """
Read every description next to the input it comes from. Keep a sentence unchanged when its description states the meaning of the input. Rewrite a sentence when its description states a different meaning, so that the new description states the meaning of the input.
Return the answer in exactly the JSON schema of the first answer, for ALL items of this input."""


def clean(desc):
    s = str(desc or "")
    s = re.sub(r"<br\s*/?>", " | ", s)
    s = re.sub(r"<[^>]+>", "", s)
    return re.sub(r"\s+", " ", s).strip()


def descriptions(texts, backend, cache_path):
    """-> {text: description}; the official parser through fret_compile, cached in cache_path (jsonl). Not available for the mock parser."""
    if backend == "mock":
        raise SystemExit("the round trip step needs the official parser (docker or node); the mock parser has no descriptions")
    cache = {}
    if os.path.exists(cache_path):
        for line in open(cache_path, encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                cache[r["t"]] = r["description"]
    todo = [t for t in dict.fromkeys(texts) if t not in cache]
    if todo:
        from nl2fret.fret_check.tools import fret_compile
        res = fret_compile.compile_list(todo, backend=backend)
        with open(cache_path, "a", encoding="utf-8") as f:
            for r in res:
                d = clean((r.get("sem") or {}).get("description")) if r.get("ok") else ""
                cache[r["fretish"]] = d
                f.write(json.dumps({"t": r["fretish"], "description": d}, ensure_ascii=False) + "\n")
    return {t: cache.get(t, "") for t in texts}


def applicable(rec):
    """a unit whose last answer has at least one sentence and every sentence is accepted by the official parser"""
    if rec["pending"] or rec["pipeline"] or not rec["rounds"]:
        return False
    last = rec["rounds"][-1]
    if last.get("pending") or not last["sentences"]:
        return False
    return all(s.get("text") and s.get("official") is not None and s["official"]["ok"] for s in last["sentences"])


def last_texts(rec):
    return [s["text"] for s in rec["rounds"][-1]["sentences"]]


def body(original_body, rec, descs):
    last = rec["rounds"][-1]
    ans = ((last.get("row") or {}).get("raw_result") or "").strip()
    lines = []
    for i, s in enumerate(last["sentences"], 1):
        lines.append(f"{i}. {s['text']}\n   description: {descs.get(s['text'], '')}")
    return "\n".join([original_body.rstrip(), "", RT_HEAD, "", "YOUR ANSWER:", ans, "", "FRET DESCRIPTION OF EACH SENTENCE:", "\n".join(lines), RT_TAIL]) + "\n"


def with_rt(rec, rows, item, arm, rep, comp):
    """-> (rec2, adopted). rec2 has the round trip round appended (when its row exists and is ok); adopted is True when its sentences are all accepted by the parser."""
    row = rows.get(U.skey(item["id"], arm, rep, RT_STAGE))
    if row is None or not applicable(rec):
        return rec, False
    rule = U.is_rule(arm)
    free = (not rule) or bool(rec.get("fallback"))
    n = len(rec["rounds"])
    if free:
        rr = U._free_round(n, RT_STAGE, row, comp)
    else:
        rr = U._slot_round(n, RT_STAGE, row, rec["parses"], rec["reqs"], comp, U.is_r2(arm))
    rec2 = dict(rec)
    rec2["rounds"] = rec["rounds"] + [rr]
    adopted = bool(rr["sentences"]) and not rr.get("pending") and not U.round_failed(rr) and all(s.get("text") for s in rr["sentences"])
    rec2["rt_adopted"] = adopted
    return rec2, adopted
