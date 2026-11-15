# PRE_RUN_DEFINITIONS: 본 실험 입력 3개 만들기 (61개 항목, 동결 도구용), 2026-11-11

이 문서는 변환을 실행하기 전에 쓴다. 이 문서와 스크립트의 해시는 실행 전에 고정하고(`notes/PIN_scripts.sha256`), 결과를 본 뒤 정의와 스크립트를 바꾸지 않는다. 바꿔야 하면 바꾼 이유와 시각을 `notes/CHANGELOG.md`에 남기고 보고서에 적는다.

## 1. 범위와 원칙

- 지시문: `docs/NL2FRET_61_INPUTS.md` (사용자의 `~/nl2semiformal/testnote.md`를 바이트 단위로 복사한 것, sha256 `519e9837f3c5055bb033157a48401498a9a8397756a237ace0e30446c22398c2`, `notes/INSTRUCTION.sha256`). 금지 사항, 단계, 최종 보고 형식은 지시문을 따른다.
- 이 저장소의 원칙을 지시문의 경로나 명령보다 우선한다: git 명령을 쓰지 않는다, 값을 보정하거나 단위, 문장, 항목을 임의로 제외하지 않는다(변환은 형식 변환과 키 이름 맞춤만), 각 단계는 1회 실행하고 중단 재개만 허용한다, 관측만 적고 확인하지 못한 것은 "확인하지 못함"으로 적는다, 에이전트를 쓰지 않는다.
- 동결된 도구(`nl2fret_tool_v1.2.zip`)와 bench 결과 폴더는 읽기만 한다. 변환 스크립트는 도구 밖(`scripts/`)에 둔다.
- CPU: 호스트 쪽 모든 명령은 `nice -n 10`과 최소 환경(`scripts/cleanenv.sh`), NuSMV는 컨테이너 1개(`--cpus=1`)로 질의 한 번에 하나, 끝나면 컨테이너와 프로세스를 남기지 않는다.
- 언어: 스크립트의 주석, 독스트링, 출력 라벨은 영어, 이 폴더의 문서는 한국어.
- 폴더 이름: `018_lm61_inputs`(experiments의 번호 규칙, `experiments/000_INDEX.md`).

## 2. 도구와 환경

- 입력 패키지: `nl2fret_tool_v1.2.zip`(sha256 `430ff36588f1559180a75472f7a08b15061c330e67a84f5fa250324bbabb367e`, v1.2 실행이 보고한 값과 같음, `notes/INPUT_ZIP.sha256`). 풀어서 읽기 전용으로 둔 사본 `bench/pristine/nl2fret_tool/`(75개 파일, 해시 목록은 v1.2 빌드 기록과 같음 `notes/PKG_V12_FILES.sha256`)과, 소규모 시험(5단계)에 쓰는 쓰기 가능한 실행 사본 `bench/nl2fret_tool/`(같은 zip에서 따로 풀었고 파일 해시가 같음 `notes/PKG_RUN_COPY_START.sha256`). 실행 사본에는 `runs/`와 `inputs/`(둘 다 git 무시 대상)만 새로 생기고 zip 안의 파일은 바꾸지 않는다. 작업 전후에 `shasum -a 256 -c JUDGE_FROZEN_MANIFEST.sha256`, `make freeze-check`, 파일 해시 목록을 비교한다.
- venv: 패키지의 `requirements.txt`(`z3-solver==5.3.3.0`, `pytest==9.2.0`)로 만든 `venv/`(Python 3.12.14). `pip freeze`는 v1.2 실행과 같다(`notes/PIP_FREEZE.txt`).
- NuSMV: v1.2 실행과 같은 Docker 이미지 `cst-nusmv:local`(Colima), 래퍼 `scripts/bin/NuSMV`(컨테이너 이름 `nusmv-lm61`, `--cpus=1`).
- 이미 관측한 것(변환 규칙을 정하기 전의 읽기 전용 점검, `logs/step0_*.log`, `notes/OBS_READONLY_TESTS.txt`): 읽기 전용 사본에서 `make test`는 43 passed, 5 failed(테스트 헬퍼가 읽기 전용 모드까지 복사해서 코드 파일을 바꾸는 시험이 `PermissionError`), 쓰기 가능한 사본에서는 48 passed. 패키지는 수정하지 않는다.

## 3. 원천 (1단계)

- 후보 탐색: `scripts/source_candidates.py`가 저장소 전체에서 bench 결과 파일(`calls.jsonl`, `units_v3.jsonl`, `units_scored.jsonl`, `fret_ltl*.jsonl`, `fret_realizability*.jsonl`)이 있는 폴더를 찾고 61개 항목(`bench/data/lm_items.jsonl`)을 몇 개 담는지 센다(`logs/source_candidates.log`, `.json`).
- 선택 기준: 61개 항목을 모두 담고, `run_state.json`의 상태가 `finished_all`이며 `n_items`가 61이고, 폴더 이름이 개발 실행(`results_dev`), 사전 점검(`results_pre`), 모의(`results_mock`)가 아닌 것. 이 기준에 맞는 폴더가 하나이면 그것을 쓰고, 둘 이상이면 후보 표를 보고하고 중단한다. 후보가 없어도 중단한다.
- 예상(사전 점검에서 본 것): `experiments/nl7/results_lm`(v6 주 실행: 항목 61, 방식 13, 반복 3, 2026-11-02 17:39에서 11-03 07:20, `finished_all`)이 유일한 후보다. 단위 수는 61 x 13 x 3 = 2379이고 bench의 자체 기록(`score.log`의 "units 2379", `RUN_RECORD.md` 1장)과 같아야 한다.

## 4. 변환 규칙

### 4.1 `units.json` (`convert_inputs.py units`)

- 단위의 구성과 순서: 항목은 그 실행이 쓴 항목 파일(`snapshot/items_used.jsonl`)의 순서, 방식은 `run_state.json`의 `arms` 순서, 반복은 `calls.jsonl`의 `rep` 값의 오름차순. 이는 `bench/units3.py`와 v8 추가 스크립트 `rlz_dict8.py`의 `build_inventory`가 쓰는 순서이고 v8 예시 파일의 순서와 같다.
- 최종 문장: 단위마다 `units3.derive(rows, item, arm, rep, comp)`로 상태를 유도하고 변형 `vf`(피드백 라운드를 거친 최종 답)를 쓴다. 근거: `rlz_dict8.py` 머리말("the answer after the feedback rounds (variant vf) ... as in the scoring of the v6 main run"), `bench/score3.py final`과 `RUN_RECORD.md`의 "단위 상태(vf)".
- 유도에 쓰는 bench 코드: 그 실행이 쓴 코드(그 실행의 `snapshot/`). v8은 패키지 `bench/`와 모듈 해시가 같다. v6 주 실행의 `units3.py`, `prompts3.py`, `tpl_rules.py`, `common.py`는 패키지 `bench/`와 다르다(`logs/preliminary_analysis.log`: R2 규칙 처리 등 v7, v8에서 바뀜). 패키지 코드로 +R 방식을 다시 유도하면 v6 기록과 달라질 수 있으므로 v6은 v6의 snapshot 코드로 유도하고, 결과를 그 실행이 `score3.py build`로 남긴 `units_v3.jsonl`(`variants.vf`)과 단위마다 대조한다. 다섯 필드(`pre`, `code`, `texts`, `accepted_texts`, `n_rounds`)가 한 단위라도 다르면 중단한다.
- 단위의 필드(v8 예시와 같은 키와 순서): `item`, `arm`, `rep`, `status`, `code`, `texts`, `n_rounds`, 항목 계층을 넣는 경우 마지막에 `stratum`.
  - `status`, `code`: `units3.variant(rec, "vf")`가 돌려주는 단계 상태(`parsed`, `parse_error`, `pipeline`)와 코드(공식 파서 오류 분류나 파이프라인 사유, 없으면 빈 문자열). 도구는 이 두 필드를 읽지 않는다(`units.load_units`는 `status`를 단위에 싣기만 하고 `aggregate`는 쓰지 않는다). realizability가 반영된 상태(`realizable` 등)는 넣지 않는다.
  - `n_rounds`: 유도된 라운드의 수(`len(rec["rounds"])`, 첫 답 한 번이면 1). 근거: v8 예시의 값이 1, 2, 3이고(1: 167, 2: 44, 3: 5) 피드백 라운드의 최대가 2이므로 `len(rounds)-1`(0에서 2)이 아니라 `len(rounds)`다. 이 가설은 3단계의 v8 재현이 확인한다.
  - `texts`: 최종 라운드의 모든 문장(문장이 있는 줄 전부, `score3.build`의 `all_texts`). 공식 파서가 거부한 문장도 들어간다. 근거: 지시문은 `texts`를 "그 단위의 최종 FRETish 문장 목록"이라 하고 문장을 임의로 제외하지 말라고 하며, 도구 `units.py`의 머리말은 "A sentence without a parsed formula stays in the unit (it counts as parser-rejected, i.e. failure, never as excluded)"라고 한다. 거부 문장이 없는 v8에서는 `variant`가 돌려주는 통과 문장 목록과 같다(`parsed` 단위에서는 항상 같다). 대안(`--texts accepted`, 파서가 통과시킨 문장만)은 만들지 않고 6절 6번의 영향 점검에만 쓴다.
  - `stratum`: 항목 파일의 `stratum`(그 실행의 `snapshot/items_used.jsonl`, 패키지 `bench/data/lm_items.jsonl`과 항목 id, 순서, `stratum`, `raw_nl`이 같은지 검증에서 확인). 61개 항목 입력에는 넣고, v8 재현에는 넣지 않는다(v8 예시에 `stratum`이 없다).
- 어느 단위도 빼지 않는다. 유도가 `pending`인 단위가 있으면(실행이 끝나지 않은 것) 중단한다.
- 직렬화(v8 예시의 바이트를 재현하는 형식, 사전 점검으로 확인): `json.dumps({"units": [...]}, ensure_ascii=False)`, 들여쓰기 없음, 끝 개행 없음.

### 4.2 `fret_ltl_gen.jsonl` (`convert_inputs.py ltl`)

- 원천: 그 실행의 `fret_ltl.jsonl`(`fret_check/check.py single`의 출력, 기준 문장과 생성 문장). 문장이 `units.json`의 어느 단위의 `texts`에든 있는 줄만 남기고 문장(파이썬 문자열 순서) 오름차순으로 쓴다(v8의 `fret_ltl_gen.jsonl`이 `sorted(...)` 순서). 줄의 내용은 바꾸지 않는다(키와 값, 키 순서 그대로, 직렬화는 `json.dumps(row, ensure_ascii=False)` 한 줄과 개행).
- `units.json`에 있지만 원천에 줄이 없는 문장은 만들지 않고 세어서 보고한다(도구는 줄이 없는 문장을 `parser_ok` 거짓으로 읽어 실패로 센다). 원천의 기준 문장 줄과 쓰이지 않는 줄은 버린다(세어서 보고).

### 4.3 `fret_realizability_gen.jsonl` (`convert_inputs.py rlz`)

- 원천: 그 실행의 `fret_realizability.jsonl`. 남기는 줄: `kind == "gen"`, `mode == "single_requirement"`, `rep`가 null이 아님, `arm`이 `#vf`로 끝남(변형 접미사 `#v0`, `#vn`, `#vf`는 `score3.py build`가 `variants.jsonl`에 붙인 변형 이름이고 단위의 `arm`은 접미사 없는 방식 이름이다). 남기는 줄은 `arm`에서 `#vf`를 떼고 나머지 필드를 바꾸지 않는다(키 순서 그대로).
- 버리는 줄(모두 세어서 보고): 기준 문장 줄(`kind == "gt"`, `rep` null, 도구가 읽지 못한다), 다른 변형(`#v0`, `#vn`)의 줄. v8 원천은 이미 접미사 없는 `_gen` 파일이라 `--variant none`으로 접미사 처리 없이 같은 선택 규칙을 쓴다.
- 순서: 단위 순서(`units.json`의 순서), 같은 단위 안에서는 `sentence_idx` 오름차순(v8의 `fret_realizability_gen.jsonl`의 순서). 같은 (항목, 방식, 반복, `sentence_idx`)가 둘이면 중단한다. 단위에 속하지 않는 줄이 있으면 중단한다.
- `units.json`에 있지만 줄이 없는 문장은 만들지 않고 단위 상태별로 세어서 보고한다(도구는 줄이 없는 문장을 `not_run`으로 읽는다). 줄은 `parsed` 단위에만 있고, `sentence_idx`는 그 단위의 통과 문장 목록의 위치이므로 `parsed` 단위에서는 `texts[sentence_idx]`와 줄의 `sentence`가 같아야 한다(다르면 중단).

## 5. 3단계: v8 예시 재현의 정의

- 같은 스크립트를 v8 원천(`experiments/v8_dict8/bench/results_dict8`: `calls.jsonl`, `parser_cache.jsonl`, `run_state.json`, `snapshot/`, `fret_ltl_gen.jsonl`, `fret_realizability_gen.jsonl`)에 돌려 `units.json`, `fret_ltl_gen.jsonl`, `fret_realizability_gen.jsonl`을 만들고 패키지의 `data/example_units_v8.json`, `example_fret_ltl_gen_v8.jsonl`, `example_fret_realizability_gen_v8.jsonl`과 바이트 단위로 비교한다(`scripts/compare_example.py`). 한 파일이라도 다르면 필드 단위 차이를 보고하고 61개 항목 변환으로 넘어가지 않는다.
- 이 재현이 시험하는 것과 못 하는 것: `units.json`은 `calls.jsonl`에서 처음부터 유도하므로 상태 유도, 변형 선택, `n_rounds`, 순서, 직렬화를 시험한다. v8의 `_gen` 두 파일은 v8 원천이 이미 `_gen` 형식이어서(예시 파일이 v8 폴더의 파일과 바이트가 같다, `logs/preliminary_analysis.log`) 항등 시험이다: 선택 규칙과 줄 직렬화가 값을 바꾸지 않음을 보이지만 `#vf` 접미사를 떼는 처리와 기준 문장 줄 제외는 v8 데이터로 시험할 수 없다(v8에는 그런 줄이 없다). 그 두 처리는 61개 항목 데이터에서 6절의 검증(단위 상태를 bench의 `units_scored.jsonl`, `RUN_RECORD.md`와 대조)으로 확인한다.

## 6. 4단계: 61개 항목 변환 후 검증의 정의와 예상값

실행 전에 이미 읽은 값으로(`logs/preliminary_analysis.log`) 정한 예상이다. 예상과 다르면 보고하고, 아래 "중단" 표시가 있는 것은 이후 단계로 넘어가지 않는다.

1. 단위: 2379개(61 x 13 x 3), 항목 61(모두 `LM-`로 시작), 방식 13개(`run_state.json` 순서), 반복 0, 1, 2, `status` `parsed` 2329, `parse_error` 31, `pipeline` 19, `texts`가 빈 단위 19개(`pipeline`), `texts`의 문장 합 2892, `stratum`은 conditional 1053, invariant 858, scoped 78, timed 390. 모든 (항목, 방식, 반복)이 정확히 한 번(빠짐 0, 중복 0, 예상 밖 0, 중단).
2. `units_v3.jsonl`과의 단위별 대조(4.1절): 다섯 필드 모두 차이 0(중단).
3. 문장 대응: `fret_ltl_gen.jsonl`에 쓴 줄 2014, 줄이 없는 고유 문장 36개(2050 - 2014, 파서가 거부했거나 realizability 점검 대상이 아니었던 단위의 문장), 그 줄 중 `parser_ok` 거짓 0. `fret_realizability_gen.jsonl`에 쓴 줄 2852(버린 줄: 기준 109, `#v0` 2178, `#vn` 2180), 줄이 없는 단위 문장 40개 전부 `parse_error` 단위의 것(통과 9 + 거부 31).
4. 도구의 `units.load_units`(패키지의 `judging/nl2fret_judge/units.py`를 읽기 전용으로 import)가 세 파일을 오류 없이 읽는다(중단).
5. realizability 이후의 단위 상태를 `bench/score3.py final`의 규칙(문장 결과 중 가장 나쁜 것, 순서 pipeline, parse_error, not_run, unknown, unrealizable, realizable)으로 변환된 파일에서 다시 계산해 그 실행의 `units_scored.jsonl`(`variants.vf.status`)과 단위마다 대조한다. 차이 0이어야 하고, 합계는 `RUN_RECORD.md` 1장의 realizable 1861, unrealizable 5, unknown 365, parse_error 31, not_run 98, pipeline 19와 같아야 한다.
6. `texts`가 모든 문장일 때와 통과 문장만일 때(별도 what-if 변환, 전달하지 않음)의 차이: `texts`가 다른 단위 31개, 문장 2892 대 2861. 두 경우 도구의 단위 결과(판정 기록 없이 `aggregate.aggregate`를 부른 값)가 다른 단위 수는 0으로 예상한다(파서 거부 단위의 문장은 어느 경우에도 `parser_ok` 거짓이라 failure).
7. 항목 파일의 `stratum` 출처 대조: 실행의 `snapshot/items_used.jsonl`과 패키지 `bench/data/lm_items.jsonl`이 항목 id, 순서, `stratum`, `raw_nl` 모두 같다.

## 7. 데이터 분리 검증의 정의 (지시문 "데이터 분리 검증")

연구 설계: 규칙과 프롬프트 개발은 개발셋(`data/dev_items.jsonl`, 94개 항목)만 쓰고, 시험셋은 록히드마틴 61개 항목이다. 개발셋 파일은 `experiments/v7_dev0/bench/data/dev_items.jsonl`(sha256 `e70710a0...`, `v7_dev1`의 것과 같음)이다.

1. `units.json`의 모든 항목 id가 `LM-`로 시작하고 서로 다른 항목이 정확히 61개.
2. 개발셋 항목 id(`N-`, `X-`로 시작)가 단위에 없다. 개발셋 파일과 id 교집합 0, 원문 자연어(공백을 합치고 소문자로 정규화한 뒤)의 완전 일치 교집합 0. 0이 아니면 목록을 보고한다.
3. 원천 폴더가 개발 실행, 사전 점검, 모의가 아님: 폴더 이름(`results_lm`), `run_state.json`(`finished_all`, `n_items` 61), 항목 목록이 `units.json`의 항목과 같음.
4. `fret_ltl_gen.jsonl`의 줄 중 문장이 `units.json`에 없는 줄 수(0이어야 함). 참고로 원천 `fret_ltl.jsonl`의 줄 중 `units.json`에도 기준 문장에도 없는 줄 수와, 사전 점검, 모의, 개발 실행의 LTL 파일과 문장이 글자 그대로 겹치는 수(겹침은 같은 문장이 우연히 나온 것일 수 있어 혼입의 증거가 아니다. 보고만 한다).

## 8. 5단계: 소규모 시험의 정의

- 항목 2개: 파일의 첫 항목 `LM-00_TRIPLEX-RM-001`(참조 부분 1개)과 참조 부분이 가장 많은 항목(`data/reference/lm_reference_with_ltl.jsonl`의 `n_parts`가 최대인 것: `LM-09_EUL-N1`, 9개, 둘째로 많은 것은 4개라 유일). 부분 입력은 전체 입력에서 해당 항목의 단위, 그 문장의 LTL 줄, 해당 항목의 realizability 줄을 편집 없이 골라서 만들고 이름에 `_part2`를 붙인다(`units_part2.json`, `fret_ltl_gen_part2.jsonl`, `fret_realizability_gen_part2.jsonl`). 실행 사본의 `inputs/`에 둔다.
- `make selfcheck`(NuSMV, 5쌍 모두 PASS), `make judge`(z3 엔진: Makefile 명령 끝에 `JUDGE_ARGS='--engine z3'`를 붙여 뒤의 옵션이 앞의 `--engine nusmv`를 덮는다), `make aggregate`가 오류 없이 끝나는지 본다. 판정 결과(역할 분포)는 시험의 대상이 아니고 보고만 한다. 헤더에 `frozen: true`와 `frozen_manifest_sha256`이 남는지도 확인한다.
- 지시문이 허용한 z3 대신 NuSMV로 같은 부분 입력을 돌리는 것은 추가 시험이며 필수가 아니다(`run_stage.sh partial_nusmv`). 돌리면 쌍당 시간을 본 데이터 전체의 실행 시간 추정에 쓴다.

## 9. 시작 시점에 알고 있는 확인하지 못할 항목

- 이 변환이 만든 입력으로 도구를 61개 항목 전체에 돌리는 것(지시문 범위 밖).
- v8 데이터로는 `#vf` 접미사 처리와 기준 문장 줄 제외를 시험할 수 없다(5절).
- v8 예시의 `units.json`을 만든 원래 스크립트는 저장소에서 찾지 못했다. 규칙은 예시 파일의 값과 bench 코드에서 읽은 것이고 3단계 재현이 확인한다.
- 도구의 `aggregate.unit_outcome`은 단위의 문장 중 가장 좋은 등급을 단위 결과로 쓴다(`success`가 하나라도 있으면 success). bench의 단위 상태(가장 나쁜 문장)와 규칙이 다르다. 의도인지는 확인하지 못했다(이 작업은 도구를 바꾸지 않는다).
