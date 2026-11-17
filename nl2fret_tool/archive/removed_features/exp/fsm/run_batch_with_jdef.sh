#!/usr/bin/env bash
# v2.0 batch run (agent per approach and challenge). Usage: bash exp/fsm/run_batch.sh STEP [RUN_DIR]
# STEP: pin | gen | inputs | judge | judgedef | group | effect | all   (judgedef = judge variant J+def, docs/V20_BATCH_DESIGN.md 7.2; judge = strict)
# env: MODEL (sonnet), REPS (3), PARSER (docker), NUSMV, ENGINE (nusmv), ONLY (challenge ids, optional), ENVPASS (names of environment variables the agent process may inherit, optional), CLI_EXTRA
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
STEP="${1:-pin}"
RUN="${2:-$ROOT/runs/batch_$(date +%Y%m%d)}"
MODEL="${MODEL:-sonnet}"; REPS="${REPS:-3}"; PARSER="${PARSER:-docker}"; NUSMV="${NUSMV:-NuSMV}"; ENGINE="${ENGINE:-nusmv}"
DATA="$ROOT/bench/data/lm_items.jsonl"
ONLYARG=(); if [ -n "${ONLY:-}" ]; then ONLYARG=(--only-challenge $ONLY); fi
ENVARG=(); if [ -n "${ENVPASS:-}" ]; then ENVARG=(--env-pass $ENVPASS); fi
mkdir -p "$RUN"
case "$STEP" in
  pin)    # first time on a computer: WRITEPIN=1 stores the fingerprint; later runs compare against it
          (cd "$ROOT/bench" && python3 -I fret_check/parser_fingerprint.py --backend "$PARSER" ${WRITEPIN:+--write-pin} --check --dump "$RUN/parser_fingerprint.json") ;;
  gen)    (cd "$ROOT/bench" && python3 -I fret_check/parser_fingerprint.py --backend "$PARSER" --check &&
           python3 batch_pipeline.py --data "$DATA" --results "$RUN/gen" --reps "$REPS" --dict-all --g-parity --tm-source-only --sourced-rules-only --fret-reference --parser "$PARSER" \
             --model "$MODEL" --cli-extra "${CLI_EXTRA:---effort medium}" ${ONLYARG[@]+"${ONLYARG[@]}"} ${ENVARG[@]+"${ENVARG[@]}"}) ;;
  inputs) for v in v0 vf rt; do (cd "$ROOT/bench" && python3 tools/make_judge_inputs.py --results "$RUN/gen" --data "$DATA" --out "$RUN/inputs_$v" --parser "$PARSER" --reps "$REPS" --variant $v); done ;;
  judge)  for v in v0 vf rt; do (cd "$ROOT/judging" && python3 -m nl2fret_judge judge-parts --engine "$ENGINE" --nusmv "$NUSMV" --out "$RUN/judge_$v" --units "$RUN/inputs_$v/units.json" \
             --ltl "$RUN/inputs_$v/fret_ltl_gen.jsonl" --reference "$ROOT/data/reference/lm_reference_with_ltl.jsonl" --dictionary "$ROOT/data/dictionary/lm_dictionary.csv" --mode anchor); done ;;
  judgedef) for v in v0 vf rt; do (cd "$ROOT/bench" && python3 tools/make_def_inputs.py --inputs "$RUN/inputs_$v" --reference "$ROOT/data/reference/lm_reference_with_ltl.jsonl" \
             --dictionary "$ROOT/data/dictionary/lm_dictionary.csv" --out "$RUN/inputs_def_$v" --parser "$PARSER" ${ONLYARG[@]+"${ONLYARG[@]}"} 2>&1 | tail -n 1) &&
            (cd "$ROOT/judging" && python3 -m nl2fret_judge judge-parts --engine "$ENGINE" --nusmv "$NUSMV" --out "$RUN/judge_def_$v" --units "$RUN/inputs_def_$v/units.json" \
             --ltl "$RUN/inputs_def_$v/fret_ltl_gen.jsonl" --reference "$RUN/inputs_def_$v/reference_def.jsonl" --dictionary "$ROOT/data/dictionary/lm_dictionary.csv" --mode anchor); done ;;
  group)  (cd "$ROOT/bench" && python3 -I fret_check/group_rlz.py --inputs "$RUN/inputs_rt" --reference "$ROOT/data/reference/lm_reference_with_ltl.jsonl" --out "$RUN/group_rlz.jsonl" \
             --parser "$PARSER" ${ONLYARG[@]+"${ONLYARG[@]}"}) ;;
  effect) # primary measure J+def (rt_effect.json), secondary strict (rt_effect_strict.json); docs/V20_BATCH_DESIGN.md 7.4
          (cd "$ROOT/bench" && python3 tools/rt_effect.py --judge v0="$RUN/judge_def_v0" vf="$RUN/judge_def_vf" rt="$RUN/judge_def_rt" ${ONLYARG[@]+"${ONLYARG[@]}"} --out "$RUN/rt_effect.json" &&
           python3 tools/rt_effect.py --judge v0="$RUN/judge_v0" vf="$RUN/judge_vf" rt="$RUN/judge_rt" ${ONLYARG[@]+"${ONLYARG[@]}"} --out "$RUN/rt_effect_strict.json") ;;
  all)    for s in pin gen inputs judge judgedef group effect; do bash "$0" "$s" "$RUN"; done ;;
  *) echo "unknown step $STEP"; exit 2 ;;
esac
echo "step $STEP done: $RUN"
