# Developer entry points of the nl2fret project (PyPA layout: pyproject.toml, src/, tests/). Run inside an activated virtual environment.
PY      ?= python3
NUSMV   ?= NuSMV
.PHONY: install test build selfcheck selftest clean
install:
	$(PY) -m pip install -e ".[test]"
test:
	$(PY) -m pytest
build:
	$(PY) -m pip install --quiet build && $(PY) -m build
selftest:
	bash scripts/run_selftests.sh
selfcheck:
	$(PY) -m nl2fret_judge selfcheck --engine nusmv --nusmv "$(NUSMV)" --out runs/judge_selfcheck
clean:
	rm -rf build dist src/*.egg-info
