# 프로세스 전 주기

자연어 요구사항이 FRETish 문장, LTL 식, 판정 역할, 집계 표로 바뀌는 전 과정을 단계 순서대로 적은 안내서이다. 처음 오는 사람은 1절의 표로 전체를 보고, 2절에서 필요한 단계의 블록을 읽는다. 경로는 모두 저장소 루트 기준이다. 자산 파일은 `assets/<자산>/v1/` 아래에 있고 색인은 `VERSIONS.md`이다.

## 1. 전 주기 표

| 번호 | 단계 | 입력 | 처리 | 출력 |
|---|---|---|---|---|
| 1 | 요구사항 입력과 기준 데이터 | `data/cases/`, 항목 파일 | 61개 항목의 자연어 원문과 기준 FRETish, 기준 LTL을 파일로 갖춘다 | `assets/reference_data/v1/` |
| 2 | 템플릿 가이드와 프롬프트 구성 | 템플릿 가이드 5종, FRETish 가이드, 사용자 프롬프트 코드 | 시스템 프롬프트 21개를 조립해 파일로 쓴다 | `prompts/current/system_prompts/` |
| 3 | 정의 고정 | 규칙, 판정 정의, 스크립트, 입력 | 정의 문서와 파일 해시를 판정 기록을 열기 전에 고정한다 | `assets/preregistration/v1/` |
| 4 | LLM 생성 | 시스템 프롬프트, 항목 파일 | 단계마다 Claude Code CLI를 한 번 호출해 템플릿 문장과 FRETish를 만든다 | `calls.jsonl`, 생성 문장 |
| 5 | FRETish 파싱과 LTL 컴파일 | 생성 문장, 기준 문장 | 공식 FRET 파서가 수락 여부와 `ltl_ft`, `ltl_pt`를 돌려준다 | `fret_ltl.jsonl` |
| 6 | 실현가능성 검사 | 파서가 수락한 문장 | FRET이 Kind2로 검사해 네 가지 결과 중 하나를 적는다 | `fret_realizability.jsonl` |
| 7 | 판정 입력 변환 | bench 결과 3종 | 단위 파일, 문장별 LTL 파일, 실현가능성 파일로 바꾸고 점검한다 | `assets/judge_input_data/v1/` |
| 8 | 신호 이름 딕셔너리 구성 | 기준 신호 목록, 생성 이름 목록 | 항목별로 생성 이름을 기준 신호 이름에 대응시킨다 | `assets/signal_dictionary/v1/` |
| 9 | 딕셔너리 적용 | 딕셔너리, 원본 LTL 파일 | 식별자 토큰을 항목별 딕셔너리로 바꾼다 | `fret_ltl_gen_dict_only.jsonl` |
| 10 | 별칭 증명 | 딕셔너리 적용 LTL 파일, 기준 LTL | z3가 동치를 증명한 부분식만 기준 부분식으로 바꾸고 증명서를 쓴다 | `fret_ltl_gen.jsonl`, `alias_certificates.jsonl` |
| 11 | 판정 | 판정 입력 3개, 기준 LTL | 동결 도구가 이름 정렬, 불리언 추상화, NuSMV 질의로 쌍마다 역할을 정한다 | `judge_records.jsonl`, `run_header.json`, `smv/` |
| 12 | 집계와 점검 | `judge_records.jsonl` | 방식별 단위 결과를 다시 계산하고 기록을 점검한다 | `aggregate.json`, 점검 파일 |
| 13 | RQ 분석 | 판정 기록, 입력, 항목 파일 | 방식별 단위 결과와 비교 표를 계산한다 | `rq_tables.md`, `rq_tables.json` |
| 14 | 비교 가능성 분석 | 같은 판정 입력 | free와 strict 모드 판정, 골격 비교로 표를 만든다 | `tables_021.md`, `tables_021.json` |
| 15 | 대조 실험 | 본 판정 기록, 대조용 입력 | 음성 대조, 이름 교환 대조, 별칭 대조를 판정한다 | 대조 단위 파일, 역할 이동표 |
| 16 | 버전 관리 | 고친 자산 | 새 버전 폴더를 만들고 이전 버전을 보관하며 색인을 갱신한다 | `assets/`, `archive/`, `VERSIONS.md` |

## 2. 단계별 설명

### 단계 1. 요구사항 입력과 기준 데이터

- 입력: `data/cases/nasa_papers/`, `data/cases/lockheed_martin/`, `data/cases/fsm/`, `assets/reference_data/v1/lm_items.jsonl`
- 처리:
  1. 케이스 폴더가 출처 묶음(NASA 보고서와 논문 183, 록히드마틴 49, FSM 12)별로 자연어 요구사항을 모으고 각 `SOURCES.md`에 출처를 적는다.
  2. 61개 항목(록히드마틴 49개와 FSM 12개)은 항목 파일에 항목 번호, 챌린지, 계열, 층, 자연어 원문(`raw_nl`)으로 적힌다.
  3. 기준 답은 항목마다 기준 FRETish 문장 버전과 공식 FRET으로 컴파일한 LTL을 `gt_parts`에 담은 별도 파일로 보관한다.
- 출력: `assets/reference_data/v1/`(`lm_items.jsonl` 61줄, `lm_reference_with_ltl.jsonl` 61줄, `lm_items_combined_v6.jsonl` 61줄, `dict8_items.jsonl` 18줄), `assets/llm_signal_dictionary/v1/sigdict.json`
- 근거: `data/INDEX.md`, `data/cases/README.md`, `nl2fret_tool/README.md`, `nl2fret_tool/docs/DESIGN.md` 2절

### 단계 2. 템플릿 가이드와 프롬프트 구성

- 입력: `assets/template_guides/v1/`(`adv_ears.md`, `boilerplate.md`, `ears.md`, `masteR.md`, `spider.md`), `assets/fretish_guide/v1/fretish_guide.md`, `assets/user_prompt_builders/v1/`(`common.py`, `prompts3.py`), `assets/llm_signal_dictionary/v1/sigdict.json`
- 처리:
  1. 시스템 프롬프트는 코드의 고정 문장, FRETish 가이드, 템플릿 문서 하나로 조립된다.
  2. `tools/render_prompts.py`가 파이프라인과 같은 조립 함수를 불러 시스템 프롬프트 21개를 파일로 쓰고, `MANIFEST.csv`에 파일, 단계, 사용 방식, 크기, sha256을 적는다.
  3. 사용자 메시지는 코드(`user_prompt_A`, `user_prompt_B`, `user_prompt_D`, `user_prompt_S`, `user_prompt_feedback`)가 만들고, +D 방식은 딕셔너리를 사용자 메시지에 붙인다.
- 출력: `prompts/current/system_prompts/`(txt 21개와 `MANIFEST.csv`), `assets/llm_system_prompts/v1/`
- 근거: `prompts/INDEX.md`, `tools/render_prompts.py`, `nl2fret_tool/bench/common.py`, `nl2fret_tool/bench/prompts3.py`

### 단계 3. 정의 고정

- 입력: 실행 전에 쓴 규칙, 판정 정의, 스크립트, 입력 파일
- 처리:
  1. 정의 문서(`PRE_RUN_DEFINITIONS*.md`)와 스크립트와 입력 파일의 sha256 목록을 만들어 판정 기록을 열기 전에 고정한다.
  2. 각 단계는 한 번 실행하고, 프로세스가 중단되면 같은 명령으로 재개한다.
  3. 규칙은 결과를 보기 전에 정한 값 그대로 쓰고, 고정한 파일이 바뀌면 실행을 중단한다.
- 출력: `assets/preregistration/v1/`(`NL2FRET_DICT_PRE_REGISTRATION.md`와 실험별 `PRE_RUN_DEFINITIONS_*.md` 10개), `experiments/022_dict_judge_run/notes/PIN_pin1.sha256`, `experiments/022_dict_judge_run/notes/PIN_pin2.sha256`
- 근거: `nl2fret_tool/docs/DESIGN.md` 8절, `assets/preregistration/v1/`

### 단계 4. LLM 생성

- 입력: `prompts/current/system_prompts/`, 항목 파일(`assets/reference_data/v1/lm_items.jsonl`), `nl2fret_tool/bench/run_pipeline.py`, `nl2fret_tool/bench/cli.py`
- 처리:
  1. `run_pipeline.py`가 단계마다 구독 로그인의 Claude Code CLI를 헤드리스로 한 번 호출한다. 단계는 A(자연어에서 템플릿 문장), B(템플릿 문장에서 FRETish), D(자연어에서 FRETish 직접), S(규칙 조립용 슬롯)이다.
  2. 호출마다 `calls.jsonl`에 토큰과 시간이 한 줄씩 쌓이고, `cli.py`가 세션 한도 메시지를 읽어 재설정 시각까지 기다린 뒤 같은 호출을 다시 보낸다.
  3. 같은 명령을 다시 실행하면 끝난 키는 건너뛰고 남은 일만 수행한다.
- 출력: 결과 폴더의 `calls.jsonl`, 61개 항목 본 실행의 결과 폴더 `experiments/019_lm61_main_gen/bench/results_main/`
- 근거: `nl2fret_tool/bench/run_pipeline.py`, `nl2fret_tool/bench/cli.py`, `nl2fret_tool/bench/units3.py`, `prompts/current/instructions/NL2FRET_61_MAIN_RUN.md`

### 단계 5. FRETish 파싱과 LTL 컴파일

- 입력: 생성 문장, 기준 문장, Docker 이미지 `fret-lab`
- 처리:
  1. 공식 FRET 파서(`FretSemantics.compile`)가 문장마다 수락 여부와 오류 문장을 돌려주고, 수락한 문장의 미래시제 LTL(`ltl_ft`)과 과거시제 LTL(`ltl_pt`)을 함께 돌려준다.
  2. 생성 중에는 파서 오류를 돌려준 문장에 그 오류 문장을 붙인 피드백 호출 F1, F2를 최대 2회 보내고, 호출 뒤마다 파서를 다시 부른다.
  3. `fret_check/check.py single`이 서로 다른 문장을 한 번씩 컴파일해 결과를 쓴다.
- 출력: `fret_ltl.jsonl`(문장, `parser_ok`, `error`, `ltl_ft`, `ltl_pt`)
- 근거: `nl2fret_tool/bench/fretparse.py`, `nl2fret_tool/bench/fret_check/tools/fret_compile.py`, `nl2fret_tool/bench/fret_check/check.py`, `docker/fret-lab/README.md`

### 단계 6. 실현가능성 검사

- 입력: 파서가 수락한 문장, `assets/variable_policy/v1/variable_policy.md`
- 처리:
  1. 문장마다 변수 표를 한 가지 규칙(`variable_policy.md`)으로 만든다.
  2. FRET이 Kind2로 실현가능성을 검사하고 결과를 realizable, unrealizable, unknown, not_run 중 하나로 적는다.
  3. 결과 파일에는 기준 문장의 행이 먼저, 생성 문장의 행이 다음에 쓰인다.
- 출력: `fret_realizability.jsonl`
- 근거: `nl2fret_tool/bench/fret_check/check.py`, `nl2fret_tool/bench/fret_check/tools/fret_rlz.py`, `nl2fret_tool/bench/fret_check/variable_policy.md`

### 단계 7. 판정 입력 변환

- 입력: bench 결과(`units_scored.jsonl`, `fret_ltl.jsonl`, `fret_realizability.jsonl`)
- 처리:
  1. `score3.py`가 단위(항목, 방식, 반복)마다 상태를 계산해 `units_scored.jsonl`에 쓰고, 단위 상태는 문장 중 가장 나쁜 결과이다.
  2. `convert_inputs.py`가 bench 결과를 판정 도구의 입력 3개(`units.json`, `fret_ltl_gen.jsonl`, `fret_realizability_gen.jsonl`)로 바꾼다.
  3. `validate_inputs.py`가 개수, 단위의 포함 관계, 도구 로더 읽기, 단위 상태 재계산을 점검한다.
- 출력: `assets/judge_input_data/v1/`(`units.json` 단위 3387개, `fret_ltl_gen.jsonl` 2730줄, `fret_realizability_gen.jsonl` 3999줄)
- 근거: `nl2fret_tool/bench/score3.py`, `assets/experiment_scripts/v1/convert_inputs.py`, `assets/experiment_scripts/v1/validate_inputs.py`, `prompts/current/instructions/NL2FRET_61_INPUTS.md`

### 단계 8. 신호 이름 딕셔너리 구성

- 입력: 항목별 기준 FRETish 신호 목록, 생성 문장의 이름 목록(`assets/judge_input_data/v1/fret_ltl_gen.jsonl`)
- 처리:
  1. 한 항목 안에서 생성 이름 하나를 기준 신호 하나에 대응시키고, 신뢰도 H(이름이 사실상 같음)와 M(의미상 같다고 판단)을 기록한다.
  2. 초안 407쌍을 전수 재검토해 41쌍을 빼고, 대응이 비어 있던 이름 999개를 항목별로 재검토해 26쌍을 더해 392쌍(50개 항목)을 만든다.
  3. 규칙 파일의 한 줄은 `항목 ; 생성 이름 목록 => 기준 이름 ; 신뢰도` 형식이다.
- 출력: `assets/signal_dictionary/v1/mapping_final.json`, `assets/signal_dictionary_rules/v1/`(`rules_01.txt`부터 `rules_08.txt`까지, `removed.json`)
- 근거: `assets/preregistration/v1/NL2FRET_DICT_PRE_REGISTRATION.md` 3절

### 단계 9. 딕셔너리 적용

- 입력: `assets/signal_dictionary/v1/mapping_final.json`, `assets/judge_input_data/v1/fret_ltl_gen.jsonl`
- 처리:
  1. `apply_dict.py`가 `ltl_pt`와 `ltl_ft`의 식별자 토큰을 문장이 속한 항목의 딕셔너리로 동시에 바꾸고, 여는 괄호가 뒤따르는 함수 이름은 그대로 둔다.
  2. 한 문장 안에서 치환 결과가 다른 이름과 같아지거나 서로 다른 두 이름이 같은 기준 신호가 되면 그 치환을 건너뛴다(38건).
  3. 여러 항목에 나오는 문장은 항목별 결과가 같은지 점검한다.
- 출력: `assets/judge_input_data_dict_alias/v1/fret_ltl_gen_dict_only.jsonl`(2730개 문장 중 1642개의 LTL이 바뀐다)
- 근거: `assets/dict_alias_scripts/v1/apply_dict.py`, `assets/preregistration/v1/NL2FRET_DICT_PRE_REGISTRATION.md` 4절

### 단계 10. 별칭 증명

- 입력: `assets/judge_input_data_dict_alias/v1/fret_ltl_gen_dict_only.jsonl`, `assets/reference_data/v1/lm_reference_with_ltl.jsonl`
- 처리:
  1. `alias_apply.py`가 생성 식에서 현재 시점의 값만으로 정해지는 최대 부분식 g를 찾고, 같은 항목 기준 식에서 현재 시점의 값만으로 정해지는 부분식 r 중 변수 집합이 g와 같은 것을 후보로 삼는다.
  2. z3가 g <-> r의 부정을 unsat으로 증명하면(제한 시간 10000 ms) g를 r로 바꾸고, 바꿀 때마다 증명서를 기록한다.
  3. `cert_check.py`가 증명기와 독립인 숫자 대입 검사(건당 3000점)로 증명서 전부를 확인한다.
- 출력: `assets/judge_input_data_dict_alias/v1/fret_ltl_gen.jsonl`, `assets/alias_certificates/v1/alias_certificates.jsonl`(증명서 302건, 140개 문장, 7개 항목)
- 근거: `assets/dict_alias_scripts/v1/alias_apply.py`, `assets/dict_alias_scripts/v1/cert_check.py`, `assets/preregistration/v1/NL2FRET_DICT_PRE_REGISTRATION.md` 5절

### 단계 11. 판정

- 입력: `units.json`, `fret_ltl_gen.jsonl`, `fret_realizability_gen.jsonl`, `nl2fret_tool/data/reference/lm_reference_with_ltl.jsonl`
- 처리:
  1. 동결 도구 v1.2.0의 `judge`는 시작할 때 판정 코드를 `JUDGE_FROZEN_MANIFEST.sha256`과 대조하고 5쌍 자기점검(`selfcheck`)을 통과해야 쌍 판정으로 넘어간다.
  2. 쌍마다 이름 정렬(기본 anchor 모드), 불리언 추상화, NuSMV 질의 3개(equiv, sound, compl)로 역할 SAME, PROOF, REFUTE, NEITHER를 정하고, 정렬 후보가 비면 UND, 엔진 사유 코드가 붙으면 N/M으로 적는다.
  3. 대량 실행은 `shard_units.py`가 항목 단위로 4조각으로 나누고, 조각마다 NuSMV 2.6.0 컨테이너(`cst-nusmv:local`) 1개로 돌리며, `merge_judge.py`가 원래 기록 줄을 그대로 모아 합친다.
- 출력: `runs/<이름>/`의 `run_header.json`, `judge_records.jsonl`, `smv/`
- 근거: `nl2fret_tool/docs/RUNBOOK.md` 2절과 5절, `nl2fret_tool/judging/nl2fret_judge/judge.py`, `nl2fret_tool/judging/nl2fret_judge/align.py`, `nl2fret_tool/judging/nl2fret_judge/recorder.py`, `nl2fret_tool/judging/nl2fret_judge/freeze.py`, `nl2fret_tool/judging/nl2fret_judge/selfcheck.py`, `assets/experiment_scripts/v1/shard_units.py`, `assets/experiment_scripts/v1/merge_judge.py`, `assets/experiment_scripts/v1/run_queue.sh`, `assets/experiment_scripts/v1/NuSMV_docker_wrapper.sh`, `docker/cst-nusmv/README.md`

### 단계 12. 집계와 점검

- 입력: `judge_records.jsonl`
- 처리:
  1. `nl2fret_judge aggregate`가 판정 기록에서 방식별, 층별 단위 결과를 다시 계산한다.
  2. 단위 결과는 success, partial, failure, unjudged 네 가지이고, 주 분모는 전체 단위이다.
  3. `judge_checks.py`가 기록 수와 파서 수락 문장 수, 헤더의 frozen과 코드 해시, 역할 분포, 시간 초과 쌍, 같은 문장의 판정 일치를 점검한다.
- 출력: `aggregate.json`, 점검 md 파일과 json 파일
- 근거: `nl2fret_tool/judging/nl2fret_judge/aggregate.py`, `assets/experiment_scripts/v1/judge_checks.py`

### 단계 13. RQ 분석

- 입력: `units.json`, `fret_ltl_gen.jsonl`, `fret_realizability_gen.jsonl`, `judge_records.jsonl`, `units_scored.jsonl`, `calls.jsonl`, `assets/reference_data/v1/lm_items_combined_v6.jsonl`
- 처리:
  1. `rq_aggregate.py`가 판정 기록을 읽기만 하며 방식별 단위 결과와 비교 표를 계산한다.
  2. 문장별 분류와 단위별 분류는 동결 도구의 `nl2fret_judge.aggregate` 코드에서 가져온다.
  3. 표와 부트스트랩 구간을 `rq_tables.md`와 `rq_tables.json`에 쓴다.
- 출력: `rq_tables.md`, `rq_tables.json`
- 근거: `assets/experiment_scripts/v1/rq_aggregate.py`, `assets/preregistration/v1/PRE_RUN_DEFINITIONS_020_lm61_main_judge.md`

### 단계 14. 비교 가능성 분석

- 입력: 단계 7의 판정 입력 3개, 동결 도구 v1.2.0
- 처리:
  1. 같은 3999쌍을 이름 대응 모드 free와 strict로 다시 판정한다.
  2. `skeleton_eval.py`가 현재 시점의 값만으로 정해지는 최대 부분식을 불투명 원자 하나로 바꾼 골격을 `judge5.skeleton_compare`로 비교한다.
  3. `tables_021.py`가 판정 기록과 골격 기록에서 표 1부터 8까지 만든다.
- 출력: `tables_021.md`, `tables_021.json`, 골격 기록
- 근거: `assets/experiment_scripts/v1/skeleton_eval.py`, `assets/experiment_scripts/v1/tables_021.py`, `prompts/current/instructions/NL2FRET_PROMPT_COMPARABILITY_TEST.md`

### 단계 15. 대조 실험

- 입력: 본 판정 기록, 대조용 단위 파일, 증명서가 있는 문장의 딕셔너리 적용 결과와 별칭 적용 결과
- 처리:
  1. 음성 대조는 `make_control_units.py`가 단위 300개를 시드 20261112로 뽑고 항목 번호를 31칸 밀어 다른 항목의 기준과 비교하게 한다.
  2. 이름 교환 대조는 `swap_control.py`가 본 판정에서 SAME인 쌍의 두 변수를 맞바꾼 식을 같은 기준과 판정한다.
  3. 별칭 대조는 증명서가 있는 문장의 딕셔너리 적용 결과와 별칭 적용 결과를 같은 기준과 판정해 역할 이동표를 만든다.
- 출력: 대조 단위 파일, 이름 교환 입력 파일, 역할 이동표(`tables_022.py`가 만든다)
- 근거: `assets/experiment_scripts/v1/make_control_units.py`, `assets/dict_alias_scripts/v1/swap_control.py`, `assets/experiment_scripts/v1/tables_022.py`, `assets/preregistration/v1/NL2FRET_DICT_PRE_REGISTRATION.md` 7절

### 단계 16. 버전 관리

- 입력: 고친 자산, `VERSIONS.md`
- 처리:
  1. 자산은 `assets/<자산>/v<N>/`에 파일과 `SHA256SUMS`를 두어 보관한다.
  2. 자산을 고치면 `assets/<자산>/v<N+1>/`을 만들고 이전 버전을 `archive/<자산>/v<N>/`로 옮긴다.
  3. `VERSIONS.md`의 현재 버전, 경로, sha256, 변경 사유, 변경을 일으킨 실험 열을 같은 규칙으로 갱신한다.
- 출력: `assets/`, `archive/`, `VERSIONS.md`
- 근거: `VERSIONS.md`, `archive/README.md`

## 3. 이 문서의 갱신

이 문서를 고치면 `VERSIONS.md`의 `process_lifecycle_doc` 행에 새 버전, sha256, 변경 사유, 변경을 일으킨 실험을 적고, 이전 문서 파일은 `archive/process_lifecycle_doc/v<N>/`에 둔다.
