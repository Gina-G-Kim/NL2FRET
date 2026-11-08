#!/usr/bin/env python3
"""Check the Lockheed Martin cases against the text of the original docx files.

For every case in lockheed_martin/cases.jsonl (49) and fsm/cases.jsonl (12), verify that `raw_nl`
occurs in the corresponding original docx file.

Source: GitHub repository hbourbouh/lm_challenges, original_models/<n>_<name>/<file>.docx
  - The docx files are not part of this repository. Download them as shown below and keep the original
    file names in one directory. This script does not access the network.
      SHA=133447a8943721eaa1d16acf1ba5845b67a98df1   # HEAD of master (2020-02-12); the docx files have
                                                     # not changed since commit 4ee0e326
      URL=https://raw.githubusercontent.com/hbourbouh/lm_challenges/$SHA/original_models/1_fsm/1_fsm_reqs.docx
      curl -L -o <dir>/1_fsm_reqs.docx "$URL"
      (repeat for all 10 files)
  - The downloaded files are untrusted data. The script reads them with zipfile and regular
    expressions only; it uses no XML parser.

Match levels (strictest first)
  exact_paragraph            raw_nl equals one docx paragraph, character for character
  exact_in_joined_text       raw_nl occurs verbatim in the full text (paragraphs joined by newlines)
  normalized_in_joined_text  raw_nl occurs in the full text after normalizing whitespace, line breaks,
                             quotation marks, dashes and non-breaking spaces
  none                       no match

Usage (from the repository root):
    python3 -I -B tools/verify_lm_docx.py <docx directory> [--out data/cases/lockheed_martin/docx_match.csv]
"""
import csv
import hashlib
import html
import json
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = [("lockheed_martin", os.path.join(ROOT, "data", "cases", "lockheed_martin", "cases.jsonl")),
         ("fsm", os.path.join(ROOT, "data", "cases", "fsm", "cases.jsonl"))]


def paragraphs(path):
    with zipfile.ZipFile(path) as z:
        info = z.getinfo("word/document.xml")
        assert info.file_size < 20_000_000, "document.xml too large"
        x = z.read("word/document.xml").decode("utf-8", "replace")
    out = []
    for p in re.findall(r"<w:p[ >].*?</w:p>", x, flags=re.S):
        # Match <w:t> and <w:t xml:space=...> only; <w:tab/> and <w:tbl> must not match.
        out.append(html.unescape("".join(re.findall(r"<w:t(?:\s[^>]*)?>(.*?)</w:t>", p, flags=re.S))))
    return out


def norm(s):
    for a, b in (("’", "'"), ("‘", "'"), ("“", '"'), ("”", '"'), ("–", "-"), ("—", "-"), (" ", " ")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def git_blob_sha1(b):
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    dl = sys.argv[1]
    out = os.path.join(ROOT, "data", "cases", "lockheed_martin", "docx_match.csv")
    if "--out" in sys.argv:
        out = sys.argv[sys.argv.index("--out") + 1]
    cache = {}
    rows = []
    summary = {}
    for group, path in CASES:
        for l in open(path, encoding="utf-8"):
            if not l.strip():
                continue
            r = json.loads(l)
            src = r["nl_source"] if "nl_source" in r else r["origins"][0]["nl_source"]
            repo_path = src["file"].split(" ", 1)[1]          # e.g. original_models/1_fsm/1_fsm_reqs.docx
            base = os.path.basename(repo_path)
            if base not in cache:
                fp = os.path.join(dl, base)
                b = open(fp, "rb").read()
                cache[base] = (paragraphs(fp), git_blob_sha1(b), hashlib.sha256(b).hexdigest(), len(b))
            ps, gsha, _, _ = cache[base]
            joined = "\n".join(ps)
            raw = r["raw_nl"]
            if raw in ps:
                k = "exact_paragraph"
            elif raw in joined:
                k = "exact_in_joined_text"
            elif norm(raw) in norm(joined):
                k = "normalized_in_joined_text"
            else:
                k = "none"
            rows.append([r["case_id"], group, r["challenge"], repo_path, src["locator"], k, gsha])
            summary[(group, k)] = summary.get((group, k), 0) + 1
    with open(out, "w", newline="", encoding="utf-8") as w:
        cw = csv.writer(w)
        cw.writerow(["case_id", "group", "challenge", "docx_path_in_repo", "locator", "match", "docx_git_blob_sha1"])
        cw.writerows(rows)
    print("docx files (file name, size, git blob sha1, sha256):")
    for base, (_, g, s, n) in sorted(cache.items()):
        print(f"  {base:28} {n:7} {g} {s}")
    print("match summary:")
    for (g, k), n in sorted(summary.items()):
        print(f"  {g:16} {k:28} {n}")
    print("total", len(rows), "| none", sum(1 for r in rows if r[5] == "none"), "| output", os.path.relpath(out, ROOT))


if __name__ == "__main__":
    main()
