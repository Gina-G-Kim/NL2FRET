# 프롬프트: 본 실험(019) 후처리와 판정, RQ 집계 (동결 도구 v1.2.0)

아래 전체를 Mac의 LLM 에이전트에게 전달한다. 첨부: `nl2fret_main_judge_pack.zip`(이 지시문 `NL2FRET_PROMPT_MAIN_JUDGE.md`, 도구 원본 `nl2fret_tool_v1.2.zip`(sha256 `430ff36588f1559180a75472f7a08b15061c330e67a84f5fa250324bbabb367e`), 참고용 `NL2FRET_ref_rq_v8.py`(이전 RQ 분석 스크립트, 읽기 전용 명세), `SHA256SUMS`)와 `results_main.zip`(sha256 `18e4a3a94ad6fa01281ef2f7dc2480cd8bae49abcfca6c69dd0ba84b41786bc7`).

이 실행은 동결된 프로토콜에 따른 본 실험의 판정 단계다. 생성은 이미 끝났다(019, run A 61항목 x 16방식, run B 51항목 x 3방식, 반복 3, 모델 sonnet, 상태 finished_all). 61개 LM 항목은 v4부터 v8 사전 실험에서 이미 관찰된 자료라는 점이 보고서 첫 문단에 있어야 한다(사전 관찰 사실은 숨기지 않는다).

---

너는 후처리와 판정을 실행하는 에이전트다. 확인하지 못한 것은 "확인하지 못함"으로 적고 추측으로 채우지 마라. 이모지와 em dash를 쓰지 마라. 코드에 대한 사실 주장은 코드를 읽고 쓴다. 아래에 정해진 것은 되묻지 말고 따른다. 의미 해석, 방식 우열 판단, 원인 설명은 쓰지 않는다. 표, 정의, 한계만 쓴다.

## 절대 규칙
1. 원본 `nl2fret_tool_v1.2.zip` 파일 자체와 생성에 쓰인 bench 파일은 수정하지 마라. 쓰기 가능한 사본에서 실행한다. 사본의 수정은 아래 0.5절이 허용하는 "사소한 버그 수정"에 한정하며, 그 외 수정은 금지다. `--allow-unfrozen` 금지. 모든 판정 기록 헤더가 `frozen: true`여야 한다. 수정이 없으면 두 동결 매니페스트(bench `FROZEN_MANIFEST.sha256` 기대 `176b144f...e571`, 판정 `JUDGE_FROZEN_MANIFEST.sha256` 기대 `1fda2c19...a154b`) 대조가 실행 전후 모두 OK여야 한다. 수정이 있으면 0.5절 5항의 재동결 절차를 따른다.
2. 생성 결과를 다시 만들거나 보정하지 마라. 재실행, `--retry-errors`, 단위 제외, 값 수정 금지. `results_main`은 읽기 전용 원본이다. 후처리는 복사본 `results_main_post/`에서 하고 원본 `calls.jsonl`의 해시가 전후 같음을 기록한다.
3. 결과를 보고 설정(모드, cap, timeout, 집계 규칙)을 바꾸지 마라. 판정 기본값(`--mode anchor`, `--cap 128`, `--timeout 120`, NuSMV 엔진)만 쓴다.
4. 판정 기록을 열어 보기 전에 `PRE_RUN_DEFINITIONS.md`와 집계 스크립트를 쓰고 해시를 고정한다. 이후 정의를 바꾸지 마라. 바꿔야 한다면 멈추고 사용자에게 알린다.
5. git 명령 금지. 사용자 환경 정보(경로, 계정)는 보고서에 필요 이상으로 쓰지 않는다.

## 이미 알려진 사실 (사전 정의에 그대로 옮긴다)
- 생성 호출 5295행 중 비정상 29행: 모델 거부(`stop_reason: refusal`, `general_harms`) 14행(전부 LM-04_NLG-N2p3의 +R2 방식 5개, S 단계), JSON 깨짐 `no_json` 13행, 스키마 위반 `schema_fretish` 2행. 인프라 오류는 0행. 이 단위들은 실패로 분모에 남긴다. 재실행하지 않는다.
- `+D` 방식(DIRECT+D, MASTeR+D, EARS+D)은 신호 사전이 없는 07_AP 챌린지(10항목)를 빼고 51항목에서만 돌렸다. 이 10항목의 `+D` 단위는 "설계상 실행 안 함"이며 분모에서 뺀다(실패가 아님). 기본 방식 대 `+D` 비교는 같은 51항목에서만 한다.
- `model_used`에 `claude-haiku-4-5`가 보조로 함께 찍힌 행이 5266행 있다. 원인은 확인하지 못함. 보고서의 한계에 적는다.

## 단계

### 0. 사전 확인
1. 두 zip의 sha256 대조, `results_main`의 `calls.jsonl` 해시와 줄 수(5295) 기록, `run_state.json`의 `status`가 `finished_all`인지.
2. 도구 사본 풀기, 두 동결 매니페스트 OK, `make selfcheck`(NuSMV, 5쌍 PASS). NuSMV 컨테이너 timeout은 120초의 2% 이상 여유를 둔다(예: 125초 이상). 60초짜리 시험으로 호스트와 컨테이너 시계 차이를 먼저 재서 적는다(이전에 Colima VM 시계가 약 0.92% 빨랐음).
3. Docker 이미지 `fret-lab` 확인, `fretparse.compile_texts`의 `ok: true`와 `ok: false`(예: `when a b shall every 5 seconds satisfy c`)를 확인. 아니면 멈추고 원문을 보고한다.

### 0.5 도구와 py 점검, 패치 확인, 사소한 버그 수정 (판정 기록을 만들기 전에 끝낸다)
1. 비교: 본 환경(Mac 저장소)에 이미 있는 도구 폴더(`nl2fret_tool/` 또는 같은 역할의 폴더)가 있으면 첨부 원본 v1.2와 파일 해시 트리로 비교해 "패치가 되어 있는지"를 판단한다. 같음, 추가된 파일, 바뀐 파일, 없어진 파일을 목록으로 보고하고 바뀐 파일은 diff 요약을 적는다. 본 환경 도구가 없으면 "없음"으로 적는다. 본 환경에 패치가 있으면 어떤 판정 동작이 달라지는지(역할 판정, 정렬, 질의, 집계, 입력 읽기 중 어디인지)를 코드로 확인해 적고, 판정 동작을 바꾸는 패치는 적용하지 말고 멈춘 뒤 사용자에게 묻는다. 판정 동작을 바꾸지 않는 패치(문서, 테스트, 경로, 오류 처리)만 사본에 반영한다.
2. 읽기: `judging/nl2fret_judge/` 전체, `bench/score3.py`, `bench/score_lm.py`, `bench/fret_check/`, 첨부 `NL2FRET_ref_rq_v8.py`를 처음부터 끝까지 읽고, 이 지시문의 단계와 맞지 않는 곳(인자 이름, 파일 이름, 키 이름, 가정)을 목록으로 만든다.
3. 시험: 사본에서 `make test`(48개 기대)와 `make selfcheck`(NuSMV)를 실행한다. 이전에 알려진 실패는 읽기 전용 사본에서 `PermissionError` 5건(`test_patch_v12.py`, 무해로 판단됨)이다. 같은 실패 외의 실패는 전부 보고한다.
4. 사소한 버그의 정의와 허용 범위:
   - 허용: 충돌(예외, 잘못된 경로, 읽기 전용 파일 쓰기), 입력 읽기 오류(마지막 줄이 반쯤 쓰인 파일 등), 문서나 안내문 오류, 테스트 코드 오류, 보고 형식 오류처럼 판정 결과의 값을 바꾸지 않는 수정.
   - 금지(발견하면 수정하지 말고 보고 후 멈춘다): 역할 판정(`role_of`, `RANK`), 정렬 후보와 점수, 질의 식 생성, 불리언 추상화, 단위 결과 규칙(`unit_outcome`, `sentence_class`), timeout과 cap 기본값, 생성 결과를 만드는 bench 파일(`prompts3.py`, `run_pipeline.py`, `tpl_rules.py`, `fretlint.py`, `fretparse.py`, `common.py`, `cli.py`, `units3.py`, `prompts/`, `templates/`, `data/`)의 변경.
   - 알려진 미해결(자동 수정 금지, 보고만): 여러 부분 항목을 "어느 한 문장이라도"로 관대하게 판정하는 규칙, `texts` 규칙이 거부된 문장을 포함하는 1개 단위의 차이, LM-03_REG 9쌍이 600초에서도 시간 초과된 원인. 경로나 읽기 전용 테스트 문제 같은 환경성 문제는 수정해도 된다.
   - 경계가 애매한 수정은 하지 말고 사용자에게 묻는다.
5. 수정 기록과 재동결: 수정마다 `patches/NNN_<이름>.md`(문제, 재현 방법, 원인 코드 위치, 수정 diff, 수정 후 시험 결과, 판정 값을 바꾸지 않는다는 근거)를 쓴다. 수정이 하나라도 있으면 `make release`로 판정 매니페스트를 다시 만들고, 새 `JUDGE_FROZEN_MANIFEST.sha256`의 해시와 원본 해시 `1fda2c1982c1...`를 둘 다 보고서에 적는다. 수정한 판정 코드로 만든 판정 기록 헤더의 `code_tree_sha256`은 새 매니페스트 해시여야 한다. 수정한 bench 후처리 스크립트(`score3.py`, `score_lm.py`, `fret_check/`)는 새 해시를 적는다. 수정 후 다시 `make test`와 `make selfcheck`를 통과시킨다. 수정은 판정 기록을 만들기 전에 모두 끝내고, 판정 시작 후에는 코드를 바꾸지 않는다.
6. 수정이 없으면 "수정 없음, 원본과 같음"이라고 적고 다음으로 간다.

### 1. bench 후처리 (복사본 `results_main_post/`에서)
bench 파일 머리말과 `docs/RUNBOOK.md`를 읽고 아래 순서로 한다. 인자는 코드로 확인한다.
1. `python3 -I score3.py build --results results_main_post --data data/lm_items.jsonl` (`variants.jsonl` 생성)
2. `python3 -I fret_check/check.py single --results results_main_post --procs 3` (공식 FRET 컴파일과 Kind2 실현가능성. 서로 다른 문장마다 1회. 중단되면 같은 명령으로 재개. 소요는 확인하지 못함)
3. `python3 -I score3.py final --results results_main_post --data data/lm_items.jsonl` (`units_scored.jsonl`)
4. `python3 -I score_lm.py all --results results_main_post` (문자열 수준 지표와 `lm_judgment_queue.jsonl` 등)
5. `+D` 방식의 07_AP 단위를 bench가 어떻게 세는지 확인한다(예: `not_run`, `pipeline`으로 분모에 들어가는지). bench 코드를 고치지 말고, 어떻게 세는지만 보고하고, 아래 변환과 집계에서 사전 정의대로 뺀다.
6. 점검: 단위 수 기대치(run A 방식 16개 x 61항목 x 3반복 = 2928, `+D` 3개 x 51 x 3 = 459, 합 3387), 방식별 `v0`, `vf` 파서 거부 수, 실현가능성 결과 분포(realizable, unrealizable, unknown, not_run), 기준 문장(61항목)의 LTL이 도구의 `data/reference/lm_reference_with_ltl.jsonl`과 같은지(같음 또는 차이 목록).

### 2. 도구 입력 3개 변환
1. 이전 변환 스크립트 `convert_inputs.py`(저장소 `experiments/018_*`)와 그 `PRE_RUN_DEFINITIONS.md`를 읽고 같은 규칙(최종 문장 = `variant(rec, "vf")`의 `texts`, 접미사 처리, status 값, 기준 문장 줄 제외)을 쓴다. 규칙을 바꾸지 말고, 새 데이터에 필요한 변경은 방식 목록과 `+D` 51항목 처리뿐이다. 변경점을 목록으로 적는다.
2. 먼저 이전 v6 결과(`results_lm`)가 있으면 같은 스크립트로 변환해 이전 해시(units `b80300fd...`, ltl `06bfa6d6...`, rlz `d86de038...`)가 재현되는지 확인한다. 재현되면 규칙이 같다는 증거다. 이전 결과가 없으면 "확인하지 못함"으로 적는다. 방식 목록이 달라 해시가 바뀌는 부분이 있으면 공통 방식만 비교한다.
3. 새 데이터 변환 후 검증: `units.json`의 단위 수(3387 기대, `+D` 07_AP 제외), 모든 문장이 `fret_ltl_gen.jsonl`에 있는지, `fret_realizability_gen.jsonl` 누락 수, 도구 `units.load_units` 읽기, 항목 id가 모두 `LM-`이고 61개인지, 개발셋 id(`N-`, `X-`)와 원문 자연어 교집합 0, `stratum` 매핑 출처.
4. 산출물 3개의 sha256을 기록한다.

### 3. 사전 정의 고정 (판정 전)
`PRE_RUN_DEFINITIONS.md`에 아래를 그대로 쓰고 해시를 고정한다. 집계 스크립트(`scripts/`)도 이 시점에 완성해 해시를 고정한다(판정 기록 없이 합성 예시로 시험).

정의:
- 단위 = 항목 x 방식 x 반복. 분모는 방식별 전체 단위이다(run A 방식 183, `+D` 방식 153). 파서 거부, 문장 없음, 모델 거부, UND, N/M은 모두 분모에 남는다.
- 항목 구분은 `n_parts`(기준 부분 수) 1과 2 이상. 부분이 여러 개인 항목에서 "어느 한 문장이라도 일치"는 모든 부분을 만족한다는 뜻이 아님을 표 주석에 쓴다.
- 의미 판정 주 지표는 도구의 역할(SAME, PROOF, REFUTE, NEITHER, UND, N/M)이다. 단위 결과는 도구의 `unit_outcome`(단위 안 가장 좋은 문장, 관대한 규칙)을 쓰고, 추가로 단위 안 가장 나쁜 문장 기준 결과와 둘이 다른 단위 수를 병기한다. 성공 = SAME 또는 PROOF이면서 같은 문장이 realizable. 이전의 "구조 일치"(골격 동치) 지표는 이 실행에서 계산하지 않는다(동결 도구 밖). 이전 버전 수치와 직접 비교할 수 없음을 한계에 쓴다.
- RQ1 (오류와 의미 손실):
  a. 구문 오류: 방식별 `v0` 미통과 단위 수(되먹임 전)와 `vf` 미통과 단위 수(되먹임 후), 실패 코드 분포.
  b. 필드 수준: `NL2FRET_ref_rq_v8.py`의 `classify`와 같은 규칙(파서 통과 단위, 기준 부분과 가장 적게 어긋나는 문장, 필드 timing, condition 유무, scope 유무, 전 필드 일치). 방식별과 stratum별(기본 방식 합산, `+D` 합산).
  c. trigger 대 holding 패턴: conditional 단위 중 condition 유무 불일치이면서 기준 timing이 always이고 생성 timing이 always가 아닌 단위 수와 비율(기본 방식과 `+D` 방식 각각).
  d. 도구 역할 분포(문장 수준, 사용 횟수 가중)와 단위 결과 분포, 방식별.
- RQ2 (템플릿 중간 표현):
  a. 방식별 문장 수준 역할 분포와 단위 성공률(분모 전체 단위, 판정된 단위만 분모인 값을 나란히).
  b. 반복 간 일관성: 항목별 반복 쌍(3반복이면 쌍 3개)에서 같은 문장 비율과 같은 구조(`common.struct_key`) 비율의 평균.
  c. 방식 쌍 비교는 항목 단위 부트스트랩(항목이 재표집 단위, 반복은 항목 안에서 평균, 5000회, 시드 고정) 95% 구간: 각 방식 대 DIRECT, 템플릿 방식 대 PARA, `+R2` 대 같은 템플릿의 자유 방식, `+V` 대 기본 방식, `+D` 대 기본 방식(51항목). 모든 방식이 판정된 항목만 쓰는 짝 비교는 별도 표로 하고 남는 항목 수를 적는다.
- RQ3 (요구사항 유형별): 방식 x stratum(conditional, invariant, timed, scoped) 표(단위 성공률, 단위 SAME 비율, 전체 분모). scoped는 항목 2개이므로 표에 n을 반드시 적는다.
- 실현가능성: 방식별 realizable, unrealizable, unknown, not_run 분포(단위 수준과 문장 수준).
- 민감도 표(보조, 주 결과를 바꾸지 않음): LM-04_NLG-N2p3의 +R2 단위(모델 거부)를 뺀 값과 뺀 항목 수를 별도 표로. 주 표는 뺀 값이 아니라 전체 단위 기준이다.
- RQ4(템플릿 단계 정보 손실 기록)는 이 실행에서 분석하지 않는다. 기록만 보존한다: 단계 A 출력의 `unmapped_content`, `choices` 수를 방식별로 세어 표로만 적고, 판정 기록의 AP 불일치 기록(`ap_check`) 분포를 방식별로 센다. 해석 없음.
- 해석 문장은 쓰지 않는다.

### 4. 판정 실행 (분할, 코드 변경 없음)
1. 입력 sha256 대조 후 `units.json`을 항목 단위로 N개(권고 4, Mac 물리 코어 수와 컨테이너 CPU 제한 안)로 나눈다(항목 id 정렬 후 라운드로빈, 항목 통째로, 단위를 쪼개지 마라). `fret_ltl_gen.jsonl`과 `fret_realizability_gen.jsonl`은 전체를 그대로 쓴다.
2. 부분별 별도 `OUT` 폴더(NuSMV 작업 폴더가 겹치지 않게)에서 `make judge`를 `nohup caffeinate -i`로 동시에 실행. 중단되면 같은 명령으로 재개하고 `run_header.json`이 처음 값임을 보고서에 적는다. 진행은 `judge_records.jsonl` 줄 수와 마지막 `pair_id`로만 보고한다. 소요는 확인하지 못함(v8 예시 252쌍이 NuSMV로 36분, 이전 v6 입력은 쌍 2855개였음, 이번 쌍 수는 변환 후 센다).
3. 끝나면 부분별 `judge_records.jsonl`과 `smv/`를 합치고(중복 `pair_id` 0), 헤더에 `shards` 목록(부분별 입력 해시, 코드 해시)을 추가해 `make aggregate`를 실행한다. 도구의 `aggregate` 결과는 그대로 보존한다(관대한 규칙 표시).
4. 점검: 기록 쌍 수 = `units.json`에서 `parser_ok`이고 LTL이 있는 문장 수와 같은지(다르면 원인 목록), 모든 헤더 `frozen: true`와 `code_tree_sha256` 일치, 역할 분포, UND와 N/M 사유별, timeout 쌍 수, 쌍당 시간 평균과 최대, 같은 문장이 다른 단위에서 다른 역할을 받았는지(0이어야 하고 아니면 전부 보고), 이전 v1.2 실행과 겹치는 쌍의 역할 비교(비교만).
5. 알려진 미해결: 이전에 LM-03_REG 9쌍이 timeout 600초에서도 시간 초과였다. 이번에도 timeout 쌍은 설정을 바꿔 다시 돌리지 말고 N/M(timeout)으로 둔 채 목록만 보고한다.

### 5. 집계
고정한 `scripts/`로 3절의 표를 계산한다(판정 기록은 읽기만). 결과는 `rq_tables.md`와 `rq_tables.json`으로 저장한다.

## 최종 보고
1. 첫 문단: 본 실험 판정 단계임, LM 61항목은 v4 이후 사전 관찰된 자료임, 모델 거부 14행과 모델 깨짐 15행은 실패로 분모에 남겼음
2. 환경(NuSMV, Docker 이미지, `claude --version`), 시계 차이, 분할 방식
3. 0절과 1절 점검 결과(해시, 단위 수, 실현가능성 분포, `+D` 07_AP 처리)
4. 2절 변환 결과(재현 여부, 통계표, 해시)
5. 4절 판정 점검(쌍 수, 헤더, 역할 분포, 결정성, timeout 목록)
6. RQ1 내지 RQ3 표, 실현가능성 표, 민감도 표, RQ4 기록 표 (해석 없음)
7. 이상 징후와 확인하지 못한 항목, 사용자가 결정해야 할 것
8. 0.5절 결과: 본 환경 도구와 원본의 비교표, 코드 읽기에서 찾은 불일치 목록, 수정 목록(`patches/`)과 새 판정 매니페스트 해시(수정이 있을 때), 보고만 하고 수정하지 않은 항목
9. 산출물 경로와 sha256: 입력 3개, 합친 `judge_records.jsonl`, `aggregate.json`, `rq_tables.md`, `rq_tables.json`, `PRE_RUN_DEFINITIONS.md`, 집계 스크립트
