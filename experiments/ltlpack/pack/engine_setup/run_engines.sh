#!/bin/bash
# executor script: README_MAC.md section 2 with Spot and NuSMV running in docker containers. Log in logs/run2.log. Resume = run the same script again.
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
