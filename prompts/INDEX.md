# Prompts Index

Two parts. Section 1 lists the **current prompts**, which are stored as files in `prompts/current/`. Section 2 indexes the historical prompt and instruction documents, which stay inside the experiment folders (`experiments/` is excluded from git).

## 1. Current prompts (`prompts/current/`)

State: final tool `nl2fret_tool/`, release 1.2.0 (frozen, see `nl2fret_tool/CHANGELOG.md`), as used by the 61-item main generation run of 2026-11-11. The files are copies. For the model-facing prompts the source of truth is the frozen tool (`nl2fret_tool/bench/`, hashes in `nl2fret_tool/bench/FROZEN_MANIFEST.sha256`); do not edit the copies. Check the whole folder with `cd prompts/current && shasum -a 256 -c SHA256SUMS`, and the assembled system prompts with `python3 -I -B tools/render_prompts.py --check`.

### 1.1 Model-facing prompts (what the pipeline sends to the model)

The pipeline assembles each system prompt from fixed text in code, the FRETish guide and one template document (`nl2fret_tool/bench/common.py`, `prompts3.py`).

| Path | Content | sha256 (first 12 characters) |
|---|---|---|
| `prompts/current/fretish_guide.md` | FRETish guide; part of every system prompt that asks the model for FRETish (stages B and D) | 00366ed670c5 |
| `prompts/current/templates/adv_ears.md` | Adv-EARS template specification; part of the stage A prompt, and of the stage B prompt for reading the input | 013f6afd16f8 |
| `prompts/current/templates/boilerplate.md` | Boilerplate template specification | 2c9dcb4e4e75 |
| `prompts/current/templates/ears.md` | EARS template specification | 7d1b29218d10 |
| `prompts/current/templates/masteR.md` | MASTeR template specification | 33cbe67863de |
| `prompts/current/templates/spider.md` | SPIDER template specification | 1c8c13d8f4b2 |
| `prompts/current/system_prompts/` | the 21 assembled system prompts, byte for byte as the pipeline sends them (rendered by `tools/render_prompts.py`; the 18 prompts of run A are byte-identical to the `snapshot/` of the main run); `MANIFEST.csv` lists file, stage, arms that use it, size and sha256 | see `MANIFEST.csv` |

Stages: A = natural language to template sentences; B = template sentences to FRETish; D = natural language directly to FRETish; S2 = slot filling of the rule-assembly methods (+R2), where a script assembles the FRETish sentence. The feedback rounds F1 and F2 reuse the system prompt of the first stage of the method and add the parser's rejection messages to the user message.

| System prompt file | Used by |
|---|---|
| `system_prompt_A_<template>.txt` (PARA, MASTeR, EARS, Adv-EARS, SPIDER, Boilerplate) | stage A of every method with that template; shared by the +R2, +V and +D variants |
| `system_prompt_B_<method>.txt` (PARA, MASTeR, EARS, Adv-EARS, SPIDER, Boilerplate, MASTeR+V, EARS+V, Boilerplate+V, MASTeR+D, EARS+D) | stage B of the method in the file name |
| `system_prompt_D_none.txt`, `system_prompt_D_DIRECT+V.txt`, `system_prompt_D_DIRECT+D.txt` | DIRECT, DIRECT+V, DIRECT+D |
| `system_prompt_S2_none.txt` | the five +R2 methods |

The user messages of each stage and the feedback message are built in code: `user_prompt_A`, `user_prompt_B`, `user_prompt_D` in `nl2fret_tool/bench/common.py`, `user_prompt_S` and `user_prompt_feedback` in `nl2fret_tool/bench/prompts3.py`. The signal dictionary that the +D methods add to the user message is `nl2fret_tool/bench/data/sigdict.json`.

### 1.2 Instruction prompts (given to the executor, Claude Code)

Written by the project owner in Korean and kept verbatim. `testnote.md`, the living file at the repository root, is not copied here (the project owner excludes it from git); these are its named copies from the experiment folders.

| Path | Content | sha256 (first 12 characters) |
|---|---|---|
| `prompts/current/instructions/NL2FRET_PROMPT_v8_DICT_SMOKE.md` | last numbered instruction prompt of the generation line (v8, signal-dictionary smoke run); also inside the frozen tool as `nl2fret_tool/bench/NL2FRET_PROMPT_v8_DICT_SMOKE.md` | 2b0ebc9a9113 |
| `prompts/current/instructions/NL2FRET_TOOL_V12_FREEZE.md` | final patch and freeze of the tool (release 1.2.0) | e40c499a03f5 |
| `prompts/current/instructions/NL2FRET_61_INPUTS.md` | build the three judge input files from the v6 main run of the 61 items | 519e9837f3c5 |
| `prompts/current/instructions/NL2FRET_61_MAIN_RUN.md` | the 61-item main generation run with the frozen bench (run A: 16 methods; run B: the signal-dictionary methods on 51 items) | 568e5712636b |

## 2. Historical prompts (locations inside `experiments/`)

The original prompt and instruction documents of the runs stay inside each experiment folder in the state they had at run time, so that the hash verification (`FROZEN*.sha256`) and the relative paths of `snapshot/` remain valid. This section lists locations only. `testnote.md` is updated by the project owner at the repository root, so it was not moved.

| Path | sha256 (first 12 characters) |
|---|---|
| `experiments/018_lm61_inputs/docs/NL2FRET_61_INPUTS.md` | 519e9837f3c5 |
| `experiments/019_lm61_main_gen/docs/NL2FRET_61_MAIN_RUN.md` | 568e5712636b |
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

100 entries in total (95 as of 2026-11-09, plus 5 instruction documents of 2026-11-10 and 2026-11-11 added on 2026-11-11). Files with the same name in different experiment folders can have different contents (see the hash column). `testnote.md` is a living file: the hash above is its value on 2026-11-09 21:03, when it was copied to `experiments/judge_recording/docs/NL2FRET_JUDGE_RECORDING.md` (byte-identical at that time). Its earlier value 565a8dc6015b (18:27 the same day) is the hash of the copy `experiments/nusmv_paper/docs/NL2FRET_NUSMV_PAPER.md`.
