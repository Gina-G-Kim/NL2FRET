# INSTALL_NOTES (2026-11-07, second run)

- machine: macOS 15.7.9, x86_64; docker 29.6.1 (Colima)
- Spot (ltlfilt): `brew install spot` not possible (Homebrew gives no bottles for macOS Intel; dry-run stopped on a non-writable /usr/local/share/man/man8; no sudo used). Docker Hub image lrde/spot: pull access denied. Debian bookworm and Ubuntu 24.04 apt: "Unable to locate package spot". Built a local image ltl-spot:local from debian:bookworm-slim with Spot 2.16.1 compiled from source (https://www.lrde.epita.fr/dload/spot/spot-2.16.1.tar.gz, sha256 182f4180da851588886a2e5f1540c3e2bb5cfddd228fd20689fa7ce498f57733 verified in the build, as printed by Homebrew metadata). `ltlfilt --version`: ltlfilt (spot) 2.16.1. Build started 14:38:38, image available 14:47:44. Dockerfile in engine_setup/docker_spot/Dockerfile.
- NuSMV: no brew formula or cask. A local docker image cst-nusmv:local (existing before this test, from other work) contains /opt/nusmv/bin/NuSMV; its banner: NuSMV 2.6.0 (compiled on Wed Oct 14 15:36:56 2015). Used through the wrapper engine_setup/bin/NuSMV (docker exec into a persistent container with the work folder mounted at the same path).
- ltlfilt is called through engine_setup/bin/ltlfilt (docker exec into a persistent container). Both containers were started by scripts/run_engines.sh and removed at its end.
- z3: python module z3 5.1.0 exists in the user site-packages directory; python3 -I does not see it (see NOTES.md).
- MacPorts: not used.
- local image ids: ltl-spot:local abb8d639c12a; cst-nusmv:local 910e958e8920
