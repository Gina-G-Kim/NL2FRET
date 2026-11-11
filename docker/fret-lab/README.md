# fret-lab: build recipe of the FRET Docker image

This folder is the build recipe of the Docker image `fret-lab:latest` that the NL2FRET tool uses for the official FRET parser (`FretSemantics.compile`) and for the Kind2 realizability checks. It was copied here on 2026-11-11 from the project `~/fret` ("All in One FRET", a browser-GUI image of NASA FRET for classroom use). The image itself is not stored in the repository.

## How the tool uses the image

- `nl2fret_tool/bench/fret_check/tools/fret_compile.py` runs `docker run --rm --cpus 1 --entrypoint node ... fret-lab:latest /tools/fret_parse_full.js` with `NODE_PATH` pointing to FRET's `app/node_modules` inside the image.
- `nl2fret_tool/bench/fret_check/tools/fret_rlz.py` runs `fretCLI realizability <project> <component> --solver kind2` inside the image.

## Files

| File | Content |
|---|---|
| `Dockerfile` | Copy of `~/fret/Dockerfile` (last modified 2026-09-16 11:41, before the image was built). Two stages: the builder compiles NASA FRET (tag `FRET_VERSION`, default `v3.1.0`) and optionally AE-VAL from source; the runtime stage copies only the built application and installs the optional tools selected by build arguments |
| `fret.sh` | The file that the Dockerfile copies to `/usr/local/bin/docker-entrypoint.sh` (container entrypoint, analysis-engine wrapper, and host-side CLI in one script). It is the exact file taken from the image `fret-lab:latest` (27,515 bytes), not the working copy in `~/fret`; see "Differences" below |
| `.dockerignore`, `LICENSE` | Copies from `~/fret` (LICENSE: Apache License 2.0) |

## Build

The image on this machine was built with all five optional tools enabled. This is the command that `./fret.sh build -all` runs (see `cmd_build` in `fret.sh`):

```bash
docker build -t fret-lab:latest \
  --build-arg FRET_VERSION=v3.1.0 \
  --build-arg INSTALL_NUSMV=true --build-arg INSTALL_JKIND=true --build-arg INSTALL_KIND2=true \
  --build-arg INSTALL_Z3=true --build-arg INSTALL_AEVAL=true \
  docker/fret-lab
```

The build needs network access (GitHub for FRET, Kind2, JKind and AE-VAL; nusmv.fbk.eu for NuSMV; the Ubuntu mirrors) and takes several minutes. Compiling AE-VAL (which builds its own copy of Z3) is the slowest step. The NL2FRET tool needs the FRET parser and Kind2; the other tools are in the image because it was built with all five.

## Evidence that this recipe built the image on this machine

Checked on 2026-11-11 with `docker history --no-trunc fret-lab:latest` and by running commands inside the image:

- The history lists the same instructions as the runtime stage of the Dockerfile, in the same order: base `ubuntu:24.04`, the eight `ARG` lines (the history shows the values used for the build), `ENV`, `SHELL`, the apt package line, `COPY fret.sh`, the Z3, NuSMV, Kind2 and JKind blocks, the eight `COPY --from=builder` lines, the `ltlsim` link, the AE-VAL block, `LABEL`, `EXPOSE 6080`, `HEALTHCHECK` and `ENTRYPOINT`.
- The build arguments recorded in the history are `INSTALL_NUSMV=true INSTALL_JKIND=true INSTALL_KIND2=true INSTALL_Z3=true INSTALL_AEVAL=true NUSMV_VERSION=2.7.1 KIND2_VERSION=3.0.0 JKIND_VERSION=2.2`, and the image labels `fret.tool.*` are all `true`.
- Tool versions found inside the image: Kind2 v3.0.0, NuSMV 2.7.1, Z3 4.8.12, `/opt/jkind/jkind.jar` present.
- The image was created on 2026-09-15 and 2026-09-16 (image id `eb13a1115267`).

Not visible in the image history: the builder stage (FRET compiled from source). Its build arguments are those of `cmd_build` (`FRET_VERSION` default `v3.1.0`). Not verified: a rebuild from this folder has not been run, so the rebuilt image has not been compared with the existing one.

## Differences between `fret.sh` here and in `~/fret`

The working copy `~/fret/fret.sh` (28,581 bytes) was edited after the image was built (2026-09-16 11:56, the image layers date from 11:43 to 11:44). The differences are only in the host-side part: help text, the `start` command (a new `--memory N` option with default 4 GB, replacing the environment variable `FRET_MEMORY_GB` as the primary setting) and the command dispatch. The container-side roles (entrypoint and analysis-engine wrapper) are the same. This folder keeps the version that is inside the image so that it matches what was built.
