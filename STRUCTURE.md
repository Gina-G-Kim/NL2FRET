# STRUCTURE: Repository Layout and Cleanup Decisions

Cleanup date: 2026-11-08. All moves were made with plain `mv`; no git commands were run (no `.git` was created, and `git init` is left to the project owner). Code logic and the contents of result files were not changed.

## 1. Layout

Current layout (since 2026-11-17, sections 4i and 4j). Earlier layouts are described in the sections 4 to 4h.

```
nl2semiformal/                  root: the research workspace only
  README.md  STRUCTURE.md
  testnote.md                   run instructions maintained by the project owner, kept at the root
  nl2fret_tool/                 the tool (a PyPA project) and everything that belongs to it
    pyproject.toml  VERSION  VERSIONS.md  Makefile  README.md  .gitignore
    src/                        nl2fret (generation pipeline), nl2fret_judge (judging), legacy (alignment candidates of the judge)
    tests/  scripts/            tests; run scripts and maintenance scripts (render_prompts.py, build_cases.py, verify_lm_docx.py, run_selftests.sh)
    prompts/                    current/: the current prompts as files; INDEX.md
    data/                       dataset/, dictionary/, reference/, audit/, cases/ (organized input cases), INDEX.md
    assets/  archive/           versioned copies of the assets; older releases (archive/releases/), removed features, old documents (version index: VERSIONS.md)
    external/docker/            build recipes of the Docker images fret-lab and cst-nusmv (external programs)
    docs/                       RUNBOOK, DESIGN, V20_BATCH_DESIGN, TOOL_PROCESS_GUIDE and others
    runs/                       run output (not tracked)
  experiments/                  one folder per experiment (000_INDEX.md numbers them and carries the folder rule of section 4k, RESULTS_INDEX.md indexes the result folders)
  docs/                         project documents: the analysis-format document, references/, paper/ (excluded from git), refactor_plan/ (excluded from git), records/ (MOVE_LOG.csv, UNVERIFIED.md)
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

## 4c. Later changes (2026-11-11): final tool and current prompts moved into tracked folders

At the request of the project owner, the final tool and the current prompts are now files in the repository instead of locations inside the git-excluded `experiments/`. This supersedes two rows of the decision table in section 4 ("`prompts/`, `data/` and `results/` hold indexes only" for the prompts, and "No `src/nl2fret` was created" for the final tool). Those decisions were made on 2026-11-08 without asking; the target structure of the cleanup instruction listed `prompts/` and `src/nl2fret/` or `scripts/`.

| Change | Detail |
|---|---|
| `nl2fret_tool/` added | The unpacked release 1.2.0 of the tool (`nl2fret_tool_v1.2.zip`, sha256 `430ff36588f1559180a75472f7a08b15061c330e67a84f5fa250324bbabb367e`, 75 files). The package layout is kept as released (`bench/`, `judging/`, `data/`, `docs/`, `tests/`, `Makefile`, manifests), because both manifests (`bench/FROZEN_MANIFEST.sha256`, 38 files, sha256 `176b144fe280158e05a4ec4a5aa9c7e912fab067b8e989ccacd12a2f2f16e571`; `JUDGE_FROZEN_MANIFEST.sha256`, 18 files, sha256 `1fda2c1982c14c7ae7363c8c5ced72c11d0019afe9804a5693a35cae15aa154b`) and the relative paths of the code depend on it. A flat `src/nl2fret/` was not built: moving files out of the package layout would change the pinned paths and break both manifest checks. Checked after the copy: `diff -r` against a fresh unpacking of the zip shows no difference, 38 of 38 and 18 of 18 manifest entries are OK, no file of the tool is matched by the root or by the package `.gitignore` |
| `prompts/current/` added | `fretish_guide.md` and `templates/` (copies from `nl2fret_tool/bench`), `system_prompts/` (the 21 assembled system prompts of the 19 methods of the 61-item main run, rendered by `tools/render_prompts.py` from the project copy of the tool; the 18 prompts of run A are byte-identical to the `snapshot/` of the main run), `instructions/` (eight instruction prompts: v8, tool freeze, 61-item inputs, 61-item main run, main judging, comparability test, dictionary judging run, FSM test of tool v1.3; the fifth and the sixth were added on 2026-11-12, the seventh and the eighth on 2026-11-13) and `SHA256SUMS` |
| `prompts/INDEX.md` | Section 1 indexes the current prompts, section 2 is the earlier location table (95 entries) plus the 5 instruction documents of 2026-11-10 and 2026-11-11 |
| `README.md`, `data/INDEX.md` | New section and rows for the tool and the current prompts; `data/INDEX.md` notes that the tool carries the answer key in `nl2fret_tool/data/reference/` |
| `.gitignore` | `docs/refactor_plan/` and `unsorted/` added at the project owner's request (the entries `docs/paper/`, `experiments/`, `testnote.md` and `UNVERIFIED.md` were already there). The folders stay on disk. A `.gitignore` entry has no effect on files that git already tracks: by reading the git index and the last commit (without running git), `docs/paper/` (18 files in the last commit, pushed to `origin/main`) and `docs/refactor_plan/` (2 files) are tracked, `unsorted/` is not. They leave the tracking only after `git rm -r --cached docs/paper docs/refactor_plan` and a commit, which the project owner runs; earlier commits keep them |
| `docker/` added | At the request of the project owner, replacing the "origin unknown" notes. `docker/fret-lab/`: Dockerfile, `fret.sh`, `.dockerignore` and `LICENSE` copied from the project `~/fret`; the Dockerfile was matched instruction by instruction with `docker history` of `fret-lab:latest`, and `fret.sh` is the exact file taken from the image (the working copy in `~/fret` is newer). `docker/cst-nusmv/`: the three-line Dockerfile of the experiment `cst_test` (round 3, E10) and a manifest of the 175 files of its build context (the official NuSMV 2.6.0 binaries, not stored here); the context was checked against the original (175 of 175 OK). Details and commands are in the README of each folder |
| `engines/` removed | At the request of the project owner. The folder held one file, `engines/README.md` (a table of the three Docker images and their origin); its content moved unchanged into the section "External engines" of `README.md`. The earlier file stays in the git history |
| Not changed | `experiments/` (including the per-run code copies and the running 61-item generation run), `MOVE_LOG.csv` (nothing was moved; the additions are copies), `UNVERIFIED.md`, the root `Makefile` |

Not in `nl2fret_tool/`: the RQ analysis scripts of the earlier runs (for example `experiments/nl3/analyze3.py`, `experiments/nl2fret/tools_extra/`) and the NuSMV and Spot comparison study (`packages/ltlpack/`, which was already outside `experiments/`). They are not part of release 1.2.0.

## 4d. Later changes (2026-11-13): asset registry, version index and process document

The dictionary judging run (`experiments/022_dict_judge_run/`) came with an instruction to register the assets of the experiments as versions in the main directory and to write a process document for newcomers. The instruction was written without knowledge of this repository; where it conflicted with the repository rules, the rules were followed and every deviation is listed in the run report (`experiments/022_dict_judge_run/REPORT.md`).

| Change | Detail |
|---|---|
| `assets/` added | 16 assets with 84 files, stored as copies in `assets/<asset>/v1/` with one `SHA256SUMS` per asset (every copy was compared with its source by sha256): signal dictionary and its rules, dictionary and alias scripts, alias certificates, pre-registration documents, template guides, system prompts, user prompt builders, FRETish guide, signal dictionary of the +D methods, variable policy, examples, reference data, judge inputs (original, and dictionary and alias applied), experiment scripts |
| `archive/` added | holds older versions as `archive/<asset>/v<N>/` after a version-up |
| `VERSIONS.md` added | the version-up rule (first line) and one row per asset: current version, path, sha256, reason of the change, experiment that caused it |
| `docs/PROCESS_LIFECYCLE.md` added | the whole process from the natural-language requirement to the judging tables, as a table and one block per stage with input, process, output and evidence paths |
| `prompts/` | the instruction of the run was added to `prompts/current/instructions/` and to `prompts/INDEX.md` (104 entries), and `prompts/current/SHA256SUMS` was extended |
| Not changed | `nl2fret_tool/` (frozen), `experiments/`, the sources of the copies |

## 4e. Later changes (2026-11-14): FSM test of the tool package v1.3

The package `nl2fret_tool_v1.3.zip` (sha256 `9b54c38d5daee934cf4898c8574ae8b5702e055c181d3373e605990d89ffdd74`) came with an instruction written without knowledge of this repository (`NL2FRET_PROMPT_FSM_RUN_v1.md`). Where it left a point open or conflicted with the repository rules, the rules were followed and every deviation is listed in the run report (`experiments/023_fsm_run_v13/REPORT_FSM.md`).

| Change | Detail |
|---|---|
| `experiments/023_fsm_run_v13/` added | the FSM test: 13 `01_FSM` items, 11 arms, 3 repetitions (429 units), generation, FRET compile, NuSMV part-level judging with counterexample records and a per-unit trace; the package is unpacked read-only in `bench/pristine/nl2fret_tool_v1.3/` and run from a work copy |
| `assets/` extended | `dataset`, `dictionary`, `reference` (v1, 8 files, `SHA256SUMS` per asset) from the package `data/` folder; the registry now has 19 assets; the instruction's "current version K" does not exist under these names, so they start at v1 and nothing was moved to `archive/` |
| `VERSIONS.md` | three rows added (reason as given by the instruction, experiment `023_fsm_run_v13`) |
| `prompts/` | the instruction was added to `prompts/current/instructions/`, to `prompts/INDEX.md` (105 entries) and to `prompts/current/SHA256SUMS` |
| Not changed | `nl2fret_tool/` (release 1.2.0, frozen). The judging module of the v1.3 package is of the v1.0.0 line and carries none of the v1.1 and v1.2 changes (report section 7.1) |

## 4f. Later changes (2026-11-15): the final tool is updated to release 1.4

At the request of the project owner the main directory always holds the latest version of the tool; the experiments run that tool and are not the place where the current tool lives. The package `nl2fret_v1.4_FSM_retest_package.zip` (sha256 `af896dde6673a6bb0f41807a2a67de63b3711ae3d2d76fa3fa44e72da1b2e93e`) had been run only from `experiments/024_fsm_v14_retest/`, so the main directory was brought up to date.

| Change | Detail |
|---|---|
| `nl2fret_tool/` replaced | release 1.4, 113 files, byte-identical to the unpacked package (the five `.pytest_cache` files of the zip are left out); `make test`: 29 passed, `make freeze-check`: 55 files OK |
| `archive/nl2fret_tool/v1.2.0/` added | the previous release 1.2.0 moved as it was (75 files; both manifests were checked before and after the move: 38 and 18 files OK). The judging module of release 1.4 is of the v1.0.0 line with the v1.3 features (part-level judging, dictionary alignment, counterexample records); the v1.1 and v1.2 changes of release 1.2.0 (`freeze.py`, `JUDGE_FROZEN_MANIFEST.sha256`, handling of an empty candidate list, recording of a partial last line) are in the archived release |
| `prompts/current/system_prompts/` | the 17 prompts of release 1.4 (11 approaches), byte-identical to `gen/snapshot/` of the v1.4 FSM test; the 21 prompts of the 61-item main run stay in `assets/llm_system_prompts/v1/` (checked byte-identical before they were replaced) |
| `tools/render_prompts.py` | sets the switches of release 1.4 like `run_pipeline.main()`, handles the fallback prompts (`BF`), default arms are the 11 approaches; `--run-info` compares the prompt hashes of a run |
| `prompts/INDEX.md`, `prompts/current/SHA256SUMS`, `README.md`, `VERSIONS.md`, `archive/README.md` | updated for release 1.4 |
| `docs/TOOL_PROCESS_GUIDE.md` added | process-by-process description of release 1.4 with one worked example; all paths are relative to the main directory |
| Not changed | `assets/` (the data assets `dataset`, `dictionary` and `reference` v1 are byte-identical to `nl2fret_tool/data/`), `docs/PROCESS_LIFECYCLE.md` (its `nl2fret_tool/` paths describe the layout of release 1.2.0, now in `archive/nl2fret_tool/v1.2.0/`), `experiments/` (each experiment keeps its own copy of the package) |

## 4g. Later changes (2026-11-16): the final tool is updated to release 2.0

The package `nl2fret_tool_v1.6.zip` (sha256 `b5fc55e257951d117cbb77bef949b8394242e0dee863c68cbde8475591e5b185`) was installed as release 2.0 (instruction `testnote.md`, work in `experiments/025_tool_v20_install/`). The main directory holds the installed tool; the experiment folder holds the unpacked original, the work copy and the checks.

| Change | Detail |
|---|---|
| `nl2fret_tool/` replaced | release 2.0, 191 files: the unpacked package plus the edits listed in `experiments/025_tool_v20_install/notes/CHANGES.md`; `bench/FROZEN_MANIFEST.sha256` regenerated (74 entries, the shipped file list, 4 changed entries); `python3 -m pytest tests -q`: 50 passed; the judging folder is byte-identical to release 1.4 (v1.0.0 line, no freeze files) |
| `archive/nl2fret_tool/v1.4/` added | the previous release 1.4 moved as it was (113 files) |
| `prompts/current/` | `fretish_guide.md` and the five `templates/` now hold the release 2.0 documents (`bench/prompts/fretish_reference.md`, `bench/templates_v15/`), `sources_v15.json` added, `system_prompts/` holds the 17 prompts of the 11 approaches (hashes equal those of the shipped smoke run), `SHA256SUMS` recomputed (34 files) |
| `tools/render_prompts.py` | sets the switches of release 2.0 like `batch_pipeline.main()` (adds `--fret-reference`, `--intent-decl` off) |
| `prompts/INDEX.md`, `README.md`, `VERSIONS.md`, `archive/README.md`, `STRUCTURE.md` | updated for release 2.0 |
| `docs/TOOL_PROCESS_GUIDE.md` rewritten | process-by-process description of release 2.0 with one worked example from a real run (challenge `06_EB`, item `LM-06_EB-N1`); built from the tool files by `experiments/025_tool_v20_install/scripts/guide/build_guide_v20.py` and checked by `verify_guide_v20.py` (59 checks) |
| `assets/dictionary/v2/` added | dictionary v2 = v1 plus the columns `alias_of` and `alias_evidence` (9 alias pairs with an original text evidence in the NASA requirement EB-001; 33 candidate pairs without evidence are unknown); `build_alias_v2.py`, `alias_evidence.json`; v1 moved to `archive/dictionary/v1/`; `nl2fret_tool/data/dictionary/lm_dictionary.csv` is the v2 file; the dictionary text that the model sees (`bench/data/sigdict.json`) is unchanged | (superseded on 2026-11-17, see 4h: v2 moved to the extension overlay, v1 is current again)
| Measurement rules | `docs/V20_BATCH_DESIGN.md` section 7 (N-LIT and the primary and secondary rule for Realizability), implemented in `bench/fret_check/tools/litnorm.py`, `bench/fret_check/group_rlz.py`, `bench/fret_check/check.py` (the J+def and alias parts of the first version of this row were withdrawn on 2026-11-17, see 4h) |
| Not changed | `docs/PROCESS_LIFECYCLE.md` (describes release 1.2.0), `assets/` other than the dictionary, `experiments/` |

## 4h. Later changes (2026-11-17): the tool is tidied up to the original design

| Item | Change |
|---|---|
| `docs/V20_BATCH_DESIGN.md` | research question at the top, roles of reference and dictionary, decisions (strict judgment primary, agent definition, known limits), section 8 (extension modules), section 9 (withdrawn) |
| `archive/removed_features/` added | J+def (`make_def_inputs.py`, functions of `litnorm.py`, `judgedef` step, `rt_effect_strict.json` split), their tests and the withdrawn design sections; `README.md` there gives reason and restore method |
| `nl2fret_tool/bench/ext/` added | extension hook (`__init__.py`) and the extension `dictionary` (`README.md`, `attach.py`, `judge_input.py`, `build.py`, `versions/v1/`, `overlays/v2/`); flag `--ext` in `run_pipeline.py` and `batch_pipeline.py`, variable `EXT` (default `dictionary`) in `exp/fsm/run_batch.sh` |
| `assets/dictionary/v1/` | current again (moved back from `archive/dictionary/v1/`); the v2 files moved to the extension overlay; `nl2fret_tool/data/dictionary/lm_dictionary.csv` is the v1 file again (sha256 cf3752af...) |
| Not changed | the 17 system prompts (with the extension on), `judging/` (19 code files), input data, `bench/data/sigdict.json` |

## 4i. Later changes (2026-11-17): PyPA structure (experiment `experiments/026_pypa_restructure/`, plan and gates in its `notes/PLAN.md`)

Basis: the Python Packaging User Guide (pyproject.toml with `[build-system]` and `[project]`, src layout, tests outside the package, package data declared, `python -m build`). The request was to restructure by PyPA rules and not only to move directories.

| Item | Change |
|---|---|
| `nl2fret_tool/pyproject.toml` added | setuptools build, project name `nl2fret`, version from `VERSION`, dependency `z3-solver`, extra `test`, scripts `nl2fret-batch`, `nl2fret-run`, `nl2fret-judge`, package data, pytest settings |
| `nl2fret_tool/bench/` -> `src/nl2fret/` | the folder was renamed as a whole, so its inner structure (`data/`, `prompts/`, `templates*/`, `tools/`, `fret_check/`, `ext/`) is unchanged. The flat imports (`import common`) became package imports (124 import lines) and 46 `sys.path.insert` helper lines were removed; `paths.py` (PACKAGE, PROJECT) replaces path computations that reached above the old `bench/` folder. 27 Python files changed, 249 changed lines; all changed lines are imports, path computations, usage lines of docstrings and blank lines (the list is in `experiments/026_pypa_restructure/notes/BYTE_CHANGES.md`). 59 manifest files are byte-identical (the 29 others are the 27 Python files and two non-code files: the dictionary extension README and its version record) |
| `nl2fret_tool/judging/nl2fret_judge/`, `judging/legacy/` -> `src/nl2fret_judge/`, `src/legacy/` | moved only, all 19 code files byte-identical (`align.py` finds `legacy` next to the package folder, so the siblings stay siblings) |
| `nl2fret_tool/exp/fsm/*.sh` -> `scripts/` | the three scripts call `python -m nl2fret...` through the variable `PYTHON` |
| `nl2fret_tool/tests/` | `sys.path` helper lines removed; the tests import the installed package |
| `nl2fret_tool/Makefile`, `README.md`, `docs/RUNBOOK.md`, `docs/DESIGN.md` | rewritten for release 2.0 (originals in `archive/nl2fret_tool_docs/v1.4/`, together with `EXPERIMENT_FSM.md`, `controls_nusmv512/`, `old_prompts/`, `NL2FRET_PROMPT_FSM_V14_MAC.md` and `requirements.txt`); `ANALYSIS_PLAN.md`, `V14_GUIDE_SUPPLEMENT.md`, `V14_INTENT_TEST.md` stay in `docs/` because code or scripts of release 2.0 cite them |
| `src/nl2fret/FROZEN_MANIFEST.sha256` | regenerated at the new path (93 entries; the former 88-entry list is kept in `experiments/026_pypa_restructure/notes/FROZEN_MANIFEST_before_pypa.sha256`) |
| root files | `MOVE_LOG.csv` and `UNVERIFIED.md` -> `docs/records/`; `results/INDEX.md` -> `experiments/RESULTS_INDEX.md`; `unsorted/` -> `archive/unsorted/`; `tests/run_selftests.sh` -> `tools/run_selftests.sh`; `docs/PROCESS_LIFECYCLE.md` -> `archive/process_lifecycle_doc/v1/`; `.gitignore` entries follow the new paths |
| `tools/render_prompts.py` | imports the installed package instead of adding `bench/` to the path |
| `docs/TOOL_PROCESS_GUIDE.md` | rebuilt with the new paths |
| Not changed | the 17 system prompts, `src/nl2fret_judge/` and `src/legacy/` code, the input data, `sigdict.json`, dictionary v1, `experiments/` (other folders) and `archive/` contents, `packages/ltlpack/`, `docker/`, `testnote.md` |

## 4j. Later changes (2026-11-17): everything that belongs to the tool moves into the tool folder (experiment `experiments/027_workspace_layout/`, plan in its `notes/PLAN.md`)

Request of the project owner: the root `tools/` duplicated `nl2fret_tool/`, and prompts, packages, assets and data belong inside the tool folder; the Docker folder holds external programs and does not belong at the root. All moves were made with plain `mv` (file counts before and after are in the experiment notes); no files were deleted.

| Before (root) | After (inside `nl2fret_tool/`) |
|---|---|
| `tools/` (render_prompts.py, build_cases.py, verify_lm_docx.py, run_selftests.sh) | `scripts/` (next to the run scripts; the path constants of the scripts were adapted) |
| `prompts/` | `prompts/` |
| `assets/`, `VERSIONS.md` | `assets/`, `VERSIONS.md` |
| `archive/` (`archive/nl2fret_tool/` renamed to `archive/releases/`) | `archive/` |
| `data/` (INDEX.md, cases/) | merged into `data/` (the former empty `data/cases/` was replaced) |
| `packages/ltlpack/` | `studies/ltlpack/` |
| `docker/` | `external/docker/` |
| `docs/TOOL_PROCESS_GUIDE.md` | `docs/TOOL_PROCESS_GUIDE.md` |
| `Makefile` (root; text kept in the experiment notes) | the target `selftest` of the tool `Makefile` |

Hash list removed at the same time (request: remove what is not needed): `src/nl2fret/FROZEN_MANIFEST.sha256`, `make freeze-check`, its `package-data` entry and the sha256 column of `VERSIONS.md` (moved to `archive/removed_features/`, reason and restore method in its README); the code is fixed by a git release tag. Kept: run snapshots, judge headers, the parser fingerprint, `render_prompts.py --check`, the `SHA256SUMS` files inside the asset folders.
Documents inside the tool folder name paths relative to the tool folder; `.gitignore`: the tool patterns `runs/` and `inputs/` are anchored to the tool root (the unanchored `inputs/` would have hidden `studies/ltlpack/inputs/`), the entry of `archive/unsorted/` follows the move. Not changed: `experiments/` (the historical documents of the experiment folders keep the old paths), `testnote.md`, the history sections of this file.

## 4k. Later changes (2026-11-17): experiment folder rule

Instruction of the project owner: `experiments/` organizes, per experiment, only the data the experiment needs, the test package that the owner placed in the main directory, and a copy of `testnote.md`; the tool is the one in `nl2fret_tool/`. Answers to the follow-up questions: the rule applies from the new experiments on (028 and later; 001 to 027 stay as records), and the results are produced by the tool at its designated place (`nl2fret_tool/runs/`), then copied by the assistant into the experiment folder and zipped for the owner.

| Item | Rule for 028 and later |
|---|---|
| `experiments/NNN_slug/inputs/` | data, the test package zip, `testnote.md` copy |
| `experiments/NNN_slug/results/` | copy of the run output taken from `nl2fret_tool/runs/`; `REPORT.md`, `notes/` (pre-registration, change record) and `logs/` next to it when needed |
| `experiments/NNN_slug/zips/` | the zip given to the owner |
| tool code | never copied into an experiment folder; the run uses `nl2fret_tool/` |
| `experiments/000_INDEX.md` | carries the rule at its head and numbers the folders |

## 4l. Later changes (2026-11-17): tool documents consolidated, SHA files moved (experiment 027)

Request of the project owner: keep only the latest documents in `nl2fret_tool/docs/` and move the old ones to the archive; merge when there are too many; and since the hash features were removed, clean up the SHA files as well.

| Item | Change |
|---|---|
| `nl2fret_tool/docs/` now | `DESIGN.md`, `RUNBOOK.md`, `V20_BATCH_DESIGN.md` (normative pre-registration), `TOOL_PROCESS_GUIDE.md`. The README of the tool is the entry document |
| moved to `archive/nl2fret_tool_docs/v1.4/docs/` | `ANALYSIS_PLAN.md`, `V14_GUIDE_SUPPLEMENT.md`, `V14_INTENT_TEST.md` (specifications of the release 1.4 tests; the docstrings of `analyze_run.py`, `compare_runs.py`, `prompt_lint.py` and the comments of `run_intent.sh` now name the archive path), `DATA_VERSIONING.md` (the version-up rule is at the head of `VERSIONS.md`), `TRACE_FORMAT.md` (describes the `gen/ inputs/ judge/` layout of release 1.4 runs, which the batch layout of release 2.0 does not use) |
| moved | `docs/paper_passage_AP003c.txt` -> `data/paper_passage_AP003c.txt` (a data text read by the lint, not a document); `src/nl2fret/NL2FRET_PROMPT_v8_DICT_SMOKE.md` -> `archive/nl2fret_tool_docs/v1.4/package/` (a v8 instruction prompt inside the package; a copy is in `prompts/current/instructions/`) |
| SHA files | the 22 `SHA256SUMS` files of the tool (19 asset folders, `prompts/current/`, `ext/dictionary/versions/v1/`, `ext/dictionary/overlays/v2/`) -> `archive/removed_features/sha_files/` with the same relative paths; `build.py` of the dictionary extension no longer reads or writes them and `EVIDENCE.json` lost its generator hash. Kept on purpose: the hash files inside the archived releases (snapshots), `external/docker/cst-nusmv/nusmv_context.sha256` (integrity check of a downloaded third-party binary context), the records of `studies/ltlpack/`, `prompts/current/system_prompts/MANIFEST.csv` (a table of the rendered prompts; its sha256 column is not a check) and the hashing inside the code (prompt hashes of the run snapshots, parser fingerprint) |
| `docs/TOOL_PROCESS_GUIDE.md` | rebuilt (verification 66 checks) |

## 4m. Later changes (2026-11-17): prompt text with the paper rules (experiment 028)

Package `prompts_paper_rules_final.zip` of the project owner (instruction `MAC_INSTRUCTION.md`, `CHANGES.md`); plan, byte comparison and report in `experiments/028_prompt_paper_rules/`.

| Item | Change |
|---|---|
| `nl2fret_tool/src/nl2fret/common.py` | wording G1 to G4 in the v1.5 constants and assembly; the assembled system prompts equal the 12 files of the package byte for byte |
| `nl2fret_tool/prompts/current/system_prompts/` | 12 files (the 5 BF files, byte identical to the B files, are no longer kept); the 17 earlier files are in `archive/prompts/system_prompts_before_paper_rules/` |
| run snapshot | no BF prompt files; hash stays in `run_info.json` |
| `nl2fret_tool/prompts/current/instructions/` | moved to `archive/instructions/` (records of instructions to the executor, not model-facing prompts) |
| `src/nl2fret/prompts/sources_v15.json` | replaced by the package file (entry `task_rules` added) |
| `docs/V20_BATCH_DESIGN.md` | section 10 (dated) |
| the uploaded zip | moved from the root to `experiments/028_prompt_paper_rules/inputs/` (experiment folder rule) |

## 4n. Later changes (2026-11-17): the comparison study leaves the tool folder

Question of the project owner: why are `studies/` and `tests/` in the tool folder, and should they not be in `experiments/`, `archive/` or `docs/`? Answer: `tests/` is the pytest suite of the package (PyPA keeps tests next to the package, outside `src/`) and stays. `studies/ltlpack/` is a research study with its own data, logs and results (NuSMV and Spot comparison on 610 pairs); no code of the tool imports it (only `scripts/run_selftests.sh` runs its selftest), so under the experiment folder rule it belongs to `experiments/`.

| Before | After |
|---|---|
| `nl2fret_tool/studies/ltlpack/` (851 files) | `experiments/ltlpack/` (same files; `nl2fret_tool/studies/` removed) |

`experiments/` is excluded from git (`.gitignore`, decision of 2026-11-08), so the study would have left git tracking with the move. To keep it tracked the `.gitignore` entry `experiments/` became `experiments/*` with the exceptions `!experiments/ltlpack/`, `!experiments/000_INDEX.md` and `!experiments/RESULTS_INDEX.md` (a file cannot be re-included while its parent folder is ignored, so the pattern had to change from the folder to its entries). The paths in the documents and in `scripts/run_selftests.sh` were updated; the historical documents of other experiment folders that name `packages/ltlpack` or `studies/ltlpack` were not changed. The Docker recipes of the external programs stay in `nl2fret_tool/external/docker/` (the Spot recipe is inside the study: `experiments/ltlpack/scripts/docker_spot/`).

## 4o. Later changes (2026-11-17): prompt text, paper rules version 2 (experiment 029)

Package `prompts_paper_rules_final_v2.zip` of the project owner (supersedes the first package of experiment 028); plan, byte comparison and report in `experiments/029_prompt_paper_rules_v2/`.

| Item | Change |
|---|---|
| `nl2fret_tool/src/nl2fret/common.py`, `prompts3.py` | G4 (notation block after the template specification), G5 (`NOTATION_FRETISH_V15` after the FRETish guide in B, D and S2), G6 (`_writing_first`: section order of the guide inside the prompt); the assembled prompts equal the 12 files of the package byte for byte |
| `nl2fret_tool/prompts/current/system_prompts/`, `MANIFEST.csv`, `sources_v15.json` | replaced by version 2; the 12 files of version 1 are in `archive/prompts/system_prompts_paper_rules_v1/` |
| `tests/test_v15_reference.py` | one expectation changed: the prompt must hold every section of the guide verbatim and "Writing requirements" before the grammar (the old test required the whole guide in file order, which G6 changes on purpose) |
| `docs/V20_BATCH_DESIGN.md` section 10, `prompts/INDEX.md`, `docs/TOOL_PROCESS_GUIDE.md` | updated |
| the uploaded zip | moved from the root to `experiments/029_prompt_paper_rules_v2/inputs/` |

## 4p. Later changes (2026-11-17): keyword check step KC (experiment 030)

Package `kc_stage_package.zip` of the project owner (`KC_STAGE_SPEC.md`, `MAC_KC_INSTRUCTION.md`, five reference documents); plan, report and verification in `experiments/030_kc_stage/`.

| Item | Change |
|---|---|
| `nl2fret_tool/src/nl2fret/kc_stage.py` (new), `prompts/kc/KC_*.md` (new, 5 files) | the step: groups from the fields of the FRET parser output, message, adoption rule, unit state, variant chain; reference documents are copies of lines of the FRETish guide |
| `batch_pipeline.py`, `run_pipeline.py` (snapshot), `tools/make_judge_inputs.py`, `tools/rt_effect.py`, `tools/prompt_v15_lint.py`, `scripts/run_batch.sh` | phase KC between the feedback and RT1 (`--no-kc`, `NO_KC=1`); RT1 starts from the adopted kc answer; variants v0, vf, kc, rt; keyword distribution table; `kc_doc_sha` in `run_info.json`; V-STYLE list extended (KC and the paper-rule constants) |
| `prompts/sources_v15.json` (two copies) | entry `keyword_reference` |
| `tests/test_v20_kc.py`, `tests/data/kc_parser_fields.json` (new) | 18 unit tests |
| `docs/V20_BATCH_DESIGN.md` (sections 2, 3, 11), `docs/RUNBOOK.md`, `docs/TOOL_PROCESS_GUIDE.md`, `prompts/INDEX.md` | updated |
| the uploaded zip | moved from the root to `experiments/030_kc_stage/inputs/` |

## 4q. Later changes (2026-11-17/18): FSM retest, paper rules v2 against release 2.0 (experiment 031)

Package `fsm_retest_package.zip` of the project owner (`MAC_FSM_RETEST_INSTRUCTION.md`, prompt files); plan, report, tables and logs in `experiments/031_fsm_retest_paper2/`. No change to `nl2fret_tool/`.

| Item | Content |
|---|---|
| runs | two paired runs of 01_FSM (13 items, 11 arms, 3 repetitions, 429 units each): A = code before the PyPA restructure with release 2.0 prompts (backup zip of experiment 026), B = current code with paper rules v2 prompts, `--no-kc`; both ran in scratch copies (deleted afterwards) because the group step writes into `fret_check/work/` |
| results | `experiments/031_fsm_retest_paper2/results/runs/fsm_rel20_20261117`, `fsm_paper2_20261117`; seven tables in `results/analysis/tables/`; `REPORT.md`; `zips/fsm_retest_results.zip` |

## 4r. Later changes (2026-11-18): FSM diagnostic and tool fix (experiment 032)

Package `fsm_diag_pack.zip` of the project owner (instruction, pre-registration, `und17.csv`); plan, report, tables, patches and logs in `experiments/032_fsm_diag/`. No model call.

| Item | Change |
|---|---|
| `nl2fret_tool/src/nl2fret/batch_pipeline.py` | stage S schema retry (`SCHEMA_RETRIES = 2`, `schema_retry`, `schema_retry_note`); rows that need no retry are byte-identical to the earlier version (checked by replay of the stored replies of experiment 031) |
| `nl2fret_tool/src/nl2fret/tools/retry_counts.py` (new), `tests/test_v20_schema_retry.py` (new) | per-approach retry counts; 9 tests (pytest 82 -> 91 passed) |
| `docs/V20_BATCH_DESIGN.md`, `docs/RUNBOOK.md`, `docs/TOOL_PROCESS_GUIDE.md` | stage S schema retry described (the guide was edited in place; its generator in experiment 025 is a record and was not changed) |
| not applied (proposals) | `experiments/032_fsm_diag/proposals/`: D1 unknown names, D2 signal coverage, D3 slot condition kept, D4 unique message ids, T1 prompt set argument |
| the uploaded zip | moved from the root to `experiments/032_fsm_diag/inputs/` |

## 4s. Later changes (2026-11-18): FSM pack 2 (experiment 033)

Package `fsm_pack2.zip` of the project owner (instruction, decisions); plan, report, check tables and logs in `experiments/033_fsm_pack2/`. No model call.

| Item | Change |
|---|---|
| `nl2fret_tool/src/nl2fret/batch_pipeline.py`, `kc_stage.py` | unique message ids when one batch message holds the same item id several times (`<item id>@<approach>`; D4 of experiment 032); no change when ids are not repeated (142 stored batches replayed byte-identical) |
| `src/nl2fret/prompts3.py` (`ARMS_FSM5`), `batch_pipeline.py` (`--arms` default), `scripts/run_batch.sh` (`ARMS`) | default arm set of the batch run = DIRECT, Adv-EARS+G, Boilerplate+G, MASTeR+G, SPIDER+G (195 units); EARS and +R2 stay in the code and are selected with `--arms` |
| `nl2fret_tool/prompts/current/kc/` (new, 8 files + MANIFEST), `scripts/render_prompts.py`, `prompts/INDEX.md` | prompts of the keyword check step KC stored as files and checked together with the system prompts |
| `src/nl2fret/tools/readable_report.py` (new), `scripts/run_batch.sh` (step `readable`), `tests/test_v20_readable.py` (new) | human-readable result files (Korean outline Markdown per item, INDEX.md, results_flat.csv) in `$RUN/readable/`; copied into `experiments/<NNN>/results/` |
| `experiments/031_fsm_retest_paper2/results/readable/` (new) | first use of the readable report on the two runs of experiment 031 |
| `docs/V20_BATCH_DESIGN.md` (section 12), `docs/RUNBOOK.md`, `docs/TOOL_PROCESS_GUIDE.md` | updated |
| the uploaded zip | moved from the root to `experiments/033_fsm_pack2/inputs/` |

## 4t. Later changes (2026-11-18): FSM pack 3 investigation (experiment 034)

Package `fsm_pack3.zip` of the project owner; report, tables, FRET inputs and CLI outputs in `experiments/034_fsm_pack3/`. Investigation only: no change in `nl2fret_tool/`, no model call (docker `fret-lab` only). The uploaded zip was moved from the root to `experiments/034_fsm_pack3/inputs/`.

## 4u. Later changes (2026-11-18): FSM pack 4, dataset exclusions (experiment 035)

Package `fsm_pack4.zip`; report, tables, CLI outputs and change record in `experiments/035_fsm_pack4/`. Tool: `data/dataset_exclusions.json` (new, FSM N03, N05, N07, N09, N11), `src/nl2fret/tools/apply_exclusions.py` (new), `scripts/run_batch.sh` (uses filtered copies in `$RUN/filtered/`), `tests/test_v20_exclusions.py` (new), docs; the original data files are not changed. The uploaded zip was moved from the root to `experiments/035_fsm_pack4/inputs/`.

## 4v. Later changes (2026-11-19): FSM pack 6, variable table of the group stage and FSM rerun (experiment 037)

Package `fsm_pack6.zip`; report, tables, change record, CLI records and the copy of the rerun results in `experiments/037_fsm_pack6/`. Tool: `src/nl2fret/fret_check/tools/fretexpr.py` (`analyze` classifies further expression fields), `src/nl2fret/fret_check/tools/fret_rlz.py` (`sentence_info` passes `scope_mode` and `stop_condition`), `tests/test_v20_rlz_variable_table.py` and `tests/data/rlz_sem_fields.json` (new), `docs/V20_BATCH_DESIGN.md` (section 14), `docs/TOOL_PROCESS_GUIDE.md` (one sentence in P12). The run folder of the FSM rerun (120 units) is `nl2fret_tool/runs/fsm_pack6_20261119/`. The uploaded zip was moved from the root to `experiments/037_fsm_pack6/inputs/`.

## 4w. Later changes (2026-11-19): FSM pack 7, confound audit (experiment 038)

Package `fsm_pack7.zip`; report, tables (md and csv), scripts, Kind2 inputs and outputs of the 600 s re-run and the group queries without N13 in `experiments/038_fsm_pack7/`. Observation only: no change of the tool, prompts, dataset, exclusion list, dictionary or judge, no model call. New files only under `experiments/038_fsm_pack7/` (`scripts/`, `analysis/`, `notes/`, `logs/`, `zips/fsm_pack7_results.zip`).

## 4x. Later changes (2026-11-19): FSM pack 8, intent declaration on (experiment 039)

Package `fsm_pack8.zip`; report, tables (md and csv), scripts, the A/B checks of the declaration paragraph and a run summary in `experiments/039_fsm_pack8/`. New run folder `nl2fret_tool/runs/fsm_pack8_20261119/` (8 items x 5 approaches x 3 repetitions = 120 units, only `intent_decl` differs from the pack 6 run; `--intent-decl` was appended by the wrapper `experiments/039_fsm_pack8/scripts/py_intent.sh`, no change of the tool, `run_batch.sh`, prompts, dataset, exclusion list, dictionary or judge). Model calls: 73 batch calls of the run and one isolation probe call. `experiments/000_INDEX.md` has a row 039.

## 4y. Later changes (2026-11-19): FSM pack 9 step 1, read-only code check (experiment 040)

Package `fsm_pack9.zip`; report, tables (md and csv), code quotes and the report generator in `experiments/040_fsm_pack9_step1/`. Read only: no change of the tool, prompts, dictionary, judge, parser, dataset, exclusion list or settings, no model call, no new run folder. New files only under `experiments/040_fsm_pack9_step1/` and the row 040 of `experiments/000_INDEX.md`.

## 4z. Later changes (2026-11-19): FSM pack 9 step 2, structure-preserving edits M1, M2, M3 (experiment 041)

Package `fsm_pack9_mod.zip`; report, tables, rendered messages (before and after), code quotes, the diff against the saved originals and the scripts in `experiments/041_fsm_pack9_mod1/`. No model call, no new run folder. Tool changes (10 files, listed in REPORT.md section 0): stage A dictionary (`common.user_prompt_A`, `prompts3.build_system_A3`, `batch_pipeline.phase_A`, `run_pipeline.sd_of_a`, new `src/nl2fret/prompts/stage_a_dict_rules.txt`), term correspondences (`ext/dictionary/attach.py` `term_block` and `prompt_text`, new `data/dictionary/term_correspondence/01_FSM.md`), KC COND note (`kc_stage.cond_note`, new `src/nl2fret/prompts/kc/KC_COND_authors_note.md`), new test file `tests/test_v20_mod1.py`. `prompts/current/` was not re-rendered (`render_prompts.py --check` lists 6 files).

## 4aa. Later changes (2026-11-20): FSM pack 10, 120-unit rerun with the stage A dictionary rules only (experiment 043)

Package `fsm_pack10_run.zip` (first version and rev2 kept in `experiments/043_fsm_pack10_run/inputs/`; rev2 followed). Report, tables, results, quoted prompts and scripts in `experiments/043_fsm_pack10_run/`; run folder `nl2fret_tool/runs/fsm_pack10_m1only`. Tool tree changes: `KC_COND_authors_note.md` and `data/dictionary/term_correspondence/01_FSM.md` moved to `experiments/043_fsm_pack10_run/work/removed/` (not deleted, not restored); `prompts/current/system_prompts/` stage A files re-rendered (6 files differ in content). No code, prompt source, dictionary, judge, parser, dataset or exclusion list change. `experiments/042_fsm_pack9_run/` holds the pack 9 step 3 input only (never run).

## 4ab. Later changes (2026-11-20): FSM pack 11, 120-unit rerun with the term correspondence row `mode | activeMode` (experiment 044)

Package `fsm_pack11_run.zip` (first upload and second upload kept in `experiments/044_fsm_pack11_run/inputs/`; the second, without the git start condition and with the baseline ledger, was followed). Report, tables, results, quoted prompts and scripts in `experiments/044_fsm_pack11_run/`; run folder `nl2fret_tool/runs/fsm_pack11_termrow`; baseline ledger `nl2fret_tool/runs/baseline_pack11/BASELINE_LEDGER.md` (ignored path). Tool tree change: one new file `nl2fret_tool/data/dictionary/term_correspondence/01_FSM.md` (184 bytes, sha256 `c62ef2ee...a456`, copied from the package); `prompts/current/` re-rendered with identical content. The KC authors quote file stays outside the tool tree. No git command was run; the commit is the user's.

## 4ac. Later changes (2026-11-20): FSM pack 12, 120-unit rerun with NL substitution outside the tool (experiment 045)

Package `fsm_pack12_run.zip` (in `experiments/045_fsm_pack12_run/inputs/`). Report, tables, results, substituted dataset copy (`work/dataset_substituted/items.jsonl`), substitution log, quoted prompts and scripts in `experiments/045_fsm_pack12_run/`; run folder `nl2fret_tool/runs/fsm_pack12_nlsubst`; baseline ledger `nl2fret_tool/runs/baseline_pack12/BASELINE_LEDGER.md` (ignored path). Tool tree change: `data/dictionary/term_correspondence/01_FSM.md` moved to `experiments/045_fsm_pack12_run/work/removed/term_correspondence_01_FSM_pack11.md` (the folder is empty). The dataset path of the run points to the substituted copy through the `PYTHON` hook (`scripts/py_subst.sh`), which rewrites the value of the existing `--data` option; tool code unchanged. No git command was run; the commit is the user's (suggested branch `pack12-nlsubst`).

## 4ad. Later changes (2026-11-20): result tables of a run for people (experiment 046)

Package `readable_tables_pkg.zip` (first upload stopped at step 0.1, second upload implemented; both in `experiments/046_readable_tables/inputs/`). New `nl2fret_tool/scripts/make_readable_tables.py` (reads the stored results of a run folder, writes `results_tables_<challenge>.xlsx` + 7 CSV files per challenge, default `<run>/readable/tables/<challenge>/`), one call line in the `readable` step of `scripts/run_batch.sh` (a failure only writes `<run>/readable/tables_failed.txt`), test `tests/test_readable_tables.py`, `openpyxl` added to `pyproject.toml` dependencies and installed in the tool venv (3.1.5 + et_xmlfile 2.0.0). Report, checks (`check_pack12/`, `check_pack11/`), comparison tables and zip in `experiments/046_readable_tables/`; ledger `nl2fret_tool/runs/baseline_readable_tables/BASELINE_LEDGER.md`

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
| Prompts | current: `nl2fret_tool/prompts/current/`; historical: `experiments/*/NL2FRET_*.md`, `experiments/*/prompts/`, `templates/` | `nl2fret_tool/prompts/INDEX.md` |
| Data | `experiments/*/data/` | `nl2fret_tool/data/INDEX.md` |
| Conversion runner | final: `nl2fret_tool/src/nl2fret/batch_pipeline.py`, `run_pipeline.py`, `cli.py`, `units3.py`, `prompts3.py`, `common.py`; earlier runs: `experiments/*/` | per-run copies in `experiments/` |
| FRET compile | final: `nl2fret_tool/src/nl2fret/fretparse.py`, `fret_check/`; earlier runs: `experiments/*/` | requires the Docker image `fret-lab` |
| Kind2 realizability | final: `nl2fret_tool/src/nl2fret/fret_check/check.py`, `group_rlz.py`, `fret_check/tools/fret_rlz.py`; earlier runs: `experiments/*/fret_check/check.py` | the engine is inside the Docker image |
| z3/NuSMV/Spot judgment | final judge: `nl2fret_tool/src/nl2fret_judge/`; comparison study: `experiments/ltlpack/pack/tools/ltl_engines.py` | |
| Control experiments | `experiments/ltlpack/pack/data/pairs.jsonl` | |
| RQ analysis | `experiments/nl3/analyze3.py`, `nl2fret/tools_extra/`, `score3.py`, `score_lm.py`, `analysis/` in the result folders | |
| Reports | `REPORT*.md`, `FINAL_REPORT*.md`, `RUN_RECORD.md`, `DEV_RECORD.md` and `RLZ_RECORD.md` in the result folders, `docs/paper` | |
| judge3/judge4/judge5, `sk.py`, `rq.py` | **Not found on this machine** | Unknown |

## 7. Known limitations
- The Docker images (`fret-lab:latest`, `ltl-spot:local`, `cst-nusmv:local`) live outside the repository; their build recipes are in `nl2fret_tool/external/docker/fret-lab/`, `nl2fret_tool/external/docker/cst-nusmv/` and `experiments/ltlpack/scripts/docker_spot/`. See "External engines" in `README.md` (formerly `engines/README.md`). The images were not rebuilt from these recipes, so the rebuilt images have not been compared with the existing ones.
- No `requirements.txt` was created. There is no pinned dependency list (the 4 lines of `experiments/nl2fret/requirements.txt` are mostly unpinned), and the instructions from v4 onward state that the Python commands use only the standard library (z3b in `ltl_engines` is optional). Since 2026-11-17 the tool declares its dependencies in `nl2fret_tool/pyproject.toml` (`z3-solver`, extra `test` with `pytest`; both unpinned).
