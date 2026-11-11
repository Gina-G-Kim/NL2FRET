# NL2FRET Experiment Repository

A collection of experiments and tools that compare methods for converting natural-language requirements into FRETish (DIRECT, five templates, +R, +V, +D, and others) on the same items. The final tool (release 1.2.0, frozen) is in `nl2fret_tool/` and the current prompts are in `prompts/current/`. The structure and cleanup decisions are described in `STRUCTURE.md`, the file move log is in `MOVE_LOG.csv`, and the verification results and unverified items are in `UNVERIFIED.md`.

## Process

```
natural-language items (data) --> [conversion runner: Claude CLI call with a per-method prompt] --> generated FRETish
   --> [official FRET parser compile (Docker fret-lab)] --> LTL
   --> [Kind2 realizability (fret_check, Docker)]            : realizable / unrealizable / unknown / not_run
   --> [LTL judgment: bounded z3 check, NuSMV, Spot (packages/ltlpack)]
   --> [scoring, RQ analysis, reports (REPORT, RUN_RECORD, DEV_RECORD)]
```

## Final tool: `nl2fret_tool/`

Release 1.2.0 of the NL2FRET tool: 75 files, byte-identical to the unpacked release package (sha256 of the zip `430ff36588f1559180a75472f7a08b15061c330e67a84f5fa250324bbabb367e`). The code is pinned by two manifests, so it is not edited in place: a change needs a new release (see `nl2fret_tool/README.md`, Korean, and `nl2fret_tool/CHANGELOG.md`).

| Stage of the process | Where in `nl2fret_tool/` |
|---|---|
| conversion runner (one Claude CLI call per stage, prompt per method, feedback rounds) | `bench/run_pipeline.py`, `cli.py`, `prompts3.py`, `common.py`, `units3.py`; rule layer `tpl_rules.py`, `fretlint.py` |
| official FRET compile and Kind2 realizability (Docker image `fret-lab`) | `bench/fretparse.py`, `bench/fret_check/` |
| scoring and run records | `bench/score3.py`, `bench/score_lm.py`, `bench/tools/` |
| judging (alignment, Boolean abstraction, NuSMV queries, role verdicts SAME/PROOF/REFUTE/NEITHER, aggregation, code freeze check) | `judging/nl2fret_judge/`; `judging/legacy/` (judge2, judge4, judge5 as alignment candidates) |
| reference answers, signal dictionaries, example inputs | `data/` (`reference/`, `example_*`; the bench inputs are in `bench/data/`) |
| design and run procedure | `docs/DESIGN.md`, `docs/RUNBOOK.md` |
| tests (z3 engine; no NuSMV needed) | `tests/` |

`nl2fret_tool/Makefile` targets: `test`, `selfcheck`, `judge`, `aggregate`, `freeze-check`, `release`. Check that the tool is intact (no model calls, no Docker):

```bash
cd nl2fret_tool/bench && sha256sum -c FROZEN_MANIFEST.sha256        # 38 files, all OK
cd nl2fret_tool && shasum -a 256 -c JUDGE_FROZEN_MANIFEST.sha256    # 18 files, all OK
```

The prompts of this tool are stored as files in `prompts/current/` (see `prompts/INDEX.md`).

## Directories

| Location | Contents |
|---|---|
| `experiments/` | 14 experiment runs. Each folder holds the code copy of that run, its input data, results and hash manifests. Folder names and internal structure are unchanged |
| `packages/ltlpack/` | NuSMV and Spot comparison study (610 pairs), Docker wrappers, and the Dockerfile of the Spot image |
| `docs/` | Paper in progress (`docs/paper/`, excluded from git), references, the analysis-format document, and the survey notes of this cleanup (`docs/refactor_plan/`, excluded from git) |
| `data/cases/` | Input cases in three groups: `nasa_papers` (NASA reports and other papers, 183), `lockheed_martin` (49) and `fsm` (12 cases whose natural-language text occurs identically in both sources). `SOURCES.md` in each folder records where the cases were collected; `fsm/ORIGIN_MAP.csv` records their original membership |
| `nl2fret_tool/` | The final tool, release 1.2.0 (see the section above) |
| `docker/` | Build recipes of the Docker images `fret-lab` and `cst-nusmv` (see "External engines") |
| `prompts/` | `current/`: the current prompts as files (model-facing prompts, the assembled system prompts, instruction prompts). `INDEX.md` indexes the current prompts and the historical ones, whose originals are inside the experiment folders |
| `data/`, `results/` | Location indexes (`INDEX.md`). The originals are inside the experiment folders |
| `tools/` | Helper scripts: `build_cases.py`, `verify_lm_docx.py`, and `render_prompts.py` (renders `prompts/current/system_prompts/` from `nl2fret_tool/bench`) |
| `tests/` | Wrapper that runs the existing selftests and a representative metric |
| `unsorted/` | Files whose purpose could not be determined (excluded from git) |
| `testnote.md` | Current run instructions (maintained by the project owner) |

## Experiment runs

| Folder | Contents |
|---|---|
| `experiments/nl2fret` | v1 (10-repetition main run, 5-repetition copy, pilot) |
| `experiments/nl2fret_v2` | v2 (FRET unknown metric, 68 items) |
| `experiments/nl3` | v3 (rule-assembly methods, calibration, main run) |
| `experiments/nl4`, `nl5` | v4 LM smoke run and second smoke run |
| `experiments/nl6`, `nl7` | v6 LM preflight (first attempt), then rerun and main run (61 items) |
| `experiments/v7_dev0`, `v7_dev1` | v7 development set, first and second run (94 items) |
| `experiments/v8_dict8` | v8 signal-dictionary smoke run and realizability stage |
| `experiments/nusmv_paper` | NuSMV judgment in the style of Danso et al. (SecDev '26): Equiv, Sound, Compl and N/M on the 610 stored pairs of `packages/ltlpack`, comparison with the stored judge4 verdicts, and a check of the paper's author repository |
| `experiments/judge_recording` | Recording extension of the paper-style NuSMV judge (per-pair raw records: queries, SMV files, NuSMV output, atom abstraction, run header) and a regression check on 27 pairs; no measurement was made |
| `experiments/fret_template_bench`, `fret_retest_v2` | Earlier experiments (classification unknown; names preserved) |

Runs added after 2026-11-09 (the checks and patches that led to release 1.2.0 of the tool, the input conversion for the 61 items, and the 61-item main generation run) are listed in order in `experiments/000_INDEX.md`.

## How to run

The run commands of each experiment are in that folder's instruction document (`NL2FRET_*.md`) and in `scripts/` or `run_*.sh`. The code is a per-run copy, so use the code in the respective folder as it is. New runs start from the final tool: take a writable copy of `nl2fret_tool/` (or of its release zip) for the run and leave `nl2fret_tool/` itself untouched. Model calls use only the subscription login of the `claude` CLI and never an API key. The official parser and the realizability checks require the Docker image `fret-lab:latest` (see "External engines" below).

Lightweight check (no model calls, no Docker):

```bash
make selftest        # or: bash tests/run_selftests.sh
```

## External engines

This repository does not contain the engines themselves. The engines are local Docker images. Only what was verified on this machine is listed. (This section replaces the former `engines/README.md`; the folder was removed on 2026-11-11 at the request of the project owner and stays in the git history.)

| Engine | Docker image | Purpose | How it is built, or where it comes from |
|---|---|---|---|
| FRET official parser, LTL translation, Kind2 realizability (the image also holds NuSMV 2.7.1, JKind 2.2, Z3 and AE-VAL) | `fret-lab:latest` (id eb13a1115267) | Compilation and realizability for all experiments | Build recipe in `docker/fret-lab/` (Dockerfile and `fret.sh`, copied from the project `~/fret`): NASA FRET v3.1.0 and Kind2 3.0.0, all five optional tools enabled. Its README has the build command and the evidence that this recipe built the image |
| Spot 2.16.1 (`ltlfilt`) | `ltl-spot:local` (id abb8d639c12a) | ltlpack comparison study | Dockerfile: `packages/ltlpack/scripts/docker_spot/Dockerfile`; build script: `packages/ltlpack/scripts/build_spot_image.sh` |
| NuSMV 2.6.0 | `cst-nusmv:local` (id 910e958e8920) | ltlpack comparison study; the Mac check runs of `nl2fret_tool` | Build recipe in `docker/cst-nusmv/` (three-line Dockerfile; the build context is the `bin/` and `share/` folders of the official NuSMV 2.6.0 Linux tarball, which is not stored here; its README has the tarball hash and a manifest of the 175 context files) |

- Installation attempt log: `packages/ltlpack/pack/INSTALL_NOTES.md`
- Docker container wrappers: `packages/ltlpack/scripts/bin/`
- Mac-specific note: Homebrew provides no bottles for Intel Macs, so Spot was built from source inside Docker (see the notes above).

## Notes

- The `snapshot/` folders and the `FROZEN*.sha256` and `MANIFEST.sha256` files inside the experiment folders are evidence records. Moving or editing the contents of a folder breaks the hash verification (`sha256sum -c`).
- `experiments/nl2fret/.venv` (1.2 GB) is a virtual environment with hard-coded absolute paths and is not tracked.
- judge3/judge4/judge5, `sk.py` and `rq.py` were not found on this machine.
- This repository is not a git repository yet. The home directory (`~`) is already a git repository (0 tracked files), so running `git init` in this folder would nest repositories.
