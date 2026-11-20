#!/usr/bin/env bash
# v2.0 batch run (agent per approach and challenge). Usage: bash scripts/run_batch.sh STEP [RUN_DIR]
# STEP: pin | gen | inputs | judge | group | effect | readable | all
# env: MODEL (sonnet), REPS (3), PARSER (docker), NUSMV, ENGINE (nusmv), ONLY (challenge ids, optional), ENVPASS (names of environment variables the agent process may inherit, optional), CLI_EXTRA,
#      EXT (extension modules, default `dictionary`; EXT= switches all off; docs/V20_BATCH_DESIGN.md section 8),
#      ARMS (space separated approach names for `gen`, default: DIRECT Adv-EARS+G Boilerplate+G MASTeR+G SPIDER+G; the 11 approaches of the earlier FSM runs: ARMS="DIRECT MASTeR+G EARS+G Adv-EARS+G SPIDER+G Boilerplate+G MASTeR+R2 EARS+R2 Adv-EARS+R2 SPIDER+R2 Boilerplate+R2"),
#      EXCLUSIONS (file of excluded items, default data/dataset_exclusions.json; no file or an empty list: no exclusion),
#      NO_KC=1 (switch the keyword check step KC off; default on, docs/V20_BATCH_DESIGN.md section 11)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"          # the interpreter of the environment where the package is installed (pip install -e ".[test]")
STEP="${1:-pin}"
RUN="${2:-$ROOT/runs/batch_$(date +%Y%m%d)}"
MODEL="${MODEL:-sonnet}"; REPS="${REPS:-3}"; PARSER="${PARSER:-docker}"; NUSMV="${NUSMV:-NuSMV}"; ENGINE="${ENGINE:-nusmv}"
DATA="$ROOT/src/nl2fret/data/lm_items.jsonl"
ONLYARG=(); if [ -n "${ONLY:-}" ]; then ONLYARG=(--only-challenge $ONLY); fi
ARMARG=(); if [ -n "${ARMS:-}" ]; then ARMARG=(--arms $ARMS); fi      # default (ARMS unset): the five approaches of the batch run (DIRECT Adv-EARS+G Boilerplate+G MASTeR+G SPIDER+G)
ENVARG=(); if [ -n "${ENVPASS:-}" ]; then ENVARG=(--env-pass $ENVPASS); fi
EXT="${EXT-dictionary}"
EXTARG=(); if [ -n "$EXT" ]; then EXTARG=(--ext $EXT); fi
KCARG=(); VARIANTS="v0 vf kc rt"; if [ -n "${NO_KC:-}" ]; then KCARG=(--no-kc); VARIANTS="v0 vf rt"; fi
mkdir -p "$RUN"
# dataset exclusions (docs/V20_BATCH_DESIGN.md section 13): with a non-empty `data/dataset_exclusions.json` (or EXCLUSIONS=<file>) the excluded items are removed from the items file and from the reference file
# by copies in $RUN/filtered/ (the original data files are not changed); without a list nothing is written and the original paths are used (no change of behavior)
REFFILE="$ROOT/data/reference/lm_reference_with_ltl.jsonl"
EXFILE="${EXCLUSIONS:-$ROOT/data/dataset_exclusions.json}"
if [ -s "$EXFILE" ]; then (cd "$ROOT" && $PY -m nl2fret.tools.apply_exclusions --exclusions "$EXFILE" --items "$DATA" --reference "$REFFILE" --out "$RUN/filtered"); fi
if [ -s "$EXFILE" ] && [ -f "$RUN/filtered/items.jsonl" ]; then DATA="$RUN/filtered/items.jsonl"; REFFILE="$RUN/filtered/reference.jsonl"; fi
case "$STEP" in
  pin)    # first time on a computer: WRITEPIN=1 stores the fingerprint; later runs compare against it
          (cd "$ROOT" && $PY -I -m nl2fret.fret_check.parser_fingerprint --backend "$PARSER" ${WRITEPIN:+--write-pin} --check --dump "$RUN/parser_fingerprint.json") ;;
  gen)    (cd "$ROOT" && $PY -I -m nl2fret.fret_check.parser_fingerprint --backend "$PARSER" --check &&
           $PY -m nl2fret.batch_pipeline --data "$DATA" --results "$RUN/gen" --reps "$REPS" ${EXTARG[@]+"${EXTARG[@]}"} ${KCARG[@]+"${KCARG[@]}"} ${ARMARG[@]+"${ARMARG[@]}"} --g-parity --tm-source-only --sourced-rules-only --fret-reference --parser "$PARSER" \
             --model "$MODEL" --cli-extra "${CLI_EXTRA:---effort medium}" ${ONLYARG[@]+"${ONLYARG[@]}"} ${ENVARG[@]+"${ENVARG[@]}"}) ;;
  inputs) for v in $VARIANTS; do (cd "$ROOT" && $PY -m nl2fret.tools.make_judge_inputs --results "$RUN/gen" --data "$DATA" --out "$RUN/inputs_$v" --parser "$PARSER" --reps "$REPS" --variant $v); done ;;
  judge)  DICT="$(cd "$ROOT" && $PY -m nl2fret.ext.dictionary.judge_input --ext "$EXT" --run "$RUN")"   # extension off: a header-only dictionary file (the frozen judge requires the argument)
          for v in $VARIANTS; do (cd "$ROOT" && $PY -m nl2fret_judge judge-parts --engine "$ENGINE" --nusmv "$NUSMV" --out "$RUN/judge_$v" --units "$RUN/inputs_$v/units.json" \
             --ltl "$RUN/inputs_$v/fret_ltl_gen.jsonl" --reference "$REFFILE" --dictionary "$DICT" --mode anchor); done ;;
  group)  (cd "$ROOT" && $PY -I -m nl2fret.fret_check.group_rlz --inputs "$RUN/inputs_rt" --reference "$REFFILE" --out "$RUN/group_rlz.jsonl" \
             --parser "$PARSER" ${ONLYARG[@]+"${ONLYARG[@]}"}) ;;
  effect) JUDGES=(); KWARG=(); for v in $VARIANTS; do JUDGES+=("$v=$RUN/judge_$v"); done; if [ -z "${NO_KC:-}" ]; then KWARG=(--keyword-inputs vf="$RUN/inputs_vf" kc="$RUN/inputs_kc"); fi
          (cd "$ROOT" && $PY -m nl2fret.tools.rt_effect --judge "${JUDGES[@]}" ${KWARG[@]+"${KWARG[@]}"} ${ONLYARG[@]+"${ONLYARG[@]}"} --out "$RUN/rt_effect.json") ;;
  readable) # human-readable result files (Korean outline Markdown per item, INDEX.md, results_flat.csv) in $RUN/readable; copy this folder into experiments/<NNN>/results/ with the other results
          (cd "$ROOT" && $PY -m nl2fret.tools.readable_report --run "$RUN" --reference "$REFFILE" --out "$RUN/readable" ${ONLYARG[@]+"${ONLYARG[@]}"})
          # result tables (xlsx + CSV) in $RUN/readable/tables/<challenge>/; a failure only writes the reason and keeps all other outputs
          (cd "$ROOT" && $PY scripts/make_readable_tables.py --run "$RUN" --out "$RUN/readable/tables" ${ONLYARG[@]+"${ONLYARG[@]}"}) || echo "make_readable_tables failed (rc=$?); the other readable files are unchanged" | tee "$RUN/readable/tables_failed.txt" ;;
  all)    for s in pin gen inputs judge group effect readable; do bash "$0" "$s" "$RUN"; done ;;
  *) echo "unknown step $STEP"; exit 2 ;;
esac
echo "step $STEP done: $RUN"
