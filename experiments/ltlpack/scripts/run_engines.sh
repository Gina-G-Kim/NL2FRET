#!/bin/bash
# Run the ltlpack engine comparison (README_MAC.md, section 2) with Spot and NuSMV inside Docker containers.
#
# Starts one long-lived container per engine (ltl-spot, ltl-nusmv), runs selftest, parse, run and report from
# the pack directory, appends progress to logs/run2.log (relative to the package root), and removes the
# containers at the end.
# Resumable: running the script again continues the "run" stage from the existing results.
# Requires the local images ltl-spot:local (see build_spot_image.sh) and cst-nusmv:local.
BASE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$BASE/pack"
docker rm -f ltl-spot ltl-nusmv >/dev/null 2>&1
docker run -d --name ltl-spot --entrypoint sleep ltl-spot:local infinity >/dev/null
docker run -d --name ltl-nusmv -v "$BASE/pack/work:$BASE/pack/work" --entrypoint sleep cst-nusmv:local infinity >/dev/null
{
echo "start $(date '+%F %T')"
"$BASE/scripts/bin/ltlfilt" --version | head -1
"$BASE/scripts/bin/NuSMV" -help 2>&1 | head -1
python3 -I tools/ltl_engines.py selftest | tail -1
nice python3 -I tools/ltl_engines.py parse --nusmv "$BASE/scripts/bin/NuSMV" --spot "$BASE/scripts/bin/ltlfilt" --timeout 120
nice python3 -I tools/ltl_engines.py run --nusmv "$BASE/scripts/bin/NuSMV" --spot "$BASE/scripts/bin/ltlfilt" --timeout 120 | tail -4
nice python3 -I tools/ltl_engines.py report --nusmv "$BASE/scripts/bin/NuSMV" --spot "$BASE/scripts/bin/ltlfilt" > REPORT.txt
echo "end $(date '+%F %T')"
} >> "$BASE/logs/run2.log" 2>&1
docker rm -f ltl-spot ltl-nusmv >/dev/null 2>&1
