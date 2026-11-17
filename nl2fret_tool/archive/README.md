이전 버전은 `archive/<자산>/v<N>/` 형식으로 둔다. 색인은 `../VERSIONS.md`이다.

- `archive/releases/v1.4/`: 도구 릴리스 v1.4 (113개 파일, 11개 변환 방식 FSM 시험용). 현재 도구는 이 폴더의 상위(`nl2fret_tool/`)(v2.0)이다.
- `archive/releases/v1.2.0/`: 도구 릴리스 v1.2.0 (75개 파일, 동결 판정 모듈 포함).
- `archive/removed_features/`: 2026-11-17 정리에서 도구에서 뺀 기능(J+def 판정 변형과 그 시험, 설계 문서의 철회된 절)과 복원 방법(README.md). 딕셔너리 v1은 다시 현재 자산(`../assets/dictionary/v1/`)이고, 별칭 열을 가진 v2는 `../bench/ext/dictionary/overlays/v2/`에 있다.
- `archive/removed_features/sha_files/`: the `SHA256SUMS` files of the assets, of `prompts/current/` and of the dictionary extension (moved 2026-11-17, same relative paths). Left in place: the hash files inside the archived releases, `external/docker/cst-nusmv/nusmv_context.sha256` (integrity check of the third-party NuSMV build context) and the records of the study `experiments/ltlpack/`.
- `archive/nl2fret_tool_docs/v1.4/`: 도구 문서의 릴리스 1.4 판 (`docs/DESIGN.md`, `docs/RUNBOOK.md`, `docs/EXPERIMENT_FSM.md`, `docs/ANALYSIS_PLAN.md`, `docs/V14_GUIDE_SUPPLEMENT.md`, `docs/V14_INTENT_TEST.md`, `docs/DATA_VERSIONING.md`, `docs/TRACE_FORMAT.md`, `docs/controls_nusmv512/`, `docs/old_prompts/`, `package/` (NL2FRET_PROMPT_v8_DICT_SMOKE.md of the old package), `package_root/`의 README.md, Makefile, NL2FRET_PROMPT_FSM_V14_MAC.md, requirements.txt). 현재 문서는 `../nl2fret_tool/`의 README.md와 `docs/`이다.
- `archive/process_lifecycle_doc/v1/`: 릴리스 1.2.0 시기의 전 주기 문서. 현재 문서는 `../docs/TOOL_PROCESS_GUIDE.md`이다.
- `archive/unsorted/`: 용도를 알 수 없는 파일 (`fret_template_bench.zip`, git 추적 제외). 2026-11-17에 루트의 `unsorted/`에서 옮김.
- `archive/prompts/system_prompts_before_paper_rules/`: the 17 system prompt files of release 2.0 before the paper rules (2026-11-17) with their `MANIFEST.csv` and `sources_v15.json`.
- `archive/instructions/`: instruction records given to the executor (moved on 2026-11-17 from `prompts/current/instructions/`; they are not model-facing prompts). Index: `prompts/INDEX.md` section 1.2.
- `archive/prompts/system_prompts_paper_rules_v1/`: the 12 system prompt files of the first paper-rule version (G1 to G4) with `MANIFEST.csv` and `sources_v15.json`, replaced on 2026-11-17 by version 2 (experiment 029).
