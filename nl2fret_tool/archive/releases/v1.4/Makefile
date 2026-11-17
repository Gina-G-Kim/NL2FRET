# Judging stage (bench/ generation stays as frozen; see docs/RUNBOOK.md)
PY      ?= python3
NUSMV   ?= NuSMV
OUT     ?= runs/judge_$(shell date +%Y%m%d_%H%M)
UNITS   ?= inputs/units.json
LTL     ?= inputs/fret_ltl_gen.jsonl
RLZ     ?= inputs/fret_realizability_gen.jsonl
.PHONY: test selfcheck judge aggregate freeze-check
test:
	cd judging && $(PY) -m pytest ../tests -q
selfcheck:
	cd judging && $(PY) -m nl2fret_judge selfcheck --engine nusmv --nusmv "$(NUSMV)" --out ../$(OUT)
judge:
	cd judging && $(PY) -m nl2fret_judge judge --engine nusmv --nusmv "$(NUSMV)" --out ../$(OUT) --units ../$(UNITS) --ltl ../$(LTL) --rlz ../$(RLZ)
aggregate:
	cd judging && $(PY) -m nl2fret_judge aggregate --out ../$(OUT) --units ../$(UNITS) --ltl ../$(LTL) --rlz ../$(RLZ)
freeze-check:
	cd bench && sha256sum -c FROZEN_MANIFEST.sha256
fsm-dryrun:
	bash exp/fsm/run_fsm.sh dryrun
fsm-all:
	bash exp/fsm/run_fsm.sh all
