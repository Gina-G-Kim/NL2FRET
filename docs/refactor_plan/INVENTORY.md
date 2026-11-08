# INVENTORY: Current State of the Whole NL2FRET Toolset (before the move, read-only survey)

Survey date: 2026-11-08. No file was moved or modified in this stage. The only new files are this document and `PROPOSAL.md` in `refactor_plan/`. Verified facts and speculation are kept apart, and what is not known is written as "unknown".

Status note: this is a historical record made before the move. The directory names used below are the pre-move names; for example, `nl2fret` is now `experiments/nl2fret` and `ltl_engines` is now `packages/ltlpack` (see `../../STRUCTURE.md` and `../../MOVE_LOG.csv`).

## 1. Scale

| Item | Value |
|---|---|
| Survey scope | All of `~/nl2semiformal/` and `~/NL2FRET_REFSQ_2026/` (Overleaf copy of the paper, 32 files) |
| Number of files | 41,116 (of which 36,071 are in `nl2fret/.venv`) |
| Size | 1.7 GB (of which 1.24 GB is `.venv`) |
| Without `.venv` | about 5,045 files, about 0.46 GB |
| Home git repository | `~` is a git repository, but 0 files are tracked (all untracked). `git mv` therefore cannot be used and `mv` must be used instead |

Most files by extension are `.py` 12,334, `.pyc` 11,879 and `.h` 8,654, all of which come from `.venv` and `__pycache__`. The project's own material is `.jsonl` 208, `.csv` 199, `.json` 417, `.md` 325, `.smv` 812 (NuSMV input work files), `.log` 483 and `.sh` 57.

## 2. State per directory

Sizes and file counts exclude `.venv`. The descriptions list only what was verified from documents inside the directories (CHANGELOG, prompt documents) and from memory records.

| Directory | Files | MB | Contents | Prompt documents | Result folders |
|---|---|---|---|---|---|
| `nl2fret` | 857 | 135 | First experiment (v1). 10-repetition main run, 5-repetition copy, pilot, 11 paper PDFs | `NL2FRET_PROMPT_v1.md` | `results_nl2fret`, `results_nl2fret_5reps`, `results_pilot`, `results_verify`, `results_dry` (empty folder) |
| `nl2fret_v2` | 671 | 55 | v2 (FRET unknown metric, 68 items, 3 repetitions) | `NL2FRET_PROMPT_v2.md` | `results_nl2fret`, `results_pilot` |
| `nl3` | 861 | 96 | v3 (rule-assembly methods, 3 repetitions and G methods) | `NL2FRET_PROMPT_v3.md` | `results_nl3`, `results_calib`, `results_calib2`, `results_pilot` |
| `nl4` | 120 | 6 | v4 LM smoke run | `NL2FRET_PROMPT_v4_LM.md`, `NL2FRET_SMOKE_v4_LM.md` | `results_smoke` |
| `nl5` | 150 | 9 | v4 LM second smoke run | `NL2FRET_PROMPT_v4_LM.md`, `NL2FRET_SMOKE2_v4_LM.md` | `results_smoke2` |
| `nl6` | 154 | 19 | v6 LM preflight, first attempt (did not proceed to the main run because P25 failed) | `NL2FRET_PROMPT_v6_LM.md` | `results_pre` |
| `nl7` | 781 | 132 | v6 LM rerun (main run after the preflight passed, 61 items x 13 methods x 3 repetitions) | `NL2FRET_PROMPT_v6_LM.md` | `results_pre`, `results_lm` |
| `v7_dev0` | 88 | 7 | v7 development set, first run (DEV0, 94 items x 12 methods) | `NL2FRET_PROMPT_v7_DEV0.md` | `bench/results_dev` |
| `v7_dev1` | 138 | 14 | v7 development, second run (DEV1, 13 new methods) | `NL2FRET_PROMPT_v7_DEV1.md` | `bench/results_dev` (copy of DEV0), `bench/results_dev1` |
| `v8_dict8` | 157 | 8 | v8 signal-dictionary smoke run and realizability stage | `NL2FRET_PROMPT_v8_DICT_SMOKE.md`, `NL2FRET_RLZ_DICT8.md` | `bench/results_dict8` |
| `ltl_engines` | 851 | 8 | NuSMV and Spot comparison study (610 pairs) | `README_MAC.md` | `pack/results`, `run1_noengines/results` |
| `fret_template_bench` | 108 | 30 | Earlier experiment (an old experiment according to the memory records) | `README.md` | `results`, `results_pilot_low`, `results_run1`, `results_smoke` |
| `fret_retest_v2` | 82 | 2 | Retest. Its contents are unknown (only the prompt `RETEST_PROMPT_v2.md` exists) | `RETEST_PROMPT_v2.md` | `results_pilot`, `results_v2` |
| `paper` | 23 | 2 | LaTeX source and bibliography of the REFSQ 2026 paper | - | - |
| `source` | 1 | 0.3 | PDF of the Konrad 2005 paper | - | - |
| Top-level files | 3 | 0 | `NL2FRET_v6_main_analysis_ppt_format.md`, `testnote.md` (v7 TEST instructions, November 4 version), `fret_template_bench.zip` | - | - |
| `~/NL2FRET_REFSQ_2026` | 32 | - | Overleaf copy (`main.tex`, `AsiaCCS_2027/` and others). Separate from `nl2semiformal/paper` | - | - |

## 3. Survey of the per-test directory classification rules (key point)

### 3.1 What was not found
The project document `claude/NL2FRET_*.md` mentioned in the task brief is not on this machine (there is no `~/claude` directory, and a search for `NL2FRET_*.md` within three levels of the home directory returns only the prompt documents in the table above). `NL2FRET_v7_post_dev1_adjustments.md` and the v7 TEST (evaluation) prompt document are not on disk either. The `.md` files of all directories were searched for `directory`, `folder structure`, `layout`, `naming`, `classification rule` and similar terms, but **no sentence stating a classification rule was found.**

### 3.2 Observed conventions (not confirmed as rules)
The following are facts observed in the files; none of them is written down as a "rule".

| Observation | Evidence |
|---|---|
| One experiment run = one top-level directory containing the full code copy of that time + result folders + zips | the whole table above |
| Result folder names: `results_<stage>` (`results_pilot`, `results_smoke`, `results_smoke2`, `results_pre`, `results_lm`, `results_nl3`, `results_calib`, `results_dev`, `results_dev1`, `results_dict8`) | directory listing |
| Preflight results (`results_pre`) are not mixed with main-run results (`results_lm`) | `nl7/NL2FRET_PROMPT_v6_LM.md` lines 22 and 265 |
| When a first attempt fails, it is redone from the start in a new folder (`nl6`, then `nl7`) and the earlier folder is left untouched | `nl7/results_lm/RUN_RECORD.md` lines 41 and 826 |
| The version notation `v1, v2, v3, v4_LM, v6_LM, v7_DEV0, v7_DEV1, v8_DICT_SMOKE` is part of the prompt file names. There is no v5, and `nl5` uses the v4 prompt | list of prompt documents |
| From this session on, `v7_dev0`, `v7_dev1`, `v8_dict8` and `ltl_engines` use the structure `inputs/ docs/ scripts/ notes/ logs/ zips/ bench/` | created by the assistant at the project owner's request (2026-11-03) |
| The folder names `nl2fret`, `nl2fret_v2` and `nl3` to `nl7` have a different naming form from `v7_dev0` and later | directory listing |

### 3.3 List of unclear rules (work stops here and asks)
1. The source text of the rules "smoke, dev, test, version distinction v4 to v8, experiment run distinction" mentioned in the task brief (which document, which sentence) is not on this machine. Either the source text must be provided, or one of the interpretations under item 4 below must be chosen.
2. It cannot be read from the documents where `nl2fret`, `nl2fret_v2` and `nl3` to `nl7` belong in a classification scheme such as `v1` to `v6`, `smoke` and `pre`. For example, whether `nl4` (smoke), `nl5` (smoke2), `nl6` (pre) and `nl7` (pre and lm) belong to the same "v6" version, or whether `nl4` and `nl5` are "v4", is speculative.
3. The directory that would correspond to "test" (the v7 TEST evaluation run) is not on disk. `testnote.md` contains only the instructions, and there is no `results_test` result.
4. The "dev" classification: it is unknown whether `v7_dev0` and `v7_dev1` should be placed as runs 0 and 1 under `dev`, or kept with their names.
5. It is unknown where `fret_template_bench` and `fret_retest_v2` belong in the current classification (the memory records only say "old experiment").
6. Some components mentioned in the task brief are not on this machine (section 4). Whether they exist elsewhere must be stated before `src/nl2fret/judge` and similar parts can be created.

## 4. Component mapping (task brief list versus what is on disk)

| Component in the task brief | What was found on disk | Status |
|---|---|---|
| Prompts v4 to v8 | `v4_LM` (nl4, nl5), `v6_LM` (nl6, nl7), `v7_DEV0`, `v7_DEV1`, `v8_DICT_SMOKE`, `RLZ_DICT8`. The shared `prompts/fretish_guide.md` and `templates/*.md` (5 files), and the code `prompts3.py` | No documents for v5, v7 TEST, or v8 and later |
| Dataset of 61 Lockheed Martin items | `data/lm_items.jsonl` (nl4 to nl7, v8_dict8) | Present (several copies) |
| NASA FRETish reference | `dev_items.jsonl` has 25 NASA items. No separate reference file was searched for (because of the rule not to look for ground-truth files) | Not checked |
| Conversion runner | `run_pipeline.py`, `cli.py`, `units3.py`, `prompts3.py`, `common.py`, `mock_claude.py` | Present, a copy per directory |
| FRET compile integration | `fretparse.py`, `fret_check/` (a copy per directory; only `nl2fret/fret_check` has 610 files) | Present |
| Judges judge3/judge4/judge5 | No files. Only mentions in documents and reports (README and REPORT of `ltl_engines`). `judge.py` exists only in `nl2fret` and `nl2fret_v2` and is presumed to be the v1 similarity judge (speculative) | **No code** |
| z3 judgment, NuSMV, Spot | `ltl_engines/pack/tools/ltl_engines.py` (z3b, NuSMV and Spot translation and execution) | Present (this one file) |
| Kind2 realizability | `fret_check/check.py` and `fret_rlz.py` call Kind2 inside the Docker `fret-lab` | Present (code); the engine is in the Docker image |
| Control experiments | `ltl_engines/pack/data/pairs.jsonl` (includes 512 control pairs) | Present (data) |
| RQ analysis scripts sk.py, rq.py | No files with these names. The analysis code is `nl3/analyze3.py`, `nl2fret/tools_extra/analysis_*.py`, `score3.py`, `score_lm.py`, `nl7/make_run_record.py`, and `analysis/` inside the result folders | **sk.py and rq.py are missing** |
| ltlpack (Mac execution package) | `ltl_engines/pack/` (the original zip is in `ltl_engines/inputs/`) | Present |
| Results | table in section 3 | Present |
| Reports | `results_*/REPORT.md`, `FINAL_REPORT.md`, `RUN_RECORD.md`, `DEV_RECORD.md`, `RLZ_RECORD.md`, `paper/` | Present |

## 5. Code divergence (the biggest risk of the refactoring)

The code is not a single code base; it is a **snapshot copied for each experiment run**, and the snapshots differ from each other. The numbers below are the numbers of distinct sha256 values for files of the same name (excluding `snapshot/` and `rules_original/`).

| File | Copies | Distinct contents |
|---|---|---|
| `run_pipeline.py` | 10 | 8 |
| `prompts3.py` | 8 | 8 |
| `mock_claude.py` | 12 | 7 |
| `extract_files.py` | 11 | 6 |
| `common.py` | 10 | 4 |
| `units3.py` | 8 | 4 |
| `tpl_rules.py` | 8 | 3 |
| `score3.py` | 8 | 3 |
| `score_lm.py` | 7 | 3 |
| `cleanenv.sh` | 6 | 3 |
| `cli.py` | 10 | 2 |
| `fretlint.py` | 8 | 2 |
| `fretparse.py` | 8 | 1 |

Implication: to merge them into a single `src/nl2fret`, one version must be chosen as the basis, and after merging there is no guarantee that the figures of earlier experiments can be reproduced with that code (this may conflict with the "results must not change" rule of the task brief). In addition, each `results_*/snapshot/` is a copy of the code as it was at run time, and `FROZEN*.sha256` and `RULES_FROZEN.sha256` are based on relative paths, so moving files can break `sha256sum -c`. These copies and manifests are evidence records and must be preserved without modification (20 `snapshot/` directories).

## 6. Survey of path references

| Search | Result |
|---|---|
| `/home/claude` | 0 occurrences in file contents |
| `/Users/gina` (code files `.py .sh .yml Dockerfile .js`) | 1 occurrence: `nl3/results_nl3/analysis/posthoc_sensitivity.py` |
| `/Users/gina` (documents, logs, reports) | About 25 files, such as the FRET_NOTES of the `nl2fret` family, the CHANGELOG and notes files, and the logs of the result folders. These are run records and are not to be modified (rule for original results) |
| `/Users/gina` (inside `.venv`) | 29 files |
| Hard-coded `/tmp` | `nl6/run_mock6.sh`, `nl7/run_mock6.sh` (temporary path for the mock test) |
| Relative paths | It was verified that `ltl_engines/pack/tools/ltl_engines.py` and `v8_dict8/bench/tools/rlz_dict8.py` use `ROOT = the parent of the script folder` as their basis. The path handling of the other code was not verified (to be checked file by file before stage 3) |
| `sys.path` | `rlz_dict8.py` puts the parent folder and `fret_check/` on `sys.path` and imports `units3`, `prompts3` and `common` as sibling modules. Other files presumably do the same, but this was not verified. Packaging would require fixing the imports |

## 7. Files that need care when moved

| Target | Problem |
|---|---|
| `nl2fret/.venv` (36,071 files, 1.24 GB) | Absolute paths are hard-coded (`VIRTUAL_ENV=/Users/gina/nl2semiformal/nl2fret/.venv` in `bin/activate`, and the `bin/python` symbolic links). It breaks when moved. `nl2fret_v2/.venv` is a symbolic link to it. The dependencies are the 4 lines of `requirements.txt` (torch, transformers, bert-score==0.3.12, sentence-transformers), and **the versions are not pinned** |
| `fret_check/work/`, `*/work/`, `.mock_state` | Intermediate run products (temporary work files, for example the 812 `.smv` files in `ltl_engines/pack/work`) |
| `__pycache__` | 1,476 directories (the split between inside and outside `.venv` was not counted) |
| zip files | Result zips and input zips are mixed (24 in the list above). The documents contain no rule for distinguishing inputs from outputs |
| Docker images | Local images that the code depends on: `fret-lab:latest`, `ltl-spot:local`, `cst-nusmv:local`. The images are outside the repository, so `engines/` can only hold Dockerfiles and installation notes (the Dockerfile of `ltl-spot` is in `ltl_engines/scripts/docker_spot`) |
| 20 `snapshot/` directories, `FROZEN*.sha256` | Section 5 above. The folder structure must be kept as it is to keep the hash verification working |
| Paper | `nl2semiformal/paper` and `~/NL2FRET_REFSQ_2026` (outside the repository) exist separately. Their relationship is unknown |

## 8. Secret scan (values are not printed)

The whole tree outside `.venv` was searched for API key, token and private key patterns (`sk-ant-`, `sk-`, `ghp_`, `AKIA`, `xox*-`, `*_API_KEY=value`, `BEGIN ... PRIVATE KEY`), and **no file matched.** There are no `.env` files either. `ANTHROPIC_API_KEY` is mentioned only by name in CHANGELOG files and prompt documents (no value). `~/NL2FRET_REFSQ_2026/.overleaf/settings.json` was not opened and is outside the scope of this scan (`nl2semiformal`).

## 9. Reference figures usable for verification (to be checked before moving)

| Figure | Can it be rerun? |
|---|---|
| v8 dictionary usage (DIRECT 24.6, DIRECT+D 54.4, EARS 21.5, EARS+D 54.4, MASTeR 18.6, MASTeR+D 52.2) | Reproducible with `v8_dict8/bench/tools/dict_usage.py` |
| ltlpack control experiment (NuSMV matches in total 434; of the 98 generated pairs, NuSMV 85 and Spot 83 match) | About 54 minutes if the Docker images `ltl-spot:local` and `cst-nusmv:local` exist. The selftest can run immediately |
| Selftest of each experiment | Can run immediately with `tools/selftest.py` (`SELFTEST_OK 21 rule cases`) and `cli.py --selftest` |
| Number of matches in the judge4 (z3) control experiment | Planned as **unverified** because the judge code is missing |
| Realizability | Possible with Docker `fret-lab`, but it takes time |
