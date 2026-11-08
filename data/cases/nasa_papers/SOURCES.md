# nasa_papers: Cases from NASA Technical Reports, Other Papers, and Public Repositories

Input cases of the experiments that convert natural-language requirements into FRETish (v1 to v7). Organized on 2026-11-08. Facts that were verified are given with their evidence (original file or document line); what could not be verified is stated as "unknown". This folder contains inputs only and **does not contain the reference FRETish (ground truth)** (the originals remain in the corresponding data files inside `experiments/`).

**Of the 195 cases before the split, the 12 FSM cases of RC22 were moved to `../fsm/`.** `nasa_papers 183 + fsm 12 = 195`; the RC22 ids of those 12 cases are in the rows with `original_group == nasa_papers` in `../fsm/ORIGIN_MAP.csv`.

## 1. Files

| File | Contents | Lines |
|---|---|---|
| `cases.jsonl` | One line per distinct natural-language text. Fields: `case_id`, `raw_nl`, `source_code`, `origin`, `provenance` (original source), `used_in` (in which experiment sets and under which id the case was used), optional fields `stratum`, `nl_fretish_like` | 183 |
| `legacy_fretish_inputs.jsonl` | Inputs of the legacy experiments (`fret_template_bench`, `fret_retest_v2`). Their input is **a FRETish sentence, not natural language**, so they are kept separately with `text_kind: fretish` | 71 (20 + 51) |

How it was built: `tools/build_cases.py` (repository root) only reads `experiments/` and produces these files. A natural-language text that is present in several sets is merged into one line and all memberships are listed in `used_in`.

## 2. Source classification (`origin`)

| origin | Meaning | Cases |
|---|---|---|
| `nasa_tr` | Natural language and FRETish printed together in a NASA technical report (NASA/TM) | 42 (54 before the split; the 12 RC22 FSM cases are in `fsm/`) |
| `paper_or_slides` | Papers and slides on NTRS (LM10, BG20, TUT22) | 3 |
| `external_repo` | Public GitHub repositories and their case-study documents (MLV, UC69, DRONE) | 138 |
| Total | | 183 (195 before the split) |

Whether `external_repo` should count as "other papers" cannot be read from the request, so it was **kept in the same group and distinguished by `origin`**. To separate it, filter on `origin == "external_repo"`.

## 3. Collection details per source

### 3.1 NASA technical reports (nasa_tr, 42)

"(verified)" after an NTRS id means that on 2026-11-08 the id was looked up through the public NTRS API (`https://ntrs.nasa.gov/api/citations/<id>`) and the title equals the title recorded in the data. The earlier notes "assumed equal to the report number", "NTRS id not checked" and "NTRS id unknown" are all resolved (table in section 3.4).

| Code | Document | NTRS id | Cases | Location | Verification method |
|---|---|---|---|---|---|
| TC4 | NASA/TM-20240006865 Recommendations on Evidence and Process for Certification of Learning-enabled Components in Aerospace Systems | 20240006865 (verified) | 10 | Table 4 and others | Script (character comparison with the PDF) |
| WF23 | NASA/TM-20230010160 Wildfire-fighting Use Case Requirements to Monitor | 20230010160 (verified) | 9 | Section 4.1 and others | Visual check by a person (`manual`) |
| IR20 | NASA/TM-2020-20205011049 Integration and Evaluation of the AdvoCATE, FRET, CoCoSim, and Event-B Tools on the Inspection Rover Case Study | 20205011049 (verified) | 7 | NL section 4.4, FRETish section 4.6 and others | `manual` |
| PLC23 | NASA/TM-20230003752 Automated Verification of Programmable Logic Controller Programs against Structured Natural Language Requirements | 20230003752 (verified) | 2 | NL section 4.1, FRETish figure 4.2a | `manual` |
| CP22 | NASA/TM-20220000049 Integrating FRET with Copilot | 20220000049 (verified) | 1 | Figure 2.2 (PDF page 14) | Script |
| CR21 | NASA/TM-2021-20210013008 Compositional Realizability Checking within FRET (Liquid Mixer) | 20210013008 (verified) | 12 | Table | Script |
| RC22 | NASA/TM-20220007510 Realizability Checking of Requirements in FRET (FSM) | 20220007510 (verified) | 1 (`FSM-007`) | Table 4 (PDF page 15) | Script |

### 3.2 NTRS papers and slides (paper_or_slides, 3)
| Code | Document | NTRS id | Cases |
|---|---|---|---|
| LM10 | The Ten Lockheed Martin Cyber-Physical Challenges: Formalized, Analyzed, and Explained (RE 2020) | 20205000433 (verified) | 1 |
| BG20 | Bridging the Gap Between Requirements and Model Analysis: Evaluation on Ten Cyber-Physical Challenge Problems | 20200002241 (verified) | 1 |
| TUT22 | FRET Tutorial (slides, not a TM) | 20220009659 (verified) | 1 |

### 3.3 Public repositories (external_repo, 138)
| Code | Description | Repository and commit | Cases | Source of the natural language | Verification method |
|---|---|---|---|---|---|
| MLV | Mechanical Lung Ventilator, ABZ 2024 case study | `valu3s-mu/FRETISH-requirements` @ `cf849717be5903b6abb5d4eb2bfc2f78ab174a4b`. GitHub description "A repository of FRETISH requirements sets for a variety of Use Cases. Inititally for demonstrating refactoring functionality in Mu-FRET.", created 2024-01-15, **no license** (API `license: null`). When looked up on 2026-11-08, this commit equals the HEAD of `main` (2025-12-15, "Updating names") | 79 | Requirement sentences of the official requirements PDF | `verbatim_in_pdf` (a script verified a character-level match) |
| UC69 | VALU3S use cases 6 and 9 | Same repository and commit as above | 18 | NL cells of the requirements table | `table_cell_in_pdf` |
| DRONE | Drone requirements, REFSQ 2025 | `oisinsheridan/refsq2025` @ `db34d50eaa051bb1a7ef1c145bd07e291d0b2f65`. GitHub description "Requirements used in the paper 'Sharper Specs for Smarter Drones: Formalising Requirements with FRET' at REFSQ2025", license CC-BY-4.0 (API). This commit equals the HEAD of `main` (2025-03-31, "Added licence text README.md") | 41 | `Natural_Language_Requirements.xlsx` of the same repository | `xlsx_and_json_agree` |

The file inside the repository, the requirement id, and the PDF name and pages of each case are in the `provenance` field of `cases.jsonl` (`file`, `reqid`, `nl_pdf`, `nl_pages`).

### 3.4 Report PDF files and NTRS verification table (2026-11-08)

Which document each of the 11 PDFs in `experiments/nl2fret/pdfs/` is was determined from the title and report number in the text of its first page (`pdftotext`), and the NTRS ids were verified from the title, type and registration date in the NTRS API. The "report number" column is the value recorded in the NTRS record; an empty value means that NTRS does not record one.

| Code | PDF file | NTRS id | Title match | Report number in NTRS | Type, registration date |
|---|---|---|---|---|---|
| TC4 | `TC4.pdf` | 20240006865 | match | (none) | TM, 2024-05-28 |
| WF23 | `TR_UseCase_Reqts-8.pdf` | 20230010160 | match | NASA/TM-20230010160 | TM, 2023-07-11 |
| IR20 | `FOLRover_TR_NASATemplate 4.pdf` | 20205011049 | match | NASA/TM-20205011049 | TM, 2020-12-03 |
| PLC23 | `Adam-2023-Automated Verification of Programmable Logic Controller Program...-vor.pdf` | 20230003752 | match | NASA/TM-20230003752 | TM, 2023-03-20 |
| CP22 | `copilot.pdf` | 20220000049 | match | NASA/TM-20220000049 | TM, 2022-01-17 |
| CR21 | `TechnicalReport__Unrealizability_in_FRET_FSESubmission.pdf` | 20210013008 | match | (none) | TM, 2021-04-01 |
| RC22 | `TechnicalReport__FRET_Realizability_Checking.pdf` | 20220007510 | match | (none) | TM, 2022-05-13 |
| LM10 | `LM10.pdf` | 20205000433 | match | (none) | Conference paper, 2020-04-02 |
| BG20 | `20200002241.pdf` | 20200002241 | match | ARC-E-DAA-ARC_61118_TN75645 | Conference paper, 2020-04-06 |
| TUT22 | `tutorial.pdf` | 20220009659 | match | (none) | Presentation, 2022-06-22 |
| RZ19 (for legacy experiments) | `20190033980.pdf` | 20190033980 | match | NASA/TM-2019-220365 | TM, 2019-12-16 |

The report numbers printed on the first page of the PDFs are RC22 `NASA/TM-20220007510`, CR21 `NASA/TM-2021-20210013008`, CP22 `NASA/TM-20220000049`, WF23 `NASA/TM-20230010160`, IR20 `NASA/TM-2020-20205011049`, PLC23 `NASA/TM-20230003752`, TC4 `NASA/TM-20240006865` and RZ19 `NASA/TM-2019-220365`. The cover of `tutorial.pdf` says "May 02, 2022", while the NTRS registration date is 2022-06-22 and the distribution date (`distributionDate`) is 2022-07-12; they differ (`experiments/fret_retest_v2/RETEST_PROMPT_v2.md` line 2690 contains the same note, "NTRS shows July 12, 2022").

The copyright determination of the NTRS record (`copyright.determinationType`) is `MAY_INCLUDE_COPYRIGHT_MATERIAL` for IR20, CP22 and PLC23, and `PUBLIC_USE_PERMITTED` for the rest (TC4, WF23, CR21, RC22, LM10, BG20, TUT22, RZ19, RQ20, SL21). The distribution class (`distribution`) is `PUBLIC` for all, and export control (`exportControl`) is "no" for all.

Of the source codes of the legacy experiment `fret_retest_v2`, the two whose document title was unknown in `legacy_fretish_inputs.jsonl` of this folder were identified as follows.

| Code | Document | NTRS id | How it was verified |
|---|---|---|---|
| SL21 | *Capturing and Analyzing Requirements with FRET* (presentation, Anastasia Mavridou, file name `FRET2021Sfymmhv2.pdf`) | **20210014189** (registered 2021-04-21) | In an NTRS search, 2 of 7 results have this title (20210014189, 20220007610). The downloaded PDF of 20210014189 has a creation date of 2021-04-22 KST, which matches the "PDF creation date 2021-04-21" in `RETEST_PROMPT_v2.md`, and its body contains "Step 0: Requirement Elicitation" and `If abs(roll_angle) >30 & roll_hold_mode_engagement,`, which matches the source ("Step 0 slides") of `AP-003c-v1` to `v3`. The record 20220007610 with the same title is the NFM22 tutorial (file name `NFM22Tutorialv5.pdf`, 2022-05-16) and is not this file |
| RQ20 | *Formal Requirements Elicitation with FRET* (REFSQ 2020, Giannakopoulou et al.) | 20200001989 (verified, registered 2020-03-27) | The NTRS API title matches. `RETEST_PROMPT_v2.md` line 134 and `tools/build_data.py` line 21 already record this id |
| TUT | *FRET Tutorial* (presentation, Pressburger) | 20220009659 | The **same document** as TUT22 in the v1 data (same NTRS id). `RETEST_PROMPT_v2.md` line 133 |

## 4. Where and how the cases were collected (evidence)

| Set | How it was collected | Evidence |
|---|---|---|
| v1 pairs (57; 45 in this folder + 12 in `fsm/`) | Only the pairs for which both natural language and FRETish are **printed** in a public NASA report were collected. The 11 report PDFs were downloaded from NTRS and compared | `experiments/nl2fret/NL2FRET_PROMPT_v1.md` line 53, `experiments/nl2fret/CHANGELOG.md` line 14; the PDF list is in `experiments/nl2fret/pdfs/` |
| Candidate pool pool_v2 (167) | The natural language was not produced by an LLM; it was excerpted verbatim from documents that contain the FRETish (report PDFs, requirements documents, spreadsheets). The source is kept in `prov`. The FRET tool examples (Liquid Mixer, FSM, tutorial, Lockheed Martin challenge) and their reports (CR21, RC22, TUT22, LM10, BG20) were left out of this pool | `experiments/nl2fret_v2/NL2FRET_PROMPT_v2.md` lines 66 to 75 |
| v2 main run (68) | Selected from pool_v2 (seed 20261028, per-source caps MLV 26, DRONE 16, UC69 10, exclusion reasons recorded) | `experiments/nl2fret_v2/data/selection_log.json` |
| nl3 calibration (99) | The pool_v2 items that remain after removing the 68 items of the v2 main run | `experiments/nl3/NL2FRET_PROMPT_v3.md` line 4437 (a code comment) |
| v7 development set (94) | `nasa_dev` 25 + `ext_dev` 69. **The selection rule is unknown** (section 4.1) | `experiments/v7_dev0/bench/NL2FRET_PROMPT_v7_DEV0.md` line 15, `experiments/v7_dev0/bench/data/dev_items.jsonl`, `used_in.v7_dev` in `cases.jsonl` of this folder |

### 4.1 The 94 v7 development items: composition confirmed by the documents, and what is unknown

| Item | Contents | Evidence |
|---|---|---|
| Count and composition | 94 items = NASA 25 (`role: nasa_dev`) + external 69 (`role: ext_dev`) | `experiments/v7_dev0/bench/NL2FRET_PROMPT_v7_DEV0.md` line 15, `experiments/v7_dev1/bench/NL2FRET_PROMPT_v7_DEV1.md` line 13 ("same as DEV0") |
| Sources of the external 69 | MLV, UC69, DRONE | The `family` values of the rows with `ext_dev` in `dev_items.jsonl`. The three sources are defined in `experiments/nl2fret_v2/NL2FRET_PROMPT_v2.md` lines 71 to 73 |
| File hash | sha256 of `data/dev_items.jsonl`: `e70710a0f99af125fa38fab27782ec4a36bfd21ed775d79ac7373239e9b380f1` | DEV0 document line 75, DEV1 document line 50. The hashes of the two copies in `v7_dev0` and `v7_dev1` equal this value (rechecked 2026-11-08) |
| **Selection rule** | **Unknown.** It is not in the documents or scripts of this repository | - |

The counts per source code are in the `v7 dev` column of the table in section 5.

## 5. Case count comparison (per code, per set)

A case can belong to several sets, so the column sums differ from the total number of cases. The total of the `v1 pairs` column is 45, which is the 57 before the split minus the 12 in `fsm/` (RC22 is not in `pool_v2`, `v2 main`, `nl3 calibration` or `v7 dev`, so those columns are unchanged).

| Code | Total | v1 pairs | pool_v2 | v2 main | nl3 calibration | v7 dev |
|---|---|---|---|---|---|---|
| CP22 | 1 | 1 | 1 | 0 | 1 | 0 |
| IR20 | 7 | 7 | 7 | 5 | 2 | 7 |
| PLC23 | 2 | 2 | 2 | 1 | 1 | 1 |
| TC4 | 10 | 10 | 10 | 6 | 4 | 10 |
| WF23 | 9 | 9 | 9 | 4 | 5 | 7 |
| CR21 | 12 | 12 | 0 | 0 | 0 | 0 |
| RC22 | 1 | 1 | 0 | 0 | 0 | 0 |
| LM10 | 1 | 1 | 0 | 0 | 0 | 0 |
| BG20 | 1 | 1 | 0 | 0 | 0 | 0 |
| TUT22 | 1 | 1 | 0 | 0 | 0 | 0 |
| MLV | 79 | 0 | 79 | 26 | 53 | 30 |
| UC69 | 18 | 0 | 18 | 10 | 8 | 18 |
| DRONE | 41 | 0 | 41 | 16 | 25 | 21 |
| Total | 183 | 45 | 167 | 68 | 99 | 94 |

## 6. Notes
- **The 12 FSM cases were separated**: the 12 FSM cases of RC22 (`FSM-001` to `FSM-013`, except `FSM-007`) have natural language that is character-identical to `LM-01_FSM-N*` of the Lockheed Martin `01_FSM`, so they are stored once in `../fsm/` (they are not kept in this group or in `lockheed_martin/`). The evidence and the verification method are in `../fsm/SOURCES.md`.
- **`FSM-007` stays in this group (project owner's decision, 2026-11-08).** Its id and source are those of the FSM report (RC22), but it differs by one word from the Lockheed Martin `LM-01_FSM-N07` (MANEUVER versus PULLUP), so it does not meet the criterion of `fsm/` (character-identical cases only). It is recorded in `../fsm/README.md` as a near candidate (one-word difference) and is not moved. The same file also lists the ids of the 14 FSM-prefixed ids in `legacy_fretish_inputs.jsonl` of this folder (FRETish rather than natural language, so the definition does not fit) and of the 10 MLV mode-transition descriptions (different source, no evidence that they come from the FSM problem); the decision for both is not to move them.
- The 7 cases with `nl_fretish_like: true` are items that the v2 selection record marked as "natural language that looks like FRETish" (`nl_fretish_like` 7 in `selection_log.json`).
- The NTRS ids of WF23, IR20, PLC23 and CP22 were "assumed" or "not checked" in earlier records, but were verified through the NTRS API on 2026-11-08 (section 3.4).
- The original report PDFs are in `experiments/nl2fret/pdfs/` (11 files) and were not copied into this folder. The original files of the repositories `valu3s-mu/FRETISH-requirements` and `oisinsheridan/refsq2025` are also not on this machine. Both repositories are public and the commits above were the HEAD at lookup time, so the same content can be obtained with `git clone`.
- **Redistribution caution (confirmation needed before publication; no action taken now)**: of the 138 `external_repo` cases, the source repository `valu3s-mu/FRETISH-requirements` of MLV and UC69 (97 cases) has no license, and `oisinsheridan/refsq2025` of DRONE (41 cases) is CC-BY-4.0 (attribution required). According to the NTRS records, the copyright determination of the NASA reports and NTRS documents is `PUBLIC_USE_PERMITTED`, but IR20, CP22 and PLC23 (10 cases) are `MAY_INCLUDE_COPYRIGHT_MATERIAL` (section 3.4). This must be checked before the repository is published; no action has been taken so far and no license file has been created (no legal judgment was made). The overall summary, including the Lockheed Martin notice, is in `../README.md`.
- Of the 51 `fret_retest_v2` entries in `legacy_fretish_inputs.jsonl`, the documents of the codes SL21, RQ20 and TUT were verified in section 3.4 (SL21 = NTRS 20210014189, RQ20 = NTRS 20200001989, TUT = the same NTRS 20220009659 as TUT22). The 20 `fret_template_bench` entries are the 16 sentences of the appendix of NASA/TM-2019-220365 "Integrating Realizability Checking in FRET" (NTRS 20190033980) and 4 sentences of NTRS 20200002241; the data states that they went through a comparison with page images of the original PDF (2026-10-23).
