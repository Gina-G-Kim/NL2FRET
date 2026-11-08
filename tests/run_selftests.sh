#!/bin/bash
# Run the existing self-tests and the dictionary-usage report without changing any code.
# No writes (bytecode generation is disabled), no model calls, no Docker.
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export PYTHONDONTWRITEBYTECODE=1
echo "== v8_dict8 rule selftest";    (cd "$ROOT/experiments/v8_dict8/bench" && python3 -I -B tools/selftest.py | tail -1)
echo "== v8_dict8 cli selftest";     (cd "$ROOT/experiments/v8_dict8/bench" && python3 -B cli.py --selftest | tail -1)
echo "== v8_dict8 dictionary usage"; (cd "$ROOT/experiments/v8_dict8/bench" && python3 -I -B tools/dict_usage.py results_dict8)
echo "== ltlpack selftest";          (cd "$ROOT/packages/ltlpack/pack" && python3 -I -B tools/ltl_engines.py selftest | tail -1)
