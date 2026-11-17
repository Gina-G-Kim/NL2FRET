"""Aggregation from judge_records.jsonl (everything is recomputed from the raw records).

Unit outcome (item x arm x rep), taken over the unit's sentences against all reference versions of the item:
  success    : some sentence is SAME or PROOF and that same sentence is realizable (Kind2)
  partial    : no success, some sentence is REFUTE (MISS only), or SAME/PROOF but not realizable
  failure    : sentences judged, none above (NEITHER); or parser-rejected / no sentence
  unjudged   : every sentence is UND (no vocabulary alignment) or N/M (engine could not decide)
Primary denominator: ALL units (failure and unjudged stay in). Secondary: units that were judged (unjudged removed), reported only next to the
primary value and only for comparison with the literature (Danso et al. exclude N/M)."""
import collections
import json
import sys

from .recorder import split_tail

ORDER = {"SAME": 0, "PROOF": 1, "REFUTE": 2, "NEITHER": 3}


def sentence_class(rec, realizable):
    r = rec.get("role")
    if r in ("SAME", "PROOF"):
        return "success" if realizable else "partial"
    if r == "REFUTE":
        return "partial"
    if r == "NEITHER":
        return "failure"
    return "unjudged"


def unit_outcome(sent_classes):
    if not sent_classes:
        return "failure"
    for c in ("success", "partial", "failure"):
        if c in sent_classes:
            return c
    return "unjudged" if all(c == "unjudged" for c in sent_classes) else "failure"


def aggregate(units, records):
    """units: from units.load_units; records: {pair_id: record} with pair_id = f"{item}|{arm}|{rep}|{sentence_index}"."""
    rows = []
    for u in units:
        cl = []
        for i, s in enumerate(u["sentences"]):
            if not s["parser_ok"] or not s["ltl_pt"]:
                cl.append("failure")
                continue
            rec = records.get(f"{u['item']}|{u['arm']}|{u['rep']}|{i}")
            cl.append(sentence_class(rec, s["realizability"] == "realizable") if rec else "unjudged")
        rows.append({"item": u["item"], "arm": u["arm"], "rep": u["rep"], "stratum": u.get("stratum"), "outcome": unit_outcome(cl)})
    return rows


def table(rows, key="arm"):
    g = collections.defaultdict(collections.Counter)
    for r in rows:
        g[r[key]][r["outcome"]] += 1
    out = []
    for k in sorted(g, key=str):
        c = g[k]
        n = sum(c.values())
        judged = n - c["unjudged"]
        out.append({key: k, "n_units": n, "success": c["success"], "partial": c["partial"], "failure": c["failure"], "unjudged": c["unjudged"],
                    "success_rate_all": round(c["success"] / n, 4) if n else None,
                    "success_rate_judged_only": round(c["success"] / judged, 4) if judged else None})
    return out


def nm_summary(records):
    c = collections.Counter()
    for r in records.values():
        c[("UND:" + str(r["und_reason"])) if r["role"] == "UND" else (("NM:" + str(r["nm_reason"])) if r["nm"] else r["role"])] += 1
    return dict(c)


def read_records(path):
    """pair_id -> record. v1.1.0: an incomplete last line (a write interrupted by a forced stop, see recorder.py) is skipped with a warning and the file is not
    changed; any other unreadable line is still an error."""
    offset, tail, complete = split_tail(path)
    with open(path, "rb") as f:
        data = f.read(offset) if (tail and not complete) else f.read()
    if tail and not complete:
        print(f"warning: {path}: ignored an incomplete last line ({len(tail)} bytes, interrupted write); it is not part of this aggregate", file=sys.stderr)
    return {r["pair_id"]: r for r in (json.loads(l) for l in data.decode("utf-8").split("\n") if l.strip())}
