# CHANGELOG (ltl_engines)

## 2026-11-07
- ltl_engines_pack.zip moved from nl2semiformal/ into ltl_engines/inputs/, extracted to ltl_engines/pack/ (ltlpack renamed to pack); README copy in docs/
- MANIFEST.sha256: 5 lines all OK
- no Spot (ltlfilt) and no NuSMV/nuXmv on this machine; brew has no bottle for macOS Intel and install-dry-run stopped on a non-writable /usr/local/share/man/man8 (no sudo used); details in pack/INSTALL_NOTES.md
- selftest SELFTEST_OK; parse, run (610/610), report done in under one minute with python3 -I
- observation: z3b not importable under python3 -I (z3 is in user site-packages), so no engine produced a result; not fixed, not re-run (README rule); in pack/NOTES.md
- pack data/ and tools/ files unchanged (notes/PACK_FILES_BEFORE.sha256 diff empty)
- zip: ltl_engines/zips/ltl_engines_out.zip (results/ with parse.jsonl and pairs_out.jsonl, REPORT.txt, NOTES.md, INSTALL_NOTES.md; 6 files)

## second run with engines, 2026-11-07 (user: use Spot; MacPorts or docker if troublesome)
- first run outputs moved to run1_noengines/ (zip renamed zips/ltl_engines_out_run1_noengines.zip)
- Spot 2.16.1 built from source into docker image ltl-spot:local (brew Intel no bottle; lrde/spot denied; no apt package); NuSMV 2.6.0 taken from existing local image cst-nusmv:local (not asked by the user, used because the README compares NuSMV and Spot); wrappers in scripts/bin, Dockerfile in scripts/docker_spot, run script scripts/run_engines.sh
- run 14:48:29 to 15:42:23 KST, 610/610 pairs; errors (NuSMV timeouts 10 pairs, window>128 32, Spot syntax errors on past-time text, 6 Spot errors in pairs, z3b missing under -I) recorded in pack/NOTES.md, not fixed, not re-run
- pack data/ and tools/ unchanged (diff with notes/PACK_FILES_BEFORE_RUN2.sha256 empty; MANIFEST.sha256 OK)
- zip: zips/ltl_engines_out.zip (results/, REPORT.txt, NOTES.md, INSTALL_NOTES.md, plus engine_setup/ with wrappers, Dockerfile, run script as extra)
