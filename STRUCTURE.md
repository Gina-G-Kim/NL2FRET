# STRUCTURE: Repository Layout and Cleanup Decisions

Cleanup date: 2026-11-08. All moves were made with plain `mv`; no git commands were run (no `.git` was created, and `git init` is left to the project owner). Code logic and the contents of result files were not changed.

## 1. Layout

```
nl2semiformal/                  root (name and location unchanged)
  README.md  STRUCTURE.md  MOVE_LOG.csv  Makefile  .gitignore
  testnote.md                   run instructions maintained by the project owner, kept at the root
  docs/                         paper (in progress, excluded from git), references, analysis-format document, survey notes of this cleanup (refactor_plan)
  prompts/INDEX.md              index of the prompt and instruction documents (originals are inside the experiment folders)
  data/INDEX.md                 index of the input data with hashes (originals are inside the experiment folders)
  data/cases/                   organized input cases: nasa_papers/ (183), lockheed_martin/ (49), fsm/ (12; original membership in ORIGIN_MAP.csv). Each folder has a SOURCES.md
  tools/build_cases.py          script that rebuilds data/cases from experiments/
  results/INDEX.md              index of the result folders (originals are inside the experiment folders)
  experiments/                  14 experiment run folders (12 existing ones with names and internal structure unchanged, plus nusmv_paper and judge_recording added on 2026-11-09)
  packages/ltlpack/             NuSMV/Spot comparison study (formerly ltl_engines; includes pack/, scripts/, notes/ and others)
  engines/README.md             locations of the external engines (Docker images) and installation notes
  tests/run_selftests.sh        wrapper that runs the existing selftests and a representative metric
  unsorted/                     files whose purpose could not be determined, and the list (UNSORTED.md)
```

## 2. Classification rules (none newly created)

The source document of the classification rules (`claude/NL2FRET_*.md`) is not on this machine and could not be found. No new rules were therefore created; **the existing folder names were kept as they are**. Moving a whole experiment folder keeps the relative paths inside it (`snapshot/`, `FROZEN*.sha256`, run scripts) valid. The conventions observed inside the folders are listed below; they are not confirmed rules.

| Observed convention | Evidence |
|---|---|
| One experiment run = one folder (code copy of that run, result folders, hash manifests, zips) | all of `experiments/` |
| Result folders are named `results_<stage>` (`pilot`, `smoke`, `smoke2`, `pre`, `lm`, `calib`, `dev`, `dev1`, `dict8`) | folder names |
| Preflight results (`results_pre`) are not mixed with main-run results (`results_lm`) | `nl7/NL2FRET_PROMPT_v6_LM.md` lines 22 and 265 |
| When a first attempt fails, it is redone in a new folder and the earlier folder is left untouched (`nl6`, then `nl7`) | `nl7/results_lm/RUN_RECORD.md` line 41 |
| The prompt version is part of the file name (`v1, v2, v3, v4_LM, v6_LM, v7_DEV0, v7_DEV1, v8_DICT_SMOKE`) | prompt documents |

## 3. Move results

| Before | After |
|---|---|
| `nl2fret`, `nl2fret_v2`, `nl3` to `nl7`, `v7_dev0`, `v7_dev1`, `v8_dict8`, `fret_template_bench`, `fret_retest_v2` | `experiments/<same name>` |
| `ltl_engines` | `packages/ltlpack` (whole folder) |
| `paper` | `docs/paper` |
| `source` | `docs/references` |
| `NL2FRET_v6_main_analysis_ppt_format.md` | `docs/` |
| `refactor_plan` | `docs/refactor_plan` (INVENTORY.md is the survey made before the move; PROPOSAL.md is kept for reference only because the lighter cleanup replaced it) |
| `fret_template_bench.zip` | `unsorted/` (an archive of 17 files; whether it is an input or an output is unknown) |

The full mapping is in `MOVE_LOG.csv` (per folder, with file counts before and after). When checked right after the move, there were 41,118 files before the move and 41,119 after (one more file, `MOVE_LOG.csv`), and the file counts matched for every folder. Index and documentation files were added later.

## 4. Decisions (made without asking)

| Decision | Reason |
|---|---|
| `prompts/`, `data/` and `results/` hold **indexes only**; the originals are not moved | The originals are tied to the `snapshot/` folders, the `FROZEN*.sha256` files and the relative paths of the scripts in the experiment folders; moving them would break hash verification and reruns |
| No `src/nl2fret` was created | The code is a copied snapshot per run and the copies differ (8 variants of `run_pipeline.py`, 8 of `prompts3.py`). Merging them into one version could not guarantee that earlier figures remain reproducible, so they were not merged. Use the code in each folder as it is |
| `testnote.md` stays at the root | The project owner updates it there and places new input zips at the root |
| No `data/reference/` was created | The documents do not say which files hold the reference FRETish data, and the instructions tell the executor not to look for reference data |
| `fret_template_bench` and `fret_retest_v2` were kept under `experiments/` with their names | Their classification is unknown, so no new classification was invented and the names were preserved |
| `nl2fret/.venv` stays at `experiments/nl2fret/.venv`, and only the paths in `bin/` were fixed | See section 5 |
| The external material `~/NL2FRET_REFSQ_2026` (Overleaf copy) is outside the repository and was not moved | Its relationship to `docs/paper` is unknown |

## 4b. Later changes (2026-11-08)
- `testnote.md` and `experiments/` were added to `.gitignore` (project owner's request). Later the same day `docs/paper/` (the paper in progress) was added as well; it stays on disk but is not tracked. As a result, git does not track the results and code inside the experiment folders, so the input cases were organized separately in the tracked `data/cases/`.
- `data/cases/` and `tools/build_cases.py` were added. The input cases form three groups (`nasa_papers` 183, `lockheed_martin` 49, `fsm` 12); the pre-split total 195 + 61 - overlap 12 = 244 equals the post-split total.
- Language (2026-11-08): the code-level and project-level text of the tracked files is written in professional English: code comments and docstrings, the output labels of the helper scripts, and the project documentation (README, INDEX, SOURCES, STRUCTURE, UNVERIFIED and similar files). Korean was kept where it is essential: the experiment records and instruction documents (`experiments/`, which is frozen evidence and excluded from git, and `testnote.md`), the content documents written by the project owner (`docs/NL2FRET_v6_main_analysis_ppt_format.md`, the analysis report) and the received package README (`packages/ltlpack/pack/README_MAC.md` and its copy `packages/ltlpack/docs/README_MAC.md`), and data values copied from the source datasets (for example the `verified` notes in `nasa_papers/legacy_fretish_inputs.jsonl`).
- Provenance research (2026-11-08): `tools/verify_lm_docx.py` (comparison with the original Lockheed Martin docx files; no network access) and its result `data/cases/lockheed_martin/docx_match.csv` were added, and the `SOURCES.md` of each group now contains an NTRS verification table, the repository history, and license notices.
- NuSMV paper-style test (2026-11-09): the project owner updated `testnote.md` with a new instruction that was written without knowledge of this repository's structure. Where the instruction conflicted with the repository rules, the rules were followed and every deviation is listed in the run report (`experiments/nusmv_paper/bench/nusmv_paper/REPORT.md`, section 7). The run folder follows the layout of the earlier runs (`bench/`, `docs/`, `notes/`, `scripts/`, `logs/`, `zips/`): the instruction text is kept as `docs/NL2FRET_NUSMV_PAPER.md`, the working folder named in the instruction (`nusmv_paper/`) is `bench/nusmv_paper/`, and the delivery zip is `zips/nusmv_paper.zip`. No git command was used: the instruction's `git clone` was replaced by an HTTP download of the author repository, and the third-party code (GPL-3.0) is kept out of the delivery zip.
- Judge recording extension (2026-11-09): a second instruction written without knowledge of this repository asked for raw-data recording in the paper-style NuSMV judge and a regression check, without any measurement. The run folder `experiments/judge_recording/` follows the same layout (`bench/judge_recording/` is the working folder named in the instruction, `docs/NL2FRET_JUDGE_RECORDING.md` is the instruction copy, the delivery zip is `zips/judge_recording.zip`). Existing files of earlier runs were not modified; the code was copied into the new folder and the copies were compared by sha256. The deviations from the instruction are listed in `experiments/judge_recording/bench/judge_recording/RECORDING_CHANGES.md`, last section. For this run, additions were made to README.md, STRUCTURE.md, prompts/INDEX.md, results/INDEX.md and UNVERIFIED.md (existing entries changed only in counts and in the `testnote.md` hash).

## 5. Path repairs (no logic changes)

| Target | Change |
|---|---|
| `experiments/nl3/results_nl3/analysis/posthoc_sensitivity.py` | The two hard-coded occurrences of `/Users/gina/nl2semiformal/nl3` were replaced by paths based on the script location (`__file__`), and one `import os` line was added. The script was not run (it overwrites a result `.md` file) |
| `experiments/nl2fret/.venv/bin/*` (28 files: activation scripts and the shebang lines of console scripts) | The old absolute path `.../nl2fret/.venv` was replaced by the new one. `pip --version` and `python -c "import torch, transformers"` were checked. The `command =` line of `pyvenv.cfg` is a creation record and was left as it is |
| `experiments/nl2fret_v2/.venv` | The symbolic link `../nl2fret/.venv` remains valid at the same relative location |
| `../nl6/results_pre` in `experiments/nl7/make_run_record.py` and others | Both folders are under `experiments/`, so the relative path remains valid |
| `/home/claude/...` | 0 occurrences in file contents |
| `/Users/gina/...` in run records (CHANGELOG, logs, reports) | Original records; not modified |
| `/tmp` in `run_mock6.sh` | Temporary path for the mock test; left as it is |

## 6. Component classification (one line each)

| Component | Location | Notes |
|---|---|---|
| Prompts | `experiments/*/NL2FRET_*.md`, `experiments/*/prompts/`, `templates/` | `prompts/INDEX.md` |
| Data | `experiments/*/data/` | `data/INDEX.md` |
| Conversion runner | `experiments/*/run_pipeline.py`, `cli.py`, `units3.py`, `prompts3.py`, `common.py` | per-run copies |
| FRET compile | `experiments/*/fretparse.py`, `fret_check/` | requires the Docker image `fret-lab` |
| Kind2 realizability | `experiments/*/fret_check/check.py`, `tools/fret_rlz.py` | the engine is inside the Docker image |
| z3/NuSMV/Spot judgment | `packages/ltlpack/pack/tools/ltl_engines.py` | |
| Control experiments | `packages/ltlpack/pack/data/pairs.jsonl` | |
| RQ analysis | `experiments/nl3/analyze3.py`, `nl2fret/tools_extra/`, `score3.py`, `score_lm.py`, `analysis/` in the result folders | |
| Reports | `REPORT*.md`, `FINAL_REPORT*.md`, `RUN_RECORD.md`, `DEV_RECORD.md` and `RLZ_RECORD.md` in the result folders, `docs/paper` | |
| judge3/judge4/judge5, `sk.py`, `rq.py` | **Not found on this machine** | Unknown |

## 7. Known limitations
- The Docker images (`fret-lab:latest`, `ltl-spot:local`, `cst-nusmv:local`) live outside the repository. See `engines/README.md`.
- No `requirements.txt` was created. There is no pinned dependency list (the 4 lines of `experiments/nl2fret/requirements.txt` are mostly unpinned), and the instructions from v4 onward state that the Python commands use only the standard library (z3b in `ltl_engines` is optional).
