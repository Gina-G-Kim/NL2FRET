버전업 규칙: 자산을 고치면 `assets/<자산>/v<N+1>/`에 새 버전을 만들고 이전 버전은 `archive/<자산>/v<N>/`로 옮기며, 이 표의 현재 버전, 경로, sha256, 변경 사유, 변경을 일으킨 실험 열을 같은 규칙으로 갱신한다.

# 자산 버전 색인

| 자산 | 현재 버전 | 경로 | sha256 (자산 폴더의 `SHA256SUMS` 파일, 문서 행은 문서 파일) | 변경 사유 | 변경을 일으킨 실험 |
|---|---|---|---|---|---|
| signal_dictionary | v1 | `assets/signal_dictionary/v1/` | `0a9fb81250a868c459207aaf1736fe94743dc9db79898ce23b5944b9425c04bd` | 신호 이름 딕셔너리(392쌍, 50개 항목) 등록 | 022_dict_judge_run |
| signal_dictionary_rules | v1 | `assets/signal_dictionary_rules/v1/` | `3ccbd00c8a5acf5696e3ef1ca42a59a4fbd03f2b9eb7fd9c749bfaa324fc4272` | 딕셔너리 구성 규칙 rules_01 내지 rules_08과 제거 목록 등록 | 022_dict_judge_run |
| dict_alias_scripts | v1 | `assets/dict_alias_scripts/v1/` | `a3a9672f1f796e699baeac35463f63d2dbc7cfbb86f504845631efe3a501f75d` | 딕셔너리 적용, 별칭 증명, 증명서 검사, 이름 교환 스크립트 등록 | 022_dict_judge_run |
| alias_certificates | v1 | `assets/alias_certificates/v1/` | `b5b1adb25095c3303bd8aabf4ced5175a5f7d501dea45eea186720c4a4151e8c` | 별칭 증명서 302건 등록 | 022_dict_judge_run |
| preregistration | v1 | `assets/preregistration/v1/` | `bad998eef25f77a8c76db317efadf4aa8ebbc5a3e7f7c4d24db2e8215d048dd5` | 사전등록 문서(딕셔너리와 별칭)와 실험별 사전 정의 문서 등록 | 022_dict_judge_run |
| template_guides | v1 | `assets/template_guides/v1/` | `b32cc51e95a6b578560079e20cd31c69f4db775cc82f72078c25f2c93e4ea9a1` | 템플릿 가이드 5종(MASTeR, EARS, Adv-EARS, SPIDER, Boilerplate) 등록 | 022_dict_judge_run |
| llm_system_prompts | v1 | `assets/llm_system_prompts/v1/` | `bda5c19cd00d0212b4112a3c6dbc154cd3a647cda478ad0844c0af849f69ef68` | 생성에 쓴 시스템 프롬프트 21종(PARA, +R2, +V, +D 방식 포함)과 MANIFEST 등록 | 022_dict_judge_run |
| user_prompt_builders | v1 | `assets/user_prompt_builders/v1/` | `f038389d6fb16989d481a232507a984a69e8d4e0fe9d19288a6bcbdf0c9a3aa2` | 사용자 프롬프트를 만드는 코드(user_prompt_A, B, D, S, feedback) 등록 | 022_dict_judge_run |
| fretish_guide | v1 | `assets/fretish_guide/v1/` | `8eedea53a7a5fd6155c6194576e8a2fa26ff71c77b5290ea8aefbc2fbacf0dbf` | FRETish 키워드 가이드 등록 | 022_dict_judge_run |
| llm_signal_dictionary | v1 | `assets/llm_signal_dictionary/v1/` | `cbaff223228a301cf7fcfcca2b4bb30c81a96b13cf7b8919a51777f1417dc11c` | +D 방식이 사용자 메시지에 붙이는 딕셔너리 등록 | 022_dict_judge_run |
| variable_policy | v1 | `assets/variable_policy/v1/` | `1ed1cb435a7b48a5df5189195c0ab32c10cea1916bda8dabc8e499223cc89654` | 변수 정책 문서 등록 | 022_dict_judge_run |
| examples | v1 | `assets/examples/v1/` | `24fa528cfe278305d96b06150f79db36ebabbe13bdd33f03065f5d217a20a1d5` | 예시 입력(v8 단위, ltl, 실현가능성)과 쌍 표본 등록 | 022_dict_judge_run |
| reference_data | v1 | `assets/reference_data/v1/` | `29fd34d96b0659c7e93b79a45e3f82e11f50bcb7f88d050bd4a381ba30cbc229` | 기준 데이터와 항목 파일 등록(lm_items_combined_v6는 기준 키를 포함) | 022_dict_judge_run |
| judge_input_data | v1 | `assets/judge_input_data/v1/` | `bd12635730f624cf7645a98c9d8908d28ea5806f44b8bda8420f9a5b0b6a7dfd` | 판정 입력 3개(020, 021, 022의 원본 입력) 등록 | 022_dict_judge_run |
| judge_input_data_dict_alias | v1 | `assets/judge_input_data_dict_alias/v1/` | `1e6585b0a66ac05eb6a9b1f07734691a6c0407e5819af6b88833802c3a1acf36` | 딕셔너리와 별칭을 적용한 ltl 입력(본 판정용)과 딕셔너리만 적용한 ltl 입력 등록 | 022_dict_judge_run |
| experiment_scripts | v1 | `assets/experiment_scripts/v1/` | `0261cc4e795917a733991dc4e62475f3a756c93a3c075c0d535c8a13219b4453` | 판정 입력 변환, 분할, 합치기, 점검, 집계, 골격 비교, 대조 단위, 표, 큐, NuSMV 래퍼 스크립트 등록 | 022_dict_judge_run |
| dataset | v1 | `assets/dataset/v1/` | `672be262e256a4ff806926c88043f1083de988992bb96e209f9b4fc6dc8f0274` | 데이터셋 고정(61 항목, 기준 112행, EB-N2 제외, EB-N4 추가, AP-1.2와 AP-1.8 복원, EUL-N1 7부, EUL-N4, EUL-N8에 NASA-lus 판 추가) | 023_fsm_run_v13 |
| dictionary | v1 | `assets/dictionary/v1/` | `ed334341445376396ccbd7c9340fed2c6776dc926b2cfbf59d0c4691da087e51` | 딕셔너리 564 항목 | 023_fsm_run_v13 |
| reference | v1 | `assets/reference/v1/` | `761bd6a0319df8be29cb570105164b5db970d3c34a3e350c22302938eaf195c3` | 데이터셋 고정(61 항목, 기준 112행)에서 만든 기준 파일과 딕셔너리 564 항목에서 만든 딕셔너리 | 023_fsm_run_v13 |
| nl2fret_tool | v1.4 | `nl2fret_tool/` | `af896dde6673a6bb0f41807a2a67de63b3711ae3d2d76fa3fa44e72da1b2e93e` (패키지 zip) | 도구 v1.4 패키지 반영(최신화): 113개 파일, 11개 변환 방식 FSM 시험용 코드, 프롬프트 원문, 입력 데이터 포함. 이전 릴리스 v1.2.0은 `archive/nl2fret_tool/v1.2.0/` | 024_fsm_v14_retest |
| process_lifecycle_doc | v1 | `docs/PROCESS_LIFECYCLE.md` | `3e5b049868aa63ff5f8ba2feb623f0d1c4f970e2752b161996c7e7fba5ef0f7a` | 신규 참여자를 위한 전 주기 문서 작성 | 022_dict_judge_run |
