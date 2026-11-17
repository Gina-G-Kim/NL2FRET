버전업 규칙: 자산을 고치면 `assets/<자산>/v<N+1>/`에 새 버전을 만들고 이전 버전은 `archive/<자산>/v<N>/`로 옮기며, 이 표의 현재 버전, 경로, 변경 사유, 변경을 일으킨 실험 열을 같은 규칙으로 갱신한다.

# 자산 버전 색인

(2026-11-17: sha256 열을 없앴다. 자산 폴더 안의 `SHA256SUMS` 파일도 옮겼다(`archive/removed_features/sha_files/`). 도구 코드의 고정은 git 릴리스 태그로 한다. `archive/removed_features/README.md` 참조)

| 자산 | 현재 버전 | 경로 | 변경 사유 | 변경을 일으킨 실험 |
|---|---|---|---|---|
| signal_dictionary | v1 | `assets/signal_dictionary/v1/` | 신호 이름 딕셔너리(392쌍, 50개 항목) 등록 | 022_dict_judge_run |
| signal_dictionary_rules | v1 | `assets/signal_dictionary_rules/v1/` | 딕셔너리 구성 규칙 rules_01 내지 rules_08과 제거 목록 등록 | 022_dict_judge_run |
| dict_alias_scripts | v1 | `assets/dict_alias_scripts/v1/` | 딕셔너리 적용, 별칭 증명, 증명서 검사, 이름 교환 스크립트 등록 | 022_dict_judge_run |
| alias_certificates | v1 | `assets/alias_certificates/v1/` | 별칭 증명서 302건 등록 | 022_dict_judge_run |
| preregistration | v1 | `assets/preregistration/v1/` | 사전등록 문서(딕셔너리와 별칭)와 실험별 사전 정의 문서 등록 | 022_dict_judge_run |
| template_guides | v1 | `assets/template_guides/v1/` | 템플릿 가이드 5종(MASTeR, EARS, Adv-EARS, SPIDER, Boilerplate) 등록 | 022_dict_judge_run |
| llm_system_prompts | v1 | `assets/llm_system_prompts/v1/` | 생성에 쓴 시스템 프롬프트 21종(PARA, +R2, +V, +D 방식 포함)과 MANIFEST 등록 | 022_dict_judge_run |
| user_prompt_builders | v1 | `assets/user_prompt_builders/v1/` | 사용자 프롬프트를 만드는 코드(user_prompt_A, B, D, S, feedback) 등록 | 022_dict_judge_run |
| fretish_guide | v1 | `assets/fretish_guide/v1/` | FRETish 키워드 가이드 등록 | 022_dict_judge_run |
| llm_signal_dictionary | v1 | `assets/llm_signal_dictionary/v1/` | +D 방식이 사용자 메시지에 붙이는 딕셔너리 등록 | 022_dict_judge_run |
| variable_policy | v1 | `assets/variable_policy/v1/` | 변수 정책 문서 등록 | 022_dict_judge_run |
| examples | v1 | `assets/examples/v1/` | 예시 입력(v8 단위, ltl, 실현가능성)과 쌍 표본 등록 | 022_dict_judge_run |
| reference_data | v1 | `assets/reference_data/v1/` | 기준 데이터와 항목 파일 등록(lm_items_combined_v6는 기준 키를 포함) | 022_dict_judge_run |
| judge_input_data | v1 | `assets/judge_input_data/v1/` | 판정 입력 3개(020, 021, 022의 원본 입력) 등록 | 022_dict_judge_run |
| judge_input_data_dict_alias | v1 | `assets/judge_input_data_dict_alias/v1/` | 딕셔너리와 별칭을 적용한 ltl 입력(본 판정용)과 딕셔너리만 적용한 ltl 입력 등록 | 022_dict_judge_run |
| experiment_scripts | v1 | `assets/experiment_scripts/v1/` | 판정 입력 변환, 분할, 합치기, 점검, 집계, 골격 비교, 대조 단위, 표, 큐, NuSMV 래퍼 스크립트 등록 | 022_dict_judge_run |
| dataset | v1 | `assets/dataset/v1/` | 데이터셋 고정(61 항목, 기준 112행, EB-N2 제외, EB-N4 추가, AP-1.2와 AP-1.8 복원, EUL-N1 7부, EUL-N4, EUL-N8에 NASA-lus 판 추가) | 023_fsm_run_v13 |
| dictionary | v1 | `assets/dictionary/v1/` | 딕셔너리 v1(564 항목)이 다시 현재 버전이다(2026-11-17 정리: 별칭 열을 가진 v2는 확장 모듈 `bench/ext/dictionary/overlays/v2/`의 선택 덧씌우기로 옮김, 기본 꺼짐). 모델이 보는 딕셔너리 글과 도구의 `data/dictionary/lm_dictionary.csv`는 v1과 같다 | 025_tool_v20_install |
| reference | v1 | `assets/reference/v1/` | 데이터셋 고정(61 항목, 기준 112행)에서 만든 기준 파일과 딕셔너리 564 항목에서 만든 딕셔너리 | 023_fsm_run_v13 |
| nl2fret_tool | v2.0 | 이 폴더(`nl2fret_tool/`) | 도구 v2.0 반영(최신화): v1.6 패키지의 내용에 버전 표기만 2.0으로 바꿈. 191개 파일(2026-11-17 PyPA 구조로 정리: `pyproject.toml`, `src/` 레이아웃, `bench/`는 `src/nl2fret/`, `judging/`은 `src/nl2fret_judge/`와 `src/legacy/`, `exp/fsm/`은 `scripts/`), 방식·챌린지·반복별 격리 에이전트 실행, 라운드 트립 단계, 챌린지 단위 실현가능성, 12개 프롬프트 린트 포함. 이전 릴리스 v1.4는 `archive/releases/v1.4/`, v1.2.0은 `archive/releases/v1.2.0/` (설치한 패키지 zip `nl2fret_tool_v1.6.zip`) | 025_tool_v20_install |
| process_lifecycle_doc | v1 | `archive/process_lifecycle_doc/v1/PROCESS_LIFECYCLE.md` | 신규 참여자를 위한 전 주기 문서(릴리스 1.2.0 시기). 2026-11-17에 `docs/`에서 옮김: 현행 문서는 `docs/TOOL_PROCESS_GUIDE.md`. | 026_pypa_restructure |
| nl2fret_tool_docs | v2.0 | `docs/` (README.md, docs/DESIGN.md, docs/RUNBOOK.md, docs/V20_BATCH_DESIGN.md, docs/TOOL_PROCESS_GUIDE.md, Makefile 포함) | 도구 문서를 릴리스 2.0과 PyPA 구조에 맞춰 다시 쓰고(026), 옛 판 문서(릴리스 1.4 시기의 분석 계획, 가이드 보충문, 의도 선언 시험, 추적 형식, 데이터 버전업, FSM 시험)를 `archive/nl2fret_tool_docs/v1.4/`로 옮김(027) | 026_pypa_restructure, 027_workspace_layout |
