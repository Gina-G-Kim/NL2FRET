#!/usr/bin/env bash
# FSM test, one command per step. Usage: bash scripts/run_fsm.sh STEP [RUN_DIR]
# STEP: lint | dryrun | gen | inputs | judge | trace | all
# env: FRETDOCS (directory fret-electron/docs/_media/user-interface/examples of the FRET repo, commit cf0f913; needed by step lint), SUP=1 (v1.4 supplement test), MODEL (default sonnet), REPS (default 3), PARSER (docker), NUSMV (NuSMV command), ENGINE (nusmv), ONLY (optional item ids)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"          # the interpreter of the environment where the package is installed (pip install -e ".[test]")
STEP="${1:-dryrun}"
RUN="${2:-$ROOT/runs/fsm_$(date +%Y%m%d)}"
MODEL="${MODEL:-sonnet}"; REPS="${REPS:-3}"; PARSER="${PARSER:-docker}"; NUSMV="${NUSMV:-NuSMV}"; ENGINE="${ENGINE:-nusmv}"
ARMS=(DIRECT MASTeR+G EARS+G Adv-EARS+G SPIDER+G Boilerplate+G MASTeR+R2 EARS+R2 Adv-EARS+R2 SPIDER+R2 Boilerplate+R2)
EXTRA=()
# SUP=1: v1.4 test. Official FRET semantics supplement (+ dictionary rule D-5) for Direct and the free (+G) arms only. Rule assembly arms do not read the guide and are not rerun.
if [ "${SUP:-0}" = "1" ]; then ARMS=(DIRECT MASTeR+G EARS+G Adv-EARS+G SPIDER+G Boilerplate+G); EXTRA=(--guide-sup --g-parity); RUN="${2:-$ROOT/runs/fsm_sup_$(date +%Y%m%d)}"; fi
DATA="$ROOT/src/nl2fret/data/lm_items_fsm.jsonl"
mkdir -p "$RUN"
gen()    { (cd "$ROOT" && $PY -m nl2fret.run_pipeline --data "$DATA" --results "$RUN/gen" --arms "${ARMS[@]}" --reps "$REPS" --dict-all --parser "$PARSER" --model "$MODEL" ${EXTRA[@]+"${EXTRA[@]}"} "$@"); }
case "$STEP" in
  lint)   (cd "$ROOT" && $PY -m nl2fret.tools.prompt_lint --fret-docs "${FRETDOCS:?set FRETDOCS to the FRET docs directory}" --out "$RUN/prompt_lint.json") ;;
  dryrun) gen --dry-run ;;
  gen)    gen ;;
  inputs) (cd "$ROOT" && $PY -m nl2fret.tools.make_judge_inputs --results "$RUN/gen" --data "$DATA" --out "$RUN/inputs" --parser "$PARSER" --reps "$REPS") ;;
  judge)  (cd "$ROOT" && $PY -m nl2fret_judge selfcheck --engine "$ENGINE" --nusmv "$NUSMV" --out "$RUN/judge_selfcheck" &&
           $PY -m nl2fret_judge judge-parts --engine "$ENGINE" --nusmv "$NUSMV" --out "$RUN/judge" --units "$RUN/inputs/units.json" --ltl "$RUN/inputs/fret_ltl_gen.jsonl" \
             --reference "$ROOT/data/reference/lm_reference_with_ltl.jsonl" --dictionary "$ROOT/data/dictionary/lm_dictionary.csv" --mode anchor) ;;
  trace)  (cd "$ROOT" && $PY -m nl2fret.tools.trace_report --run "$RUN") ;;
  all)    for s in lint dryrun gen inputs judge trace; do bash "$0" "$s" "$RUN"; done ;;
  *) echo "unknown step $STEP"; exit 2 ;;
esac
echo "step $STEP done: $RUN"
