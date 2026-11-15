#!/usr/bin/env bash
# v1.4 retest = the same 11 approaches (DIRECT, 5 x +G, 5 x +R2) as v1.3, prompt version changed. No approach is added.
# Usage: bash exp/fsm/run_intent.sh STEP SET VER [RUN_DIR]
# STEP: lint | dryrun | gen | inputs | judge | trace | controls | analyze | compare | all   (controls: judge on pairs with known answers; analyze: strict success, decision points, causes; compare: BASE=<analysis dir of the other version>)
# SET : fsm (13 items x 3 reps = 429 units) | confirm (48 non-FSM items x 1 rep = 528 units)
# VER : v13 = prompts of v1.3 (no flags; fsm already exists as runs/fsm_20261113, needed only for confirm)
#       v14 = --g-parity --intent-decl --tm-source-only --sourced-rules-only (see docs/V14_INTENT_TEST.md)
# env: STAGEA_FROM (gen: reuse stage A rows of an earlier run folder, e.g. runs/fsm_20261113/gen), FRETDOCS, PAPERRAW (lint), MODEL (sonnet), PARSER (docker), NUSMV, ENGINE (nusmv)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STEP="${1:-dryrun}"; SET="${2:?SET fsm|confirm}"; VER="${3:?VER v13|v14}"
RUN="${4:-$ROOT/runs/intent_${SET}_${VER}_$(date +%Y%m%d)}"
MODEL="${MODEL:-sonnet}"; PARSER="${PARSER:-docker}"; NUSMV="${NUSMV:-NuSMV}"; ENGINE="${ENGINE:-nusmv}"
case "$SET" in fsm) DATA="$ROOT/bench/data/lm_items_fsm.jsonl"; REPS=3;; confirm) DATA="$ROOT/bench/data/lm_items_nonfsm.jsonl"; REPS=1;; *) echo "bad SET"; exit 2;; esac
ARMS=(DIRECT MASTeR+G EARS+G Adv-EARS+G SPIDER+G Boilerplate+G MASTeR+R2 EARS+R2 Adv-EARS+R2 SPIDER+R2 Boilerplate+R2)
case "$VER" in v13) EXTRA=();; v14) EXTRA=(--g-parity --intent-decl --tm-source-only --sourced-rules-only);; *) echo "bad VER"; exit 2;; esac
mkdir -p "$RUN"
SA=(); [ -n "${STAGEA_FROM:-}" ] && SA=(--stage-a-from "$STAGEA_FROM")
gen() { (cd "$ROOT/bench" && python3 run_pipeline.py --data "$DATA" --results "$RUN/gen" --arms "${ARMS[@]}" --reps "$REPS" --dict-all --parser "$PARSER" --model "$MODEL" ${EXTRA[@]+"${EXTRA[@]}"} ${SA[@]+"${SA[@]}"} "$@"); }
case "$STEP" in
  lint)   (cd "$ROOT/bench" && python3 tools/prompt_lint.py --fret-docs "${FRETDOCS:?set FRETDOCS}" --paper-raw "${PAPERRAW:?set PAPERRAW (pdftotext -raw of the paper 'The Ten Lockheed Martin Cyber-Physical Challenges...' or docs/paper_passage_AP003c.txt)}" --out "$RUN/prompt_lint.json") ;;
  dryrun) gen --dry-run ;;
  gen)    gen ;;
  inputs) (cd "$ROOT/bench" && python3 tools/make_judge_inputs.py --results "$RUN/gen" --data "$DATA" --out "$RUN/inputs" --parser "$PARSER" --reps "$REPS") ;;
  judge)  (cd "$ROOT/judging" && python3 -m nl2fret_judge selfcheck --engine "$ENGINE" --nusmv "$NUSMV" --out "$RUN/judge_selfcheck" &&
           python3 -m nl2fret_judge judge-parts --engine "$ENGINE" --nusmv "$NUSMV" --out "$RUN/judge" --units "$RUN/inputs/units.json" --ltl "$RUN/inputs/fret_ltl_gen.jsonl" \
             --reference "$ROOT/data/reference/lm_reference_with_ltl.jsonl" --dictionary "$ROOT/data/dictionary/lm_dictionary.csv" --mode anchor --cap "${CAP:-512}") ;;
  trace)  (cd "$ROOT/bench" && python3 tools/trace_report.py --run "$RUN") ;;
  controls) (cd "$ROOT/bench" && python3 tools/judge_controls.py --engine "$ENGINE" --nusmv "$NUSMV" --cap "${CAP:-512}" --out "${CTRLDIR:-$ROOT/runs/judge_controls_$ENGINE}") ;;
  analyze) (cd "$ROOT/bench" && python3 tools/analyze_run.py --run "$RUN" --controls "${CTRLDIR:-$ROOT/runs/judge_controls_$ENGINE}" --engine "$ENGINE" --nusmv "$NUSMV") ;;
  compare) (cd "$ROOT/bench" && python3 tools/compare_runs.py --base "${BASE:?set BASE=<analysis dir of the base version>}" --new "$RUN/analysis" --out "$RUN/comparison") ;;
  all)    for s in lint dryrun gen inputs judge trace analyze; do bash "$0" "$s" "$SET" "$VER" "$RUN"; done ;;
  *) echo "unknown step $STEP"; exit 2 ;;
esac
echo "step $STEP done: $RUN"
