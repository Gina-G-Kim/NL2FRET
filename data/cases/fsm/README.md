# fsm Group Guide

## Definition
A group that stores **12 cases, limited to those whose natural language is character-identical** in the Lockheed Martin challenge `01_FSM` and NASA/TM-20220007510 (RC22), once each. It contains only the input cases (natural language); the reference FRETish (ground truth) was not copied.

| File | Contents |
|---|---|
| `cases.jsonl` | The 12 cases |
| `ORIGIN_MAP.csv` | 12 cases x 2 original memberships (24 rows). `case_id` is the Lockheed Martin id |
| `SOURCES.md` | Collection sources, collection method, identity verification, evidence line numbers |
| `README.md` | This file. Decisions and the list of cases that were not moved |

Count connection: `lockheed_martin` 49 + `fsm` 12 = 61, `nasa_papers` 183 + `fsm` 12 = 195.

The 12 included cases: the Lockheed Martin ids `LM-01_FSM-N01` to `N13` (except `N07`) are paired with the RC22 ids `FSM-001` to `FSM-013` (except `FSM-007`) (`LM-01_FSM-N01` = `FSM-001`, ...; the numbers are the same).

## Decision (2026-11-08, project owner's decision)

The criterion for `fsm/` is the **12 character-identical cases**. The three kinds of candidates below were **decided not to be moved.** Their id lists are kept so that they can be moved if the project owner asks later. The "request for user confirmation" in `SOURCES.md` section 8 is closed by this decision.

### 1. Near candidates: one-word difference, not moved

| Membership | id | Location | Differing word | Status |
|---|---|---|---|---|
| `lockheed_martin` | `LM-01_FSM-N07` | `lockheed_martin/cases.jsonl` line 5 | **PULLUP** | Near candidate, one-word difference, not moved |
| `nasa_papers` | `FSM-007` (RC22 table 4, PDF page 15) | `nasa_papers/cases.jsonl` line 180 | **MANEUVER** | Near candidate, one-word difference, not moved |

The two original texts differ in one word (`PULLUP` versus `MANEUVER`); the rest, "The autopilot shall change states from ... to TRANSITION when the system is supported and sensor data is good.", is identical. The origin of the difference (the Lockheed Martin docx and the FRET example say PULLUP, the RC22 paper says MANEUVER) is described in `SOURCES.md` section 8.1.

### 2. 14 legacy FRETish inputs with an FSM-prefixed id, not moved
Location: `nasa_papers/legacy_fretish_inputs.jsonl` (line numbers start at 1). The **inputs are FRETish sentences, not natural language**, so they do not match the definition of this group (input case = natural language); only the name says FSM.

| Line | Set | id | Source | Location |
|---|---|---|---|---|
| 9 | `fret_template_bench` | `FSM-006` | NASA/TM-2019-220365 | PDF page 31 |
| 10 | `fret_template_bench` | `FSM-007` | NASA/TM-2019-220365 | PDF page 31 |
| 11 | `fret_template_bench` | `FSM-008v1` | NASA/TM-2019-220365 | PDF page 32 |
| 12 | `fret_template_bench` | `FSM-009` | NASA/TM-2019-220365 | PDF page 32 |
| 13 | `fret_template_bench` | `FSM-002` | NASA/TM-2019-220365 | PDF page 33 |
| 14 | `fret_template_bench` | `FSM-003` | NASA/TM-2019-220365 | PDF page 33 |
| 15 | `fret_template_bench` | `FSM-010` | NASA/TM-2019-220365 | PDF page 34 |
| 16 | `fret_template_bench` | `FSM-011` | NASA/TM-2019-220365 | PDF page 34 |
| 17 | `fret_template_bench` | `FSM-001` | NTRS 20200002241 | PDF page 5 |
| 18 | `fret_template_bench` | `FSM-001v2` | NTRS 20200002241 | PDF page 11 |
| 31 | `fret_retest_v2` | `FSM-006t` | RC22 | Table 2 |
| 32 | `fret_retest_v2` | `FSM-007t` | RC22 | Table 2 |
| 33 | `fret_retest_v2` | `FSM-001r` | RC22 | Table 3 |
| 50 | `fret_retest_v2` | `FSM-001v2` | CP22 | FSM requirements JSON |

### 3. 10 MLV mode-transition descriptions, not moved
Location: `nasa_papers/cases.jsonl` (line numbers start at 1). These are cases whose natural language contains a state-transition description of the form "The transition from A Mode to B Mode shall occur ...".

| Line | id | Beginning of the natural language |
|---|---|---|
| 41 | `X-MLV-011` | The transition from Start-up Mode to Self test Mode shall occur once the configurations ... |
| 46 | `X-MLV-016` | The transition from VentilationOff to PSV shall occur if the change mode command ... |
| 49 | `X-MLV-019` | The transition from PSV to VentilationOff shall occur if the user stops the ventilation ... |
| 51 | `X-MLV-021` | The transition from VentilationOff to PCV mode shall occur if the change mode command ... |
| 93 | `X-MLV-063` | If the pressure sensor fails to connect or reports an error condition after a fixed number of retries ... |
| 96 | `X-MLV-066` | The transition from PSV to PCV shall occur if the patient does not trigger a breath ... |
| 100 | `X-MLV-070` | The transition to Start-up Mode shall be allowed by pushing the power button ... |
| 103 | `X-MLV-073` | If the external ADC fails to initialize or reports an error condition after a fixed number of retries ... |
| 105 | `X-MLV-075` | The transition from PCV to PSV shall occur if ventilation is on, ... |
| 106 | `X-MLV-076` | The transition from PCV to VentilationOff shall occur if the user stops the ventilation in PCV mode. |

Rationale (why they were not moved):
- **The source is different.** They come from the Mechanical Lung Ventilator (ABZ 2024) case study and from the repository `valu3s-mu/FRETISH-requirements` (`nasa_papers/SOURCES.md` section 3.3). They have no relation to Lockheed Martin `01_FSM` or to RC22.
- The content describes state transitions, but there is **no evidence that it comes from the FSM challenge.**
- The other cases that appeared in the keyword search were left out of the candidates. `X-MLV-013`, `X-MLV-018` and `X-MLV-054` ("Recruitment Maneuver" is the name of a lung procedure) and `LM-08_SWIM-N2` ("evasive maneuver") only share a word, and `X-MLV-040` and `X-MLV-043` ("Standby Mode") were left out because there is no evidence that they are the same as the STANDBY state of the FSM challenge.

### 4. When moving them later
The ids in the three lists above are all that can be moved (ids to move: `LM-01_FSM-N07`, `FSM-007`, the 14 `legacy` ids, and the 10 MLV ids). At present `tools/build_cases.py` sends only **character-identical overlaps** to `fsm/`. To move them, change that criterion together with `ORIGIN_MAP.csv` and the per-group case counts (49 + 12 = 61, 183 + 12 = 195). Nothing has been moved so far.
