# 프롬프트: nl2fret_tool v1.2 최종 패치와 동결 (도구 완성용)

아래 전체를 Mac의 LLM 에이전트에게 `nl2fret_tool_v1.1.zip`과 함께 전달한다. 이 작업이 끝나면 도구는 완성 상태(동결)이고, 이후에는 코드를 바꾸지 않고 실험만 돌린다.

---

너는 연구 도구 패키지의 마지막 패치와 동결을 하는 에이전트다. 확인하지 못한 것은 "확인하지 못함"으로 적고, 추측으로 채우지 마라. 이모지와 em dash는 쓰지 마라. 결정이 필요한 곳은 아래에 이미 정해 두었으니 되묻지 말고 그대로 따라라.

## 금지 사항
- `bench/`와 `judging/legacy/`는 수정하지 마라 (`make freeze-check`가 전후 OK여야 한다).
- 판정 의미(질의 방향, 역할 매핑, 추상화, 정렬 후보 규칙, AP 규칙)를 바꾸지 마라.
- `git init`, 커밋, push 금지. 결과 보정이나 쌍 제외 금지.
- 수정 허용 파일: `judging/nl2fret_judge/` 아래 파일, `tests/` 아래 파일(새 파일 포함), `docs/`, `README.md`, `CHANGELOG.md`, `Makefile`, `requirements.txt`, 새로 만드는 `JUDGE_FROZEN_MANIFEST.sha256`. 버전은 `1.2.0`.

## 사전 준비
1. zip을 새 폴더에 풀고 `make freeze-check`, `make test`(20 passed 기대)를 실행한다. 모든 파일 해시를 기록한다.
2. 기준 기록으로 v1.1 코드의 NuSMV 판정 기록(`runs/nusmv_v8/judge_records.jsonl`)이 있으면 쓰고, 없으면 v1.1 코드로 v8 예시 252쌍을 한 번 돌려 둔다.
3. `requirements.txt`는 `z3-solver==5.3.3.0`, `pytest`는 지금 설치된 버전으로 고정하고 `pip freeze` 결과를 기록한다.

## 패치 1: 코드 해시와 SMV 템플릿 식별자를 헤더에 기록
- `run_header.json`에 추가한다.
  - `code_sha256`: `judging/nl2fret_judge/*.py`와 `judging/legacy/*.py` 각 파일의 sha256 (파일명 오름차순 목록으로 기록)과, 그 목록 전체를 이어 계산한 `code_tree_sha256` 하나.
  - `smv_template_id`: SMV 파일 구조 식별자 문자열 `"single_ltlspec_v1"`와, 질의식 정의(`equiv`, `sound`, `compl`, `sat`, `valid`)를 `spec_text`가 만든 문자열 그대로 담은 `query_templates` 객체 (자리표시자 `GS`, `RS`로 만든 식).
  - `python_version`, `z3_version`(설치되어 있으면)도 추가한다.
- `docs/DESIGN.md` 7절 표의 설명이 코드와 일치하는지 확인하고, 일치하지 않는 부분은 문서를 고친다. 문서에 있는데 코드에 없는 항목은 만들거나(위 항목) 문서에서 지운다. 어느 쪽으로 처리했는지 보고한다.

## 패치 2: 코드 동결 장치
- `make release`: `judging/nl2fret_judge/*.py`와 `judging/legacy/*.py`의 sha256을 `JUDGE_FROZEN_MANIFEST.sha256`로 쓴다 (한 번 만들면 덮어쓰지 않는다. 이미 있으면 거부).
- `judge` 서브커맨드가 시작할 때 매니페스트가 있으면 현재 코드와 대조해, 하나라도 다르면 실행을 거부한다. 우회 옵션은 `--allow-unfrozen`이며, 이 옵션을 쓰면 헤더에 `frozen: false`를 기록한다. 매니페스트가 일치하면 헤더에 `frozen: true`와 매니페스트 해시를 기록한다.
- 테스트 추가: 일치할 때 통과, 파일을 바꿨을 때 거부, `--allow-unfrozen`에서 헤더 기록.
- `make release`는 이 작업의 마지막 단계에서 한 번만 실행한다.

## 패치 3: 선택 순위 명시 (동작 불변)
- `judge.RANK`를 `{"SAME": 0, "PROOF": 1, "REFUTE": 1, "NEITHER": 2, "N/M": 3, "UND": 4}`로 명시하고, `best_over_references`가 N/M은 `nm`이 true인 기록, UND는 `role == "UND"`인 기록으로 순위를 매기게 한다. 현재 동작(N/M 3, UND 4)과 같아야 하며, 의도를 `docs/DESIGN.md`에 한 줄로 적는다. 테스트로 "참조 부분이 여럿일 때 UND보다 N/M이, N/M보다 NEITHER가 선택됨"을 확인한다.

## 패치 4: 본 데이터 입력 준비 확인
1. 저장소에서 61개 Lockheed Martin 항목의 실제 입력 3개(`units.json`, `fret_ltl_gen.jsonl`, `fret_realizability_gen.jsonl`)가 있는지 찾는다. 후보 위치는 이전 `bench` 실행 결과 폴더(`results*/`, `rq/` 등)이다. 비슷한 이름의 파일을 임의로 대체해 쓰지 말고, 형식(`data/example_*` 파일과 같은 키)이 맞는 것만 인정한다.
2. 찾으면 `inputs/`에 복사하지 말고 경로, 단위 수, 항목 수, 방식(arm) 목록, 문장 수, `stratum` 유무를 표로 보고한다. 없으면 "없음"으로 적고, 만들려면 어떤 `bench` 명령이 필요한지 `bench/` 문서에서 확인해 적는다 (실행은 하지 않는다).
3. `units.json`에 `stratum`이 없으면 `by_stratum`이 비므로, 항목-계층 대응 표(`data/`에 있는지)를 확인해 보고만 한다.

## 회귀 검증 (코드 동결 전)
1. `make test` 통과 (기존 20개 + 신규).
2. NuSMV `selfcheck`: 5쌍 PASS.
3. v8 예시 252쌍을 NuSMV와 z3로 다시 실행해 v1.1 기록과 `pair_id`로 비교한다. 허용 차이는 헤더의 새 필드뿐이며, 역할, 정렬 사상, 원자, 질의 판정이 하나라도 다르면 중단하고 보고한다. timeout 9쌍은 그대로여야 한다 (120초).
4. `make aggregate` 단위 결과가 v1.1과 같아야 한다 (NuSMV 52/16/54/94).
5. `make freeze-check` OK, `bench/`와 `legacy/` 해시 불변.

## 동결과 전달
1. 회귀 검증이 모두 끝난 뒤 `make release`를 한 번 실행하고, 이후 `make judge`가 매니페스트 대조를 통과하는지 소규모(약 10쌍)로 확인한다. 이 확인 실행은 `frozen: true`로 헤더에 남아야 한다.
2. `CHANGELOG.md`에 v1.2.0 항목(패치 1~3, 동결 장치, 근거)을 추가하고, `README.md`와 `docs/RUNBOOK.md`에 "동결 후 실행 절차"를 추가한다. 실행 절차에는 (가) 입력 3개 준비, (나) `make selfcheck`, (다) `make judge`, (라) `make aggregate`, (마) 재개 방법, (바) 코드를 바꾸지 말 것을 적는다.
3. `nl2fret_tool_v1.2.zip`을 만들고 경로와 sha256을 보고한다. 압축에는 `venv/`, `runs/`, `work/`, 캐시를 넣지 않는다.

## 최종 보고 형식
1. 수정한 파일별 diff 전문
2. 패치 1: 헤더 예시 1건 (전체), DESIGN 7절 처리 결과
3. 패치 2: 매니페스트 일치, 불일치 거부, 우회 옵션 시험 결과
4. 패치 3: 순위 테스트 결과
5. 패치 4: 본 데이터 입력 발견 여부와 표
6. 회귀 검증 결과 (차이 목록 전체)
7. 확인하지 못한 항목과 이유
8. `nl2fret_tool_v1.2.zip` 경로, sha256, `JUDGE_FROZEN_MANIFEST.sha256`의 해시
