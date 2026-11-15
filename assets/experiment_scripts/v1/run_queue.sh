#!/bin/bash
# usage: scripts/run_queue.sh <jobs file> <slots>
# Every non-empty line of the jobs file is one shell command (here: scripts/run_judge_shard.sh ...). At most <slots> of them run at the same time (xargs -P), the next one
# starts when a slot frees. The VM of the container backend has 4 CPUs and every job holds one container with --cpus=1, so slots = 4 keeps every container on its own CPU
# (more concurrent containers would stretch the wall time of a query and could turn the 120 s query limit into spurious timeouts). The same command resumes a stopped queue:
# a finished shard is checked and ends at once, an unfinished shard continues with the pairs not yet recorded.
JOBS="${1:?jobs file}"; SLOTS="${2:-4}"
echo "== queue start slots=$SLOTS jobs=$(grep -c . "$JOBS") ($(date '+%F %T'))"
grep . "$JOBS" | tr '\n' '\0' | xargs -0 -n 1 -P "$SLOTS" bash -c
rc=$?
echo "== queue exit $rc ($(date '+%F %T'))"
exit $rc
