# NOTES (2026-11-07)

## versions
- ltlfilt --version: command not found (Spot not installed, see INSTALL_NOTES.md)
- NuSMV / nuXmv version: not available (no executable found, see INSTALL_NOTES.md)
- python3 3.9.6; z3 module version 5.1.0 (found in the user site-packages directory)

## observation, not fixed and not re-run (README section 3 rule 2)
- commands run with python3 -I as in README section 2: selftest -> SELFTEST_OK; parse -> printed 'NuSMV binary: None | ltlfilt: None'; run (no --nusmv, default --timeout given as 120) -> 610 / 610 pairs, total 0.216 s wall; report -> REPORT.txt
- in REPORT.txt the z3b column is 0 (err/na) for all 512 controls and 'n/a' for all 98 generated pairs, and the median seconds per pair for z3b is None; sandbox_reference_z3b.txt shows z3b results for the same data (total 478 matches)
- observed with the same interpreter: 'python3 -I -c "import z3"' prints ModuleNotFoundError: No module named 'z3'; 'python3 -c "import z3"' (without -I) works, z3 file located in the user site-packages directory. Python flag -I ignores the user site-packages. This was observed after the run; the run was not repeated
- consequence: in this run no engine produced a result (NuSMV and Spot not installed, z3b not importable under -I)

## timing
- start 2026-11-07 13:57:00 KST; run and report finished within the same minute
