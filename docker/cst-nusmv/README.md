# cst-nusmv: build recipe of the NuSMV 2.6.0 Docker image

This folder is the build recipe of the Docker image `cst-nusmv:local` (NuSMV 2.6.0). It was copied here on 2026-11-11 from the experiment `cst_test` (round 3, E10), where the image was built on 2026-10-12. The image itself and the NuSMV binaries are not stored in the repository.

Used by: the NuSMV wrapper of `packages/ltlpack` (`scripts/bin/NuSMV`) and the Mac check runs of `nl2fret_tool`, which used the same image through a wrapper. The judge itself only needs an executable `NuSMV` that takes the `.smv` path as its last argument (see `nl2fret_tool/docs/RUNBOOK.md`); this image is one way to provide it.

## Files

| File | Content |
|---|---|
| `Dockerfile` | Copy of `cst_test/round3_testnote3/E10_run/docker/Dockerfile` (three lines: `FROM ubuntu:24.04`, `COPY nusmv/ /opt/nusmv/`, `ENV PATH=/opt/nusmv/bin:$PATH`) |
| `nusmv_context.sha256` | sha256 of the 175 files of the build context `nusmv/` (`nusmv/bin/NuSMV`, `nusmv/bin/ltl2smv`, `nusmv/share/nusmv/...`). It was checked against the original context on 2026-11-11: 175 of 175 OK |

## Build

The build context `nusmv/` is the `bin/` and `share/` folders of the official NuSMV 2.6.0 Linux binary distribution. It is not stored here (about 20 MB of third-party binaries). The E10 record in `cst_test` says that the official NuSMV-2.6.0 Linux binary tarball was used because Ubuntu 24.04 and Debian bookworm have no NuSMV package; the download URL was not recorded.

1. Get the tarball (top-level folder `NuSMV-2.6.0-Linux/`) and check it. The file that was used for the image was 7,496,637 bytes with sha256 `11b12e42bc04566c4ec1f7cc205fa8704382ac4d69e052154cbb59c9b7e8e08c`.
2. Unpack it and copy its `bin/` and `share/` folders into `docker/cst-nusmv/nusmv/` (the `include/` and `lib/` folders were not copied into the image).
3. Check the context and build:

```bash
cd docker/cst-nusmv
shasum -a 256 -c nusmv_context.sha256     # 175 files, all OK
docker build -t cst-nusmv:local .
docker run --rm --entrypoint NuSMV cst-nusmv:local -help | head -1     # "*** This is NuSMV 2.6.0 (compiled on Wed Oct 14 15:36:56 2015)"
```

## Evidence that this recipe built the image on this machine

Checked on 2026-11-11: `docker history --no-trunc cst-nusmv:local` lists `FROM ubuntu:24.04`, `COPY nusmv/ /opt/nusmv/` (19.9 MB, 2026-10-12 11:45:59) and the `PATH` setting, which is the three-line Dockerfile; the image prints "NuSMV 2.6.0 (compiled on Wed Oct 14 15:36:56 2015)" and holds 175 files under `/opt/nusmv`; in the `cst_test` folder the context `docker/nusmv/` is identical in content to the `bin/` and `share/` folders of the unpacked tarball (`tools_dl/unpack/NuSMV-2.6.0-Linux/`).

Not verified: a rebuild from this folder has not been run.
