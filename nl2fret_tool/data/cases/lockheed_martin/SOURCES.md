# lockheed_martin: NASA Lockheed Martin Cases (49 cases)

Cases of the original natural-language requirements of the Lockheed Martin Cyber-Physical Challenge problems (inputs of the v4 to v8 experiments). Organized on 2026-11-08. Verified facts are given with their evidence; what could not be verified is stated as "unknown". This folder contains inputs only and **does not contain the reference FRETish (ground truth)** (the originals remain in `experiments/nl4/data/lm_items.jsonl` and elsewhere).

**Of the 61 cases before the split, the 12 FSM cases were moved to `../fsm/`.** The 61-case basis of the earlier evaluations is preserved as `lockheed_martin 49 + fsm 12 = 61` (the 12 rows with `original_group == lockheed_martin` in `../fsm/ORIGIN_MAP.csv` are those 12 cases).

## 1. Files

| File | Contents |
|---|---|
| `cases.jsonl` | 49 lines. Fields: `case_id`, `challenge`, `raw_nl`, `stratum`, `nl_source` (`file`, `locator`), `used_in` (the result folders in which the case was used) |
| `docx_match.csv` | 61 rows (49 in this group + 12 in `fsm/`). For each case, the result of the comparison with the original docx (`match`) and the git blob sha1 of the docx. Produced by `tools/verify_lm_docx.py` |
| `sigdict.json` | Signal dictionary per challenge (keys `"00"` to `"09"`; 9 entries, challenge 7 excluded). The material used by the `+D` method in the v8 dictionary smoke run. sha256 `a190a714c61622b24fd93dcfb83001b3e45fc66c83315c3a6f50b04d2dfd7cf3` (same as the original). The signal table of the FSM challenge is key `"01"`; it is kept only in this file and not copied to `fsm/` |

How it was built: `tools/build_cases.py` reads `experiments/v8_dict8/bench/data/lm_items.jsonl` (the natural-language-only version) and takes the provenance field `nl_source` from `experiments/nl4/data/lm_items.jsonl`. After the script verified that the 61 ids and natural-language texts of the two files are the same, the 12 cases whose text is character-identical to `nasa_papers` were separated into `fsm/`.

## 2. Sources

| Item | Contents | Evidence |
|---|---|---|
| Natural language | Original natural-language requirements (docx) of the 10 Lockheed Martin Cyber-Physical Challenge problems. The `original_models/` folder of the GitHub repository `hbourbouh/lm_challenges` | The `nl_source.file` field, `experiments/nl4/NL2FRET_PROMPT_v4_LM.md` line 111 |
| Reference FRETish (not copied) | Written by NASA directly in FRET: 97 from the LMCPS repository and 13 from the FSM case study | Same document, line 111 |
| Composition (basis: 61 cases before the split) | 61 items, 84 parts, 109 reference versions, 15 items with alternative versions. EB-004 was excluded because it has no corresponding natural language | Same document, lines 111 to 116 |
| Pairing of natural language and reference | `rationale` (the NASA rationale sentence equals the original natural language) 34, `id_order` (requirement id order) 27 (basis: 61 cases before the split) | Same document, line 111; `mapping_basis` in `lm_items.jsonl` |
| Repository | GitHub `hbourbouh/lm_challenges` (description "Cyber-Physical V&V Challenges for the Evaluation of State of the Art Model Checkers", created 2019-04-11, a single branch `master`, 5 commits, last push 2020-02-12). The README contains only "Copyright 2016, Lockheed Martin Corporation. All rights reserved" and the address of a 2016 S5 presentation. No license file | GitHub API and raw README (looked up on 2026-11-08) |
| Commit | All 10 docx files were added in commit `4ee0e32633eb72d5da79863208676412347f3b2f` (2020-02-12 03:07:33Z, "add CoCoSim Fret files"), and the later master HEAD `133447a8943721eaa1d16acf1ba5845b67a98df1` (03:18:35Z) did not change them. The docx contents are therefore the same for any commit taken after 2020-02-12. **The commit that was used when the data was built is not recorded and is unknown** | Per-path commit history lookup (`commits?path=`) |
| Download date | No record. Lower bound 2020-02-12, upper bound 2026-11-01 16:03 (modification time of `experiments/nl4/data/lm_items.jsonl` = the time it was extracted from the instruction document). **The exact date is unknown** | `experiments/nl4/CHANGELOG.md` line 3, file timestamps |
| Original docx | Not on this machine (a search for `*.docx` finds nothing). On 2026-11-08 the 10 docx files of master HEAD were downloaded and compared (the git blob sha1 matched the GitHub tree for 10 of 10); the files were not kept. The download commands are in the header of `tools/verify_lm_docx.py` | `experiments/v8_dict8/bench/NL2FRET_PROMPT_v8_DICT_SMOKE.md` also states that the original docx files are not in that folder |
| Result of the docx comparison | **All 61 cases (49 in this group + 12 in `fsm/`) match the original docx text** (0 `none`): 41 equal one paragraph character for character, 10 occur verbatim in the text of several joined paragraphs, and 10 differ only in whitespace and line breaks (`LM-00_TRIPLEX-RM-002`, `LM-04_NLG-N2p3`, `N4`, `N6`, `N7`, `LM-07_AP-1.3`, `1.4`, `1.10`, `LM-08_SWIM-N1`, `LM-09_EUL-N6`). For the 49 cases of this group alone it is 30 + 9 + 10 | `docx_match.csv` |
| Original of the reference FRETish (not copied) | The FRET v3.1.0 example projects `LMCPS/LM_requirements.json` (97 entries) and `FiniteStateMachine/fsm_reqts_and_vars.json` (13 entries). They are in `~/fret/import/caseStudies/` on this machine, and the counts equal the 97 and 13 stated in the document | The files above, `~/fret/README.md` |
| Signal dictionary | The signal tables of the challenge requirement documents (the Input Scope and Output Scope tables and the definition table of challenge 4) were copied cell by cell as they are. No dictionary was made for challenge 7 (autopilot) because its signal tables are empty or contain requirement sentences | Header of `experiments/v8_dict8/bench/tools/make_sigdict.py` |

## 3. Cases per challenge and original files

| Challenge | This group | `fsm/` | Original (before the split) | Original file (`hbourbouh/lm_challenges`) |
|---|---|---|---|---|
| 00_TRIPLEX | 4 | 0 | 4 | `original_models/0_triplex/0_triplex_reqs.docx` |
| 01_FSM | 1 (`LM-01_FSM-N07`) | 12 | 13 | `original_models/1_fsm/1_fsm_reqs.docx` |
| 02_TUSTIN | 3 | 0 | 3 | `original_models/2_tustin/2_tustin_reqs.docx` |
| 03_REG | 10 | 0 | 10 | `original_models/3_regulators/3_regs_reqs.docx` |
| 04_NLG | 6 | 0 | 6 | `original_models/4_nlguide/4_nlguide_reqs.docx` |
| 05_NN | 4 | 0 | 4 | `original_models/5_nn/5_nn_reqs.docx` |
| 06_EB | 2 | 0 | 2 | `original_models/6_eb/6_eb_reqs.docx` |
| 07_AP | 10 | 0 | 10 | `original_models/7_autopilot/7_ap_requirements.docx` |
| 08_SWIM | 2 | 0 | 2 | `original_models/8_swim/8_swim_reqs.docx` |
| 09_EUL | 7 | 0 | 7 | `original_models/9_euler/9_euler321_I2B_reqs.docx` |
| Total | 49 | 12 | 61 | |

Requirement type (`stratum`): this group has 15 conditional, 22 invariant, 10 timed and 2 scoped (49 in total). The 61 cases before the split were 27 conditional, 22 invariant, 10 timed and 2 scoped, and all 12 cases in `fsm/` are conditional. The type was assigned mechanically from the reference structure (v4 document, section 2.8).

## 4. Where the cases were used (`used_in`, verified through `snapshot/items_used.jsonl` of each result folder)

| Result folder | This group | `fsm/` | Basis before the split | Note |
|---|---|---|---|---|
| `nl4/results_smoke` | 5 | 1 | 6 | v4 smoke run |
| `nl5/results_smoke2` | 5 | 1 | 6 | v4 second smoke run |
| `nl6/results_pre` | 5 | 1 | 6 | v6 preflight, first attempt |
| `nl7/results_pre` | 5 | 1 | 6 | v6 preflight, rerun |
| `nl7/results_lm` | 49 | 12 | 61 | v6 main run |
| `v8_dict8/bench/results_dict8` | 16 | 2 | 18 | v8 dictionary smoke run (the first 2 items in file order from each of the 9 challenges, excluding challenge 7 (autopilot); v8 document line 23) |

## 5. Notes
- **The 12 FSM cases were separated**: the 12 cases of `01_FSM` (`LM-01_FSM-N01` to `N13`, except `N07`) have natural language that is character-identical to the FSM cases of NASA/TM-20220007510 (RC22), so they are stored once in `../fsm/` (they are not kept in `nasa_papers/` either). The evidence and the verification method are in `../fsm/SOURCES.md`.
- **`LM-01_FSM-N07` stays in this group.** Its challenge is `01_FSM`, but it differs by one word from `FSM-007` of RC22 (PULLUP versus MANEUVER), so it is not the same case. Decision (2026-11-08): it is not moved to `fsm/`; it is recorded in `../fsm/README.md` as a near candidate.
- Basis of the name "NASA Lockheed Martin cases": the copyright notice of the natural-language requirements is **Lockheed Martin** (repository README, 2016), while the reference FRETish is a NASA FRET example. The repository `hbourbouh/lm_challenges` is given as the public location of "The Ten Lockheed Martin CPS Challenge Problems (LMCPS)" by the LM10 paper (NTRS 20205000433, line 80 of the extracted PDF text) and the SL21 slides (NTRS 20210014189, line 84), both NASA-side documents. The LM10 paper cites the original presentation as Chris Elliot, S5 conference, 2015 (line 15; the address in the repository README is the 2016 Proceedings). Whether the account `hbourbouh` is the same person as the NASA researcher Hamza Bourbouh was not verified.
- **Redistribution caution**: `cases.jsonl` in this folder and `../fsm/cases.jsonl` contain the sentences of the docx files above as they are; the original repository has no license file, and its README states "All rights reserved". This must be checked before the repository is published (no legal judgment was made).
- The `lm_items.jsonl` used for the v7 TEST (evaluation) run (the version that has only `id`, `raw_nl`, `stratum`, `family` and `challenge`; sha256 starting with `a8314c94`) has the same ids and natural-language texts as the 61 cases before the split (observed). Those 61 cases are `lockheed_martin` 49 + `fsm` 12.
