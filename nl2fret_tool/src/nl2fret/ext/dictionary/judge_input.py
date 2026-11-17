#!/usr/bin/env python3
"""Extension `dictionary`, judge side: the argument `--dictionary` of `nl2fret_judge judge-parts`.
The frozen judge (src/nl2fret_judge/cli.py) declares `--dictionary` as a required argument and reads it for its name alignment (exact / aliased / oov). `src/nl2fret_judge/` is not changed, so:
  extension on   -> the dictionary file of the extension (data/dictionary/lm_dictionary.csv, version v1)
  extension off  -> a header-only file with the same columns and no entry (written to <run>/ext_off_dictionary.csv): the judge receives the argument but no dictionary content,
                    every identifier is `oov`, nothing is renamed
usage: python3 -m nl2fret.ext.dictionary.judge_input --ext "dictionary" --run RUN_DIR      (prints the path to pass to --dictionary)
       judge_args(exts, run_dir) -> ["--dictionary", path]"""
import argparse
import csv
import sys
from pathlib import Path

from nl2fret.ext import DICTIONARY, parse
from nl2fret.paths import PROJECT

CSV = PROJECT / "data" / "dictionary" / "lm_dictionary.csv"


def dictionary_path(exts, run_dir):
    if DICTIONARY in exts:
        return str(CSV)
    header = next(csv.reader(open(CSV, encoding="utf-8-sig")))
    out = Path(run_dir) / "ext_off_dictionary.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as f:
        csv.writer(f, lineterminator="\n").writerow(header)
    return str(out)


def judge_args(exts, run_dir):
    return ["--dictionary", dictionary_path(exts, run_dir)]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--ext", default="")
    ap.add_argument("--run", required=True)
    a = ap.parse_args()
    print(dictionary_path(parse([a.ext]), a.run))
