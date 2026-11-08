# engines: External Engines and Installation Notes

This repository does not contain the engines themselves. The engines are local Docker images. Only what was verified on this machine is listed.

| Engine | Docker image | Purpose | How it is built, or where it comes from |
|---|---|---|---|
| FRET official parser, LTL translation, Kind2 realizability | `fret-lab:latest` (id eb13a1115267) | Compilation and realizability for all experiments | The location of the Dockerfile that built the image is unknown in this repository (a separate project `~/fret` exists; speculative) |
| Spot 2.16.1 (`ltlfilt`) | `ltl-spot:local` (id abb8d639c12a) | ltlpack comparison study | Dockerfile: `packages/ltlpack/scripts/docker_spot/Dockerfile`; build script: `packages/ltlpack/scripts/build_spot_image.sh` |
| NuSMV 2.6.0 | `cst-nusmv:local` (id 910e958e8920) | ltlpack comparison study | An image that already existed locally before this study; how it was built is unknown |

- Installation attempt log: `packages/ltlpack/pack/INSTALL_NOTES.md`
- Docker container wrappers: `packages/ltlpack/scripts/bin/`
- Mac-specific note: Homebrew provides no bottles for Intel Macs, so Spot was built from source inside Docker (see the notes above).
