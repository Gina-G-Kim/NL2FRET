# PRE_RUN_DEFINITIONS: nl2fret_tool 패치 v1.1 실행 (2026-11-10)

이 문서는 코드를 고치기 전에 쓴다. 비교와 시험에 쓰는 스크립트는 해당 단계를 실행하기 전에 해시를 고정하고(`notes/PIN_*.sha256`), 결과를 본 뒤 이 문서의 정의와 스크립트를 바꾸지 않는다. 바꿔야 하면 바꾼 이유와 시각을 `notes/CHANGELOG.md`에 남기고 보고서에 적는다.

## 1. 범위와 원칙

- 지시문: `docs/NL2FRET_TOOL_PATCH_V11.md` (사본, `notes/INSTRUCTION.sha256`). 금지 사항, 수정 허용 파일, 최종 보고 형식은 지시문을 따른다.
- 이 저장소의 원칙을 지시문의 경로나 명령보다 우선한다: git 명령을 쓰지 않는다, 판정 의미를 바꾸지 않는다, 결과를 보정하거나 쌍을 제외하지 않는다, 각 단계는 1회 실행하고 중단 재개만 허용한다, 관측만 적고 결론을 내리지 않는다, 확인하지 못한 것은 "확인하지 못함"으로 적는다.
- CPU: 컨테이너 1개(`--cpus=1`), NuSMV 질의는 한 번에 하나, 호스트 쪽 모든 명령은 `nice -n 10`과 최소 환경(`scripts/cleanenv.sh`), 끝나면 컨테이너와 프로세스를 남기지 않는다.
- 수정 전 기준 상태
  - (가) 압축 해제 직후의 v1.0.0 패키지: `bench/pristine/nl2fret_tool/`(읽기 전용), 모든 파일 해시는 `notes/PKG_V10_FILES.sha256`(70개).
  - (나) 비교 기준 기록: 이전 실행(`experiments/nl2fret_tool_mac`)의 `runs/nusmv_v8`, `runs/z3_v8`을 `inputs/baseline_v10/`에 복사했다(`notes/BASELINE_V10.sha256`). 이전 전달 zip 안의 같은 파일과 sha256이 일치함을 확인했다. 지시문 사전 준비 2의 "이전 기록이 있으면 비교 기준으로 쓴다"에 해당하므로 수정 전 코드로 새 기록을 만들지 않는다.
- 환경 선택
  - `requirements.txt`는 버전을 고정하지 않는다. 오늘 `pip install -r requirements.txt`는 z3-solver 5.4.0.0을 설치했고, 이전 실행(기준 기록)은 5.3.3.0이었다. z3 비교에 버전 변경이 섞이지 않도록 venv의 z3-solver를 5.3.3.0으로 맞춘다(`logs/step0_6_pin_z3.log`). `requirements.txt` 자체는 수정 허용 파일이 아니므로 고치지 않는다.
  - NuSMV 2.6.0은 Docker 이미지 `cst-nusmv:local`(Colima)을 래퍼 `scripts/bin/NuSMV`로 부른다. 래퍼는 상대 경로를 절대 경로로 바꾸고, 컨테이너 안 timeout을 도구의 timeout보다 5초 길게 둔다. 이전 실행과 같은 이미지, 같은 `--cpus=1`.

## 2. 변경 범위

- 수정 대상으로 예상하는 파일: `judging/nl2fret_judge/__init__.py`(버전), `judge.py`(수정 1, 수정 2), `recorder.py`(수정 3), `cli.py`(수정 2의 헤더), `aggregate.py`(수정 3의 읽기). 다른 `judging/nl2fret_judge/` 파일(`align.py`, `engines.py`, `abstraction.py`, `ltl_engines.py`, `ap_check.py`, `selfcheck.py`, `units.py`)은 판정 로직이므로 바꾸지 않는다.
- 새 파일: `tests/test_patch_v11.py`(기존 `tests/test_judge.py`는 그대로), 패키지 루트의 `CHANGELOG.md`(지시문 최종 보고 8번이 요구한다. 수정 허용 목록에는 없으므로 새 파일로 추가하고 보고서에 적는다).
- 문서: `docs/DESIGN.md`(부록 A에 v1.1.0 절 추가. 2절 표 S6 행의 "대응 불가는 N/M"이 부록 A와 수정 1의 UND 규칙과 어긋나서 한 칸만 UND로 정정한다. 이 정정은 지시문에 명시되지 않은 추가 수정이며 보고서에 따로 적는다), `docs/RUNBOOK.md`(재개와 기록물 설명), `README.md`(버전, 변경 이력 안내).
- 고치지 않는 것: `bench/`, `judging/legacy/`, `Makefile`, `requirements.txt`, `data/`.

## 3. 구현 규칙

수정 1 (정렬 후보 없음 = UND)
- `judge_pair`에서 `align.candidates`가 `maps == []`를 돌려주면 `role="UND"`, `und_reason="atomization_mismatch"`, `nm_detail={"message": "no injective renaming candidate"}`, `nm=False`로 기록하고 질의 없이 끝낸다. `alignment`의 `n_candidates`(0)와 `anchored`는 그대로 남기고, `ap_check`는 기존 UND 분기와 같이 `ap_check(None, None)`.
- 후보가 있었으나 모든 후보의 `_prepare`가 실패한 경우는 기존대로 첫 실패의 사유(`converter_limit` 또는 `syntax`)로 N/M. 기존의 "no candidate" 폴백(`other`)은 도달할 수 없게 되지만 방어용으로 남기고 주석을 단다.
- `align.py`의 후보 구성은 바꾸지 않는다. `RANK`와 최선 선택 규칙은 바꾸지 않는다. UND 역할은 이미 `RANK`에 없어서 순위 4로 처리되므로, 이전에 N/M(순위 3)이던 "후보 없음" 시도는 여러 참조 부분이 있을 때 순위가 3에서 4로 바뀐다. 이것은 규칙 변경이 아니라 역할 변경의 결과이며, 이번 입력에서 영향을 받는 쌍이 있는지는 회귀 비교로 확인한다.

수정 2 (재현 기록)
- 헤더 `inputs`에 `rlz`(`--rlz` 파일의 sha256, 없으면 null)를 추가한다.
- `best_over_references`는 시도한 모든 참조 부분(SAME에서 멈추므로 실제로 시도한 부분만)에 대해 `reference_trials`를 선택된 기록에 붙인다. 항목: `reference_part`, `role`, `nm`, `nm_reason`, `und_reason`, `n_queries`, `smv_sha256`(질의 순서대로 목록), `queries`(질의 요약: `kind`, `verdict`, `elapsed_sec`). 선택된 시도도 같은 형식으로 목록에 들어간다. 질의 원문 출력(stdout, stderr, cmd)은 선택된 기록의 `queries`에만 둔다.
- 선택되지 않은 시도의 SMV 파일은 `_smv`를 병합해서 `smv/`에 저장한다.

수정 3 (재개)
- 먼저 v1.0.0 코드에서 시험해서 (나)가 깨지는지 본다. 깨지면 `Recorder`가 시작할 때 `judge_records.jsonl`의 마지막 불완전 줄(마지막 개행 뒤에 남은, 완전한 JSON 기록이 아닌 바이트)을 버리고, 버린 바이트는 `judge_records.discarded_tail.txt`에 덧붙여 보존한 뒤 해당 쌍을 다시 판정한다. 완전한 JSON이지만 개행만 없는 마지막 줄은 개행을 붙여 유지한다. `aggregate`의 읽기는 같은 불완전 마지막 줄을 경고하고 건너뛴다(파일을 고치지 않는다). 가운데 줄의 손상은 지금처럼 오류로 둔다.
- SMV 파일 쓰기의 원자성(빈 파일이 해시 이름으로 남는 경우)은 이번 범위가 아니다. 고치지 않고 보고서의 미확인 항목에 적는다.

## 4. 회귀 비교의 정의 (NuSMV와 z3 공통)

기준 기록과 새 기록을 `pair_id`로 맞춘다. 두 쪽의 `pair_id` 집합이 같아야 한다(252개).

- 비교에서 제외하는 필드(환경 또는 비결정): 기록의 `elapsed_sec_total`, 질의의 `elapsed_sec`, 질의의 `cmd`(래퍼와 SMV 경로가 실행 폴더에 따라 다르다).
- 새 필드: 새 기록의 `reference_trials`는 비교에서 빼고 5절의 별도 점검을 한다.
- 예상 차이: 기준 기록에서 `nm_reason == "other"`이고 `nm_detail.message == "no candidate"`인 쌍(6쌍으로 예상). 이 쌍들의 필드 차이는 정확히 다음 다섯 개여야 한다: `role` None에서 "UND", `nm` True에서 False, `nm_reason` "other"에서 None, `nm_detail` `{"message": "no candidate"}`에서 `{"message": "no injective renaming candidate"}`, `und_reason` None에서 "atomization_mismatch".
- 예상하지 않은 차이: 위 예상 차이가 아닌 모든 필드 차이.
  - 등급 A (중단 기준): `role`, `nm`, `nm_reason`, `und_reason`, `equiv`, `sound`, `compl`, `alignment`(전 필드), `atoms_gt`, `atoms_pred`, `atoms_union`, `atom_abstraction`, `reference_part`, 질의의 `kind`, `spec_text`, `smv_sha256`, `verdict`, 질의 수. 등급 A의 예상하지 않은 차이가 하나라도 있으면 이후 단계를 중단하고 차이 전체를 보고한다.
  - 등급 B (보고만): 그 밖의 필드(`stdout`, `stderr`, `exit_code`, `timed_out`, `reason`, `ap_check`, `nm_detail`, `executed`, `query_mode`, 식 필드 등). 표로 보고하고 진행한다.
- NuSMV의 timeout 쌍 9개가 이번 실행에서 판정되거나 반대로 기준에서 판정된 쌍이 timeout이 되면 그것은 `role`/`nm_reason`의 차이이므로 등급 A로 센다.
- `smv/`(NuSMV): 기준의 파일 이름 798개가 모두 새 `smv/`에 있어야 한다. 새 파일은 선택되지 않은 시도의 SMV여야 하며 `reference_trials`로 설명되는지 확인한다.
- 헤더: 키별로 비교해서 차이를 모두 적는다. 예상: `version` 1.0.0에서 1.1.0, `started_at`, `inputs.rlz` 추가(값은 `inputs/fret_realizability_gen.jsonl`의 sha256과 같아야 한다). 이 밖의 차이는 보고한다.

## 5. 새 필드 점검 (`reference_trials`)

- 모든 새 기록에 `reference_trials`가 있고 목록이며 비어 있지 않다. 항목의 키는 3절의 여덟 개.
- 선택된 `reference_part`에 해당하는 항목의 `role`, `nm`, `nm_reason`, `und_reason`이 기록의 값과 같고 `n_queries`가 기록의 `len(queries)`와 같다.
- 항목마다 `n_queries == len(queries) == len(smv_sha256)`(NuSMV). z3 엔진은 SMV가 없어서 `smv_sha256` 목록이 비어 있다.
- 항목 순서는 참조 부분 순서이고, 항목 수는 SAME에서 멈추는 규칙과 맞는다(마지막 항목 이전의 항목에 SAME이 없다).
- 기준 기록과의 `reference_part` 일치는 4절 등급 A로 이미 본다(선택 규칙이 바뀌지 않았다는 확인).

## 6. 재개 시험의 정의 (수정 3)

- 입력: `inputs/example_units_v8.json`의 단위를 파일 순서대로 보면서, 기준 NuSMV 기록에 timeout 쌍이 들어 있는 단위는 건너뛰고, 고른 단위의 기준 기록 수가 20 이상이 되는 첫 단위까지 모은다. 결과는 `inputs/resume_units.json`(단위 항목은 원본 그대로). 문장별 LTL과 실현가능성은 예시 전체 파일을 그대로 쓴다.
- 절차(코드 버전마다 한 번씩, 먼저 v1.0.0 복사본, 다음에 패치본): (1) 중단 없이 한 번에 `full/`, (2) 같은 명령을 시작해서 기록이 8줄 이상 되는 순간 프로세스 그룹에 SIGKILL(`a/`), (3) 죽은 직후의 상태를 `b/`로 복사하고 마지막 완전한 줄의 뒷부분을 잘라서(줄 길이의 절반 지점에서 파일을 자른다) 반쯤 쓰인 줄을 만든다(실제 강제 종료만으로는 끊긴 줄이 생기지 않을 수 있으므로 시험을 위한 모의 상태이며 보고서에 모의라고 적는다), (4) `a/`와 `b/`에서 같은 `make judge` 명령으로 재개. 세 폴더의 마지막 디렉터리 이름은 같아서 `run_id`가 같다.
- 확인 항목
  - (가) 이미 기록된 쌍을 건너뜀: 재개 전 완전한 줄의 바이트가 재개 후 파일의 앞부분과 같다, `pair_id` 중복이 없다, 새로 쓰인 `pair_id`는 입력 전체에서 재개 전 완전한 기록을 뺀 집합과 같다. 참고로 래퍼 호출 수 로그를 남긴다(`NUSMV_CALL_LOG`).
  - (나) 반쯤 쓰인 줄: 재개 전 `aggregate`가 읽기에 성공하는지, `Recorder`가 시작에서 예외를 내는지, 재개 후 파일의 모든 줄이 엄격한 JSON으로 읽히는지, 끊긴 줄의 쌍이 정확히 한 번 온전한 기록으로 들어 있는지, 재개 후 `aggregate`가 성공하는지.
  - (다) 최종 기록이 `full/`과 같음: 4절의 비교 규칙(`reference_trials`는 같은 코드 버전이므로 포함해서 비교), `pair_id` 순서까지, 헤더(`started_at` 제외), `smv/` 파일 이름 집합.

## 7. timeout 민감도 실험의 정의

- 대상: 기준 NuSMV 기록에서 `nm_reason == "timeout"`인 9쌍(`LM-03_REG-N01` 2쌍, `LM-03_REG-N02` 7쌍으로 예상). 9쌍은 모두 문장이 하나인 단위의 0번 문장이므로 단위 항목을 그대로 가져온 `inputs/timeout_units.json`이 9쌍만 담는다. 원본 단위 항목과 같은지 스크립트가 확인한다.
- 실행: 패치본(최종 코드), `--timeout 600`, 컨테이너 안 timeout 605초, 기본 timeout 값은 바꾸지 않는다, 출력은 `runs/timeout600/`(기본 실행 `runs/nusmv_v8`과 다름), 한 번만 실행하고 중단되면 같은 명령으로 재개한다.
- 보고: 쌍마다 판정 여부, 역할, 소요 시간(기록의 `elapsed_sec_total`), 질의 수, 질의별 종류와 시간, 600초에도 timeout인 쌍 수. 기본값 변경은 제안하지 않는다.
- 패치본으로 실행하는 이유(실행자의 선택): 결과가 전달하는 v1.1.0 코드의 동작이 되고 `reference_trials`로 참조 부분별 시간이 남는다. 이 9쌍은 수정 1(후보 없음)의 대상이 아니다.

## 8. 집계 비교의 정의 (회귀 검증 6)

- NuSMV: 새 실행에 `make aggregate`를 하고 기준 `aggregate.json`과 비교한다. `by_arm`, `by_stratum`은 완전히 같아야 한다. `pair_outcomes`는 `UND:atomization_mismatch`가 6 늘고 `NM:other`가 6 줄어(키가 사라짐) 있어야 하며 나머지 항목은 같아야 한다.
- z3: 기준 z3 기록에는 집계가 없으므로 v1.0.0 코드(`bench/v10_exec`)로 기준 기록에서 집계를 만든 뒤(기준 코드, 기준 기록) 새 z3 실행의 집계와 같은 규칙으로 비교한다.
- 추가: 패치본의 `aggregate`를 기준 NuSMV 기록에 돌려서 기준 `aggregate.json`과 같은지 확인한다(집계 코드의 읽기 경로를 고쳤으므로).

## 9. 해시 고정과 확인

- 코드 수정이 끝나고 `make test`가 통과한 직후, 검증 실행 전에 패치본 전체 파일 해시를 `notes/PKG_PATCHED.sha256`에 고정한다. 실행이 끝난 뒤 `judging/`, `tests/`, `Makefile`, `bench/`, `data/`가 고정 시점과 같은지 다시 확인한다. 문서(`README.md`, `docs/`, `CHANGELOG.md`)는 검증 결과를 반영해 실행 후에 고칠 수 있고, 고치면 해시 변경 목록에 적는다.
- `make freeze-check`는 수정 전(`step0_3`), 패치 후, 모든 실행 후에 실행한다. `bench/`와 `judging/legacy/`의 해시는 `notes/PKG_V10_FILES.sha256`과 대조한다.

## 10. 보고서

- `bench/REPORT.md`(한국어)에 지시문의 최종 보고 형식 1~8을 순서대로 쓰고, 마지막 절에 지시문과 다르게 한 점과 추가한 점을 모은다. 새 패키지 zip은 `zips/nl2fret_tool_v1.1.zip`, 증거 묶음은 `zips/nl2fret_tool_v11_evidence.zip`.
