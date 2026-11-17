#!/bin/bash
# Docker wrapper for NuSMV 2.6.0 (image cst-nusmv:local, Colima backend), copied from the v1.2 freeze run (experiments/nl2fret_tool_v12/scripts/bin/NuSMV) with
# one change: the container name comes from NUSMV_CONTAINER (required here, one container per judging shard). Contract of the tool: the executable receives the
# path of the .smv file as its LAST argument (judging/nl2fret_judge/engines.py: cmd = self.cmd + [path]).
# 1. A relative last argument is turned into an absolute path (the container has another working directory). An argument that starts with "-" is left alone.
# 2. The experiment directory is mounted at the same absolute path in the container (scripts/container.sh), so the absolute path resolves on both sides.
# 3. coreutils timeout inside the container (NUSMV_INNER_TIMEOUT seconds, default 125) is deliberately LONGER than the tool's own timeout (120 s by default).
#    The tool records the timeout itself; the inner timeout only removes a NuSMV process that the kill of the docker client would leave running in the
#    container. The Colima VM clock was measured to run about 0.92 % faster than the host (v1.1 run); the margin must be 2 % or more of the tool timeout.
set -u
: "${NUSMV_CONTAINER:?NUSMV_CONTAINER must name the container of this shard}"
args=("$@")
n=${#args[@]}
if [ "$n" -ge 1 ]; then
  last="${args[$((n-1))]}"
  case "$last" in
    -*) ;;
    /*) ;;
    *) args[$((n-1))]="$(cd "$(dirname "$last")" && pwd -P)/$(basename "$last")" ;;
  esac
fi
exec docker exec "$NUSMV_CONTAINER" timeout -k 5 "${NUSMV_INNER_TIMEOUT:-125}" /opt/nusmv/bin/NuSMV "${args[@]}"
