# STRUCTURE: Repository Layout and Cleanup Decisions

Cleanup date: 2026-11-08. All moves were made with plain `mv`; no git commands were run (no `.git` was created, and `git init` is left to the project owner). Code logic and the contents of result files were not changed.

## 1. Layout

```
nl2semiformal/                  root (name and location unchanged)
  README.md  STRUCTURE.md  MOVE_LOG.csv  Makefile  .gitignore
  testnote.md                   run instructions maintained by the project owner, kept at the root
  docs/                         paper (in progress, excluded from git), references, analysis-format document, survey notes of this cleanup (refactor_plan, excluded from git)
  prompts/current/              the current prompts as files: model-facing prompts, assembled system prompts, instruction prompts (added 2026-11-11, see section 4c)
  prompts/INDEX.md              index of the current prompts and of the historical prompt and instruction documents (historical originals are inside the experiment folders)
  nl2fret_tool/                 the final tool, release 1.4 (113 files; release 1.2.0 is in archive/nl2fret_tool/v1.2.0/; see sections 4c and 4f)
  docker/                       build recipes of the Docker images fret-lab and cst-nusmv (added 2026-11-11, see section 4c)
  assets/  archive/  VERSIONS.md  versioned copies of the assets of the experiments, older versions after a version-up, and the version index (added 2026-11-13, see section 4d)
  data/INDEX.md                 index of the input data with hashes (originals are inside the experiment folders)
  data/cases/                   organized input cases: nasa_papers/ (183), lockheed_martin/ (49), fsm/ (12; original membership in ORIGIN_MAP.csv). Each folder has a SOURCES.md
  tools/build_cases.py          script that rebuilds data/cases from experiments/
  tools/render_prompts.py       renders prompts/current/system_prompts/ from nl2fret_tool/bench (and checks them with --check)
  results/INDEX.md              index of the result folders (originals are inside the experiment folders)
  experiments/                  14 experiment run folders (12 existing ones with names and internal structure unchanged, plus nusmv_paper and judge_recording added on 2026-11-09)
  packages/ltlpack/             NuSMV/Spot comparison study (formerly ltl_engines; includes pack/, scripts/, notes/ and others)
  tests/run_selftests.sh        wrapper that runs the existing selftests and a representative metric
  unsorted/                     files whose purpose could not be determined (excluded from git)
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
| Prompts | current: `prompts/current/`; historical: `experiments/*/NL2FRET_*.md`, `experiments/*/prompts/`, `templates/` | `prompts/INDEX.md` |
| Data | `experiments/*/data/` | `data/INDEX.md` |
| Conversion runner | final: `nl2fret_tool/bench/run_pipeline.py`, `cli.py`, `units3.py`, `prompts3.py`, `common.py`; earlier runs: `experiments/*/` | per-run copies in `experiments/` |
| FRET compile | final: `nl2fret_tool/bench/fretparse.py`, `fret_check/`; earlier runs: `experiments/*/` | requires the Docker image `fret-lab` |
| Kind2 realizability | final: `nl2fret_tool/bench/fret_check/check.py`, `fret_check/tools/fret_rlz.py`; earlier runs: `experiments/*/fret_check/check.py` | the engine is inside the Docker image |
| z3/NuSMV/Spot judgment | final judge: `nl2fret_tool/judging/nl2fret_judge/`; comparison study: `packages/ltlpack/pack/tools/ltl_engines.py` | |
| Control experiments | `packages/ltlpack/pack/data/pairs.jsonl` | |
| RQ analysis | `experiments/nl3/analyze3.py`, `nl2fret/tools_extra/`, `score3.py`, `score_lm.py`, `analysis/` in the result folders | |
| Reports | `REPORT*.md`, `FINAL_REPORT*.md`, `RUN_RECORD.md`, `DEV_RECORD.md` and `RLZ_RECORD.md` in the result folders, `docs/paper` | |
| judge3/judge4/judge5, `sk.py`, `rq.py` | **Not found on this machine** | Unknown |

## 7. Known limitations
- The Docker images (`fret-lab:latest`, `ltl-spot:local`, `cst-nusmv:local`) live outside the repository; their build recipes are in `docker/fret-lab/`, `docker/cst-nusmv/` and `packages/ltlpack/scripts/docker_spot/`. See "External engines" in `README.md` (formerly `engines/README.md`). The images were not rebuilt from these recipes, so the rebuilt images have not been compared with the existing ones.
- No `requirements.txt` was created. There is no pinned dependency list (the 4 lines of `experiments/nl2fret/requirements.txt` are mostly unpinned), and the instructions from v4 onward state that the Python commands use only the standard library (z3b in `ltl_engines` is optional).
