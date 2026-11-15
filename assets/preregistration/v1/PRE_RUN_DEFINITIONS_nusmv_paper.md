# PRE_RUN_DEFINITIONS: 실행 전에 고정한 보충 정의

이 파일은 판정 스크립트(`run_steps.py`)를 돌리기 전에 작성하고 해시(`../../notes/PRE_RUN.sha256`)로 고정했습니다. 실행 중과 실행 후에는 고치지 않습니다. 지시문(`../../docs/NL2FRET_NUSMV_PAPER.md`)이 정하지 않았거나 이 머신에 없는 자료 때문에 해석이 필요한 부분만 적었습니다.

정의를 정하기 전에 이미 관측한 것 (숨기지 않기 위해 적음):
- 저장된 자료만 읽어 본 것: `pairs.jsonl`의 구성(통제 512, 생성 98), `pairs_out.jsonl`의 기존 NuSMV 결과와 저장된 judge4 값이 miss 또는 alarm에서 다른 쌍이 47개(통제 `response_always` 44, 생성 3)라는 것.
- 손으로 쓴 작은 SMV 파일(probes의 A부터 E)을 NuSMV에 넣어 본 것: 4개의 LTLSPEC를 선언 순서 S1, S2, S3, S4로 썼을 때 NuSMV가 S3, S4, S1, S2 순서로 출력한 것을 관측함. 이 원문은 `probes/`에 `run_all.sh`의 첫 단계에서 다시 저장됩니다.

## 1. 위치와 이름
- 지시문이 가리키는 `bench/`는 이 저장소 규약(`experiments/<실행>/bench/`)에 따라 `experiments/nusmv_paper/bench/`로 두고, 지시문의 새 폴더 `nusmv_paper/`는 그 아래(`bench/nusmv_paper/`)에 만들었습니다. 전달 zip의 최상위 폴더 이름은 지시문대로 `nusmv_paper`입니다.
- 지시문 사본은 `docs/NL2FRET_NUSMV_PAPER.md`(루트 `testnote.md`와 바이트 동일, sha256 565a8dc6...). 기존 파일은 수정하지 않았고, 기존 변환기는 `vendor/ltl_engines.py`로 복사해 썼습니다(원본과 sha256 동일).

## 2. 4.A 취득 방법
- 이 저장소의 작업 원칙(git 명령 사용 안 함)에 따라 `git clone` 대신 GitHub API의 tarball을 HTTP로 받아 풀었습니다. 파일 149개의 git blob SHA-1을 순수 파이썬으로 계산해 GitHub 트리와 비교했습니다. 저장소의 코드와 바이너리는 실행하지 않았습니다.

## 3. 질의와 N/M 정의 (4.C)
- 질의 형식은 기존 경로(`vendor/ltl_engines.py` 196줄)와 같은 형태입니다. 질의마다 SMV 파일 1개와 NuSMV 프로세스 1개를 씁니다.
  - Equiv: `G ((GT) <-> (Pred))`
  - Sound (GT => Pred): `G ((GT) -> (Pred))`
  - Compl (Pred => GT): `G ((Pred) -> (GT))`
- 역할 이름은 기존 `role_of`(212줄)와 같게 (Sound, Compl)에서 유도합니다: 둘 다 성립 SAME, Compl만 PROOF, Sound만 REFUTE, 둘 다 불성립 NEITHER. N/M 쌍은 역할이 없습니다.
- N/M(`nm=true`)은 다음 중 하나입니다: 식이 파싱되지 않음(`syntax`), 변환기 한도 초과(`converter limit`, 창 상한 128 초과 포함), 질의 시간 초과(`timeout`, 질의당 120초이며 기존 실행의 `--timeout 120`과 같은 값), NuSMV가 판정 하나를 출력하지 않음(`nusmv output`). 한 질의가 시간 초과하면 그 쌍의 남은 질의는 실행하지 않습니다(어차피 N/M이므로). 원인은 `nm_reason`에 문자열로 남깁니다.
- 지시문의 "AP 불일치로 검사 실패"에 해당하는 조건은 기존 변환기에는 없습니다: 변환기는 두 식의 원자 합집합을 VAR로 선언합니다(`vendor/ltl_engines.py` 195줄).
- 4.C 자가 점검 5쌍은 변환기의 입력 문법(완전 괄호식, `!`와 `|` 연산자)으로 옮겨 입력합니다. 지시문 표의 논리 내용은 같고 표기만 다릅니다. 새 변환 규칙은 만들지 않았습니다.

## 4. D1과 D2
- D1은 `pairs.jsonl`의 `source=ctl` 512쌍입니다. GT는 `ref_pt`, Pred는 `gen_pt`, 기대 역할은 저장된 `expected`를 그대로 씁니다. 지시문의 "문서 기준 517건"과 "상수 변형 88건"은 이 머신의 데이터와 다르며(변이 `rename_all`이 42쌍, 상수 변형 데이터 없음) 없는 쌍은 만들지 않습니다.
- judge4(anchor 모드)의 일치 수는 저장된 `z3_role == expected`의 개수입니다. judge4.py가 없어 judge4를 새로 돌리지 않습니다.
- "기대와 일치"는 paper_judge 역할이 기대 역할과 같은 쌍의 수이며, N/M 쌍은 일치로 세지 않습니다. "불일치(잘못된 방향)"는 N/M이 아니면서 역할이 기대와 다른 쌍의 수입니다. N/M은 별도 열입니다.
- D2는 `source=d8` 98쌍이며 judge4는 저장된 `z3_role`입니다. 저장된 값이 anchor 모드인지 이름 고정 모드인지는 데이터에 기록이 없습니다(`vendor/ltl_engines.py` 364줄의 보고 라벨은 anchor mode). 일치는 역할 문자열이 같은 경우이며 N/M은 일치와 불일치 어디에도 넣지 않고 따로 셉니다.

## 5. D3 (문서 5절 목록이 이 머신에 없음)
- `NL2FRET_ltl_engines_results.md`가 없어 45쌍 목록을 찾지 못했습니다. 지시문의 대체 규칙("NuSMV와 judge4가 다른 쌍 전체")을 다음처럼 적용합니다: 기존 실행 결과(`pairs_out.jsonl`)에 NuSMV 결과가 있고(오류 아님) 저장된 judge4와 miss 또는 alarm이 다른 쌍 전체. 지시문은 "D1에서"라고 했지만 문서의 45쌍이 "z3와 miss, gen_sat 판정이 다른 쌍"이라는 기존 경로의 어긋남이므로 기존 경로 기준으로 잡았고, 통제 쌍(D1)과 생성 쌍(D2) 모두를 포함하되 D1 한정 개수를 따로 적습니다.
- "GT에 선언된 원자"는 `ref_pt`의 불리언 추상화 원자(산술 비교 하나가 원자 하나), "Pred가 실제로 쓰는 원자"는 `gen_pt`의 원자입니다. 차집합은 GT-Pred와 Pred-GT 두 방향 모두 기록합니다.
- "어긋난 항목 이름"은 miss와 alarm 중 기존 NuSMV와 judge4의 값이 다른 것입니다. judge4의 gen_sat은 저장되어 있지 않아 비교할 수 없습니다.

## 6. D4
- 패딩(`pad`): 두 식의 원자 합집합을 VAR로 명시 선언합니다(사용되지 않는 원자는 제약 없음). 기존 변환기도 합집합만 선언하므로(195줄) 이 자료에서는 SMV 텍스트가 같은지를 쌍마다 파일 이름(내용 해시)으로 확인해 적습니다.
- 창 경계: 변환기 `to_smv`의 `cap` 인자를 32, 64로 바꿉니다. 128은 기본 설정이므로 D1과 D2 결과를 재사용합니다(SMV 텍스트가 같음).
- z3 길이(horizon 8, 16, 32): judge4.py가 없어 건너뜁니다.
- 분류(기본 설정 = paper_judge 기본 판정 b, judge4 판정 j, 변형 판정 v, N/M은 None): 불변은 v == b, 해소는 v != b 이면서 v == j, 새로 어긋남은 v != b, v != j, b == j, 기타는 v != b, v != j, b != j.
- C5는 D3 쌍 중 설정 w128(기본), pad, w32, w64 중 하나 이상에서 judge4와 일치한 쌍 수이고, 그중 기본 설정에서만 일치한 쌍 수를 병기합니다. C6은 어느 설정에서도 일치하지 않은 쌍입니다.

## 7. 추가 관측 X1 (지시문에 없음, 벗어난 점으로 보고)
- 목적: 기존 실행이 저장한 값 4개(miss, alarm, gen_sat, gen_valid)를 단일 질의로 다시 얻은 값과 비교합니다. 기존 `smv_roles`가 한 파일에 4개의 LTLSPEC를 넣고 결과를 선언 순서로 배정하기 때문입니다(`vendor/ltl_engines.py` 189-197줄).
- 기존 NuSMV 결과가 있는 쌍 전체에 대해 `G (! (gen))`과 `G (gen)`을 단일 질의로 추가 실행합니다(기존 호출의 3번째와 4번째 스펙에 해당). 나머지 두 스펙의 단일 질의 값은 D1과 D2의 compl, sound를 씁니다.
- D3 쌍에서는 원래의 4-스펙 파일을 1회 실행해 NuSMV가 출력한 순서를 기록합니다.
- 이 단계는 판정 기준이나 코드를 바꿔 다시 돌리는 것이 아니라 이미 저장된 값과 단일 질의 값을 대조하는 별도 관측입니다.
