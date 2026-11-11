# NL2FRET Experiment Repository

A collection of experiments and tools that compare methods for converting natural-language requirements into FRETish (DIRECT, five templates, +R, +V, +D, and others) on the same items. The structure and cleanup decisions are described in `STRUCTURE.md`, the file move log is in `MOVE_LOG.csv`, and the verification results and unverified items are in `UNVERIFIED.md`.

## Process

```
natural-language items (data) --> [conversion runner: Claude CLI call with a per-method prompt] --> generated FRETish
   --> [official FRET parser compile (Docker fret-lab)] --> LTL
   --> [Kind2 realizability (fret_check, Docker)]            : realizable / unrealizable / unknown / not_run
   --> [LTL judgment: bounded z3 check, NuSMV, Spot (packages/ltlpack)]
   --> [scoring, RQ analysis, reports (REPORT, RUN_RECORD, DEV_RECORD)]
```

## Directories

| Location | Contents |
|---|---|
| `experiments/` | 14 experiment runs. Each folder holds the code copy of that run, its input data, results and hash manifests. Folder names and internal structure are unchanged |
| `packages/ltlpack/` | NuSMV and Spot comparison study (610 pairs), Docker wrappers, and the Dockerfile of the Spot image |
| `docs/` | Paper in progress (`docs/paper/`, excluded from git), references, the analysis-format document, and the survey notes of this cleanup |
| `data/cases/` | Input cases in three groups: `nasa_papers` (NASA reports and other papers, 183), `lockheed_martin` (49) and `fsm` (12 cases whose natural-language text occurs identically in both sources). `SOURCES.md` in each folder records where the cases were collected; `fsm/ORIGIN_MAP.csv` records their original membership |
| `prompts/`, `data/`, `results/` | Location indexes (`INDEX.md`). The originals are inside the experiment folders |
| `engines/` | Locations of the external engines (Docker images) and installation notes |
| `tests/` | Wrapper that runs the existing selftests and a representative metric |
| `unsorted/` | Files whose purpose could not be determined |
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

## How to run

The run commands of each experiment are in that folder's instruction document (`NL2FRET_*.md`) and in `scripts/` or `run_*.sh`. The code is a per-run copy, so use the code in the respective folder as it is. Model calls use only the subscription login of the `claude` CLI and never an API key. The official parser and the realizability checks require the Docker image `fret-lab:latest` (see `engines/README.md`).

Lightweight check (no model calls, no Docker):

```bash
make selftest        # or: bash tests/run_selftests.sh
```

## Notes

- The `snapshot/` folders and the `FROZEN*.sha256` and `MANIFEST.sha256` files inside the experiment folders are evidence records. Moving or editing the contents of a folder breaks the hash verification (`sha256sum -c`).
- `experiments/nl2fret/.venv` (1.2 GB) is a virtual environment with hard-coded absolute paths and is not tracked.
- judge3/judge4/judge5, `sk.py` and `rq.py` were not found on this machine.
- This repository is not a git repository yet. The home directory (`~`) is already a git repository (0 tracked files), so running `git init` in this folder would nest repositories.
