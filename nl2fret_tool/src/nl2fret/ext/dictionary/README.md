# Extension `dictionary`

## Role (docs/V20_BATCH_DESIGN.md 0.1)
The dictionary is not a performance booster. It is an experimental extension, an additional attachment that is given identically to all methods. The NASA FRETish that serves as the reference uses information that cannot be derived from the natural language alone (variable names, defined terms); the dictionary supplies the signal, constant, defined-name and function names of the challenge. Results with the extension on are reported only as the performance under the condition that this dictionary is given.

## Contents
| File | Role |
|---|---|
| `attach.py` | what the FRETish stage gets: `prompt_block(challenge) -> str \| None` (table text of the challenge from `src/nl2fret/data/sigdict.json`), `rendered(challenge)` (the user block, wraps `common.sigdict_block`), `missing(items)`, `switch_on(P)` (the `prompts3.DICT_ALL` switch that adds the dictionary rules D-2 to D-4 to the FRETish system prompts) |
| `judge_input.py` | what the judge gets: the argument `--dictionary` of `judge-parts`. On: `data/dictionary/lm_dictionary.csv` (v1). Off: a header-only file `<run>/ext_off_dictionary.csv` (the frozen `src/nl2fret_judge/` requires the argument; it is not changed) |
| `build.py` | update side: `verify` (rebuilt table text = `src/nl2fret/data/sigdict.json` and `data/reference/sigdict.json`), `record --version`, `update` (runs `data/dictionary/build_dict.py`; its sources are not in this package), `overlay NAME` |
| `versions/v1/` | version record of the current dictionary: `EVIDENCE.json` (rows, columns, rows per challenge, name of the generator). The default dictionary is v1 |
| `overlays/v2/` | optional overlay, default off: the dictionary table with the columns `alias_of` and `alias_evidence` (9 alias pairs with an original-text evidence, 33 candidate pairs unknown) and `build_alias_v2.py`. Nothing in the core reads these columns |

## Interface
`prompt_block(challenge) -> str | None`. The core calls it through `run_pipeline.sd_of`; the core keeps only the hooks (`src/nl2fret/ext/__init__.py`: `parse`, `DICTIONARY`; the `--ext` flag of `run_pipeline.py` and `batch_pipeline.py`; `EXT` of `scripts/run_batch.sh`).

## How to enable
- Pipelines: `--ext dictionary` (several names may follow; the old `--dict-all` is an alias). No `--ext` = extension off.
- `scripts/run_batch.sh`: environment variable `EXT`, default `dictionary` (on). `EXT= bash scripts/run_batch.sh ...` switches it off for generation and judging.
- Off means: no dictionary block in the user messages, no dictionary rules in the system prompts (the prompt bytes differ from the on case; with the extension on they are the bytes of the 12 system prompts in `prompts/current/system_prompts/`), and the judge runs with an empty dictionary (every identifier `oov`, nothing renamed).
- The run record keeps `dict_all` in the flags and the list `ext` in `run_state.json`; `tools/make_judge_inputs.py` reads `dict_all` from the record.
