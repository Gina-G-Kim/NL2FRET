# Judging stage (bench/ generation stays as frozen; see docs/RUNBOOK.md)
PY      ?= python3
NUSMV   ?= NuSMV
OUT     ?= runs/judge_$(shell date +%Y%m%d_%H%M)
UNITS   ?= inputs/units.json
LTL     ?= inputs/fret_ltl_gen.jsonl
RLZ     ?= inputs/fret_realizability_gen.jsonl
JUDGE_ARGS ?=
.PHONY: test selfcheck judge aggregate freeze-check release
test:
	cd judging && $(PY) -m pytest ../tests -q
selfcheck:
	cd judging && $(PY) -m nl2fret_judge selfcheck --engine nusmv --nusmv "$(NUSMV)" --out ../$(OUT)
judge:
	cd judging && $(PY) -m nl2fret_judge judge --engine nusmv --nusmv "$(NUSMV)" --out ../$(OUT) --units ../$(UNITS) --ltl ../$(LTL) --rlz ../$(RLZ) $(JUDGE_ARGS)
aggregate:
	cd judging && $(PY) -m nl2fret_judge aggregate --out ../$(OUT) --units ../$(UNITS) --ltl ../$(LTL) --rlz ../$(RLZ)
freeze-check:
	cd bench && sha256sum -c FROZEN_MANIFEST.sha256
# Writes JUDGE_FROZEN_MANIFEST.sha256 (sha256 of judging/nl2fret_judge/*.py and judging/legacy/*.py). Run once, when the code is final; refused when the file exists.
release:
	cd judging && $(PY) -m nl2fret_judge release
