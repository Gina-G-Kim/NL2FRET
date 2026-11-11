# Data Index

The input cases are organized by source group in `cases/` (`cases/README.md`, `cases/nasa_papers/SOURCES.md`, `cases/lockheed_martin/SOURCES.md`, `cases/fsm/SOURCES.md`). The table below lists the locations of the original data files inside `experiments/`.

The input data (item files, signal dictionary, pair lists and so on) stay in the `data/` folder of each experiment folder. The reference FRETish (ground truth) was not separated into its own folder, and no `reference/` folder was created, because the documents do not say which files hold the reference data. This index lists locations and hashes only. Identical hashes mean identical contents. `experiments/nusmv_paper` holds no input data of its own: it reads `packages/ltlpack/pack/data/pairs.jsonl` and `packages/ltlpack/pack/results/pairs_out.jsonl` read-only (hashes pinned in `experiments/nusmv_paper/notes/PRE_RUN.sha256`).

| Path | Size (bytes) | sha256 (first 12 characters) |
|---|---|---|
| `experiments/fret_retest_v2/data/requirements_v2.jsonl` | 20081 | aa29da774846 |
| `experiments/fret_template_bench/data/requirements.jsonl` | 12844 | 4c749cd2ccf0 |
| `experiments/fret_template_bench/results/inputs_snapshot/data/requirements.jsonl` | 12844 | 4c749cd2ccf0 |
| `experiments/nl2fret/data/pairs_v1.jsonl` | 50494 | 562696df952d |
| `experiments/nl2fret_v2/data/fret_gt_rows.jsonl` | 20455 | da8a2b626660 |
| `experiments/nl2fret_v2/data/pairs_v2.jsonl` | 67764 | 93a08d40e116 |
| `experiments/nl2fret_v2/data/pool_v2.json` | 118874 | 55103901c1b5 |
| `experiments/nl2fret_v2/data/selection_log.json` | 2075 | bcfbb6c96743 |
| `experiments/nl2fret_v2/results_nl2fret/data/fret_gt_rows.jsonl` | 20455 | da8a2b626660 |
| `experiments/nl2fret_v2/results_nl2fret/data/pairs_v2.jsonl` | 67764 | 93a08d40e116 |
| `experiments/nl2fret_v2/results_nl2fret/data/pool_v2.json` | 118874 | 55103901c1b5 |
| `experiments/nl2fret_v2/results_nl2fret/data/selection_log.json` | 2075 | bcfbb6c96743 |
| `experiments/nl3/data/calib_items.jsonl` | 47237 | a494484e13e7 |
| `experiments/nl3/data/fret_gt_rows.jsonl` | 20455 | da8a2b626660 |
| `experiments/nl3/data/pairs_v2.jsonl` | 67764 | 93a08d40e116 |
| `experiments/nl3/data/pool_v2.json` | 118874 | 55103901c1b5 |
| `experiments/nl4/data/lm_items.jsonl` | 157865 | 815a037d4ad3 |
| `experiments/nl4/data/lm_smoke.jsonl` | 13787 | 0fd7421dea97 |
| `experiments/nl5/data/lm_items.jsonl` | 157865 | 815a037d4ad3 |
| `experiments/nl5/data/lm_smoke.jsonl` | 13787 | 0fd7421dea97 |
| `experiments/nl6/data/lm_items.jsonl` | 157865 | 815a037d4ad3 |
| `experiments/nl6/data/lm_mapping_review.json` | 6403 | fce1fc6cbb7b |
| `experiments/nl6/data/lm_preflight.jsonl` | 13787 | 0fd7421dea97 |
| `experiments/nl6/data/lm_slot_annotation.jsonl` | 27379 | ac8e1b6b83b8 |
| `experiments/nl7/data/lm_items.jsonl` | 157865 | 815a037d4ad3 |
| `experiments/nl7/data/lm_mapping_review.json` | 6403 | fce1fc6cbb7b |
| `experiments/nl7/data/lm_preflight.jsonl` | 13787 | 0fd7421dea97 |
| `experiments/nl7/data/lm_slot_annotation.jsonl` | 27379 | ac8e1b6b83b8 |
| `experiments/v7_dev0/bench/data/dev_items.jsonl` | 18814 | e70710a0f99a |
| `experiments/v7_dev1/bench/data/dev_items.jsonl` | 18814 | e70710a0f99a |
| `experiments/v7_dev1/bench/data/dev_ltl_sentences.json` | 111003 | 2b1ab3f89f89 |
| `experiments/v7_dev1/bench/data/dev_ltl_sentences_all.json` | 206238 | e25f97a49ae9 |
| `experiments/v8_dict8/bench/data/dict8_items.jsonl` | 5992 | 1649b5a61eec |
| `experiments/v8_dict8/bench/data/lm_items.jsonl` | 17660 | a8314c94aa81 |
| `experiments/v8_dict8/bench/data/sigdict.json` | 9780 | a190a714c616 |
| `packages/ltlpack/pack/data/dev_ltl_sentences.json` | 111003 | 2b1ab3f89f89 |
| `packages/ltlpack/pack/data/formulas.jsonl` | 117167 | 8d92cdd293e0 |
| `packages/ltlpack/pack/data/pairs.jsonl` | 331791 | caed59ff3d3b |

38 entries in total.
