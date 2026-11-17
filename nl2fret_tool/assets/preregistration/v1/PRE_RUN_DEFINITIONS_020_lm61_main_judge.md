# PRE_RUN_DEFINITIONS: 본 실험(019) 후처리, 판정, RQ 집계 (동결 도구 v1.2.0), 2026-11-12

이 문서는 판정 기록을 열어 보기 전에 쓰고 해시를 고정한다(`notes/PIN_scripts.sha256`, 고정 시각 `notes/PIN_scripts_TIME.txt`). 고정한 뒤 정의와 집계 스크립트를 바꾸지 않는다. 바꿔야 하면 멈추고 사용자에게 알린다. 3절(정의)의 문장은 지시문 3절을 그대로 옮긴 것이고, "구현" 줄은 그 정의를 스크립트가 정확히 어떻게 계산하는지 적은 것이다.

## 1. 범위와 원칙

- 지시문: `docs/NL2FRET_PROMPT_MAIN_JUDGE.md`(sha256 `f49188a2a5e56deceea86c452efae77ebde19691648d32ac88c14df3f3d3c91a`, 사용자가 2026-11-12 08:58에 준 `nl2fret_main_judge_pack.zip` 안의 것). 이 저장소의 원칙을 지시문의 경로나 명령보다 우선한다: git 명령 금지, 코드와 입력과 판정 기록을 고치지 않음, 설정(모드, cap, timeout, 집계 규칙)을 결과를 보고 바꾸지 않음, 의미 해석과 방식 우열과 원인 설명을 쓰지 않음, 확인하지 못한 것은 "확인하지 못함", 에이전트(서브에이전트)를 쓰지 않음, 호스트 쪽 명령은 `nice -n 10`과 최소 환경(`scripts/cleanenv.sh`), NuSMV 컨테이너는 1개당 `--cpus=1`, 끝나면 컨테이너와 프로세스를 남기지 않음.
- 도구 코드는 첨부 원본 `nl2fret_tool_v1.2.zip`(sha256 `430ff365...`)과 같고 수정하지 않는다(저장소 `nl2fret_tool/`도 같음, `notes/COMPARE_REPO_TOOL.txt`). 두 동결 매니페스트(bench `176b144f...e571`, 판정 `1fda2c19...a154b`)는 실행 전후 모두 OK여야 한다. `make release` 안 함, `--allow-unfrozen` 안 씀. 모든 판정 기록 헤더는 `frozen: true`여야 한다.
- 지시문과 코드가 맞지 않는 곳과 그 처리는 `notes/MISMATCHES.md`(M1 내지 M11). 그중 이 정의에 직접 들어오는 것: 후처리 스크립트는 정답이 들어 있는 항목 파일(`inputs/lm_items_combined_v6.jsonl`, sha256 `815a037d...`, 패키지의 두 파일과 61개 항목 모두 일치함을 `notes/ITEMS_FILE_CHECK.txt`에서 확인)을 `--data`로 받는다.
- 원본 결과 `results_main`(`calls.jsonl` sha256 `0eaafec8...`, 5295줄, `finished_all`)은 읽기 전용이고 후처리는 복사본 `bench/nl2fret_tool/bench/results_main_post/`에서 한다.
- 언어: 스크립트의 주석, 독스트링, 출력 라벨은 영어(표 머리글은 한국어), 이 폴더의 문서는 한국어.

## 2. 이미 알려진 사실 (지시문 그대로)

- 생성 호출 5295행 중 비정상 29행: 모델 거부(`stop_reason: refusal`, `general_harms`) 14행(전부 LM-04_NLG-N2p3의 +R2 방식 5개, S 단계), JSON 깨짐 `no_json` 13행, 스키마 위반 `schema_fretish` 2행. 인프라 오류는 0행. 이 단위들은 실패로 분모에 남긴다. 재실행하지 않는다. (019 실행 기록: 거부 14행의 원문은 "API Error: Sonnet 5 can't help with this ... [general_harms]", 즉 `cli_error` 상태다.)
- `+D` 방식(DIRECT+D, MASTeR+D, EARS+D)은 신호 사전이 없는 07_AP 챌린지(10항목)를 빼고 51항목에서만 돌렸다. 이 10항목의 `+D` 단위는 "설계상 실행 안 함"이며 분모에서 뺀다(실패가 아님). 기본 방식 대 `+D` 비교는 같은 51항목에서만 한다.
- `model_used`에 `claude-haiku-4-5`가 보조로 함께 찍힌 행이 5266행 있다. 원인은 확인하지 못함. 보고서의 한계에 적는다.

## 3. 정의

- **단위 = 항목 x 방식 x 반복.** 분모는 방식별 전체 단위이다(run A 방식 183, `+D` 방식 153). 파서 거부, 문장 없음, 모델 거부, UND, N/M은 모두 분모에 남는다.
  - 구현: 총 3387단위(2928 + 459). `+D` 방식의 07_AP 항목 90개 조합은 `units.json`에 넣지 않는다(`ids_B.txt`에 없는 항목, 변환기의 `--subset-ids`).
- **항목 구분은 `n_parts`(기준 부분 수) 1과 2 이상.** 부분이 여러 개인 항목에서 "어느 한 문장이라도 일치"는 모든 부분을 만족한다는 뜻이 아님을 표 주석에 쓴다.
  - 구현: 항목 파일의 `n_parts`(1: 51개 항목, 2 이상: 10개 항목). 표 "항목 구분별 단위 결과".
- **의미 판정 주 지표는 도구의 역할(SAME, PROOF, REFUTE, NEITHER, UND, N/M)이다.** 단위 결과는 도구의 `unit_outcome`(단위 안 가장 좋은 문장, 관대한 규칙)을 쓰고, 추가로 단위 안 가장 나쁜 문장 기준 결과와 둘이 다른 단위 수를 병기한다. 성공 = SAME 또는 PROOF이면서 같은 문장이 realizable. 이전의 "구조 일치"(골격 동치) 지표는 이 실행에서 계산하지 않는다(동결 도구 밖). 이전 버전 수치와 직접 비교할 수 없음을 한계에 쓴다.
  - 구현: 문장의 클래스는 도구 코드의 `nl2fret_judge.aggregate.sentence_class`(SAME 또는 PROOF이면 realizable일 때 success, 아니면 partial; REFUTE는 partial; NEITHER는 failure; UND와 N/M과 기록 없음은 unjudged), 파서가 거부했거나 LTL이 없는 문장은 failure(도구와 같음). 단위의 관대한 결과는 `aggregate.unit_outcome`(문장 클래스 중 success, partial, failure 순으로 있는 첫 것, 모두 unjudged이면 unjudged, 문장이 없으면 failure). 가장 나쁜 문장 기준은 나쁨 순서 failure > unjudged > partial > success에서 가장 나쁜 클래스(문장이 없으면 failure). "판정된 단위" = 관대한 결과가 unjudged가 아닌 단위. "단위 SAME" = 단위 안 어느 문장의 역할이 SAME.
- **RQ1 (오류와 의미 손실)**
  - a. 구문 오류: 방식별 `v0` 미통과 단위 수(되먹임 전)와 `vf` 미통과 단위 수(되먹임 후), 실패 코드 분포.
    - 구현: bench `units_scored.jsonl`의 `variants.v0`, `variants.vf`의 `pre`가 `parsed`가 아닌 단위(`parse_error` 또는 `pipeline`), 코드는 `pre:code`별 수.
  - b. 필드 수준: `NL2FRET_ref_rq_v8.py`의 `classify`와 같은 규칙(파서 통과 단위, 기준 부분과 가장 적게 어긋나는 문장, 필드 timing, condition 유무, scope 유무, 전 필드 일치). 방식별과 stratum별(기본 방식 합산, `+D` 합산).
    - 구현: 변환된 `units.json`의 `status`가 `parsed`이고 문장이 있는 단위만 분류한다. 문장의 `scope`, `condition`, `timing`은 `fret_ltl_gen.jsonl`(`check.py single`의 출력, `parser_ok` 참인 줄)에서, 기준은 항목 파일 `gt_parts`의 모든 부분의 모든 버전의 `fields`에서 읽고(`null`, 빈 값은 없음, `timing`이 없으면 `eventually`), 문장 x 기준 버전 쌍마다 어긋남 목록을 만든다: scope는 유무가 다르거나 값이 다르면 `scope`, condition은 유무가 다르면 `cond`, timing은 값이 다르면 `timing`. 어긋남이 가장 적은 쌍을 고르고 같으면 먼저 본 것(문장 순서 x 기준 순서)이다. 열: 분류된 단위 수, 전 필드 일치, timing 불일치, condition 유무 불일치, scope 불일치(분모 = 분류된 단위). 표: 방식별, 방식 x stratum, 그리고 기본 방식(DIRECT, MASTeR, EARS) 합산 대 `+D`(DIRECT+D, MASTeR+D, EARS+D) 합산의 stratum별(둘 다 같은 51항목).
  - c. trigger 대 holding 패턴: conditional 단위 중 condition 유무 불일치이면서 기준 timing이 always이고 생성 timing이 always가 아닌 단위 수와 비율(기본 방식과 `+D` 방식 각각).
    - 구현: stratum이 conditional인 항목의 분류된 단위 중, 위 분류에서 고른 쌍의 어긋남에 `cond`가 있고 기준 timing이 `always`이며 생성 timing이 `always`가 아닌 단위. 분모 = conditional 분류된 단위. 방식별과, 기본 방식 합산과 `+D` 합산(51항목)으로 낸다.
  - d. 도구 역할 분포(문장 수준, 사용 횟수 가중)와 단위 결과 분포, 방식별.
    - 구현: 단위의 최종 문장 각각(같은 문장이 여러 단위에 나오면 나온 횟수만큼)의 역할, 파서 거부와 LTL 없음은 `PARSE_FAIL`, 판정 기록 없음은 `NO_RECORD`.
- **RQ2 (템플릿 중간 표현)**
  - a. 방식별 문장 수준 역할 분포와 단위 성공률(분모 전체 단위, 판정된 단위만 분모인 값을 나란히).
  - b. 반복 간 일관성: 항목별 반복 쌍(3반복이면 쌍 3개)에서 같은 문장 비율과 같은 구조(`common.struct_key`) 비율의 평균.
    - 구현: 항목마다 반복 (0,1), (0,2), (1,2) 쌍에서 앞 반복의 최종 문장 목록이 비어 있지 않고 두 목록이 같으면 같음. 같은 문장 = 공백 제거 소문자로 정규화한 문장 목록을 정렬해서 비교. 같은 구조 = `common.struct_key(common.fretish_parse(문장))` 목록을 정렬해서 비교(파싱 예외는 `ERR`). 비율 = 같은 쌍 수 / 전체 쌍 수(항목마다 쌍 수가 같으므로 항목 평균과 같음).
  - c. 방식 쌍 비교는 항목 단위 부트스트랩(항목이 재표집 단위, 반복은 항목 안에서 평균, 5000회, 시드 고정) 95% 구간: 각 방식 대 DIRECT, 템플릿 방식 대 PARA, `+R2` 대 같은 템플릿의 자유 방식, `+V` 대 기본 방식, `+D` 대 기본 방식(51항목). 모든 방식이 판정된 항목만 쓰는 짝 비교는 별도 표로 하고 남는 항목 수를 적는다.
    - 구현: 통계량 = 단위 성공률(분모 전체)의 항목 평균 차이. 항목의 값 = 그 방식의 그 항목 단위(반복 포함)의 성공 수 / 단위 수. 비교 (A, B)마다 두 방식이 모두 있는 항목 집합(`+D`가 들어가면 51항목, 아니면 61항목), 5000회 복원 재표집, 난수는 `random.Random("20261112:A:B:구분")`(문자열 시드), 구간 = 정렬한 통계량의 125번째와 4875번째 값(`NL2FRET_ref_rq_v8.py`와 같은 위치), 점 추정 = 원래 항목에서의 평균 차이. 비교 목록: 각 방식 대 DIRECT(`+D` 방식은 51항목), 자유 템플릿 방식 5개(MASTeR, EARS, Adv-EARS, SPIDER, Boilerplate) 대 PARA, 같은 5개의 `+R2` 대 자유 방식, `DIRECT+V`, `MASTeR+V`, `EARS+V`, `Boilerplate+V` 대 각 기본 방식, `DIRECT+D`, `MASTeR+D`, `EARS+D` 대 각 기본 방식. 별도 표("모든 방식이 판정된 항목만")는 두 방식의 모든 단위의 관대한 결과가 unjudged가 아닌 항목만 쓰고 남은 항목 수를 적는다.
- **RQ3 (요구사항 유형별)**: 방식 x stratum(conditional, invariant, timed, scoped) 표(단위 성공률, 단위 SAME 비율, 전체 분모). scoped는 항목 2개이므로 표에 n을 반드시 적는다.
- **실현가능성**: 방식별 realizable, unrealizable, unknown, not_run 분포(단위 수준과 문장 수준).
  - 구현: 단위 수준 = bench `units_scored.jsonl`의 `variants.vf.status`(pipeline, parse_error, not_run, unknown, unrealizable, realizable, 단위 안 문장 결과 중 가장 나쁜 것). 문장 수준 = `fret_realizability_gen.jsonl`의 결과(문장의 사용 횟수 가중), 행이 없는 문장은 `행 없음`.
- **민감도 표(보조, 주 결과를 바꾸지 않음)**: LM-04_NLG-N2p3의 +R2 단위(모델 거부)를 뺀 값과 뺀 항목 수를 별도 표로. 주 표는 뺀 값이 아니라 전체 단위 기준이다.
  - 구현: `+R2` 방식 5개에서 항목 LM-04_NLG-N2p3의 단위(방식마다 3개)를 뺀 성공률(60항목)과 주 표의 값을 나란히.
- **RQ4(템플릿 단계 정보 손실 기록)는 이 실행에서 분석하지 않는다.** 기록만 보존한다: 단계 A 출력의 `unmapped_content`, `choices` 수를 방식별로 세어 표로만 적고, 판정 기록의 AP 불일치 기록(`ap_check`) 분포를 방식별로 센다. 해석 없음.
  - 구현: 단계 A 행(`calls.jsonl`, 키 `항목|템플릿|반복|A`, 템플릿은 방식 이름에서 `+` 앞부분)의 `parsed.unmapped_content`, `parsed.choices` 항목 수의 합과 하나라도 있는 단위 수(DIRECT 계열은 단계 A가 없어 해당 없음). `ap_check`는 판정 기록마다 `equal`, `gt_subset_pred`, `pred_subset_gt`, `nm_pair_any`, `nm_pair_all`이 참인 기록 수.
- 해석 문장은 쓰지 않는다.

## 4. 판정 실행의 정의 (지시문 4절)

- 도구 기본값만 쓴다: `--mode anchor`, `--cap 128`, `--timeout 120`, NuSMV 엔진, `--aux` 없음. 컨테이너 안쪽 timeout은 125초(도구 timeout의 4.2%, 시계 시험에서 컨테이너 시계가 호스트보다 0.11% 느림, `logs/step0b_clock.log`).
- 분할: `units.json`을 항목 id 정렬 후 라운드로빈으로 항목 통째로 4개로 나눈다(`scripts/shard_units.py`, 4개는 Colima VM의 CPU 4개와 컨테이너 `--cpus=1`에 맞춤). `fret_ltl_gen.jsonl`과 `fret_realizability_gen.jsonl`은 전체를 그대로 쓴다. 분할마다 따로 `runs/shard<k>`, 컨테이너 `nusmv-020-s<k>`. 중단되면 같은 명령(`scripts/run_shard.sh <k>`)으로 재개하고 `run_header.json`이 처음 값임을 보고서에 적는다. 진행은 `judge_records.jsonl` 줄 수와 마지막 `pair_id`로만 보고한다.
- 합치기: `pair_id` 중복 0, 모든 헤더 `frozen: true`와 `code_tree_sha256` 기대값 일치를 확인하고 원본 기록 줄을 그대로 단위 순서로 합친다(`scripts/merge_judge.py`). 헤더에 `shards` 목록(분할별 입력 해시, 코드 해시)을 더하고 `make aggregate`를 합친 폴더에 실행한다. 도구의 `aggregate.json`은 그대로 보존한다.
- 점검(`scripts/judge_checks.py`): 기록 쌍 수 대 `parser_ok`이고 LTL이 있는 문장 수(차이 목록), 헤더, 역할 분포, UND와 N/M 사유별, timeout 쌍 수와 목록, 쌍당 시간 평균과 최대, 같은 (항목, 문장)이 다른 단위에서 다른 판정을 받았는지(0이어야 하고 아니면 전부 보고), 이전 v1.2 실행과 (생성 식, 기준 식)이 같은 쌍의 역할 비교(비교만).
- timeout 쌍은 설정을 바꿔 다시 돌리지 않고 N/M(timeout)으로 두고 목록만 보고한다.

## 5. 집계 스크립트와 시험

- `scripts/rq_aggregate.py`: 3절을 계산해 `rq_tables.md`, `rq_tables.json`을 만든다(판정 기록은 읽기만). 도구 코드(`nl2fret_judge.aggregate`)와 bench의 `common.py`는 읽기 전용으로 가져다 쓴다.
- 판정 기록 없이 합성 예시로 시험했다: `scripts/test_rq_aggregate.py`(12개 확인 통과), `scripts/test_merge_checks.py`(10개 확인 통과). 합성 데이터는 만든 것이고 실제 결과와 무관하다.
- 고정하는 파일: 이 문서, `scripts/` 전부(단계 스크립트, 변환기, 분할, 실행, 합치기, 점검, 집계, 시험, 래퍼), 입력 파일은 변환 뒤의 해시를 `notes/INPUT_HASHES_FINAL.sha256`에 기록한다.

## 6. 시작 시점에 알고 있는 확인하지 못할 것

- 판정 소요 시간(v8 예시 252쌍이 NuSMV로 36분, 이전 v6 입력은 쌍 2855개였음, 이번 쌍 수는 변환 후 센다).
- LM-03_REG 9쌍이 timeout 600초에서도 시간 초과였던 원인, 관대한 단위 규칙(여러 부분 항목을 어느 한 문장이라도로 판정), `texts` 규칙이 거부된 문장을 포함하는 1개 단위의 차이: 알려진 미해결, 보고만 한다.
- `check.py single`의 실행 시간(v6는 1965문장에 `--procs 2`로 약 50분).
- 이전 실험(v1.2 이전)의 "구조 일치" 지표와 이번 단위 결과는 직접 비교할 수 없다.

## 7. 변환 뒤, 판정 전에 확인한 기대값 (`notes/INPUTS_VALIDATION.json`, `notes/STEP1_CHECKS.md`, `logs/stage2_*_summary.json`)

- 입력 3개의 sha256(`notes/INPUT_HASHES_FINAL.sha256`): `units.json` 2a130c99e1fb8606f258a48ccc7d1d3819d7c92d971974cbef92a7c74aa5b474, `fret_ltl_gen.jsonl` 52df67407b39a10934c59d39af7dd74c81f6dd78474361a9043fe11ea21bfea0, `fret_realizability_gen.jsonl` 5602692bcf13b33aa0cfa420a9e951ebef8ef3988911303e3d440158e3d3de58.
- `units.json`: 3387단위(방식 19개, 항목 61개 모두 `LM-`, 반복 0, 1, 2), 상태 parsed 3313, parse_error 34, pipeline 40, 문장이 없는 단위 40, 최종 문장 4038개(서로 다른 문장 2769, 서로 다른 (항목, 문장) 2772). `+D`의 07_AP 90개 조합은 제외(설계상 실행 안 함). bench `units_v3.jsonl`과 다섯 필드 모두 차이 0.
- 도구의 `units.load_units`가 세 파일을 읽는다: 문장 4038개 중 `parser_ok`이고 LTL이 있는 문장 3999개. **기대 판정 기록 수 = 3999쌍**(분할 합계). 나머지 39문장은 공식 파서가 거부했거나 realizability 점검 대상이 아니었던 단위(상태 parse_error)의 문장이며 도구는 이를 실패로 센다(분모에 남음).
- 같은 (항목, 문장)이 여러 단위에 나오므로(문장 발생의 31.4%가 앞선 발생과 같음) 같은 (항목, 문장)의 판정은 같아야 하고(4.4항 결정성 점검), 도구는 그 쌍을 단위마다 다시 판정한다(캐시 없음).
- 단위 상태(realizability 이후)를 변환 파일에서 다시 계산한 값이 bench `units_scored.jsonl`과 단위마다 같다(차이 0): not_run 205, parse_error 34, pipeline 40, realizable 2496, unknown 612.
- 기준 문장 109개 중 이번 공식 파서의 LTL이 도구에 저장된 LTL과 글자가 같은 것 76개, 다른 것 33개(pt 33개, ft 15개; 그중 `LM-04_NLG-N6` 0.0은 이번 파서가 거부). 판정은 지시문대로 저장된 값(`data/reference/lm_reference_with_ltl.jsonl`)을 기준으로 한다. 글자 차이의 의미 동치 여부는 주 판정이 끝난 뒤 보조 점검(`scripts/ref_ltl_diag.py`, 별도 기록 폴더)으로만 본다.
- 분할(`inputs/shards_manifest.json`, 항목 id 정렬 라운드로빈 4개): 항목 16, 15, 15, 15개.
