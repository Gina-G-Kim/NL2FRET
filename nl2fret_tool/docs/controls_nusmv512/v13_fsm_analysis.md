# Run analysis (metrics fixed in docs/ANALYSIS_PLAN.md)

run: /tmp/claude-0/-home-claude/61a6fcea-a10b-56c7-b320-96bb4509fcb7/scratchpad/r023/runs/fsm_20261113; engine for the satisfiability check: nusmv; parts analysed: 429

## Instrument controls (judge_controls.py)

| control | n | flagged | meaning |
|---|---|---|---|
| C+ID | 112 | 0/112 = 0.0 | false failure (not SAME) |
| C+NN | 112 | 0/112 = 0.0 | false failure (not SAME) |
| C+AND | 112 | 0/112 = 0.0 | false failure (not SAME) |
| C-TAUT | 112 | 0/112 = 0.0 | false success (SAME or PROOF) |
| C-CONTR | 112 | 112/112 = 1.0 | false success (SAME or PROOF) |
| C-NEG | 112 | 0/112 = 0.0 | false success (SAME or PROOF) |
| C-SHIFT | 33 | 6/33 = 0.1818 | false success (SAME or PROOF) |

## Success per arm (parts)

| arm | parts | lenient | SAME | PROOF | strict | PROOF removed: unsat | removed: renamed | parts with judgeable reference |
|---|---|---|---|---|---|---|---|---|
| DIRECT | 39 | 1/39 = 0.026 | 0 | 1 | 1/39 = 0.026 | 0 | 0 | 39/39 = 1.000 |
| Adv-EARS+G | 39 | 0/39 = 0.000 | 0 | 0 | 0/39 = 0.000 | 0 | 0 | 39/39 = 1.000 |
| Adv-EARS+R2 | 39 | 2/39 = 0.051 | 0 | 2 | 2/39 = 0.051 | 0 | 0 | 39/39 = 1.000 |
| Boilerplate+G | 39 | 6/39 = 0.154 | 0 | 6 | 5/39 = 0.128 | 0 | 1 | 39/39 = 1.000 |
| Boilerplate+R2 | 39 | 3/39 = 0.077 | 0 | 3 | 3/39 = 0.077 | 0 | 0 | 39/39 = 1.000 |
| EARS+G | 39 | 0/39 = 0.000 | 0 | 0 | 0/39 = 0.000 | 0 | 0 | 39/39 = 1.000 |
| EARS+R2 | 39 | 3/39 = 0.077 | 0 | 3 | 3/39 = 0.077 | 0 | 0 | 39/39 = 1.000 |
| MASTeR+G | 39 | 0/39 = 0.000 | 0 | 0 | 0/39 = 0.000 | 0 | 0 | 39/39 = 1.000 |
| MASTeR+R2 | 39 | 3/39 = 0.077 | 0 | 3 | 3/39 = 0.077 | 0 | 0 | 39/39 = 1.000 |
| SPIDER+G | 39 | 0/39 = 0.000 | 0 | 0 | 0/39 = 0.000 | 0 | 0 | 39/39 = 1.000 |
| SPIDER+R2 | 39 | 0/39 = 0.000 | 0 | 0 | 0/39 = 0.000 | 0 | 0 | 39/39 = 1.000 |

## Decision-point agreement with the representative reference version (parts with a generated sentence)

reading = EDGE / EVERY_TIME / UNCOND / UNLESS (decision_points.py); ntiming = timing with immediately and always merged for EVERY_TIME

| arm | n | scope same | reading same | ntiming same | all three same | gen EDGE | gen EVERY_TIME | ref EDGE | ref EVERY_TIME |
|---|---|---|---|---|---|---|---|---|---|
| DIRECT | 39 | 31/39 = 0.795 | 0/39 = 0.000 | 0/39 = 0.000 | 0/39 = 0.000 | 39/39 = 1.000 | 0/39 = 0.000 | 0/39 = 0.000 | 39/39 = 1.000 |
| Adv-EARS+G | 39 | 39/39 = 1.000 | 0/39 = 0.000 | 0/39 = 0.000 | 0/39 = 0.000 | 39/39 = 1.000 | 0/39 = 0.000 | 0/39 = 0.000 | 39/39 = 1.000 |
| Adv-EARS+R2 | 39 | 39/39 = 1.000 | 0/39 = 0.000 | 0/39 = 0.000 | 0/39 = 0.000 | 39/39 = 1.000 | 0/39 = 0.000 | 0/39 = 0.000 | 39/39 = 1.000 |
| Boilerplate+G | 39 | 30/39 = 0.769 | 1/39 = 0.026 | 1/39 = 0.026 | 0/39 = 0.000 | 32/39 = 0.821 | 1/39 = 0.026 | 0/39 = 0.000 | 39/39 = 1.000 |
| Boilerplate+R2 | 39 | 30/39 = 0.769 | 0/39 = 0.000 | 0/39 = 0.000 | 0/39 = 0.000 | 30/39 = 0.769 | 0/39 = 0.000 | 0/39 = 0.000 | 39/39 = 1.000 |
| EARS+G | 39 | 39/39 = 1.000 | 0/39 = 0.000 | 0/39 = 0.000 | 0/39 = 0.000 | 39/39 = 1.000 | 0/39 = 0.000 | 0/39 = 0.000 | 39/39 = 1.000 |
| EARS+R2 | 39 | 39/39 = 1.000 | 0/39 = 0.000 | 0/39 = 0.000 | 0/39 = 0.000 | 39/39 = 1.000 | 0/39 = 0.000 | 0/39 = 0.000 | 39/39 = 1.000 |
| MASTeR+G | 39 | 39/39 = 1.000 | 0/39 = 0.000 | 0/39 = 0.000 | 0/39 = 0.000 | 39/39 = 1.000 | 0/39 = 0.000 | 0/39 = 0.000 | 39/39 = 1.000 |
| MASTeR+R2 | 39 | 39/39 = 1.000 | 0/39 = 0.000 | 0/39 = 0.000 | 0/39 = 0.000 | 39/39 = 1.000 | 0/39 = 0.000 | 0/39 = 0.000 | 39/39 = 1.000 |
| SPIDER+G | 39 | 39/39 = 1.000 | 0/39 = 0.000 | 0/39 = 0.000 | 0/39 = 0.000 | 39/39 = 1.000 | 0/39 = 0.000 | 0/39 = 0.000 | 39/39 = 1.000 |
| SPIDER+R2 | 39 | 39/39 = 1.000 | 0/39 = 0.000 | 0/39 = 0.000 | 0/39 = 0.000 | 39/39 = 1.000 | 0/39 = 0.000 | 0/39 = 0.000 | 39/39 = 1.000 |

## Primary cause of every part that is not a strict success (exactly one cause per part)

| arm | non-strict parts | DECISION:reading+ntiming | DECISION:scope | DECISION:scope+reading+ntiming | INSTRUMENT_STRICT | INSTRUMENT_UND_NM | TEMPLATE_INFO_LOSS |
|---|---|---|---|---|---|---|---|
| DIRECT | 38 | 30 | 0 | 8 | 0 | 0 | 0 |
| Adv-EARS+G | 39 | 39 | 0 | 0 | 0 | 0 | 0 |
| Adv-EARS+R2 | 37 | 37 | 0 | 0 | 0 | 0 | 0 |
| Boilerplate+G | 34 | 29 | 1 | 2 | 1 | 0 | 1 |
| Boilerplate+R2 | 36 | 26 | 0 | 9 | 0 | 0 | 1 |
| EARS+G | 39 | 39 | 0 | 0 | 0 | 0 | 0 |
| EARS+R2 | 36 | 36 | 0 | 0 | 0 | 0 | 0 |
| MASTeR+G | 39 | 39 | 0 | 0 | 0 | 0 | 0 |
| MASTeR+R2 | 36 | 36 | 0 | 0 | 0 | 0 | 0 |
| SPIDER+G | 39 | 32 | 0 | 0 | 0 | 2 | 5 |
| SPIDER+R2 | 39 | 33 | 0 | 0 | 0 | 1 | 5 |

## Strata (all arms pooled; parts)

| stratum | parts | lenient | strict |
|---|---|---|---|
| item mapping_basis = rationale | 396 | 18/396 = 0.045 | 17/396 = 0.043 |
| item mapping_basis = id_order | 33 | 0/33 = 0.000 | 0/33 = 0.000 |
| item has no NL-linked reference row (heuristic) | 0 | 0/0 | 0/0 |
| item has conflicting duplicate definition | 0 | 0/0 | 0/0 |
| judge cannot compare the reference with itself | 0 | 0/0 | 0/0 |
| judge can compare the reference with itself | 429 | 18/429 = 0.042 | 17/429 = 0.040 |

## Check against the run's own summary

summary.json present; compare the lenient column with its part success counts (printed below by arm).
- DIRECT: recomputed lenient = 1
- Adv-EARS+G: recomputed lenient = 0
- Adv-EARS+R2: recomputed lenient = 2
- Boilerplate+G: recomputed lenient = 6
- Boilerplate+R2: recomputed lenient = 3
- EARS+G: recomputed lenient = 0
- EARS+R2: recomputed lenient = 3
- MASTeR+G: recomputed lenient = 0
- MASTeR+R2: recomputed lenient = 3
- SPIDER+G: recomputed lenient = 0
- SPIDER+R2: recomputed lenient = 0
