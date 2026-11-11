# Verification Results and Unverified Items

## Verified (rerun after the cleanup)
| Item | Result |
|---|---|
| File counts per folder before and after the move | All 18 moved items match (`MOVE_LOG.csv`) |
| Rule selftest (`v8_dict8`) | `SELFTEST_OK 21 rule cases` |
| `cli.py --selftest` (`v8_dict8`) | `cli selftest ok` |
| v8 dictionary usage (`dict_usage.py`) | DIRECT 24.6%, DIRECT+D 54.4%, EARS 21.5%, EARS+D 54.4%, MASTeR 18.6%, MASTeR+D 52.2% (same as before) |
| ltlpack selftest | `SELFTEST_OK` |
| Hash manifest recheck | `v8_dict8` FROZEN_MANIFEST 38/38, RESULTS_DICT8_BEFORE_RLZ 34/34, BENCH_FILES 40/40; `v7_dev1` DEV1_FROZEN 4/4, BENCH_FILES 40/40; `v7_dev0` DEV0_FROZEN 3/3; `nl7` FROZEN 33/33, RULES_FROZEN 2/2; `nl6` FROZEN 33/33; `nl3` RULES_FROZEN 2/2; ltlpack MANIFEST 5/5 |
| Secret scan | 0 matches for API key, token and private key patterns; no `.env` files (as surveyed before the move). No file names to report |

## Unverified
| Item | Reason |
|---|---|
| judge3/judge4/judge5, `sk.py`, `rq.py` | The code was not found on this machine |
| Number of matches in the judge4 (z3) control experiment | Same as above |
| `ctl.py`, `ctl2.py`, `ctl3.py`, `ctl_res*.json` and `NL2FRET_ltl_engines_results.md` | Not found on this machine (searched on 2026-11-09 for the `nusmv_paper` test). The 88 constant-mutation control pairs could not be rebuilt, and the list of 45 unexplained mismatches in that document was not available |
| judge4 comparison in `experiments/nusmv_paper` | Only the stored judge4 verdicts (`z3_role`, `z3_miss`, `z3_alarm` in `pairs.jsonl`) were compared. judge4 itself was not run, so its horizon variants (instruction D4.3) were skipped. Whether the stored `z3_role` of the generated pairs is anchor mode or name-fixed mode is not recorded in the data |
| NuSMV and Spot figures of ltlpack (for example, 434 NuSMV matches) | Not rerun: it requires starting the Docker containers and about 54 minutes. Only the selftest was checked. Observation from the `nusmv_paper` test (2026-11-09): when the four stored NuSMV values of the 568 pairs with a stored result were derived again with single-spec queries, 523 pairs were identical and 45 differed, and all 45 equal the values that follow from NuSMV printing the four results of one file in the order S3, S4, S1, S2 (`experiments/nusmv_paper/bench/nusmv_paper/REPORT.md`, section 5.5). The stored files and the delivered ltlpack results were not changed |
| Resume of the recording tool of `experiments/judge_recording` (`judge_cli.py --record-dir`, run again on the same directory) | Not executed: the instruction of 2026-11-09 allows only a code reading, which is in `RECORDING_CHANGES.md`, section 5. The recording paths for N/M pairs, timeouts, truncated output and skipped queries were run only against a stub script, not against NuSMV, because the real check (27 pairs) contained none of these cases |
| Rerunning the run scripts of the experiment folders (`run_*.sh`) | Not rerun because they need model calls and Docker. The moves were made per folder, so the relative paths remain valid (speculative) |
| Running `posthoc_sensitivity.py` after the edit | Not run because it overwrites a result `.md` file. Only the syntax was checked |
| Selftests of the other `experiments/*` runs | Only `v8_dict8` was run. The code copies of the other runs differ from each other |
| Full package behavior of `nl2fret/.venv` | Only `pip --version` and `import torch, transformers` were checked |
| `requirements.txt` | Not created because there is no pinned list |
