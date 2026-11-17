# PRE_RUN_DEFINITIONS: nl2fret_tool Mac 검증 실행 (2026-11-10)

지시문(`docs/NL2FRET_TOOL_MAC.md`)이 열어 둔 정의를 단계 2 실행 전에 고정합니다. 이 문서와 스크립트의 해시는 `notes/PRE_RUN.sha256`에 있습니다. 지시문은 채팅에 붙여 넣은 글이며 저장소 구조를 모르는 LLM이 쓴 것이라, 저장소 규칙(experiments/ 아래 실행 폴더, 해시 고정, git 금지, 한국어 보고서, 편차 기록)을 먼저 따랐습니다.

표기: EXP = `experiments/nl2fret_tool_mac/`, PKG = `EXP/bench/nl2fret_tool/` (zip을 푼 패키지 루트). 지시문의 "`bench/` 안의 파일"은 패키지 안의 `PKG/bench/`입니다.

## 1. 범위와 원칙

1. 지시문의 1단계부터 6단계까지를 순서대로 실행합니다. 5단계는 입력이 없으면 "입력 없음"으로 적습니다 (6절).
2. 패키지의 70개 파일(`notes/PKG_TREE.sha256`)은 수정하지 않습니다. 실행이 끝난 뒤 같은 해시를 다시 검사해 결과를 적습니다. 실행이 새로 만드는 것은 `PKG/inputs/`와 `PKG/runs/`뿐입니다 (둘 다 패키지의 `.gitignore`에 있는 폴더).
3. 판정 결과를 보정하거나 쌍을 제외하지 않습니다. 관측은 관측으로만 적고, 엔진이나 도구의 우열, 의미 동등성, 결론은 말하지 않습니다.
4. git 명령은 쓰지 않습니다.
5. 각 단계(2단계, 3단계의 NuSMV 판정, 3단계의 z3 판정, 4단계, 6단계)는 1회 실행합니다. 프로세스가 중단되면 같은 명령으로 재개합니다(도구의 재개 기능). 래퍼나 컨테이너 같은 인프라 문제로 단계가 실패해 다시 실행하면, 실패한 실행의 로그를 `logs/`에 남기고 보고서에 적습니다.
6. 개발 시험: 분석 스크립트를 점검하려고, 실행 전에 `PKG/data/reference/pairs_sample.jsonl`의 8쌍(역할별 2쌍)을 도구의 `judge_pair`로 판정하는 소규모 시험을 NuSMV와 z3로 한 번 했습니다. 3단계의 예시 데이터는 쓰지 않았고, 이 시험의 값은 보고에 쓰지 않습니다. 파일은 스크래치패드(`dev_test/`)에만 있고 `PKG/runs/_dev_test`는 시험 후 삭제했습니다.

## 2. 환경과 실행 방식

- OS와 하드웨어: `sw_vers`, `uname -m` 출력을 보고서 1항에 적습니다.
- Python: 지시문은 3.10 이상을 요구합니다. 시스템 `python3`은 3.9.6이라 쓰지 않고, pyenv 3.12.14로 `EXP/venv`를 만들어 `pip install -r requirements.txt`를 실행했습니다. 패키지의 요구 목록은 버전을 지정하지 않으므로 설치된 버전을 기록합니다(`logs/step1_2_python_env.log`). 도구의 모든 호출은 이 venv의 python으로 하고, `make`에는 `PY=<venv python>`을 넘깁니다.
- 환경 변수와 우선순위: `PYTHONDONTWRITEBYTECODE=1`, `PYTEST_ADDOPTS=-p no:cacheprovider`(패키지 폴더에 `__pycache__`와 `.pytest_cache`가 생기지 않게 함). 모든 호출은 `scripts/cleanenv.sh`(최소 환경)와 `nice -n 10` 아래에서 합니다.
- NuSMV: 직접 설치가 없어 Docker 이미지 `cst-nusmv:local`(Colima 백엔드)을 씁니다. 래퍼 `scripts/bin/NuSMV`는 다음을 합니다. (가) 마지막 인자가 상대 경로이면 절대 경로로 바꿉니다. 도구가 `judging/` 기준의 상대 경로(`../runs/<OUT>/work/<sha>.smv`)를 넘기기 때문입니다. (나) 장수 컨테이너 `nusmv-tool-mac`(`--cpus=1`, `PKG/runs`를 같은 경로로 마운트)에서 coreutils `timeout`을 붙여 NuSMV를 실행합니다. 안쪽 timeout은 125초로, 도구 자신의 timeout(120초, `subprocess.run`)보다 길게 두었습니다. 그래서 timeout 판정은 도구가 내리고, 안쪽 timeout은 도구가 docker 클라이언트를 죽인 뒤 컨테이너에 남는 NuSMV 프로세스를 정리하는 데만 씁니다. 이 래퍼는 지시문이 허용한 "Docker 래퍼 처리"이며 도구 코드의 변경이 아닙니다.
- 컨테이너는 단계 실행 스크립트가 필요할 때 시작하고, 모든 단계가 끝난 뒤 제거합니다. 이 실행과 무관한 컨테이너 `serene_chaum`은 건드리지 않습니다.
- 1단계(환경 준비)의 합격 기준은 지시문 그대로입니다: `make freeze-check`가 전부 OK, `make test`가 6개 통과, `NuSMV -h`에서 버전 문자열 확인.

## 3. 2단계 정의 (자기점검)

- 명령: `make selfcheck NUSMV=<래퍼> OUT=runs/selfcheck PY=<venv python>`.
- PASS: 도구가 출력하는 5행이 모두 `PASS`이고 마지막 줄이 `SELFCHECK PASSED`이며 종료 코드가 0. 그 밖은 FAIL이고, FAIL이면 3단계 이후를 실행하지 않고 해당 쌍의 `.smv` 파일, NuSMV 원문 출력, 기대값과 실제값을 보고합니다.
- `runs/selfcheck/selfcheck.json`을 산출물에 포함합니다.

## 4. 3단계 정의 (NuSMV 대 z3)

1. 입력: `PKG/data/example_units_v8.json`, `example_fret_ltl_gen_v8.jsonl`, `example_fret_realizability_gen_v8.jsonl`을 `PKG/inputs/units.json`, `fret_ltl_gen.jsonl`, `fret_realizability_gen.jsonl`로 `cp -p` 복사하고 sha256을 기록합니다.
2. NuSMV 판정: `make judge OUT=runs/nusmv_v8 NUSMV=<래퍼> PY=<venv python>`, 이어서 `make aggregate OUT=runs/nusmv_v8 PY=<venv python>`. 옵션은 기본값입니다(`--mode anchor`, `--cap 128`, `--timeout 120`, 보조 질의 없음).
3. z3 판정: 지시문의 명령 그대로, `judging/`에서 `python -m nl2fret_judge judge --engine z3 --out ../runs/z3_v8 --units ../inputs/units.json --ltl ../inputs/fret_ltl_gen.jsonl --rlz ../inputs/fret_realizability_gen.jsonl`. horizon은 기본값 8이고 `python`은 venv의 것입니다. z3 실행의 `aggregate`는 지시문에 없어서 실행하지 않습니다.
4. 비교(`scripts/compare_engines.py`, 두 `judge_records.jsonl`을 `pair_id`로 맞춤). 결과는 `PKG/runs/compare/`에 둡니다.
   - 범주: 기록의 `nm`이 true이면 `NM`, 아니면 `role`(SAME, PROOF, REFUTE, NEITHER, UND). "판정됨"은 앞의 네 역할입니다.
   - 교차표: 행은 NuSMV 범주, 열은 z3 범주, 값은 쌍 수. N/M은 `NM` 한 칸에 합치고, NuSMV N/M 쌍의 사유(`nm_reason`)별로 z3 범주를 센 표를 따로 둡니다.
   - 불일치: 두 엔진 모두 판정됨이고 `role`이 다른 쌍. pair_id, 두 식(`gt_pt`, `pred_pt`, 각 실행의 기록값), 두 역할, 각 실행의 sound/compl/equiv, 정렬 사상을 `disagreements.jsonl`에 모두 적습니다. 한쪽만 판정된 쌍(UND가 낀 쌍은 제외)은 불일치가 아니라 `one_sided.jsonl`에 따로 적습니다. 두 실행의 UND 쌍이 다르면 그 목록을 적습니다.
   - NuSMV N/M 사유 분포는 NuSMV 기록의 `nm_reason` 값별 쌍 수, UND 사유 분포는 `und_reason` 값별 쌍 수입니다(두 실행 모두).
   - 시간: 쌍당 시간은 기록의 `elapsed_sec_total`(정렬 탐색 질의를 모두 포함)이고, 평균과 최대를 (가) 모든 기록, (나) 질의가 1개 이상 기록된 기록 두 가지로 적습니다. 질의당 시간(`queries[].elapsed_sec`)의 평균과 최대도 적습니다. timeout 발생 수는 `timed_out`이 true인 질의 수, 그런 질의가 있는 쌍 수, 최종 `nm_reason`이 `timeout`인 쌍 수의 세 가지로 적습니다. 벽시계 시간은 단계 로그의 시작과 종료 시각입니다.
   - 추가 관측(지시문에 없음): (가) 각 실행에서 판정된 쌍 중 `equiv`가 `sound and compl`과 다른 쌍의 목록, (나) 이 Mac의 z3 실행 범주 분포와 지시문 5항의 샌드박스 값(252쌍: UND 103, NEITHER 62, SAME 43, REFUTE 16, PROOF 5, 나머지 N/M)을 나란히 적기. 둘 다 관측이며 판정이 아닙니다.

## 5. 4단계 정의 (순서 가설)

- 대상 쌍(지시문의 "임의 3쌍")의 선택 규칙: NuSMV 실행(`runs/nusmv_v8`)에서 판정된 쌍(역할이 SAME, PROOF, REFUTE, NEITHER)이면서 변환된 두 식 `gs`와 `rs`가 서로 다른 쌍의 `pair_id`를 문자열 순으로 정렬하고, `random.Random(20261110).sample(..., 3)`으로 3개를 뽑습니다. 변환식이 같은 쌍은 sound와 compl의 LTLSPEC 텍스트가 같아 출력 순서를 구분할 수 없어 제외합니다. 선택은 결과를 보기 전에 정한 이 규칙으로만 하고, 다시 뽑지 않습니다.
- 세 식의 재구성: 기록의 정렬 사상(`alignment.mapping`)으로 `pred_pt`의 식별자를 바꾸고, 도구 자신의 함수(`judge._prepare`, `engines.spec_text`)로 equiv, sound, compl의 LTLSPEC 텍스트를 만듭니다. 이 텍스트가 판정 실행의 기록(`queries[]`의 `kind`와 `spec_text`)에 있는지 같이 확인합니다.
- 파일: 도구의 SMV 템플릿(`MODULE main`, `VAR`의 boolean 선언, `LTLSPEC`)에서 `LTLSPEC`만 equiv, sound, compl 순서의 3줄로 한 파일에 둡니다. 선언 순서는 이 순서입니다.
- 출력 순서의 판독: NuSMV가 출력하는 `-- specification <식> is true|false` 줄을 위에서부터 읽고, 식은 공백과 괄호를 모두 지운 문자열로 선언된 세 식과 맞춥니다(NuSMV가 식을 다시 찍기 때문). 하나의 선언에만 대응하면 `unique`, 둘 이상이면 `ambiguous`, 없으면 `none`으로 기록하며 강제로 맞추지 않습니다. 선언 인덱스의 출력 순서가 [0, 1, 2]이면 "선언 순서와 같음"입니다.
- 대조: (가) 식으로 맞춘 판정값, (나) 출력 위치로 대응시킨 판정값(출력 순서를 선언 순서로 가정한 경우)을 각각 판정 실행에 기록된 단일 질의(질의당 파일 하나) 판정값과 비교합니다.
- 결과는 `PKG/runs/order_check/`에 두고(`pairN.smv`, `pairN.stdout.txt`, `pairN.stderr.txt`, `order_check.json`), 결과와 상관없이 도구의 단일 질의 방식은 바꾸지 않습니다. 3쌍보다 많은 쌍으로 확장하지 않습니다(지시문의 "다음만 확인해라").

## 6. 5단계 정의 (본 데이터)

- 지시문은 61개 Lockheed Martin 항목의 실제 `units.json`, `fret_ltl_gen.jsonl`, `fret_realizability_gen.jsonl`을 사용자가 제공한 경우에만 실행하라고 합니다. 이번 요청에서 사용자가 준 것은 지시문과 `nl2fret_tool.zip`뿐이고, zip에는 예시 데이터(`data/example_*_v8.*`)와 정답 키(`data/reference/lm_reference_with_ltl.jsonl`)만 있습니다. 저장소 안의 다른 폴더에서 비슷한 파일을 찾아 대신 쓰지 않습니다. 따라서 5단계는 "입력 없음"으로 적고 실행하지 않습니다.

## 7. 6단계 정의 (구간 확장 상한 256)

- 대상 쌍: NuSMV 실행(cap 128)의 기록 중 `nm`이 true이고 `nm_reason`이 `converter_limit`인 쌍. 없으면 6단계는 "대상 없음"으로 적고 실행하지 않습니다.
- 재실행 방법: 판정 CLI에는 쌍을 고르는 옵션이 없고 도구 코드는 바꾸지 않으므로, 대상 쌍이 하나라도 있는 단위만 남긴 units 파일(`PKG/inputs/units_cap256.json`, 항목과 순서는 그대로)을 만들어 같은 CLI를 `--cap 256`으로 실행합니다(`--out ../runs/nusmv_v8_cap256`, 래퍼와 나머지 옵션은 3단계와 같음). 그 단위에 있는 다른 문장의 쌍도 함께 판정되며 따로 보고합니다. 기본 실행(`runs/nusmv_v8`)의 기록은 건드리지 않습니다.
- 비교: 대상 쌍의 `NM:converter_limit`이 어떤 범주로 바뀌는지(판정으로 바뀐 건수, 여전히 N/M인 사유), 대상 쌍의 시간(`elapsed_sec_total`의 합, 평균, 최대, 질의 수, timeout 질의 수)을 두 실행에서 나란히 적습니다. 같은 단위의 다른 쌍은 범주가 달라졌는지만 적습니다. 단계의 벽시계 시간은 로그의 시각입니다.

## 8. 수정 허용 범위의 적용

- 도구 코드 수정은 계획하지 않았습니다. 실행 중 Mac 환경 차이(경로, 권한, 인코딩, Docker 래퍼)로 코드 수정이 불가피하면, 수정 전 파일을 `notes/`에 보관하고 `diff -u`를 보고서 7항에 싣습니다. 판정 로직(질의 방향, 역할 매핑, 정렬 후보 생성, 추상화), 집계 규칙, 패키지 `bench/`는 어떤 경우에도 수정하지 않고, 틀려 보이면 재현 가능한 입력과 두 엔진의 출력을 근거로 보고만 합니다.
- 1단계 시작 시점의 알려진 차이(모두 도구 코드 밖에서 처리): 패키지 `.gitignore`, `Makefile`의 `PY`는 명령행 변수로 넘김, `sha256sum`은 macOS 기본 명령(`/sbin/sha256sum`)이 동작함, GNU make 3.81, 시스템 python 3.9.6은 요구에 미달해 venv로 대체.

## 9. 보고

- 최종 보고는 지시문의 형식(1 환경, 2 자기점검, 3 교차표와 불일치, 4 N/M와 UND 사유와 시간, 5 순서 가설, 6 본 데이터와 cap 256, 7 수정 diff, 8 확인하지 못한 항목)을 따르는 `EXP/bench/REPORT.md`로 쓰고, 마지막 절에 지시문과 다르게 한 점과 그 이유를 모두 적습니다.
- 산출물은 `PKG/runs/` 아래(`selfcheck/selfcheck.json`, `nusmv_v8/run_header.json`, `nusmv_v8/judge_records.jsonl`, `nusmv_v8/aggregate.json`, `z3_v8/...`, `compare/`, `order_check/`, `cap256/`, `nusmv_v8_cap256/`)에 두고, 전달 zip(`EXP/zips/nl2fret_tool_mac.zip`)에 넣습니다. `work/` 폴더(실행용 SMV 사본)는 `smv/`와 내용이 같아 zip에서 뺍니다.
- 저장소의 추적 문서(README, STRUCTURE, 각 INDEX, UNVERIFIED)는 이번 실행에서 수정하지 않습니다(이전 실행에서 한 추가에 대한 사용자 결정이 아직 없음).
