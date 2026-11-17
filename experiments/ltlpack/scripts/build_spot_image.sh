#!/bin/bash
# Build the local Docker image ltl-spot:local: Spot 2.16.1 compiled from source, with the source tarball
# checksum-verified in scripts/docker_spot/Dockerfile.
# The build log is written to logs/spot_build.log (relative to the package root).
cd "$(dirname "$0")/.."
exec nice -n 10 docker build --progress=plain -t ltl-spot:local scripts/docker_spot > logs/spot_build.log 2>&1
