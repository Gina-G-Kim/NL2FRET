# NOTES (2026-11-07, second run with Spot and NuSMV)

## versions
- ltlfilt --version: ltlfilt (spot) 2.16.1 (docker, local image built from source)
- NuSMV banner: This is NuSMV 2.6.0 (compiled on Wed Oct 14 15:36:56 2015) (docker, local image cst-nusmv:local)
- python3 3.9.6

## run
- started 2026-11-07 14:48:29 KST, ended 15:42:23 KST (scripts/run_engines.sh: selftest, parse, run, report; python3 -I as in README section 2; --timeout 120 for parse and run; nice)
- selftest: SELFTEST_OK; run: 610 / 610 pairs
- the first run (no engine installed) is kept separately in run1_noengines/ (and in its own zip)

## errors observed (not fixed, not re-run; README section 3 rule 2)
- z3b: not importable under python3 -I (ModuleNotFoundError: No module named 'z3'; works without -I, z3 lives in the user site-packages directory). In results/pairs_out.jsonl the z3b key is missing in all 610 rows; REPORT.txt shows z3b as err/na for all.
- parse, NuSMV (smv_pt, 478 formulas): ok 449; 'skip window>128' 24; ERR 5, each "Command '[<NuSMV wrapper>, <q_*.smv>]' timed out after 120 seconds"
- parse, Spot on past-time formulas ("spot_pt_literal", 478 formulas): skip 39; ERR 439 (391 distinct texts), e.g. ">>> (H (b_no_fail -> c_336344e992))\n       ^\nsyntax error, unexpected opening parenthesis" (Spot printed syntax errors for the past-time operator text)
- parse, Spot on future-time formulas (spot_ft): ok 116, no ERR
- run, NuSMV per pair (610): result 568; error "window>128" 32; error "timed out after 120 seconds" 10
- run, Spot per pair: result 92; ERR 6 (message: "Command '[<ltlfilt wrapper>, '-c', '-f', '((b_LAST R ...' ..." as stored in pairs_out.jsonl); key missing in 512 rows (the 512 control pairs carry no future-time formula; observed from the data: spot_ft key missing in exactly the 512 control rows)
- a timeout kills the docker client call; whether the NuSMV or ltlfilt process inside the container kept running after a timeout until the container was removed is not known
