# CHANGELOG

## 1.2.0 (2026-11-11)

판정 코드를 동결하는 릴리스다. 판정 로직의 의미(질의 방향, 역할 대응, 불리언 추상화, 별칭 규칙, 정렬 후보 구성 규칙, AP 규칙, 최선 선택 규칙)는 바꾸지 않았다. 같은 입력(v8 예시 252쌍)에서 v1.1.0 기록과 모든 쌍의 모든 필드(시간과 질의 명령줄 제외)가 같다.

- 수정한 코드: `judging/nl2fret_judge/`의 `__init__.py`(버전), `cli.py`, `judge.py`, `engines.py`(상수 한 줄과 설명 주석 두 줄). 새 모듈 `freeze.py`.
- 수정한 설정과 문서: `Makefile`(`release` 대상, `JUDGE_ARGS`), `requirements.txt`(버전 고정), `README.md`, `docs/DESIGN.md`(7절 표를 코드와 일치시킴, 부록 A-3 추가), `docs/RUNBOOK.md`("동결 후 실행 절차").
- 새 파일: `judging/nl2fret_judge/freeze.py`, `tests/test_patch_v12.py`, `JUDGE_FROZEN_MANIFEST.sha256`(마지막 단계에서 `make release`로 한 번 생성). 기존 테스트 `tests/test_patch_v11.py`는 버전 단언 두 줄만 바꾸었다.
- 수정하지 않은 것: `bench/`, `judging/legacy/`, `data/`, `judging/nl2fret_judge/`의 나머지 파일(`align.py`, `abstraction.py`, `ltl_engines.py`, `ap_check.py`, `selfcheck.py`, `units.py`, `aggregate.py`, `recorder.py`). `make freeze-check`는 수정 전후 모두 OK다.

근거에 쓴 "기준 실행"은 v1.1.0으로 v8 예시 252쌍을 NuSMV 2.6.0(Docker, Colima)과 z3(horizon 8)로 판정한 2026-11-10의 Mac 실행이다(v1.1 패치 실행, `runs/nusmv_v8`, `runs/z3_v8`).

### 패치 1. 헤더에 코드 해시와 SMV 템플릿 식별자 (`cli.py`, `freeze.py`, `engines.py`)

- 증상: `docs/DESIGN.md` 7절 표는 헤더 항목으로 "변환기와 판정 코드의 sha256"과 "SMV 템플릿 식별자"를 적었으나 코드는 쓰지 않았다(v1.1.0 부록 A-2의 알려진 한계). 어느 코드와 어느 SMV 구조로 만든 기록인지 헤더만으로는 확인할 수 없었다.
- 변경: `run_header.json`에 `python_version`, `z3_version`, `code_sha256`(`judging/nl2fret_judge/*.py`와 `judging/legacy/*.py` 각 파일의 sha256, 경로 오름차순 목록), `code_tree_sha256`(그 목록을 `<sha256>  <경로>` 줄로 이은 텍스트의 sha256), `smv_template_id`(`single_ltlspec_v1`), `query_templates`(`spec_text(kind, "GS", "RS")`가 만든 다섯 식)를 추가했다. 문서에서 지우지 않고 코드에 만들었다. DESIGN 7절 표는 코드가 쓰는 모든 헤더, 기록, 질의 필드를 담도록 고쳤고, 표와 코드가 어긋나면 실패하는 테스트가 있다.
- 기존 `python` 필드는 호환을 위해 남겼다(`python_version`과 같은 값). `z3_version`은 설치된 `z3-solver` 배포판 버전이다.

### 패치 2. 코드 동결 장치 (`freeze.py`, `cli.py`, `Makefile`)

- `make release`는 위 코드 파일의 sha256을 `JUDGE_FROZEN_MANIFEST.sha256`에 쓴다(`sha256sum -c` 형식). 한 번만 쓸 수 있고 파일이 있으면 거부한다(종료 코드 2).
- `judge`는 시작할 때(엔진과 출력 폴더를 만들기 전) 매니페스트와 대조한다. 매니페스트가 없으면(릴리스 전) 진행하고 헤더에 `frozen: false`를 기록한다. 일치하면 진행하고 `frozen: true`와 `frozen_manifest_sha256`을 기록한다. 내용이 바뀐 파일, 없어진 파일, 목록에 없는 새 `.py`가 있거나 매니페스트를 읽을 수 없으면 종료 코드 2로 거부하고 출력 폴더를 만들지 않는다.
- 우회 옵션 `--allow-unfrozen`(`make judge JUDGE_ARGS=--allow-unfrozen`): 경고를 내고 실행하며 헤더에 `frozen: false`를 기록한다. 헤더에는 실제 대조 결과(`frozen_check`), `allow_unfrozen`, 불일치일 때 차이(`frozen_diff`)도 남는다.
- 범위: 실수로 바뀐 코드의 사용을 막는 장치이며 변조 방지가 아니다. `selfcheck`와 `aggregate`는 대조하지 않는다. `bench/`, `data/`, `Makefile`, 문서, 테스트는 매니페스트 밖이다. 재개한 실행의 헤더는 처음 시작 때의 값이다. 자세한 것은 `docs/DESIGN.md` 부록 A-3.

### 패치 3. 선택 순위의 명시 (`judge.py`, 동작 불변)

- `judge.RANK`가 `{"SAME": 0, "PROOF": 1, "REFUTE": 1, "NEITHER": 2, "N/M": 3, "UND": 4}`를 항목으로 갖고, `rank_of(rec)`가 `nm`이 true인 기록을 N/M, `role == "UND"`인 기록을 UND로 순위를 매긴다. v1.1.0은 같은 값을 `RANK.get(role, 3 if role is None else 4)`로 계산했다. 도달 가능한 여섯 상태에서 같은 값을 내는 것을 테스트가 확인하고, 252쌍 모두에서 선택된 참조 부분과 `reference_trials`가 v1.1.0 기록과 같다.

### 환경 고정 (`requirements.txt`)

- `z3-solver==5.3.3.0`, `pytest==9.2.0`. 같은 날(2026-11-10) 설치에서 z3-solver가 5.3.3.0과 5.4.0.0으로 달랐다. `pip freeze`: iniconfig 2.3.1, packaging 26.3, pluggy 1.7.0, Pygments 2.21.0, pytest 9.2.0, z3-solver 5.3.3.0 (Python 3.12.14). 간접 의존성은 고정하지 않았다.

### 검증 결과 (2026-11-11)

기준은 v1.1.0 실행의 기록(2026-11-10)이다. 새 실행은 같은 입력(v8 예시 252쌍), 같은 NuSMV 이미지, 같은 설정(mode anchor, cap 128, timeout 120초, z3 horizon 8)으로 릴리스된 코드와 같은 코드를 돌린 것이다. 비교는 `pair_id`로 맞추었고 시간 필드와 질의의 명령줄(`cmd`)을 뺀 모든 필드를 비교했다.

- 테스트: `make test` 릴리스 전 47 passed와 1 skipped(릴리스된 트리에서만 의미가 있는 시험), 릴리스 후 48 passed(기존 20개와 `tests/test_patch_v12.py`의 28개). 코드와 문서를 일부러 한 곳씩 망가뜨린 14가지 변형을 새 테스트가 모두 잡는다.
- `make selfcheck`(NuSMV 2.6.0): 5쌍 모두 PASS.
- NuSMV 252쌍(36분 36초): 쌍 집합과 순서가 같고 모든 쌍의 모든 필드가 같다(역할, 정렬 사상, 원자, 질의 판정과 원문 출력, `reference_part`, `reference_trials`, 질의 SMV 해시 포함). timeout 9쌍도 그대로 timeout이고 `smv/` 1060개의 이름이 같다. 쌍 결과 분포: UND 109, NEITHER 66, SAME 47, REFUTE 16, PROOF 5, N/M timeout 9.
- z3 252쌍(horizon 8): 같은 결과다(UND 109, NEITHER 62, SAME 43, REFUTE 16, PROOF 5, N/M converter_limit 17).
- `make aggregate`: 단위 결과가 v1.1.0과 같다(NuSMV 52, 16, 54, 94, z3 48, 16, 50, 102, 전체 단위 216개).
- 헤더: v1.1.0 헤더와의 차이는 새 필드(패치 1, 2), `version`, `started_at`뿐이다. 새 필드의 값은 도구의 코드를 쓰지 않는 스크립트로 다시 계산해 확인했다.
- `make freeze-check` OK. `bench/`와 `judging/legacy/`는 입력 패키지(v1.1.0)와 바이트 단위로 같다.
- 릴리스: `make release`를 한 번 실행했다. 매니페스트 sha256은 `1fda2c1982c14c7ae7363c8c5ced72c11d0019afe9804a5693a35cae15aa154b`이고, 릴리스 전 회귀 실행(NuSMV와 z3)의 헤더 `code_tree_sha256`과 같다(회귀가 릴리스된 코드와 같은 코드로 돌았다). 릴리스 후 `make judge` 10쌍은 `frozen: true`로 기록되었고 기준 기록의 같은 쌍과 모든 필드가 같다.

### 알려진 한계 (이번 릴리스에서 고치지 않은 것)

- 동결 장치의 범위(위 패치 2의 "범위")와, 재개한 실행의 헤더가 처음 시작 때의 값이라서 `--allow-unfrozen`으로 코드를 바꾼 뒤 같은 출력 폴더를 이어 돌린 경우는 헤더만으로 드러나지 않는다.
- SMV 파일을 쓰는 도중에 프로세스가 죽어서 빈 파일이나 끊긴 파일이 해시 이름으로 남는 경우의 복구가 없다(코드를 읽어서 본 것이며 재현하지 않았다).
- 61개 항목의 실제 입력 세 개(`units.json`, `fret_ltl_gen.jsonl`, `fret_realizability_gen.jsonl`)는 저장소에서 찾지 못했고, `bench/`의 출력을 이 형식으로 바꾸는 코드는 패키지에 없다. `data/`의 입력 예시는 v8 예시(18개 항목)뿐이다.
- NuSMV를 컨테이너로 부를 때 래퍼 안의 시간 제한은 도구의 `--timeout`보다 길어야 하고, 가상 머신의 시계가 호스트보다 빠를 수 있으므로 여유를 2 % 이상으로 둔다(v1.1.0 실행에서 Colima VM의 시계가 약 0.92 % 빨랐다).

### v1.1.0의 알려진 한계 중 이번 릴리스에서 해결한 것

- `requirements.txt`가 버전을 고정하지 않는다: 고정했다(`z3-solver==5.3.3.0`, `pytest==9.2.0`).
- 헤더에 변환기와 판정 코드의 sha256, SMV 템플릿 식별자가 없다: 코드에 만들었다(패치 1).
- `Makefile`에 `judge`의 옵션(예: NuSMV timeout)을 넘길 변수가 없다: `JUDGE_ARGS`를 더했다.

## 1.1.0 (2026-11-10)

원본 v1.0.0에 대한 패치다. 판정 로직의 의미(질의 방향, 역할 대응, 불리언 추상화, 별칭 규칙, 정렬 후보 구성 규칙, 최선 선택 규칙 `RANK`)는 바꾸지 않았다.

- 수정한 코드: `judging/nl2fret_judge/`의 `__init__.py`(버전), `judge.py`, `recorder.py`, `cli.py`, `aggregate.py`.
- 수정한 문서: `README.md`, `docs/DESIGN.md`(부록 A-2 추가, 2절 표 S6 행의 "대응 불가는 N/M"을 UND로 정정), `docs/RUNBOOK.md`.
- 새 파일: `tests/test_patch_v11.py`(테스트 14개), 이 파일. 기존 테스트 `tests/test_judge.py`는 그대로다.
- 수정하지 않은 것: `bench/`, `judging/legacy/`, `Makefile`, `requirements.txt`, `data/`, `judging/nl2fret_judge/`의 나머지 파일(`align.py`, `engines.py`, `abstraction.py`, `ltl_engines.py`, `ap_check.py`, `selfcheck.py`, `units.py`). `make freeze-check`는 수정 전후 모두 OK다.

근거에 쓴 "기준 실행"은 원본 v1.0.0으로 v8 예시 252쌍을 NuSMV 2.6.0(Docker, Colima)과 z3(horizon 8)로 판정한 2026-11-10의 Mac 실행이다(`runs/nusmv_v8`, `runs/z3_v8`).

### 수정 1. 정렬 후보가 없으면 UND (`judge.py`)

- 증상: `align.candidates`가 같은 유형의 대응 변수는 찾았지만 서로 다른 변수로 짝지을 수 없을 때 빈 후보 목록(`{"maps": []}`)을 돌려주고, `judge_pair`가 이를 N/M(`nm_reason="other"`, `nm_detail={"message": "no candidate"}`)으로 기록했다.
- 근거: 기준 실행의 252쌍 중 6쌍이 이 경우였다(NuSMV와 z3 모두 같은 6쌍). 6쌍 모두 `alignment.n_candidates=0`, 질의 0개, 소요 0.002초 이하였다. `docs/DESIGN.md` 부록 A(v1.0.0)는 정렬 실패를 UND로 정하고 있었으므로 설계와 코드가 어긋나 있었다.
  - `LM-00_TRIPLEX-RM-001|DIRECT+D|1|0`, `LM-00_TRIPLEX-RM-001|MASTeR+D|0|1`, `LM-00_TRIPLEX-RM-001|MASTeR+D|1|0`, `LM-00_TRIPLEX-RM-002|MASTeR|1|1`, `LM-00_TRIPLEX-RM-002|MASTeR+D|1|1`, `LM-02_TUSTIN-N1|MASTeR|1|0`
- 변경: `maps`가 비어 있으면 `role="UND"`, `und_reason="atomization_mismatch"`, `nm_detail={"message": "no injective renaming candidate"}`, `nm=False`로 기록하고 질의 없이 끝낸다(`ap_check`는 기존 UND 분기와 같이 `ap_check(None, None)`). `align.py`의 후보 구성은 바꾸지 않았다.
- 후보가 있었으나 모든 후보에서 변환(`_prepare`)이 실패한 쌍은 이전과 같이 첫 실패의 사유(`converter_limit` 또는 `syntax`)로 N/M이다. 두 경우를 구분하는 테스트가 있다.
- 부수 효과: UND는 `RANK`에 없어서 순위 4로 취급된다. 여러 참조 부분이 있는 항목에서는 후보 없음 부분이 이전(N/M, 순위 3)과 달리 다른 N/M 부분보다 뒤로 간다. 선택 규칙 자체는 그대로이고 역할이 바뀐 결과다(기준 실행의 252쌍에서는 이 효과로 선택된 참조 부분이 바뀐 쌍이 없었다, 검증 결과 절).

### 수정 2. 재현 기록 보강 (`cli.py`, `judge.py`)

- 헤더: `run_header.json`의 `inputs`에 `rlz`(`--rlz` 파일의 sha256, 없으면 null)를 추가했다. 근거: 기준 실행은 `--rlz`로 실현가능성 결과를 입력했지만 헤더 `inputs`에는 `units`, `ltl`, `reference`만 있어서 그 입력의 동일성을 기록에서 확인할 수 없었다.
- `reference_trials`: `best_over_references`가 쌍마다 시도한 모든 참조 부분의 요약을 선택된 기록에 붙인다(항목: `reference_part`, `role`, `nm`, `nm_reason`, `und_reason`, `n_queries`, `smv_sha256` 목록, 질의 요약 `queries` = `kind`, `verdict`, `elapsed_sec`). 선택되지 않은 시도의 SMV 파일도 `smv/`에 저장한다. 질의 원문 출력은 선택된 기록의 `queries`에만 둔다. 선택 규칙은 바꾸지 않았다. 근거: 기준 실행의 기록은 쌍마다 선택된 참조 부분 하나의 질의만 남기고 나머지 시도의 판정, 질의, 시간, SMV를 남기지 않았다. 기준 기록의 쌍별 `elapsed_sec_total` 합은 1972.5초이고 실행 전체는 약 36분 26초(2186초)였는데, 기록만으로는 그 차이에 선택되지 않은 시도의 시간이 얼마나 들어 있는지 확인할 수 없었다.
- 기록 형식의 상세는 `docs/DESIGN.md` 부록 A-2.

### 수정 3. 중단 후 재개 (`recorder.py`, `aggregate.py`)

- 시험(원본 v1.0.0, 21쌍 입력, 프로세스 그룹 SIGKILL로 기록 12줄에서 중단):
  - 실제 강제 종료만으로는 끊긴 줄이 생기지 않았고(마지막 줄 완결), 같은 `make judge`로 재개하면 이미 기록된 12쌍은 건너뛰고(래퍼가 받은 NuSMV 호출 수 48 = 자기점검 질의 15와 버전 조회 1 + 새 기록의 질의 32), 최종 기록은 중단 없이 돌린 결과와 같았다.
  - 마지막 줄이 반쯤 쓰인 상태를 모의로 만들었을 때(마지막 완결 줄의 절반 지점에서 파일을 자름): 재개 전 `aggregate`가 JSON 오류로 끝났다. 재개 명령은 오류 없이 끝났지만 새 기록이 끊긴 줄 뒤에 이어 붙어서(그 줄이 읽을 수 없는 JSON이 됨) 그 쌍의 기록이 읽을 수 없게 되었고, 재개 후에도 `aggregate`가 오류로 끝났다.
- 변경: `Recorder`는 시작할 때 마지막 개행 뒤의 바이트가 완전한 JSON 기록이 아니면 그것을 파일에서 제거하고 `judge_records.discarded_tail.txt`에 보존한 뒤 해당 쌍을 다시 판정한다(완전한 JSON인데 개행만 없으면 개행을 붙여 유지). `aggregate`는 같은 끊긴 마지막 줄을 경고하고 건너뛴다(파일은 바꾸지 않는다). 가운데 줄의 손상은 오류로 남는다.
- 같은 시험을 v1.1.0에서 반복한 결과는 검증 결과 절에 있다.

### 검증 결과 (패치 실행, 2026-11-10)

기준은 위의 기준 실행(원본 v1.0.0)이고, 새 실행은 같은 입력(v8 예시 252쌍), 같은 NuSMV 이미지, 같은 설정(mode anchor, cap 128, timeout 120초, z3 horizon 8)으로 v1.1.0을 돌린 것이다. 비교는 `pair_id`로 맞추었고, 시간 필드와 질의의 명령줄(`cmd`)을 뺀 모든 필드를 비교했다.

- 테스트: `make test` 20개 통과(원본 6개와 새 14개). 새 테스트를 원본 v1.0.0 코드에 돌리면 14개 중 11개가 실패하고 3개(변경 없음을 확인하는 테스트)만 통과한다.
- `make selfcheck`(NuSMV 2.6.0): 5쌍 모두 PASS.
- NuSMV 252쌍 재실행(36분 16초): 쌍 집합과 순서가 같고, 예상한 6쌍(N/M `other`에서 UND)만 다르다. 그 6쌍의 필드 변경은 `role`, `nm`, `nm_reason`, `nm_detail`, `und_reason` 다섯 개뿐이다. 나머지 246쌍은 역할, 정렬 사상, 원자, 질의 판정, 질의 원문 출력(`stdout`)을 포함한 비교 대상 필드가 모두 같다. 선택된 `reference_part`도 252쌍 모두 같다. timeout 9쌍도 그대로 timeout이다. 쌍 결과 분포: UND 103에서 109, N/M `other` 6에서 0, 나머지(NEITHER 66, SAME 47, REFUTE 16, PROOF 5, N/M timeout 9)는 같다.
- z3 252쌍(horizon 8)도 같은 결과다: N/M `other` 6쌍만 UND가 되고(UND 103에서 109), `converter_limit` 17쌍과 나머지는 같다. 다른 정렬 모드(z3, lex, strict, free)와 `--aux`로도 확인했고(원본 v1.0.0과 새 실행 비교), 바뀐 것은 해당 모드의 후보 없음 쌍뿐이었다(lex 6쌍, free 5쌍, strict 0쌍, anchor와 `--aux` 6쌍).
- `make aggregate`: 단위 결과(success, partial, failure, unjudged)가 전후 같다(NuSMV 52, 16, 54, 94, z3 48, 16, 50, 102, 전체 단위 216개). 쌍 결과 분포는 위와 같이 바뀐다. 패치본의 `aggregate`를 기준 NuSMV 기록에 돌려도 기준 `aggregate.json`과 같다.
- `reference_trials`: 252개 기록 모두에 있고 일관성 문제는 없다. 시도 수는 쌍당 1개 172, 2개 44, 3개 12, 4개 12, 9개 12쌍이며, 선택되지 않은 시도는 200개, 그 질의는 1710개(질의 시간 합 약 211초)이다. 기준 기록은 이 질의들을 남기지 않았다(기준 기록에 남은 질의는 1887개).
- `smv/`: 798개에서 1060개로 늘었다(+262, 모두 선택되지 않은 시도의 SMV). 기준의 798개는 모두 그대로 있고, 모든 파일의 내용 해시가 파일 이름과 같다. `judge_records.jsonl`은 9,661,608바이트에서 10,199,629바이트로(+5.6 %) 늘었다.
- 재개(21쌍 입력, 프로세스 그룹 SIGKILL): 이미 기록된 쌍은 건너뛰고(래퍼가 받은 NuSMV 호출 수 = 자기점검 질의 15와 버전 조회 1 + 새 기록의 질의 수), 최종 기록이 중단 없이 돌린 결과와 같다. 마지막 줄을 반쯤 자른(모의) 상태에서는 `aggregate`가 경고 후 건너뛰고, 재개하면 끊긴 줄이 `judge_records.discarded_tail.txt`로 옮겨지고 그 쌍이 한 번 온전하게 기록되며 최종 기록이 중단 없이 돌린 결과와 같다.
- `make freeze-check`는 수정 전후와 모든 실행 후에 OK이고, `bench/`와 `judging/legacy/`의 모든 파일 해시가 원본 zip과 같다.


### 알려진 한계 (이번 패치에서 고치지 않은 것)

- `requirements.txt`가 버전을 고정하지 않는다(수정 허용 파일이 아니라서 고치지 않았다). 같은 날 설치에서 z3-solver가 5.3.3.0과 5.4.0.0으로 달랐다.
- 헤더에 변환기와 판정 코드의 sha256, SMV 템플릿 식별자가 없다(`docs/DESIGN.md` 7절 표는 헤더 항목으로 적는다).
- SMV 파일을 쓰는 도중에 프로세스가 죽어서 빈 파일이나 끊긴 파일이 해시 이름으로 남는 경우의 복구가 없다(코드를 읽어서 본 것이며 재현하지 않았다).
- `Makefile`에는 NuSMV timeout을 바꾸는 변수가 없다(`python -m nl2fret_judge judge --timeout N`을 직접 부른다).

## 1.0.0

원본 패키지(2026-11-10).
