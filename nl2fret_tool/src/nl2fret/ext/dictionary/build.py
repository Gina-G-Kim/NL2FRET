#!/usr/bin/env python3
"""Extension `dictionary`, update side. Role of data/dictionary/build_dict.py: the dictionary table and what is derived from it.
Subcommands (all read-only unless an output path is named):
  verify               the table text of every challenge, rebuilt from data/dictionary/lm_dictionary.csv with the rule of tools/build_inputs.py (dict_text), equals bench/data/sigdict.json
                       and data/reference/sigdict.json
  record --version V   writes versions/V/EVIDENCE.json (version, rows, rows per challenge, columns, name of the generator build_dict.py)
  update               runs data/dictionary/build_dict.py (the generator of the layers docx / model / nasa; its source files are NOT in this package: the script reads absolute paths of the machine that built v1)
  overlay NAME --nasa LM_requirements.json --out CSV --evidence JSON
                       optional overlay (default off): writes the dictionary with the columns alias_of and alias_evidence by overlays/NAME/build_alias_v2.py; nothing in the core reads these columns
Dictionary version folder: versions/v1/ (current). The default dictionary is v1."""
import argparse
import csv
import json
import subprocess
import sys
from pathlib import Path

from nl2fret.paths import PACKAGE, PROJECT

HERE = Path(__file__).resolve().parent
BENCH = PACKAGE
PKG = PROJECT
CSV = PKG / "data" / "dictionary" / "lm_dictionary.csv"
VERSION = "v1"


def rebuilt():
    from nl2fret.tools.build_inputs import dict_text
    by = {}
    for r in csv.DictReader(open(CSV, encoding="utf-8-sig")):
        by.setdefault(r["challenge"], []).append(r)
    return {ch.split("_")[0]: dict_text(rs) for ch, rs in sorted(by.items())}


def cmd_verify(a):
    ok = True
    sig = rebuilt()
    for p in (BENCH / "data" / "sigdict.json", PKG / "data" / "reference" / "sigdict.json"):
        same = json.loads(p.read_text(encoding="utf-8")) == sig
        print(("OK   " if same else "DIFF ") + str(p.relative_to(PKG)))
        ok &= same
    return 0 if ok else 1


def cmd_record(a):
    d = HERE / "versions" / a.version
    d.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(open(CSV, encoding="utf-8-sig")))
    per = {}
    for r in rows:
        per[r["challenge"]] = per.get(r["challenge"], 0) + 1
    ev = {"version": a.version, "rows": len(rows), "rows_per_challenge": per, "columns": list(rows[0].keys()),
          "generator": {"file": "data/dictionary/build_dict.py"}}
    (d / "EVIDENCE.json").write_text(json.dumps(ev, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {d}")
    return 0


def cmd_update(a):
    return subprocess.call([sys.executable, str(PKG / "data" / "dictionary" / "build_dict.py")])


def cmd_overlay(a):
    script = HERE / "overlays" / a.name / "build_alias_v2.py"
    return subprocess.call([sys.executable, "-I", "-B", str(script), "--v1", str(CSV), "--nasa", a.nasa, "--out", a.out, "--evidence", a.evidence])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("verify").set_defaults(f=cmd_verify)
    r = sp.add_parser("record")
    r.add_argument("--version", default=VERSION)
    r.set_defaults(f=cmd_record)
    sp.add_parser("update").set_defaults(f=cmd_update)
    o = sp.add_parser("overlay")
    o.add_argument("name")
    for k in ("nasa", "out", "evidence"):
        o.add_argument("--" + k, required=True)
    o.set_defaults(f=cmd_overlay)
    a = ap.parse_args()
    return a.f(a)


if __name__ == "__main__":
    sys.exit(main())
