#!/usr/bin/env python3
"""Parser fingerprint. The official FRET parser is run on a FIXED probe corpus (every reference FRETish of data/reference/lm_reference_with_ltl.jsonl, de-duplicated, in file order);
the hash covers ok, ltl_ft and ltl_pt of every sentence. Two uses:
  1. pin: the expected hash is stored in data/reference/parser_fingerprint.pin (written once with --write-pin on the machine that runs the experiment); a run starts only when the hash matches.
  2. compare: --dump FILE stores the per sentence rows; --compare A B lists sentences whose (ok, ltl_ft, ltl_pt) differ between two dumps (docker image vs node copy).
usage (python3 -m nl2fret.fret_check.parser_fingerprint):
  python3 fret_check/parser_fingerprint.py --backend docker [--write-pin | --check] [--dump out.json]
  python3 fret_check/parser_fingerprint.py --compare a.json b.json
"""
import argparse
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
from nl2fret.paths import PROJECT  # noqa: E402

ROOT = str(PROJECT)
REF = os.path.join(ROOT, "data/reference/lm_reference_with_ltl.jsonl")
PIN = os.path.join(ROOT, "data/reference/parser_fingerprint.pin")


def corpus(ref=REF):
    out = []
    for l in open(ref, encoding="utf-8"):
        if l.strip():
            for part in json.loads(l)["gt_parts"]:
                out += [v["fretish"] for v in part]
    return list(dict.fromkeys(out))


def rows_of(texts, backend):
    from nl2fret.fret_check.tools import fret_compile
    return [{"fretish": r["fretish"], "ok": bool(r["ok"]), "ltl_ft": r.get("ltl_ft"), "ltl_pt": r.get("ltl_pt")} for r in fret_compile.compile_list(texts, backend=backend)]


def fingerprint(rows):
    h = hashlib.sha256()
    for r in rows:
        h.update(json.dumps([r["fretish"], r["ok"], r["ltl_ft"], r["ltl_pt"]], ensure_ascii=False).encode("utf-8") + b"\n")
    return h.hexdigest()


def check_pin(backend, ref=REF, pin=PIN):
    """-> (ok, fingerprint, expected). Used at the start of a generation run."""
    fp = fingerprint(rows_of(corpus(ref), backend))
    exp = open(pin).read().strip() if os.path.exists(pin) else None
    return exp == fp, fp, exp


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--backend", default="docker", choices=["docker", "node"])
    ap.add_argument("--write-pin", action="store_true")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--dump")
    ap.add_argument("--compare", nargs=2)
    a = ap.parse_args()
    if a.compare:
        x, y = [{r["fretish"]: r for r in json.load(open(p, encoding="utf-8"))["rows"]} for p in a.compare]
        diff = [t for t in x if t in y and (x[t]["ok"], x[t]["ltl_ft"], x[t]["ltl_pt"]) != (y[t]["ok"], y[t]["ltl_ft"], y[t]["ltl_pt"])]
        print(f"{len(x)} vs {len(y)} sentences, differing {len(diff)}")
        for t in diff[:20]:
            print(" ", t[:120])
        sys.exit(1 if diff else 0)
    rows = rows_of(corpus(), a.backend)
    fp = fingerprint(rows)
    print(f"backend={a.backend} sentences={len(rows)} ok={sum(r['ok'] for r in rows)} fingerprint={fp}")
    if a.dump:
        json.dump({"backend": a.backend, "fingerprint": fp, "rows": rows}, open(a.dump, "w", encoding="utf-8"), ensure_ascii=False)
    if a.write_pin:
        open(PIN, "w").write(fp + "\n")
        print("pin written", PIN)
    if a.check:
        exp = open(PIN).read().strip() if os.path.exists(PIN) else None
        print("pin", "MATCH" if exp == fp else f"MISMATCH (expected {exp})")
        sys.exit(0 if exp == fp else 1)


if __name__ == "__main__":
    main()
