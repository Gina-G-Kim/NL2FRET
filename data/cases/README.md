# data/cases: Input Case Organization

The cases used as experiment inputs are collected in three source groups. The `SOURCES.md` in each group folder records where and what was collected, with evidence (files and line numbers). The list of FSM candidates that were deliberately not moved is in `fsm/README.md`. Organized on 2026-11-08.

## Group definitions and case counts

| Group | Folder | Definition | Cases | Separation criterion |
|---|---|---|---|---|
| NASA reports and other papers | `nasa_papers/` | Natural-language requirements collected from NASA technical reports (42), NTRS papers and slides (3), and public GitHub repository case studies (138, `origin: external_repo`) | **183** (the 71 FRETish inputs of legacy experiments are not counted) | Items whose source is a NASA report, a paper, or a public repository. The 12 cases that are character-identical to the Lockheed Martin challenge go to `fsm/` |
| NASA Lockheed Martin | `lockheed_martin/` | Original natural-language requirements (docx) of the 10 Lockheed Martin Cyber-Physical Challenge problems | **49** (+ 1 signal dictionary) | Items whose source is the challenge documents. The 12 cases that are character-identical to NASA/TM-20220007510 (RC22) go to `fsm/` |
| FSM | `fsm/` | FSM cases that **appeared with character-identical natural-language text** in both sources above. Stored once | **12** | The original texts of both sources are equal under `==` without normalization. The original membership is in `fsm/ORIGIN_MAP.csv` |
| Total (distinct natural-language texts) | | | **244** = 183 + 49 + 12 | Before the split: 195 + 61 - 12 = 244 |

## Connection to the pre-split counts

| Before the split | After the split | How to reconstruct |
|---|---|---|
| Lockheed Martin **61** | `lockheed_martin` 49 + `fsm` 12 | The `case_id` values of `lockheed_martin/cases.jsonl` plus the 12 `original_id` values with `original_group == lockheed_martin` in `fsm/ORIGIN_MAP.csv`. The `case_id` of `fsm/cases.jsonl` is that Lockheed Martin id |
| NASA reports and other papers **195** | `nasa_papers` 183 + `fsm` 12 | The `case_id` values of `nasa_papers/cases.jsonl` plus the 12 `original_id` values with `original_group == nasa_papers` in `ORIGIN_MAP.csv` (the `FSM-0..` ids of RC22) |

For the 12 `fsm` cases, the Lockheed Martin entry and the RC22 entry are **the same case**. This is marked in the `same_case_as` and `text_match` (`exact`) columns of `ORIGIN_MAP.csv`. The `also_in_*` fields that used to be in `cases.jsonl` were removed and their information was moved to `ORIGIN_MAP.csv`.

## Common rules
- One case is one distinct natural-language text. A text that appears in several experiment sets is merged into one record and all memberships are listed in `used_in`.
- **Reference FRETish (ground truth) was not copied.** Only inputs are included; the references remain in the original data files inside `experiments/`. `experiments/` was only read and not modified.
- "Other papers" is not a separate group; it stays in `nasa_papers/` and is distinguished by `origin` (`nasa_tr`, `paper_or_slides`, `external_repo`).
- To rebuild: run `python3 -I -B tools/build_cases.py` from the repository root. Every run checks the count consistency, the text identity of the 12 overlapping cases, and the absence of reference fields, and stops on any mismatch. Statistics are in `_build_stats.json`. The comparison with the original Lockheed Martin files is done by `tools/verify_lm_docx.py` (it takes the directory of downloaded docx files as its argument and does not access the network).
- This folder is tracked regardless of the `experiments/` exclusion in `.gitignore` (`data/` is not excluded).

## FSM candidate decisions (2026-11-08, not moved)

The criterion for `fsm/` is the **12 character-identical cases**. All other candidates that could be considered FSM-related were decided not to be moved. Their id lists and the rationale are recorded in `fsm/README.md`, so they can be moved from those lists if requested later.

| Candidate | Location | Decision | Reason |
|---|---|---|---|
| `LM-01_FSM-N07`, `FSM-007` (2 cases) | `lockheed_martin/`, `nasa_papers/` | Not moved. Near candidates, one-word difference (PULLUP versus MANEUVER) | They are not the same case |
| 14 legacy FRETish inputs with an FSM-prefixed id | `nasa_papers/legacy_fretish_inputs.jsonl` | Not moved | Only the name says FSM; the inputs are FRETish sentences, not natural language, which does not match the group definition |
| 10 MLV mode-transition descriptions | `nasa_papers/` | Not moved | The source is different, and there is no evidence that they come from the FSM problem |

## Provenance research results (2026-11-08, local records and web lookups)

These are the results of looking up the items that had been left as "unknown". What could not be found is listed under "Still unknown" below. The evidence and lookup methods are in the `SOURCES.md` of each group.

| Item | Result | Details |
|---|---|---|
| Lockheed Martin repository commit and download date | **Unknown** (no record). All that was verified is that the 10 docx files were added in commit `4ee0e326` (2020-02-12) and have not changed since, and that master HEAD is `133447a8` (the docx contents are the same for any commit after 2020-02-12) | `fsm/SOURCES.md` section 3.1, `lockheed_martin/SOURCES.md` section 2 |
| Comparison with the original Lockheed Martin files | The original docx files were downloaded and **all** 61 cases (49 + 12 in fsm) match (51 verbatim, 10 differing only in whitespace and line breaks). `tools/verify_lm_docx.py`, `lockheed_martin/docx_match.csv` | `lockheed_martin/SOURCES.md` section 2 |
| Document titles of SL21 and RQ20 | SL21 = the presentation *Capturing and Analyzing Requirements with FRET*, **NTRS 20210014189** (verified down to the PDF creation date and the body text). RQ20 = *Formal Requirements Elicitation with FRET*, NTRS 20200001989. TUT is the same document as TUT22 (NTRS 20220009659) | `nasa_papers/SOURCES.md` section 3.4 |
| RC22 PDF file | `experiments/nl2fret/pdfs/TechnicalReport__FRET_Realizability_Checking.pdf`. A mapping of all 11 PDFs was made | `nasa_papers/SOURCES.md` section 3.4 |
| "Assumed" and "unverified" NTRS ids | All 13 ids, including WF23, IR20, PLC23, CP22, RC22 and CR21, were verified by title through the NTRS API | `nasa_papers/SOURCES.md` section 3.4 |
| Why `FSM-007` and `N07` differ | The natural language of the Lockheed Martin docx and of the FRET example says PULLUP, while the RC22 paper table says MANEUVER (the FRETish of both uses the maneuver state). A difference between source documents | `fsm/SOURCES.md` section 8.1 |
| Selection rule of the 94 v7 development items | **Unknown** (not in this repository). Only the composition confirmed by the project documents is recorded: NASA 25, external 69 (sources MLV, UC69, DRONE), `data/dev_items.jsonl` sha256 `e70710a0f99af125fa38fab27782ec4a36bfd21ed775d79ac7373239e9b380f1` | `nasa_papers/SOURCES.md` section 4.1 |

## License: confirmation needed before publication (no action taken now)

These points must be checked before this repository is published. No action has been taken so far, and **no license file has been created.** No legal judgment was made; only the notices that were found are listed.

- **The Lockheed Martin sentences are all rights reserved.** The 61 cases in `lockheed_martin/` and `fsm/` are sentences from the docx files of `hbourbouh/lm_challenges`; the README of that repository states "Copyright 2016, Lockheed Martin Corporation. All rights reserved", and the repository has no license file.
- **The source of MLV and UC69 has no license.** The 97 cases in `nasa_papers/` come from the repository `valu3s-mu/FRETISH-requirements`, whose license field in the GitHub API is empty.

Other notices found, for reference:

| Source | Notice found |
|---|---|
| `oisinsheridan/refsq2025` (DRONE, 41 cases) | CC-BY-4.0 (attribution required) |
| NASA reports and NTRS documents | The copyright determination of the NTRS record is `PUBLIC_USE_PERMITTED`. However, IR20, CP22 and PLC23 (10 cases) are `MAY_INCLUDE_COPYRIGHT_MATERIAL` |

## Still unknown
- **The Lockheed Martin repository commit and the download date: unknown.** (Only the range after 2020-02-12 and before 2026-11-01 16:03 was verified.)
- **The selection rule of the 94 v7 development items: unknown.** It is not in the documents or scripts of this repository.
- Why the authors of the RC22 paper wrote MANEUVER in the natural language of `FSM-007`
- Whether the repository account `hbourbouh` is the same person as the LM10 paper author Hamza Bourbouh
