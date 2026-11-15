# Prompts Index

Two parts. Section 1 lists the **current prompts**, which are stored as files in `prompts/current/`. Section 2 indexes the historical prompt and instruction documents, which stay inside the experiment folders (`experiments/` is excluded from git).

## 1. Current prompts (`prompts/current/`)

State: final tool `nl2fret_tool/`, release 1.4 (11 approaches of the FSM test; the previous release 1.2.0 is in `archive/nl2fret_tool/v1.2.0/`). The files are copies. For the model-facing prompts the source of truth is the tool (`nl2fret_tool/bench/`, hashes in `nl2fret_tool/bench/FROZEN_MANIFEST.sha256`); do not edit the copies. Check the whole folder with `cd prompts/current && shasum -a 256 -c SHA256SUMS`, and the assembled system prompts with `python3 -I -B tools/render_prompts.py --check`.

### 1.1 Model-facing prompts (what the pipeline sends to the model)

The pipeline assembles each system prompt from fixed text in code, the FRETish guide, the intent declaration (`nl2fret_tool/bench/prompts/intent_declaration.md`), the rule text (`nl2fret_tool/bench/tpl_rules.py`) and one template document (`nl2fret_tool/bench/common.py`, `prompts3.py`).

| Path | Content | sha256 (first 12 characters) |
|---|---|---|
| `prompts/current/fretish_guide.md` | FRETish guide; part of every system prompt that asks the model for FRETish (stages B and D) | 00366ed670c5 |
| `prompts/current/templates/adv_ears.md` | Adv-EARS template specification; part of the stage A prompt, and of the stage B prompt for reading the input | 013f6afd16f8 |
| `prompts/current/templates/boilerplate.md` | Boilerplate template specification | 2c9dcb4e4e75 |
| `prompts/current/templates/ears.md` | EARS template specification | 7d1b29218d10 |
| `prompts/current/templates/masteR.md` | MASTeR template specification | 33cbe67863de |
| `prompts/current/templates/spider.md` | SPIDER template specification | 1c8c13d8f4b2 |
| `prompts/current/system_prompts/` | the 17 assembled system prompts of release 1.4 (11 approaches, options `--dict-all --intent-decl --g-parity --tm-source-only --sourced-rules-only`), byte for byte as the pipeline sends them (rendered by `tools/render_prompts.py`; byte-identical to the `gen/snapshot/` of the v1.4 FSM test); `MANIFEST.csv` lists file, stage, arms that use it, size and sha256. The 21 system prompts of the 61-item main run (release 1.2.0) are in `assets/llm_system_prompts/v1/` | see `MANIFEST.csv` |

Stages: A = natural language to template sentences; B = template sentences to FRETish (rule text, +G); D = natural language directly to FRETish; S2 = slot filling of the rule-assembly methods (+R2), where a script assembles the FRETish sentence; BF = fallback of a rule-assembly method (the +G prompt of its template). The feedback rounds F1 to F5 reuse the system prompt of the first stage of the method and add the cumulative FRET log (rejection messages and hints) to the user message.

| System prompt file | Used by |
|---|---|
| `system_prompt_A_<template>.txt` (MASTeR, EARS, Adv-EARS, SPIDER, Boilerplate) | stage A of the +G and +R2 methods with that template (shared) |
| `system_prompt_B_<template>+G.txt` (five templates) | stage B of the rule-text methods (`<template>+G`) |
| `system_prompt_BF_<template>.txt` (five templates) | fallback of the rule-assembly methods (`<template>+R2`); the same bytes as `system_prompt_B_<template>+G.txt` |
| `system_prompt_D_none.txt` | DIRECT |
| `system_prompt_S2_none.txt` | the five +R2 methods |

The user messages of each stage and the feedback message are built in code: `user_prompt_A`, `user_prompt_B`, `user_prompt_D` in `nl2fret_tool/bench/common.py`, `user_prompt_S` and `user_prompt_feedback` in `nl2fret_tool/bench/prompts3.py`. The signal dictionary that every method adds to the FRETish-stage user message (option `--dict-all`) is `nl2fret_tool/bench/data/sigdict.json`; the feedback message is `user_prompt_feedback_log` in `nl2fret_tool/bench/prompts3.py`.

### 1.2 Instruction prompts (given to the executor, Claude Code)

Written by the project owner in Korean and kept verbatim. `testnote.md`, the living file at the repository root, is not copied here (the project owner excludes it from git); these are its named copies from the experiment folders.

| Path | Content | sha256 (first 12 characters) |
|---|---|---|
| `prompts/current/instructions/NL2FRET_PROMPT_v8_DICT_SMOKE.md` | last numbered instruction prompt of the generation line (v8, signal-dictionary smoke run); also inside the frozen tool as `nl2fret_tool/bench/NL2FRET_PROMPT_v8_DICT_SMOKE.md` | 2b0ebc9a9113 |
| `prompts/current/instructions/NL2FRET_TOOL_V12_FREEZE.md` | final patch and freeze of the tool (release 1.2.0) | e40c499a03f5 |
| `prompts/current/instructions/NL2FRET_61_INPUTS.md` | build the three judge input files from the v6 main run of the 61 items | 519e9837f3c5 |
| `prompts/current/instructions/NL2FRET_61_MAIN_RUN.md` | the 61-item main generation run with the frozen bench (run A: 16 methods; run B: the signal-dictionary methods on 51 items) | 568e5712636b |
| `prompts/current/instructions/NL2FRET_PROMPT_MAIN_JUDGE.md` | post-processing, judging and RQ aggregation of the 61-item main generation run with the frozen tool v1.2.0 (given 2026-11-12 with `nl2fret_main_judge_pack.zip`) | f49188a2a5e5 |
| `prompts/current/instructions/NL2FRET_PROMPT_COMPARABILITY_TEST.md` | exploratory side run after the main judging: the 3999 pairs judged again with the name-correspondence modes free and strict, a negative control (300 units, items shifted), and a vocabulary-independent skeleton comparison, frozen tool v1.2.0 (given 2026-11-12 with `nl2fret_comparability_test_pack.zip`) | 9f1478e3812c |
| `prompts/current/instructions/NL2FRET_PROMPT_DICT_JUDGE_RUN.md` | judging of the dictionary-applied and alias-applied LTL inputs with the frozen tool v1.2.0 (negative, name-swap and alias controls), registration of the assets as versions (`assets/`, `VERSIONS.md`) and the process document `docs/PROCESS_LIFECYCLE.md` (given 2026-11-13 with `dict_inputs.zip`) | a912e64c4d07 |
| `prompts/current/instructions/NL2FRET_PROMPT_FSM_RUN_v1.md` | FSM test of the tool package v1.3: version-up of the dataset, dictionary and reference assets, then the pipeline on the 13 `01_FSM` items (11 arms, 3 repetitions, 429 units) from generation to NuSMV judging, with counterexample records and a per-unit trace (given 2026-11-13 with `nl2fret_tool_v1.3.zip`) | e770e966147d |
| `prompts/current/instructions/NL2FRET_PROMPT_FSM_V14_MAC.md` | retest of the 13 `01_FSM` items (11 arms, 3 repetitions, 429 units) with the prompts of tool package v1.4 (guide parity, intent declaration, source-only rules), preceded by pre-tasks (environment, tests, ownership table, rule semantics check, judge controls, baseline rejudge at CAP 512, prompt lints), followed by analysis and comparison with the v1.3 baseline; observations only, no hypothesis verdicts (given 2026-11-15 with `nl2fret_v1.4_FSM_retest_package.zip`) | f0f48bde1137 |

## 2. Historical prompts (locations inside `experiments/`)

The original prompt and instruction documents of the runs stay inside each experiment folder in the state they had at run time, so that the hash verification (`FROZEN*.sha256`) and the relative paths of `snapshot/` remain valid. This section lists locations only. `testnote.md` is updated by the project owner at the repository root, so it was not moved.

| Path | sha256 (first 12 characters) |
|---|---|
| `experiments/018_lm61_inputs/docs/NL2FRET_61_INPUTS.md` | 519e9837f3c5 |
| `experiments/019_lm61_main_gen/docs/NL2FRET_61_MAIN_RUN.md` | 568e5712636b |
| `experiments/020_lm61_main_judge/docs/NL2FRET_PROMPT_MAIN_JUDGE.md` | f49188a2a5e5 |
| `experiments/021_comparability_test/docs/NL2FRET_PROMPT_COMPARABILITY_TEST.md` | 9f1478e3812c |
| `experiments/022_dict_judge_run/docs/NL2FRET_DICT_PRE_REGISTRATION.md` | aa351623fd20 |
| `experiments/022_dict_judge_run/docs/NL2FRET_PROMPT_DICT_JUDGE_RUN.md` | a912e64c4d07 |
| `experiments/023_fsm_run_v13/docs/NL2FRET_PROMPT_FSM_RUN_v1.md` | e770e966147d |
| `experiments/024_fsm_v14_retest/docs/NL2FRET_PROMPT_FSM_V14_MAC.md` | f0f48bde1137 |
| `experiments/fret_retest_v2/RETEST_PROMPT_v2.md` | a9ab2c03d747 |
| `experiments/fret_retest_v2/templates/adv_ears.md` | 6b46c563b3fa |
| `experiments/fret_retest_v2/templates/ears.md` | fadae2536d5c |
| `experiments/fret_retest_v2/templates/masteR.md` | fee29847fc57 |
| `experiments/fret_retest_v2/templates/spider.md` | 2391a2c57eb1 |
| `experiments/fret_template_bench/results/inputs_snapshot/templates/adv_ears.md` | 6b46c563b3fa |
| `experiments/fret_template_bench/results/inputs_snapshot/templates/ears.md` | 73107aeea71e |
| `experiments/fret_template_bench/results/inputs_snapshot/templates/masteR.md` | 9f33ee00d27a |
| `experiments/fret_template_bench/results/inputs_snapshot/templates/spider.md` | 22da82a2f231 |
| `experiments/fret_template_bench/results/inputs_snapshot/templates/spider_override.md` | 43401e8d694c |
| `experiments/fret_template_bench/templates/adv_ears.md` | 6b46c563b3fa |
| `experiments/fret_template_bench/templates/ears.md` | 73107aeea71e |
| `experiments/fret_template_bench/templates/masteR.md` | 9f33ee00d27a |
| `experiments/fret_template_bench/templates/spider.md` | 22da82a2f231 |
| `experiments/fret_template_bench/templates/spider_override.md` | 43401e8d694c |
| `experiments/judge_recording/docs/NL2FRET_JUDGE_RECORDING.md` | a6b8953b9fec |
| `experiments/nl2fret/NL2FRET_PROMPT_v1.md` | f6228448c9b7 |
| `experiments/nl2fret/prompts/fretish_guide.md` | 568e9c517766 |
| `experiments/nl2fret/templates/adv_ears.md` | 013f6afd16f8 |
| `experiments/nl2fret/templates/boilerplate.md` | 2c9dcb4e4e75 |
| `experiments/nl2fret/templates/ears.md` | 7d1b29218d10 |
| `experiments/nl2fret/templates/masteR.md` | 33cbe67863de |
| `experiments/nl2fret/templates/spider.md` | 1c8c13d8f4b2 |
| `experiments/nl2fret_tool_mac/docs/NL2FRET_TOOL_MAC.md` | 8cb1692b0637 |
| `experiments/nl2fret_tool_v11/docs/NL2FRET_TOOL_PATCH_V11.md` | f0bc621a60b8 |
| `experiments/nl2fret_tool_v12/docs/NL2FRET_TOOL_V12_FREEZE.md` | e40c499a03f5 |
| `experiments/nl2fret_v2/NL2FRET_PROMPT_v2.md` | e462e00c32f4 |
| `experiments/nl2fret_v2/prompts/fretish_guide.md` | 7e3821a30e85 |
| `experiments/nl2fret_v2/templates/adv_ears.md` | 013f6afd16f8 |
| `experiments/nl2fret_v2/templates/boilerplate.md` | 2c9dcb4e4e75 |
| `experiments/nl2fret_v2/templates/ears.md` | 7d1b29218d10 |
| `experiments/nl2fret_v2/templates/masteR.md` | 33cbe67863de |
| `experiments/nl2fret_v2/templates/spider.md` | 1c8c13d8f4b2 |
| `experiments/nl3/NL2FRET_PROMPT_v3.md` | 6f1d2ca8aff7 |
| `experiments/nl3/prompts/fretish_guide.md` | 7e3821a30e85 |
| `experiments/nl3/templates/adv_ears.md` | 013f6afd16f8 |
| `experiments/nl3/templates/boilerplate.md` | 2c9dcb4e4e75 |
| `experiments/nl3/templates/ears.md` | 7d1b29218d10 |
| `experiments/nl3/templates/masteR.md` | 33cbe67863de |
| `experiments/nl3/templates/spider.md` | 1c8c13d8f4b2 |
| `experiments/nl4/NL2FRET_PROMPT_v4_LM.md` | 01effda7c15d |
| `experiments/nl4/NL2FRET_SMOKE_v4_LM.md` | 95346d39da88 |
| `experiments/nl4/prompts/fretish_guide.md` | 7e3821a30e85 |
| `experiments/nl4/templates/adv_ears.md` | 013f6afd16f8 |
| `experiments/nl4/templates/boilerplate.md` | 2c9dcb4e4e75 |
| `experiments/nl4/templates/ears.md` | 7d1b29218d10 |
| `experiments/nl4/templates/masteR.md` | 33cbe67863de |
| `experiments/nl4/templates/spider.md` | 1c8c13d8f4b2 |
| `experiments/nl5/NL2FRET_PROMPT_v4_LM.md` | 7dae990f56da |
| `experiments/nl5/NL2FRET_SMOKE2_v4_LM.md` | 7ec816597584 |
| `experiments/nl5/prompts/fretish_guide.md` | dd654d7d7fcf |
| `experiments/nl5/templates/adv_ears.md` | 013f6afd16f8 |
| `experiments/nl5/templates/boilerplate.md` | 2c9dcb4e4e75 |
| `experiments/nl5/templates/ears.md` | 7d1b29218d10 |
| `experiments/nl5/templates/masteR.md` | 33cbe67863de |
| `experiments/nl5/templates/spider.md` | 1c8c13d8f4b2 |
| `experiments/nl6/NL2FRET_PROMPT_v6_LM.md` | 95fecdab0f86 |
| `experiments/nl6/prompts/fretish_guide.md` | dd654d7d7fcf |
| `experiments/nl6/templates/adv_ears.md` | 013f6afd16f8 |
| `experiments/nl6/templates/boilerplate.md` | 2c9dcb4e4e75 |
| `experiments/nl6/templates/ears.md` | 7d1b29218d10 |
| `experiments/nl6/templates/masteR.md` | 33cbe67863de |
| `experiments/nl6/templates/spider.md` | 1c8c13d8f4b2 |
| `experiments/nl7/NL2FRET_PROMPT_v6_LM.md` | 18745e0617bf |
| `experiments/nl7/prompts/fretish_guide.md` | dd654d7d7fcf |
| `experiments/nl7/templates/adv_ears.md` | 013f6afd16f8 |
| `experiments/nl7/templates/boilerplate.md` | 2c9dcb4e4e75 |
| `experiments/nl7/templates/ears.md` | 7d1b29218d10 |
| `experiments/nl7/templates/masteR.md` | 33cbe67863de |
| `experiments/nl7/templates/spider.md` | 1c8c13d8f4b2 |
| `experiments/nusmv_paper/docs/NL2FRET_NUSMV_PAPER.md` | 565a8dc6015b |
| `experiments/v7_dev0/bench/NL2FRET_PROMPT_v7_DEV0.md` | 718b9a520e4d |
| `experiments/v7_dev0/bench/prompts/fretish_guide.md` | dd654d7d7fcf |
| `experiments/v7_dev0/bench/templates/adv_ears.md` | 013f6afd16f8 |
| `experiments/v7_dev0/bench/templates/boilerplate.md` | 2c9dcb4e4e75 |
| `experiments/v7_dev0/bench/templates/ears.md` | 7d1b29218d10 |
| `experiments/v7_dev0/bench/templates/masteR.md` | 33cbe67863de |
| `experiments/v7_dev0/bench/templates/spider.md` | 1c8c13d8f4b2 |
| `experiments/v7_dev1/bench/NL2FRET_PROMPT_v7_DEV0.md` | 718b9a520e4d |
| `experiments/v7_dev1/bench/NL2FRET_PROMPT_v7_DEV1.md` | 37fb7f414978 |
| `experiments/v7_dev1/bench/prompts/fretish_guide.md` | dd654d7d7fcf |
| `experiments/v7_dev1/bench/templates/adv_ears.md` | 013f6afd16f8 |
| `experiments/v7_dev1/bench/templates/boilerplate.md` | 2c9dcb4e4e75 |
| `experiments/v7_dev1/bench/templates/ears.md` | 7d1b29218d10 |
| `experiments/v7_dev1/bench/templates/masteR.md` | 33cbe67863de |
| `experiments/v7_dev1/bench/templates/spider.md` | 1c8c13d8f4b2 |
| `experiments/v8_dict8/bench/NL2FRET_PROMPT_v8_DICT_SMOKE.md` | 2b0ebc9a9113 |
| `experiments/v8_dict8/bench/prompts/fretish_guide.md` | 00366ed670c5 |
| `experiments/v8_dict8/bench/templates/adv_ears.md` | 013f6afd16f8 |
| `experiments/v8_dict8/bench/templates/boilerplate.md` | 2c9dcb4e4e75 |
| `experiments/v8_dict8/bench/templates/ears.md` | 7d1b29218d10 |
| `experiments/v8_dict8/bench/templates/masteR.md` | 33cbe67863de |
| `experiments/v8_dict8/bench/templates/spider.md` | 1c8c13d8f4b2 |
| `experiments/v8_dict8/docs/NL2FRET_PROMPT_v8_DICT_SMOKE.md` | 2b0ebc9a9113 |
| `experiments/v8_dict8/docs/NL2FRET_RLZ_DICT8.md` | 2a96505c6379 |
| `packages/ltlpack/pack/README_MAC.md` | f78ab67ffd0b |
| `docs/NL2FRET_v6_main_analysis_ppt_format.md` | 9a302384ba80 |
| `testnote.md` | a6b8953b9fec |

106 entries in total (95 as of 2026-11-09, plus 5 instruction documents of 2026-11-10 and 2026-11-11 added on 2026-11-11, plus 2 of 2026-11-12, plus 2 of 2026-11-13: the instruction of the dictionary judging run and its pre-registration document, plus 1 of 2026-11-13: the instruction of the FSM test of tool v1.3, plus 1 of 2026-11-15: the instruction of the v1.4 FSM retest). Files with the same name in different experiment folders can have different contents (see the hash column). `testnote.md` is a living file: the hash above is its value on 2026-11-09 21:03, when it was copied to `experiments/judge_recording/docs/NL2FRET_JUDGE_RECORDING.md` (byte-identical at that time). Its earlier value 565a8dc6015b (18:27 the same day) is the hash of the copy `experiments/nusmv_paper/docs/NL2FRET_NUSMV_PAPER.md`.
