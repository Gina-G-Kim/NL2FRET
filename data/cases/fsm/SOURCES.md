# fsm: 12 FSM Cases

A group that stores once the **12 cases that appeared with character-identical natural language** in the Lockheed Martin challenge `01_FSM` and in NASA/TM-20220007510 (RC22, FSM). Organized on 2026-11-08. By the project owner's decision, these 12 cases are removed from `nasa_papers/` and `lockheed_martin/` and kept only here. Verified facts are given with the evidence file and line numbers; what could not be verified is stated as "unknown". Only inputs are included, and the **reference FRETish (ground truth) was not copied** (the originals remain in `experiments/`).

## 1. Files

| File | Contents | Lines |
|---|---|---|
| `cases.jsonl` | One case per line. Fields: `case_id`, `raw_nl`, `challenge`, `stratum`, `origins` (the two original memberships and their provenance), `used_in` (where the case was used) | 12 |
| `ORIGIN_MAP.csv` | 12 cases x 2 original memberships. Columns: `case_id`, `original_group`, `original_id`, `original_source`, `same_case_as`, `text_match` | 24 (+ header) |

`case_id` is the Lockheed Martin id (`LM-01_FSM-N..`). The earlier evaluations and result folders use this id, so it keeps the counts and ids consistent. The RC22 ids (`FSM-0..`) are in the `nasa_papers` rows of `ORIGIN_MAP.csv`. The two memberships are **the same case**; each names the other in the `same_case_as` column, and `text_match` is `exact`.

## 2. How the counts connect

| Group | After the split | Number taken from fsm (`original_group` in `ORIGIN_MAP.csv`) | Before the split |
|---|---|---|---|
| `lockheed_martin` | 49 | 12 (`lockheed_martin` rows) | 61 |
| `nasa_papers` | 183 | 12 (`nasa_papers` rows) | 195 |
| Total of distinct cases | 183 + 49 + 12 = 244 | | 195 + 61 - 12 = 244 |

The evaluation on the 61 Lockheed Martin cases is obtained by combining the `case_id` values of `lockheed_martin/cases.jsonl` (49) with the 12 ids that have `original_group == lockheed_martin` in `ORIGIN_MAP.csv`. On every run, `tools/build_cases.py` checks that this reconstruction equals the id sets of the 61 and 195 cases before the split.

## 3. Collection sources

| Membership | Collection source | Case location | Evidence |
|---|---|---|---|
| `lockheed_martin` | GitHub repository `hbourbouh/lm_challenges`, `original_models/1_fsm/1_fsm_reqs.docx` (60,223 bytes, challenge `01_FSM`) | `Requirements #1` to `#13` in the docx (`nl_source.locator`) | `experiments/nl4/data/lm_items.jsonl` lines 5 to 17, `experiments/nl4/NL2FRET_PROMPT_v4_LM.md` lines 111 and 114. The existence of the repository and the file was verified on 2026-11-08 through the GitHub API and the raw file |
| `nasa_papers` (RC22) | NASA/TM-20220007510 *Realizability Checking of Requirements in FRET (FSM)*, NTRS 20220007510 (title match verified through the NTRS API, 2026-11-08). The PDF file is `experiments/nl2fret/pdfs/TechnicalReport__FRET_Realizability_Checking.pdf` | Table 3 (PDF page 14) and table 4 (PDF page 15) | `experiments/nl2fret/NL2FRET_PROMPT_v1.md` line 124 (source list) and line 3737 (link), `experiments/nl2fret/data/pairs_v1.jsonl` lines 13 to 25. The text of the first PDF page reads "NASA/TM-20220007510 Realizability Checking of Requirements in FRET", and tables 3 and 4 of the same PDF contain FSM-001 to 013 (verified with `pdftotext`) |

### 3.1 History of the Lockheed Martin repository and when it was downloaded (investigated 2026-11-08)

| Item | What was verified |
|---|---|
| Repository | `hbourbouh/lm_challenges`, description "Cyber-Physical V&V Challenges for the Evaluation of State of the Art Model Checkers", created 2019-04-11, a single branch `master`, no releases, no license file (API `license: null`) |
| README | It contains only "Copyright 2016, Lockheed Martin Corporation. All rights reserved" and the address of a 2016 S5 presentation (`mys5.org`). That is, the copyright notice of these natural-language requirements is Lockheed Martin |
| Commits | 5 in total: `0b14403` 2019-04-11 first commit, `4f9ca18` and `2676e51` 2019-04-11 README edits, `4ee0e32633eb72d5da79863208676412347f3b2f` 2020-02-12 03:07:33Z "add CoCoSim Fret files", `133447a8943721eaa1d16acf1ba5845b67a98df1` 2020-02-12 03:18:35Z "export Models to R2017b" (master HEAD, last push) |
| When the docx files were added | The 10 docx files in `original_models/`, including `1_fsm_reqs.docx`, have a per-path commit history consisting of `4ee0e326` only. The later HEAD commit did not change them either |
| Conclusion | The contents of this docx are the same for any commit taken after 2020-02-12. **The commit that was actually used when the data was built is not recorded in this repository and is unknown** (by content, any commit from `4ee0e326` on is identical) |
| Download date | No record. The lower bound is 2020-02-12 (the day the docx files were pushed to the repository); the upper bound is 2026-11-01 16:03:37, the modification time of `experiments/nl4/data/lm_items.jsonl` (the time the data was extracted from the instruction document). **The exact date is unknown** |
| File integrity | The git blob sha1 `004ad48e641e1847c31875447ff6fc5956c12d3a` of the downloaded `1_fsm_reqs.docx` equals the value in the GitHub tree. All 10 docx files match in the same way |
| Citations by other documents | The LM10 paper (NTRS 20205000433) and the NTRS 20210014189 slides (*Capturing and Analyzing Requirements with FRET*, Mavridou) give this repository address as the public location of "The Ten Lockheed Martin CPS Challenge Problems (LMCPS)" (lines 80 and 84 of the extracted PDF text, respectively) |

## 4. Collection method

| Membership | Method | Evidence |
|---|---|---|
| `lockheed_martin` | Taken item by item from the original natural-language requirements (docx) of the challenge problem. The reference FRETish was written by NASA directly in FRET (the FRET example projects `LMCPS/LM_requirements.json` with 97 entries and `FiniteStateMachine/fsm_reqts_and_vars.json` with 13 entries; both files are in `~/fret/import/caseStudies/` on this machine and the counts were verified) and is **not copied here**. The basis of the pairing between natural language and reference is `rationale` (the NASA rationale sentence equals the original natural language) for 11 of the 12 cases and `id_order` (requirement id order) for 1 case, `LM-01_FSM-N04` | `experiments/nl4/NL2FRET_PROMPT_v4_LM.md` line 111, `experiments/nl7/NL2FRET_PROMPT_v6_LM.md` lines 155 to 167 (column `mapping_basis`) |
| `nasa_papers` (RC22) | Only the pairs for which both natural language and FRETish are **printed** in a public NASA technical report were collected, and a script verified a character-level match in the text of the report PDF (ignoring only differences in whitespace, hyphenated line breaks and arrow notation) | `experiments/nl2fret/NL2FRET_PROMPT_v1.md` line 53, `experiments/nl2fret/results_verify/strict_report.json` (for all of FSM-001 to 013, PDF page 14 or 15 is recorded in `raw_exact`) |

## 5. How identity (character-level match) was verified

1. `tools/build_cases.py` reads the 13 RC22 cases of `experiments/nl2fret/data/pairs_v1.jsonl` and the 13 `01_FSM` cases of `experiments/v8_dict8/bench/data/lm_items.jsonl`, finds the pairs through whitespace normalization, and then **compares the raw strings with `==` without normalization**. All 12 paired cases must match; if even one differs, the script stops. The files compared are `pairs_v1.jsonl`, `nl4/data/lm_items.jsonl` and `v8_dict8/bench/data/lm_items.jsonl`.
2. Independently of the script, the four original files (`pairs_v1.jsonl` and the `lm_items.jsonl` of `nl4`, `nl7` and `v8_dict8`) were read again and compared with `raw_nl` of `fsm/cases.jsonl`. **12 of 12 cases were character-identical to the four originals.**
3. **Comparison with the original docx** (2026-11-08): the `1_fsm_reqs.docx` of GitHub master HEAD was downloaded and compared with `tools/verify_lm_docx.py`. All 12 fsm cases are character-identical to the docx text (11 equal one paragraph, 1 occurs verbatim inside the text of several joined paragraphs). The per-case results are the 12 rows with `group == fsm` in `../lockheed_martin/docx_match.csv`. That is, the RC22 text (PDF), the Lockheed Martin data and the original Lockheed Martin docx agree on these 12 cases.
4. The pair that did not match is RC22 `FSM-007` and `LM-01_FSM-N07`. Their original texts differ by one word (section 8).

## 6. Evidence per case

Line numbers are all 1-based lines of the respective file. The `lm_items.jsonl` line numbers are the same in the three files `nl4`, `nl7` and `v8_dict8`.

| fsm `case_id` | RC22 id | RC22 location | LM location | `pairs_v1.jsonl` line | v1 document table line | `lm_items.jsonl` line | v6 document table line | Result folders where used (Lockheed Martin side) |
|---|---|---|---|---|---|---|---|---|
| `LM-01_FSM-N01` | `FSM-001` | Table 3, PDF page 14 | Requirements #1 | 13 | 76 | 5 | 155 | nl4 smoke, nl5 smoke2, nl6 pre, nl7 lm, nl7 pre, v8 dict8 |
| `LM-01_FSM-N02` | `FSM-002` | Table 3, PDF page 14 | Requirements #2 | 14 | 77 | 6 | 156 | nl7 lm, v8 dict8 |
| `LM-01_FSM-N03` | `FSM-003` | Table 3, PDF page 14 | Requirements #3 | 15 | 78 | 7 | 157 | nl7 lm |
| `LM-01_FSM-N04` | `FSM-004` | Table 3, PDF page 14 | Requirements #4 | 16 | 79 | 8 | 158 | nl7 lm |
| `LM-01_FSM-N05` | `FSM-005` | Table 3, PDF page 14 | Requirements #5 | 17 | 80 | 9 | 159 | nl7 lm |
| `LM-01_FSM-N06` | `FSM-006` | Table 3, PDF page 14 | Requirements #6 | 18 | 81 | 10 | 160 | nl7 lm |
| `LM-01_FSM-N08` | `FSM-008` | Table 4, PDF page 15 | Requirements #8 | 20 | 83 | 12 | 162 | nl7 lm |
| `LM-01_FSM-N09` | `FSM-009` | Table 4, PDF page 15 | Requirements #9 | 21 | 84 | 13 | 163 | nl7 lm |
| `LM-01_FSM-N10` | `FSM-010` | Table 4, PDF page 15 | Requirements #10 | 22 | 85 | 14 | 164 | nl7 lm |
| `LM-01_FSM-N11` | `FSM-011` | Table 4, PDF page 15 | Requirements #11 | 23 | 86 | 15 | 165 | nl7 lm |
| `LM-01_FSM-N12` | `FSM-012` | Table 4, PDF page 15 | Requirements #12 | 24 | 87 | 16 | 166 | nl7 lm |
| `LM-01_FSM-N13` | `FSM-013` | Table 4, PDF page 15 | Requirements #13 | 25 | 88 | 17 | 167 | nl7 lm |

The v1 document table lines refer to `experiments/nl2fret/NL2FRET_PROMPT_v1.md`, and the v6 document table lines to `experiments/nl7/NL2FRET_PROMPT_v6_LM.md`.

## 7. In which experiment sets the cases were used

| Experiment set | Of the 12 | Evidence |
|---|---|---|
| v1 pairs (`nl2fret/data/pairs_v1.jsonl`) | 12 | Section 6 above. In `nl2fret/results_nl2fret` (10 repetitions) and `results_nl2fret_5reps`, all 12 cases appear in `calls.jsonl` (110 and 55 rows per id) and in `scored.jsonl` (60 and 30 rows per id). The ids are not found in `results_pilot/*.jsonl` |
| v2 candidate pool `pool_v2`, v2 main run, nl3 calibration, v7 development set | 0 | RC22 and its report were excluded from the v2 pool (`experiments/nl2fret_v2/NL2FRET_PROMPT_v2.md` line 75). The nl3 calibration is the pool minus the v2 main run, and all 94 v7 development items are in the pool (data comparison) |
| `nl4/results_smoke`, `nl5/results_smoke2`, `nl6/results_pre`, `nl7/results_pre` | 1 each (`N01`) | `snapshot/items_used.jsonl` of each folder (of the 6 items, only `N01` is an FSM case) |
| `nl7/results_lm` (v6 main run, 61 items) | 12 | `nl7/results_lm/snapshot/items_used.jsonl` (12 of the 61) |
| `v8_dict8/bench/results_dict8` (v8 dictionary smoke run, 18 items) | 2 (`N01`, `N02`) | `snapshot/items_used.jsonl`; the selection method is in `experiments/v8_dict8/bench/NL2FRET_PROMPT_v8_DICT_SMOKE.md` line 23 |

The signal table of the FSM challenge is key `"01"` of `../lockheed_martin/sigdict.json` (header of `experiments/v8_dict8/bench/tools/make_sigdict.py`). It was not copied to this folder to avoid duplication.

## 8. FSM-category candidates that were not moved (decided 2026-11-08)

Whether other cases could be regarded as FSM cases was checked by id, challenge, source code and natural-language content. **None of the following was moved**; the project owner decided on 2026-11-08 to keep them out of `fsm/`. The id lists are in `README.md`.

| Candidate | Location | Evidence | Why it was ambiguous |
|---|---|---|---|
| `LM-01_FSM-N07` (Lockheed Martin, `01_FSM`), 1 case | `lockheed_martin/cases.jsonl` | The challenge is `01_FSM`. Original text "...change states from **PULLUP** to TRANSITION when the system is supported and sensor data is good." (`lm_items.jsonl` line 11) | It is the counterpart of `FSM-007` with the same number, but its natural language is different. It was verified that the original docx says PULLUP (see the cause investigation below) |
| `FSM-007` (RC22), 1 case | `nasa_papers/cases.jsonl` | The id is `FSM-007`; the source is RC22 table 4 (PDF page 15). Original text "...change states from **MANEUVER** to TRANSITION when ..." (`pairs_v1.jsonl` line 19). There is a record that a character-level match in the RC22 PDF was verified (`strict_report.json`) | It differs from `N07` above by one word (PULLUP, MANEUVER). The difference was traced to a difference between the source documents (see the cause investigation below); whether to treat them as the same case was left to the project owner, who decided not to move them |
| 14 FRETish inputs of legacy experiments with an FSM-prefixed id | `nasa_papers/legacy_fretish_inputs.jsonl` | 10 from `fret_template_bench` (`FSM-001`, `FSM-001v2`, `FSM-002`, `FSM-003`, `FSM-006`, `FSM-007`, `FSM-008v1`, `FSM-009`, `FSM-010`, `FSM-011`; sources: 8 from NASA/TM-2019-220365, 2 from NTRS 20200002241) and 4 from `fret_retest_v2` (`FSM-006t`, `FSM-007t`, `FSM-001r`, `FSM-001v2`; sources: 3 from RC22, 1 from CP22) | The inputs are **FRETish sentences**, not natural language, so the kind of case is different, and it was not checked whether they are the same requirements as these 12 cases |
| 10 MLV mode-transition descriptions | `nasa_papers/cases.jsonl` | `X-MLV-011`, `016`, `019`, `021`, `063`, `066`, `070`, `073`, `075`, `076`. The natural language has the form "The transition from A Mode to B Mode shall occur ..." | The name is not FSM, and the source is the Mechanical Lung Ventilator (ABZ 2024). The content describes state transitions, but there is no evidence of a relation to the FSM challenge, so this is **speculative** |

The remaining hits of the keyword search (the "Recruitment Maneuver" of `X-MLV-013`, `018` and `054`, and the "evasive maneuver" of `LM-08_SWIM-N2`) were regarded as false positives that only share a word and were left out of the candidates. The "Standby Mode" of `X-MLV-040` and `043` was not included in the MLV candidates above because it is unknown whether it is anything more than a name shared with the STANDBY state of the FSM challenge (unknown).

### 8.1 Why `FSM-007` and `LM-01_FSM-N07` differ (investigated 2026-11-08)

| Source | Natural language of the 7th state-transition requirement | How it was verified |
|---|---|---|
| Original Lockheed Martin docx (`1_fsm_reqs.docx`, GitHub HEAD) | "...change states from **PULLUP** to TRANSITION when the system is supported and sensor data is good." | Verified directly from the docx paragraphs (the 6th autopilot sentence among the 12 `change states from` sentences) |
| `rationale` of `FSM-007` in the FRET v3.1.0 examples `FiniteStateMachine/fsm_reqts_and_vars.json` and `LMCPS/LM_requirements.json` | "...from **PULLUP** to TRANSITION ..." | Verified in both JSON files. **The FRETish of the same item uses `ap_maneuver_state` in its condition** (the rationale of `FSM-006` in the same file says MANEUVER) |
| `FSM-007` in RC22 PDF table 4 (PDF page 15) | "...from **MANEUVER** to TRANSITION ...", and the FRETish next to it also uses `ap_maneuver_state` | Verified with `pdftotext`; it also agrees with the character-level match record in `strict_report.json` |

Summarized as observations: inside NASA's FRET example, the natural language (rationale, PULLUP) and the FRETish (maneuver state) of requirement 7 disagree, and the Lockheed Martin docx uses PULLUP. The RC22 paper table gives the natural language as MANEUVER, which matches the FRETish. Whether the paper's authors changed it deliberately is unknown (speculative). Because of this difference, requirement 7 of the two memberships is not the same case, and under the separation rule (only character-identical cases go to `fsm/`) each was left in its own group.

## 9. Unknown
- The commit of the Lockheed Martin repository used when the data was built (by content, any commit from `4ee0e326` on is the same) and the exact download date (only verified to lie after 2020-02-12 and before 2026-11-01 16:03).
- Why the authors of the RC22 paper wrote MANEUVER in the natural language of `FSM-007`.

Resolved by this investigation: the RC22 PDF file (`TechnicalReport__FRET_Realizability_Checking.pdf`), the history and license notice of the Lockheed Martin repository, and the origin of the difference between `FSM-007` and `N07`.
