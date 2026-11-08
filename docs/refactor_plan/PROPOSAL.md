# PROPOSAL: Proposed Target Structure (approval request, stage 2)

Status note: this document is kept for reference only. It was superseded by the lighter cleanup that is described in `../../STRUCTURE.md`.

This document is an approval request. **No file is moved before approval.** Because the source text of the classification rules is not available (INVENTORY 3.3), the structure below is a conservative draft that "keeps the existing directory names" and creates no new classification rules. If the project owner provides the source text of the classification rules, only the placement under `experiments/` will be adjusted to match it.

## 1. Draft structure

```
nl2fret-repo/                      (the root name is chosen by the project owner; for now ~/nl2semiformal itself is used as the root)
  README.md                        overview, run order, process diagram
  docs/
    STRUCTURE.md                   description of this structure
    protocols/                     "original instruction documents" rather than copies of prompt documents (NL2FRET_PROMPT_v1 ... v8, testnote)
    reports/                       REPORT, FINAL_REPORT, RUN_RECORD and similar (the originals stay in the result folders)
  prompts/                         shared prompt assets (fretish_guide.md, templates/*.md)
  data/
    raw/                           lm_items.jsonl, dev_items.jsonl, dict8_items.jsonl, sigdict.json
    reference/                     (no ground-truth files; left empty with a .gitkeep)
  src/nl2fret/                     [decision needed, section 3 B]
  tools/                           one-off helper scripts (dict_usage.py, make_run_record.py and others)
  experiments/                     existing directory names as they are (nl2fret, nl2fret_v2, nl3, nl4, nl5, nl6, nl7, v7_dev0, v7_dev1, v8_dict8)
    <existing name>/               the inside of each folder is not changed (code snapshot, results_*, snapshot/, FROZEN*.sha256, zip)
  engines/                         Docker installation notes: fret-lab guide, ltl-spot Dockerfile, cst-nusmv usage notes
  packages/ltlpack/                ltl_engines/pack and ltl_engines/inputs, with README_MAC.md and MANIFEST.sha256 kept
  legacy/                          fret_template_bench, fret_retest_v2 (classification unknown, so kept under their names) [decision needed, section 3 E]
  paper/                           paper/, source/ (~/NL2FRET_REFSQ_2026 is outside the repository and is not moved)
  tests/                           selftest wrappers (thin tests that run the existing selftests without changing code)
  results/                         [decision needed, section 3 C]
  .gitignore, Makefile, requirements.txt
  refactor_plan/                   INVENTORY, PROPOSAL, MOVE_MANIFEST.csv, VERIFICATION.md
```

## 2. What this draft preserves
1. **The internal structure and files of the experiment run directories are not changed.** Because a whole folder is moved under `experiments/` in one piece, the relative-path verification of `snapshot/` and `FROZEN*.sha256` still passes.
2. No file is deleted; `MOVE_MANIFEST.csv` (old_path, new_path, sha256) and the file counts are compared before and after the move.
3. The contents of the results (jsonl files, judgment results, raw outputs) are unchanged.

## 3. What must be decided before approval

| Key | Question | Options and the assistant's opinion |
|---|---|---|
| A | Source text of the classification rules | Provide `claude/NL2FRET_*.md`, or approve proceeding with the draft above (existing names kept). **If the source text exists, it is recommended to provide it first** |
| B | Whether to merge the code into a single `src/nl2fret` | (1) Do not merge; leave the code snapshot inside each `experiments/<run>/` as it is (guarantees reproducibility of the figures; recommended). (2) Package one version as the basis. In that case it must be decided which version is the basis and what to do with the code that reproduces the figures of older runs. Because the code diverges into 8 variants (INVENTORY section 5), (2) would make it hard to keep the "no functional change" rule (speculative) |
| C | Separating `results/` | The result folders are inside each run and are tied to `snapshot/` and the manifests. Keeping them inside the runs without separating them is recommended. Separating them would require deciding how to reconnect the relative paths used for hash verification |
| D | `nl2fret/.venv` (1.24 GB) | It breaks when moved. Decide whether to replace it with `requirements.txt` (versions not pinned) and keep `.venv` outside the repository, or create it anew. Because of the rule not to delete files, the default is to leave it where it is now |
| E | `fret_template_bench`, `fret_retest_v2` | The classification is unknown, so keeping them under their names in `legacy/` is proposed. Please tell us if another location is correct |
| F | Missing components | judge3/4/5, `sk.py`, `rq.py`, and the documents for v7 TEST and v8 and later are not on this machine. If you tell us where they are, they will be reflected in `src/nl2fret/judge` and similar places; if they do not exist, they will be documented as "missing" and the verification left as "unverified" |
| G | LICENSE, CITATION.cff | The project owner chooses the license; the assistant does not |
| H | git | The home directory `~` is a repository and has 0 tracked files. Decide whether to run a new `git init` at the root of this repository (nesting it inside the home repository). For now only `mv` and the manifest are used |

## 4. Order of work after approval (stage 3 onward)
1. Create and save a sha256 manifest of everything to be moved (including file counts) before the move.
2. `mv` according to the approved structure (per folder, contents unchanged).
3. Code path repairs change only imports and path settings (logic unchanged). At present the confirmed hard-coded paths are one `/Users/gina` occurrence in `posthoc_sensitivity.py` and `/tmp` in `run_mock6.sh`; the run records inside the result folders are originals and are not modified.
4. Write `.gitignore`, `README.md`, `docs/STRUCTURE.md` and `MOVE_MANIFEST.csv`.
5. Verification: manifest comparison, `selftest`, `dict_usage.py` (24.6, 54.4 and others), ltlpack selftest, rerun of `sha256sum -c FROZEN*`. judge4 and the Mac-only engines are marked "unverified".
