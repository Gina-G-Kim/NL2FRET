#!/usr/bin/env bash
# v2.0 batch run (agent per approach and challenge). Usage: bash scripts/run_batch.sh STEP [RUN_DIR]
# STEP: pin | gen | inputs | judge | group | effect | all
# env: MODEL (sonnet), REPS (3), PARSER (docker), NUSMV, ENGINE (nusmv), ONLY (challenge ids, optional), ENVPASS (names of environment variables the agent process may inherit, optional), CLI_EXTRA,
#      EXT (extension modules, default `dictionary`; EXT= switches all off; docs/V20_BATCH_DESIGN.md section 8),
#      NO_KC=1 (switch the keyword check step KC off; default on, docs/V20_BATCH_DESIGN.md section 11)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"          # the interpreter of the environment where the package is installed (pip install -e ".[test]")
STEP="${1:-pin}"
RUN="${2:-$ROOT/runs/batch_$(date +%Y%m%d)}"
MODEL="${MODEL:-sonnet}"; REPS="${REPS:-3}"; PARSER="${PARSER:-docker}"; NUSMV="${NUSMV:-NuSMV}"; ENGINE="${ENGINE:-nusmv}"
DATA="$ROOT/src/nl2fret/data/lm_items.jsonl"
ONLYARG=(); if [ -n "${ONLY:-}" ]; then ONLYARG=(--only-challenge $ONLY); fi
ENVARG=(); if [ -n "${ENVPASS:-}" ]; then ENVARG=(--env-pass $ENVPASS); fi
EXT="${EXT-dictionary}"
EXTARG=(); if [ -n "$EXT" ]; then EXTARG=(--ext $EXT); fi
KCARG=(); VARIANTS="v0 vf kc rt"; if [ -n "${NO_KC:-}" ]; then KCARG=(--no-kc); VARIANTS="v0 vf rt"; fi
mkdir -p "$RUN"
case "$STEP" in
  pin)    # first time on a computer: WRITEPIN=1 stores the fingerprint; later runs compare against it
          (cd "$ROOT" && $PY -I -m nl2fret.fret_check.parser_fingerprint --backend "$PARSER" ${WRITEPIN:+--write-pin} --check --dump "$RUN/parser_fingerprint.json") ;;
  gen)    (cd "$ROOT" && $PY -I -m nl2fret.fret_check.parser_fingerprint --backend "$PARSER" --check &&
           $PY -m nl2fret.batch_pipeline --data "$DATA" --results "$RUN/gen" --reps "$REPS" ${EXTARG[@]+"${EXTARG[@]}"} ${KCARG[@]+"${KCARG[@]}"} --g-parity --tm-source-only --sourced-rules-only --fret-reference --parser "$PARSER" \
             --model "$MODEL" --cli-extra "${CLI_EXTRA:---effort medium}" ${ONLYARG[@]+"${ONLYARG[@]}"} ${ENVARG[@]+"${ENVARG[@]}"}) ;;
  inputs) for v in $VARIANTS; do (cd "$ROOT" && $PY -m nl2fret.tools.make_judge_inputs --results "$RUN/gen" --data "$DATA" --out "$RUN/inputs_$v" --parser "$PARSER" --reps "$REPS" --variant $v); done ;;
  judge)  DICT="$(cd "$ROOT" && $PY -m nl2fret.ext.dictionary.judge_input --ext "$EXT" --run "$RUN")"   # extension off: a header-only dictionary file (the frozen judge requires the argument)
          for v in $VARIANTS; do (cd "$ROOT" && $PY -m nl2fret_judge judge-parts --engine "$ENGINE" --nusmv "$NUSMV" --out "$RUN/judge_$v" --units "$RUN/inputs_$v/units.json" \
             --ltl "$RUN/inputs_$v/fret_ltl_gen.jsonl" --reference "$ROOT/data/reference/lm_reference_with_ltl.jsonl" --dictionary "$DICT" --mode anchor); done ;;
  group)  (cd "$ROOT" && $PY -I -m nl2fret.fret_check.group_rlz --inputs "$RUN/inputs_rt" --reference "$ROOT/data/reference/lm_reference_with_ltl.jsonl" --out "$RUN/group_rlz.jsonl" \
             --parser "$PARSER" ${ONLYARG[@]+"${ONLYARG[@]}"}) ;;
  effect) JUDGES=(); KWARG=(); for v in $VARIANTS; do JUDGES+=("$v=$RUN/judge_$v"); done; if [ -z "${NO_KC:-}" ]; then KWARG=(--keyword-inputs vf="$RUN/inputs_vf" kc="$RUN/inputs_kc"); fi
          (cd "$ROOT" && $PY -m nl2fret.tools.rt_effect --judge "${JUDGES[@]}" ${KWARG[@]+"${KWARG[@]}"} ${ONLYARG[@]+"${ONLYARG[@]}"} --out "$RUN/rt_effect.json") ;;
  all)    for s in pin gen inputs judge group effect; do bash "$0" "$s" "$RUN"; done ;;
  *) echo "unknown step $STEP"; exit 2 ;;
esac
echo "step $STEP done: $RUN"
