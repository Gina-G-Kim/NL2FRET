# NL2FRET Experiment Repository

A research workspace around one tool, NL2FRET (release 2.0). The research question: safe software needs a formal specification (LTL), but writing LTL needs expert domain knowledge; FRET turns FRETish into LTL, but writing good FRETish is manual. This work checks whether going through a template (a semi-formal intermediate form) lets an LLM write FRETish whose LTL means the same as (SAME) or implies (PROOF) the LTL of the expert (NASA) FRETish. The core comparison is the template route against Direct. The full statement, the roles of the reference and the dictionary, and the decisions are at the top of `nl2fret_tool/docs/V20_BATCH_DESIGN.md`.

## Layout

The project root holds the research workspace only. Everything that belongs to the tool is inside the tool folder.

```
nl2semiformal/
  README.md  STRUCTURE.md  testnote.md
  nl2fret_tool/    the tool, a PyPA project (pyproject.toml, src/ layout, tests/), release 2.0, with everything that belongs to it:
    src/             packages nl2fret (generation pipeline), nl2fret_judge (judging), legacy (alignment candidates of the judge)
    tests/  scripts/ tests; run scripts (run_batch.sh ...) and maintenance scripts (render_prompts.py, build_cases.py, ...)
    prompts/         the current prompts as files and their index
    data/            research data: dataset, dictionary, reference answers, audit, input cases (cases/), index of input data
    assets/          versioned copies of the assets of the experiments (assets/<asset>/v<N>/); VERSIONS.md is the version index
    archive/         older releases (releases/), removed features, old documents, files whose purpose is unknown
    external/docker/ build recipes of the Docker images for the external programs FRET and NuSMV
    docs/            tool documents: RUNBOOK, DESIGN, V20_BATCH_DESIGN (pre-registration), TOOL_PROCESS_GUIDE, ...
    runs/            run output (not tracked)
  experiments/     one folder per experiment or study (NNN_slug; ltlpack = the NuSMV and Spot comparison study), with 000_INDEX.md and RESULTS_INDEX.md
  docs/            project documents: paper in progress (excluded from git), references, analysis-format document, records/ (MOVE_LOG.csv, UNVERIFIED.md)
```

`testnote.md` is the current run instruction maintained by the project owner and is not edited here. `STRUCTURE.md` explains where each kind of file lives (current layout in section 1, history of the changes in the later sections). `nl2fret_tool/VERSIONS.md` lists every versioned asset.

## The tool: `nl2fret_tool/`

Read `nl2fret_tool/README.md` first. In short:

```bash
cd nl2fret_tool
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[test]"
make test            # 64 tests, no model calls, no Docker
make build           # sdist and wheel into dist/
ONLY=06_EB REPS=1 NUSMV=/path/to/NuSMV bash scripts/run_batch.sh all runs/batch_06EB      # a batch run (needs the claude CLI, the Docker image fret-lab and NuSMV 2.6.0)
```

The code of the tool is fixed by a git release tag (`v2.0`). The prompts are stored as files in `nl2fret_tool/prompts/current/` and are rendered from the code by `scripts/render_prompts.py` (`--check` compares without writing). Releases 1.4 and 1.2.0 are in `nl2fret_tool/archive/releases/`.

New experiments (028 and later) get their own folder `experiments/NNN_slug/` (next number in `experiments/000_INDEX.md`). The folder holds only what the experiment needs as input in `inputs/` (the data, the test package placed in the main directory, and a copy of `testnote.md`); the tool is always the one in `nl2fret_tool/`, never a copy. The tool writes its output to its designated place (`nl2fret_tool/runs/<experiment>/`); at the end a copy of the results goes into `results/` of the experiment folder (with `REPORT.md`, `notes/`, `logs/` as needed) and a zip for the project owner into `zips/`. Experiments 001 to 027 stay as they are; the code copies in them are records.

## Experiment runs

`experiments/000_INDEX.md` lists all experiment folders in numbered order. `experiments/RESULTS_INDEX.md` indexes the result folders. Earlier runs:

| Folder | Contents |
|---|---|
| `experiments/nl2fret` | v1 (10-repetition main run, 5-repetition copy, pilot) |
| `experiments/nl2fret_v2` | v2 (FRET unknown metric, 68 items) |
| `experiments/nl3` | v3 (rule-assembly methods, calibration, main run) |
| `experiments/nl4`, `nl5` | v4 LM smoke run and second smoke run |
| `experiments/nl6`, `nl7` | v6 LM preflight (first attempt), then rerun and main run (61 items) |
| `experiments/v7_dev0`, `v7_dev1` | v7 development set, first and second run (94 items) |
| `experiments/v8_dict8` | v8 signal-dictionary smoke run and realizability stage |
| `experiments/nusmv_paper` | NuSMV judgment in the style of Danso et al. (SecDev '26) on the 610 stored pairs of `experiments/ltlpack` |
| `experiments/judge_recording` | recording extension of the paper-style NuSMV judge and a regression check on 27 pairs |
| `experiments/fret_template_bench`, `fret_retest_v2` | earlier experiments (classification unknown; names preserved) |
| `experiments/025_tool_v20_install`, `026_pypa_restructure`, `027_workspace_layout` | installation and tidy-up of release 2.0; the PyPA restructure; the move of everything that belongs to the tool into the tool folder |

## External engines

The engines themselves are not in this repository; they are local Docker images. Only what was verified on this machine is listed.

| Engine | Docker image | Purpose | Build recipe or source |
|---|---|---|---|
| FRET official parser, LTL translation, Kind2 realizability (the image also holds NuSMV 2.7.1, JKind 2.2, Z3 and AE-VAL) | `fret-lab:latest` | compilation and realizability | `nl2fret_tool/external/docker/fret-lab/` (NASA FRET v3.1.0 and Kind2 3.0.0, all five optional tools enabled) |
| Spot 2.16.1 (`ltlfilt`) | `ltl-spot:local` | ltlpack comparison study | `experiments/ltlpack/scripts/docker_spot/Dockerfile`, `experiments/ltlpack/scripts/build_spot_image.sh` |
| NuSMV 2.6.0 | `cst-nusmv:local` | ltlpack study; judging runs of the tool | `nl2fret_tool/external/docker/cst-nusmv/` (the build context is the `bin/` and `share/` folders of the official NuSMV 2.6.0 Linux tarball, which is not stored here) |

- Installation attempt log: `experiments/ltlpack/pack/INSTALL_NOTES.md`; container wrappers: `experiments/ltlpack/scripts/bin/`.
- Homebrew provides no bottles for Intel Macs, so Spot was built from source inside Docker.

## Notes

- The `snapshot/` folders and the `FROZEN*.sha256` and `MANIFEST.sha256` files inside the experiment folders are evidence records of those experiments. Moving or editing the contents of a folder breaks their hash verification (`sha256sum -c`).
- `experiments/nl2fret/.venv` (1.2 GB) is a virtual environment with hard-coded absolute paths and is not tracked.
- judge3, `sk.py` and `rq.py` were not found on this machine.
- `MOVE_LOG.csv` and `UNVERIFIED.md` are in `docs/records/`.
