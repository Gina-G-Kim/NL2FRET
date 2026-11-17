# v2.0 batch run: design and pre-registration

## 0. Research question (restated 2026-11-17 before the implementation of the tidy-up; replaces the earlier wording)
Safety-critical software needs a formal specification (LTL), but writing LTL needs expert domain knowledge. FRET turns FRETish, a structured English, into LTL, but writing good FRETish is still manual work. Earlier attempts to automate this with LLMs did not reach full automation because of the limit set by the expert knowledge that the task needs. This study checks whether going through a template, a semi-formal intermediate form, reduces that limit.
- Core comparison: the template route (Template+G and FixedTemplate+R2) against Direct (natural language straight to FRETish).
- Secondary comparison: among the five templates (Adv-EARS, Boilerplate, EARS, MASTeR, SPIDER).
- Measured: whether the LTL that FRET compiles from the generated FRETish means the same as (SAME) or implies (PROOF) the LTL of the expert FRETish (the NASA FRETish of the reference).

## 0.1 Roles (2026-11-17)
- Reference: the NASA FRETish is used as the reference because NASA made FRET and is authoritative on it. The NASA FRETish uses information that cannot be derived from the natural language alone (variable names, defined terms).
- Dictionary: the dictionary is not a performance booster. It is an experimental extension (an additional attachment, module `src/nl2fret/ext/dictionary/`) that is given identically to all methods. Its results are reported only as the performance under the condition that this dictionary is given.

## 0.2 Decisions (2026-11-17, no undecided item remains)
1. Primary measure: the strict judgment (the existing judge `src/nl2fret_judge/` plus the dictionary alignment of the judge). The earlier judge variant J+def is withdrawn (see section 9).
2. Definition of an agent: a unit whose memory information that is useful for the conversion is separated independently per (template, input data kind) is one agent. Splitting the work of one such scope over several calls still counts as one agent. The implementation groups calls by (system prompt, challenge, repetition, stage) and passes information only inside the same group, which satisfies the definition. Stage 2 sees only the template sentences of stage 1 (kept as it is).
3. Known limits: sentences that use defined terms may be under-credited; a false SAME between different parts was observed in 4 of 129 reference self pairs. Both are properties of the earlier judge and are the same for all methods.
4. The earlier decisions J+def and dictionary v2 aliases are withdrawn or moved to an extension module (dated 2026-11-17, section 9). N-LIT (7.1) is kept; its default stays ON; it records the raw and the normalized result, the normalized one is primary, the raw one secondary. History is not deleted (`CHANGES.md`, `archive/removed_features/`).


## 1. Agent structure
- One agent is one fresh headless `claude` process (memoryless). The script writes the input, the agent returns one JSON object, the script keeps only that object (`--json-schema`).
- Isolation: whitelisted environment, empty temporary working directory, `--tools "" --no-session-persistence --setting-sources "" --disable-slash-commands --strict-mcp-config`.
  An isolation probe (`agent_call.isolation_probe`) runs before the first call; the run stops when anything but the allowed items is visible. Allowed items: StructuredOutput (the CLI's own tool that carries the answer), userEmail (the CLI puts the login account's e-mail into the context, the same for every approach; allowed 2026-11-16 before any run). Probe record: `isolation_probe.json`, item names only, no e-mail value.
- Unit of one agent call: (approach, challenge, repetition, stage). All requirements of one challenge (for example 01_FSM) go into one call.
  - Direct: one agent per challenge, FRETish guide only.
  - Template (+G): one agent per template and challenge, stage A (natural language to template sentence), then stage B (template sentence to FRETish), template guide and FRETish guide.
  - FixedTemplate (+R2): same agent scope as Template; stage B is replaced by the rule assembly.
  - Stage A is shared by +G and +R2 per (template, challenge, repetition). Stage B reads the template sentences only (`--stageb-sees-raw` is an ablation, not part of this run).
- Batch reply: `{"results":[{"id","answer"}]}`. Missing ids are requested once more (`--batch-retries 1`), the same for every approach. Per item rows are written in the old `calls.jsonl` format.
- A reply with valid JSON and an empty FRETish list is `declined` (stage A: status declined; stage B: ok with error declined, judge code no_output).

## 2. Feedback and check steps (changed 2026-11-17, experiment 030)
Feedback and check steps are different things. Feedback is the step in which the agent receives the failure log of the FRET parser and writes again. A check step gives the agent reference text and a description to compare with its own answer.

### 2.1 Feedback (FRET parser failure log)
- Parser feedback (up to MAX_ROUNDS rounds): the official FRET parser accepts or rejects every sentence; rejected sentences return with the parser message. The answer after the feedback is vf.

### 2.2 Check steps (KC, RT1), in this order after vf
1. Keyword check (KC, one round, section 11): the agent reads its current answer next to the reference text of the FRETish keywords of every keyword group that its sentences use and returns the answer again. The answer after KC is kc.
2. Round trip (RT1, one round): FRET writes its English description of every accepted sentence; the agent reads each description next to its input and returns the answer again. RT1 starts from the kc answer when it was adopted, else from the vf answer. The answer after RT1 is rt.
- Adoption rule (KC and RT1): the new answer replaces the answer it started from only when the official parser accepts every sentence of it; otherwise the earlier answer stays.

Realizability, reference FRETish and any score are never fed back.

## 3. Variants and metrics
- v0 first answer, vf after parser feedback, kc after the keyword check, rt after round trip (primary). All four are judged with the same judge (NuSMV, verdict code identical to v1.2 judging). With `NO_KC=1` the variant kc does not exist.
- Success = SAME or PROOF. Analysis C (`tools/rt_effect.py`): counts of parts per arm and variant, gains and losses between variants on the same (item, rep, part).
- Auxiliary: challenge level realizability (`fret_check/group_rlz.py`): the final sentences of one (approach, challenge, repetition) form one requirement set of one component; the reference set of the challenge is the baseline.
  Sentences with a user defined function application are left out and counted (`n_excluded_function`). Result values: realizable, unrealizable, unknown, empty. Unrealizable sets are still judged sentence by sentence.
- No arm that controls the batch effect (decision of the study owner).

## 4. Fixed before the run
- Data `src/nl2fret/data/lm_items.jsonl`, prompts as built in v1.5 (`prompts/sources_v15.json`), seed 20261116, model `sonnet`, `--effort medium`, 3 repetitions.
- Parser fingerprint: SHA-256 over (fretish, ok, ltl_ft, ltl_pt) of the 111 distinct reference sentences, pinned in `data/reference/parser_fingerprint.pin` on the machine that runs the generation (`run_batch.sh pin` with `WRITEPIN=1`). `run_batch.sh gen` stops on mismatch.
  Node copy of the parser on the sandbox: 111 sentences, 110 accepted, fingerprint 6b05c991a62383977cd31b78458d700aedfd564b4536515975786075f1710562. Docker versus node equality is not yet checked (needs the docker image).
- Timing semantics `src/nl2fret/data/timing_semantics.json` sha256 8b0e4e4aed61aee7abfa560f68ebb91cc1b3b3f4ecfe66633de2ca4fa44137ec.
- Lints: `tools/prompt_v15_lint.py` now covers BATCH_RULES, RT_HEAD, RT_TAIL.

## 5. Checked in the sandbox and not checked
Checked: isolation probe, one challenge (06_EB) end to end with v0/vf/rt inputs, group realizability job construction (dry run), 50 unit tests.
Not checked (needs the computer of the study owner): docker image `fret-lab` (group realizability result, docker parser fingerprint), login variables for the agent process (`--env-pass`, the probe tells), FROZEN_MANIFEST on that computer.

## 6. Commands
`EXT=dictionary bash scripts/run_batch.sh pin|gen|inputs|judge|group|effect|all [RUN_DIR]` (`EXT` is the list of extensions; default `dictionary`; `EXT=` switches all extensions off).

## 7. Measurement rule kept: realizability input normalization (N-LIT, added 2026-11-17, fixed before the re-run of 06_EB; a general rule, it reads no reference information)

### 7.1 Definition
- Scope: only the INPUT of the FRET realizability check (`fret_check/group_rlz.py` set jobs, `fret_check/check.py` single jobs). The sentences of the judge (`units.json`, `fret_ltl_gen.jsonl`) and the sentences shown to the model are never changed.
- Regions: only the condition and the response of a sentence (the parser's `conditionTextRange` and `responseTextRange`, end index inclusive). Scope, component and timing text are never changed.
- Tokens: numbers `\d+(\.\d+)?([eE][+-]?\d+)?`, identifiers, operators. Integer literal = a number token of digits only; real literal = a number token with a decimal point or an exponent.
- Double variable = a variable whose `dataType` is `double` in the variable table built from the sentences of the same set (variable policy `variable_policy.md` unchanged).
- Segmentation: a region is split at its top-level boolean connectors (`&`, `|`, `=>`, `<=>`); a leading `!` is dropped; parentheses that wrap a part containing a connector or a comparison are opened. A leaf is an arithmetic expression with at most one comparison (`<`, `<=`, `>`, `>=`, `=`, `!=`, `==`); with a comparison the leaf has a left and a right side.
- Conversion: an integer literal `n` is written `n.0` iff (a) one of its two neighbor tokens is an arithmetic or comparison operator (`+ - * /` or a comparison) and (b) its side of the leaf contains a double variable or a real literal, or its side is the literal alone and the other side contains one. A leaf without comparison counts as one side.
- A converted sentence is compiled again by the official parser. The job of the normalized set uses a variable table built from the normalized sentences with the unchanged rule; variables whose type differs between the raw and the normalized table are recorded (`type_changes`).
- Result columns of `group_rlz.jsonl`: `result_raw` (no conversion, equal to `result`), `result_normalized`, `cli_result_raw`, `cli_result_normalized`, `n_literals_converted`, `n_sentences_changed`, `type_changes`. A set in which nothing is converted runs once.

### 7.2 Primary and secondary (2026-11-17)
- Realizability: the normalized column is primary (`result` = `result_normalized`), the raw column is secondary (`result_raw`). The flag default is ON and is not changed. Judgment: single basis, the strict judgment (`judge_*`); `rt_effect.json` is computed from it.

## 8. Extension modules (2026-11-17)
- Core keeps only hooks. The flag `--ext NAME [NAME ...]` of `batch_pipeline.py` and `run_pipeline.py` and the variable `EXT` of `run_batch.sh` select extensions. The only extension is `dictionary` (`src/nl2fret/ext/dictionary/`, its README.md states role, interface and how to enable it).
- Extension on: the FRETish stage prompts carry the dictionary block, the judge runs with the dictionary of the extension (`--dictionary`). Extension off: the prompts have no dictionary block and the judge gets no dictionary content; because the frozen `src/nl2fret_judge/cli.py` declares `--dictionary` as a required argument of `judge-parts`, the module hands it a header-only dictionary file (no entry) instead of changing `src/nl2fret_judge/`.
- Aliases (columns `alias_of`, `alias_evidence`) are an optional overlay of the extension (`src/nl2fret/ext/dictionary/overlays/`), default off.

## 9. Withdrawn on 2026-11-17 (moved, not deleted: `archive/removed_features/`, `README.md` there gives reason and restore method)
- J+def judge variant (substitution of defined terms, term level, lustre_only classification, alias renaming of the derived inputs), the `judgedef` step, `rt_effect_strict.json`: withdrawn as a primary measure. Reason: decision of the study owner on 2026-11-17 (the primary measure is the strict judgment; the dictionary is an extension, not part of the core measure).
- Dictionary v2 (alias columns in the dictionary table): moved to the extension overlay; the default dictionary is v1.
- Hash list of the tool code (`FROZEN_MANIFEST.sha256`) and `make freeze-check` (2026-11-17, experiment 027): removed on the owner's request; the code is fixed by a git release tag, the run snapshots, judge headers and the parser fingerprint stay (`archive/removed_features/`).

## 10. Prompt text of the model-facing system prompts (2026-11-17, experiments 028 and 029; fixed before any run with it)
- Source: `prompts_paper_rules_final.zip` of the study owner (wording adapted from Darif et al., IEEE REW 2026, Fig. 4 and "Notations clarification"). The wording of the 12 files of the package is binding; the tool code builds exactly these bytes (checked byte for byte, `scripts/render_prompts.py --check`).
- Added text, identical across templates: G1 (stages A, B, D, in GENERAL RULES: write only what the input states; an element that the input leaves open follows the choice rule and is reported in "choices"), G2 (stage A: keep the wording of an input that already is a sentence of the template), G3 (stage A, closing line: several sentences only when the input states several subjects, action verbs or objects in its response; each sentence one subject, one action verb, one object), G4 (stages A and B: a block "NOTATION OF THE SPECIFICATION" before "TEMPLATE SPECIFICATION"). Stage S2 (slot filling), the five template documents and the FRETish guide are unchanged.
- The fallback of a +R2 method (stage name BF in the call records) uses the B prompt (+G) of its template; the five BF prompt files were byte identical to the B files and are no longer kept, so the tool has 12 system prompt files (A 5, B 5, D 1, S2 1). The run snapshot does not write BF files; the hash stays in `run_info.json` under `BF:<template>`.
- Consequence for comparisons: runs made before this date used the earlier 17 files (kept in `archive/prompts/system_prompts_before_paper_rules/`). No run with the new prompts exists yet and no effect is claimed.
- Open risk stated by the author of the package: G3 may split differently from the NASA reference (10 of 61 items have 2 to 9 reference parts, split by case or variable). Effect unknown.
- Provenance outside the prompts: the entry `task_rules` of `src/nl2fret/prompts/sources_v15.json`.
- Version 2 (experiment 029, `prompts_paper_rules_final_v2.zip`, same day, replaces version 1; the 12 files of version 1 are in `archive/prompts/system_prompts_paper_rules_v1/`): order of every prompt after Fig. 4 of Darif et al. 2026: task, general rules, output schema, then each specification block (definition, textual template, predefined templates, notation), signal dictionary last. G4: the block "NOTATION OF THE SPECIFICATION" now follows the template specification (stages A, B). G5 (stages B, D and the slot prompt S2): the block "NOTATION OF THE FRETISH GUIDE" (ANTLR notation) follows the FRETish guide. G6 (stages B, D): in the FRETish guide the section "Writing requirements" stands before the grammar; the text of every section and the guide file are unchanged (the order is applied when the prompt is assembled, `common._writing_first`). The wording of G1 to G3 is unchanged. The code builds the 12 files of the package byte for byte. The author's stated risk: the effect of G1 to G6 is unknown.

## 11. Keyword check step KC (2026-11-17, experiment 030; decision of the study owner, fixed before any run with it)
- Decision: KC is placed before RT1. No test run that looks at the effect is made; KC is part of the main run. KC is a check step, not feedback (section 2).
- Specification (`KC_STAGE_SPEC.md` of the project owner, summary): purpose: the model compares the FRETish keyword it chose with the official reference text that lists all keywords of the same group in the same form. Order: v0 -> feedback -> vf -> KC -> kc -> RT1 -> rt. Agent scope as RT1 (calls grouped by system prompt, challenge, repetition, stage). Reference answers and scores are never given; the input is the model's own answer, its original input and official text only.
- Firing (mechanical, no model judgement): the groups of a sentence are decided from the fields of the FRET parser output (`scope.type`, `condition`, `qualifier_word`, `timing`, and the text ranges `scopeTextRange`, `timingTextRange`): COND (condition with upon, when, where, if, whenever, unless), TIMING_POINT (timing omitted, immediately, initially, at the first / same / next timepoint, finally, at the last timepoint, eventually, always, never), TIMING_DURATION (within, for, after), TIMING_STOP (until, before), SCOPE (a scope keyword is present; an omitted scope does not fire). The keyword shown is the one written in the sentence. Only when the fields are not available (the parser rejected the sentence) the groups come from the tokens of the sentence and `via` records it. A sentence without a group is not listed; a batch without any group skips KC (`kc_skipped`).
- Message (`src/nl2fret/kc_stage.py`): `KC_HEAD`, one block per item (`ITEM`, `input`, `sentence n`, `groups`), the reference document of every fired group once per batch (`src/nl2fret/prompts/kc/KC_*.md`, copies of lines of the FRETish guide), `KC_TAIL`, the signal dictionary last. The fixed wording is in the constants and is part of the V-STYLE lint.
- Adoption as RT1 (section 2.2). Records: call-row column `kc_groups`; unit state `kc_adopted`, `kc_changed`, `kc_skipped`; `kc_doc_sha` (sha256 of every reference document) in `run_info.json`; variants v0, vf, kc, rt judged by the same judge. `tools/rt_effect.py` counts gains and losses between all variants on the same (item, rep, part) and, with `--keyword-inputs`, the distribution of the keywords (timing, condition, scope) in vf and kc (check for a drift to one keyword). The adoption rule only checks the parser; an answer with a worse meaning can be adopted and then counts as a loss of the kc variant.
- Switch: `--no-kc` of `batch_pipeline.py`, `NO_KC=1` of `scripts/run_batch.sh` (default on).
- +R2 methods follow RT1: the assembled sentences are shown and the slot answer (system prompt S2) is requested again; a unit that fell back to the free path uses the B prompt (stage name BF), Direct uses D, +G uses B.
- Observed while implementing: the official parser rejects the sentence `the system shall always satisfy count >= 0` (reserved word `count`) and the example `While mode = 4 ...` of the FRETish guide; the guide text and the reference documents are not changed.

