# Lightweight entry point. Experiment run commands are in each experiments/<run>/scripts/ directory or in the
# run instructions (docs and prompt documents).
.PHONY: selftest
selftest:
	bash tests/run_selftests.sh
