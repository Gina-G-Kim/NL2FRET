#!/usr/bin/env bash
# v1.4 retest = the same 11 approaches (DIRECT, 5 x +G, 5 x +R2) as v1.3, prompt version changed. No approach is added.
# Usage: bash scripts/run_intent.sh STEP SET VER [RUN_DIR]
# STEP: lint | dryrun | gen | inputs | judge | trace | controls | analyze | compare | copybase | all   (controls: judge on pairs with known answers; analyze: strict success, decision points, causes; compare: BASE=<analysis dir of the other version>)
# SET : fsm (13 items x 3 reps = 429 units) | confirm (48 non-FSM items x 1 rep = 528 units)
# VER : v15 = v14 flags without --intent-decl + --fret-reference (the complete official FRET field documents, prompts/fretish_reference.md)
# VER : v13 = prompts of v1.3 (no flags; fsm already exists as runs/fsm_20261113, needed only for confirm)
#       v14 = --g-parity --intent-decl --tm-source-only --sourced-rules-only (see archive/nl2fret_tool_docs/v1.4/docs/V14_INTENT_TEST.md)
# env: GENARGS (extra run_pipeline arguments for gen, e.g. '--limit-items 2' for a rehearsal), SRC (copybase), STAGEA_FROM (gen: reuse stage A rows of an earlier run folder, e.g. runs/fsm_20261113/gen), FRETDOCS, PAPERRAW (lint), MODEL (sonnet), PARSER (docker), NUSMV, ENGINE (nusmv)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"          # the interpreter of the environment where the package is installed (pip install -e ".[test]")
STEP="${1:-dryrun}"; SET="${2:?SET fsm|confirm}"; VER="${3:?VER v13|v14}"
# every path argument or env path is made absolute against the CALLER's folder here, because the steps below cd into the project root first
absp() { case "$1" in /*) printf '%s' "$1";; *) printf '%s/%s' "$PWD" "$1";; esac; }
RUN="$(absp "${4:-$ROOT/runs/intent_${SET}_${VER}}")"      # fixed name (no date): a resume after midnight must find the same folder
[ -n "${STAGEA_FROM:-}" ] && STAGEA_FROM="$(absp "$STAGEA_FROM")"
[ -n "${CTRLDIR:-}" ] && CTRLDIR="$(absp "$CTRLDIR")"
[ -n "${BASE:-}" ] && BASE="$(absp "$BASE")"
[ -n "${SRC:-}" ] && SRC="$(absp "$SRC")"
MODEL="${MODEL:-sonnet}"; PARSER="${PARSER:-docker}"; NUSMV="${NUSMV:-NuSMV}"; ENGINE="${ENGINE:-nusmv}"
case "$SET" in fsm) DATA="$ROOT/src/nl2fret/data/lm_items_fsm.jsonl"; REPS=3;; confirm) DATA="$ROOT/src/nl2fret/data/lm_items_nonfsm.jsonl"; REPS=1;; *) echo "bad SET"; exit 2;; esac
ARMS=(DIRECT MASTeR+G EARS+G Adv-EARS+G SPIDER+G Boilerplate+G MASTeR+R2 EARS+R2 Adv-EARS+R2 SPIDER+R2 Boilerplate+R2)
case "$VER" in v13) EXTRA=();; v15) EXTRA=(--g-parity --tm-source-only --sourced-rules-only --fret-reference);; v14) EXTRA=(--g-parity --intent-decl --tm-source-only --sourced-rules-only);; *) echo "bad VER (v13|v14|v15)"; exit 2;; esac
mkdir -p "$RUN"
SA=(); [ -n "${STAGEA_FROM:-}" ] && SA=(--stage-a-from "$STAGEA_FROM")
gen() { (cd "$ROOT" && $PY -m nl2fret.run_pipeline --data "$DATA" --results "$RUN/gen" --arms "${ARMS[@]}" --reps "$REPS" --dict-all --parser "$PARSER" --model "$MODEL" ${EXTRA[@]+"${EXTRA[@]}"} ${SA[@]+"${SA[@]}"} "$@"); }
case "$STEP" in
  lint)   (cd "$ROOT" && $PY -m nl2fret.tools.prompt_lint --fret-docs "${FRETDOCS:?set FRETDOCS}" --paper-raw "${PAPERRAW:?set PAPERRAW (pdftotext -raw of the paper 'The Ten Lockheed Martin Cyber-Physical Challenges...' or data/paper_passage_AP003c.txt)}" --out "$RUN/prompt_lint.json") ;;
  dryrun) gen --dry-run ;;
  gen)    gen ${GENARGS:-} ;;
  inputs) (cd "$ROOT" && $PY -m nl2fret.tools.make_judge_inputs --results "$RUN/gen" --data "$DATA" --out "$RUN/inputs" --parser "$PARSER" --reps "$REPS") ;;
  judge)  (cd "$ROOT" && $PY -m nl2fret_judge selfcheck --engine "$ENGINE" --nusmv "$NUSMV" --out "$RUN/judge_selfcheck" &&
           $PY -m nl2fret_judge judge-parts --engine "$ENGINE" --nusmv "$NUSMV" --out "$RUN/judge" --units "$RUN/inputs/units.json" --ltl "$RUN/inputs/fret_ltl_gen.jsonl" \
             --reference "$ROOT/data/reference/lm_reference_with_ltl.jsonl" --dictionary "$ROOT/data/dictionary/lm_dictionary.csv" --mode anchor --cap "${CAP:-512}") ;;
  trace)  (cd "$ROOT" && $PY -m nl2fret.tools.trace_report --run "$RUN") ;;
  controls) (cd "$ROOT" && $PY -m nl2fret.tools.judge_controls --engine "$ENGINE" --nusmv "$NUSMV" --cap "${CAP:-512}" --out "${CTRLDIR:-$ROOT/runs/judge_controls_$ENGINE}") ;;
  analyze) (cd "$ROOT" && $PY -m nl2fret.tools.analyze_run --run "$RUN" --controls "${CTRLDIR:-$ROOT/runs/judge_controls_$ENGINE}" --engine "$ENGINE" --nusmv "$NUSMV") ;;
  compare) (cd "$ROOT" && $PY -m nl2fret.tools.compare_runs --base "${BASE:?set BASE=<analysis dir of the base version>}" --new "$RUN/analysis" --out "$RUN/comparison") ;;
  copybase) : "${SRC:?set SRC=<finished run folder to re-judge>}"   # copy everything except the old judge records (the recorder skips pairs that are already recorded, so a copied judge/ would not be re-judged)
           [ ! -e "$RUN/gen" ] || { echo "$RUN/gen exists; copybase needs an empty target"; exit 2; }
           for x in gen inputs summary.json console_gen.log; do [ -e "$SRC/$x" ] && cp -R "$SRC/$x" "$RUN/$x"; done ;;
  all)    for s in lint dryrun gen inputs judge trace analyze; do bash "$0" "$s" "$SET" "$VER" "$RUN"; done ;;
  *) echo "unknown step $STEP"; exit 2 ;;
esac
echo "step $STEP done: $RUN"
