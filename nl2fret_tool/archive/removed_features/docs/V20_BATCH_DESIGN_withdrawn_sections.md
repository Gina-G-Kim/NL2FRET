# Withdrawn sections of docs/V20_BATCH_DESIGN.md (text as of 2026-11-17 before the tidy-up, copied unchanged from the version of that day)

The sections 7.2 to 7.6 below were written on 2026-11-17 and withdrawn on the same day by the study owner (see README.md of this folder). Section 7.1 (N-LIT) and the primary and secondary rule for Realizability were kept in `nl2fret_tool/docs/V20_BATCH_DESIGN.md`.

### 7.2 Judge variant J+def (the strict judge stays as it is, `judging/` is not touched)
- Separate step `judgedef` of `run_batch.sh`; tool `bench/tools/make_def_inputs.py` writes derived inputs (`inputs_def_<variant>/`: units, LTL, reference, `substitution_report.json`); the unchanged `nl2fret_judge judge-parts` judges them into `judge_def_<variant>/`. The existing judgment is reported as strict.
- Dictionary rows of the challenge with `kind` = `defined` and a non-empty `definition` are the defined terms.
- Substitution: in the condition and response regions of every generated and every reference sentence (same function), every identifier token equal to a defined term is replaced by `( <definition> )`. Definitions are expanded recursively (a definition may contain defined terms). The parentheses around each substituted definition keep the precedence; the official parser prints the canonical parenthesization, so the substituted sentence is compiled again to obtain `ltl_pt` and `ltl_ft`.
- Cyclic definitions: the expansion keeps the stack of terms being expanded; a term that is already on the stack stays unexpanded and is recorded as `cycle`; depth limit 20.
- A substituted sentence that the parser rejects keeps its original text and is recorded (`parser_rejected`).
- Controls: judging the reference sentences against themselves must give SAME with the strict judge and with J+def.

### 7.3 Dictionary relation check
- The relation between the `check_1_1` family (source `nasa_lus`) and the `check_11` family is looked up in the dictionary documents and reported. The dictionary is not edited without the owner's confirmation.

### 7.4 Primary and secondary measures (2026-11-17, fixed before the re-measurement)
- Judgment: J+def is the primary measure, the strict judgment is the secondary measure. Realizability: the normalized column is primary (`result` = `result_normalized`), the raw column is secondary (`result_raw`). `rt_effect.json` is computed from the J+def judgments, `rt_effect_strict.json` from the strict judgments. Both are always reported.
(Only the judgment half was withdrawn; the Realizability half is kept as 7.2 of the current document.)

### 7.5 J+def substitution unit is the TERM (replaces the sentence level fallback of 7.2)
- A defined term is a dictionary row with `kind` = `defined` and a non-empty `definition`. A term is substitutable iff (a) its `definition` parses as a FRET expression (probe sentences `X shall always satisfy (<definition>)` or `X shall always satisfy (<definition>) < 0` accepted by the official parser) and (b) the term is not on a cycle of the definition graph (self reference or mutual reference).
- A substitutable term is replaced in BOTH the generated and the reference sentences (condition and response, `( <definition> )`, recursively for substitutable terms inside it). A term that is not substitutable stays an atom on both sides and is recorded as `lustre_only` (reason `parse_error` or `cycle`); counts per challenge are reported (`term_report.json`). Lustre expressions are not translated to FRET expressions.
- A substituted sentence that the parser still rejects keeps its original text and is recorded as `parser_rejected` (expected 0).

### 7.6 Dictionary aliases (judge side only; the dictionary table that the model sees is not changed)
- Judge behaviour (read from `judging/nl2fret_judge/dict_align.py` and `parts.py`): an identifier of a GENERATED formula that is not a dictionary name and has exactly one dictionary name with the same spelling ignoring case and underscores is `aliased` and renamed to that name before the judgment; the reference is not renamed; `aliased` has no effect on the role or on the success count (SAME or PROOF).
- An alias pair `old -> current` is written to the dictionary only with an original text evidence: in a NASA requirement of `LM_requirements.json` whose `comments` start with "Originally", a token diff of the comment text against the current `fulltext` shows `old` replaced by `current` at the same place (single identifier replaced by single identifier). A pair without such evidence is not an alias ("unknown").
- Dictionary v2 (`assets/dictionary/v2/`) adds the columns `alias_of` (the current name) and `alias_evidence` (requirement id) to the rows of the old names that have evidence; v1 is kept in `archive/dictionary/v1/`. The model-visible dictionary text (`bench/data/sigdict.json`) is not regenerated and does not contain the columns.
- The judge side use is outside `judging/`: `bench/tools/make_def_inputs.py` renames an alias name to its current name in the condition and response of generated and reference sentences before the term substitution; the derived units, LTL and reference files go to the unchanged `nl2fret_judge judge-parts`. The strict judgment does not use aliases.
(Dictionary v2 now lives in `nl2fret_tool/bench/ext/dictionary/overlays/v2/`; v1 is again `assets/dictionary/v1/`.)
