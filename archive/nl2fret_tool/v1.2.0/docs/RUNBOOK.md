# 실행 절차

## 0. 준비
- Python 3.10 이상, `pip install -r requirements.txt` (z3는 교차검증과 샌드박스 테스트용). v1.2.0부터 `requirements.txt`가 `z3-solver==5.3.3.0`, `pytest==9.2.0`으로 고정되어 있다(v1.1.0까지는 고정하지 않아서 2026-11-10에 5.3.3.0과 5.4.0.0이 모두 설치되었다). 확인된 `pip freeze`: iniconfig 2.3.1, packaging 26.3, pluggy 1.7.0, Pygments 2.21.0, pytest 9.2.0, z3-solver 5.3.3.0 (Python 3.12.14). 실행 헤더가 `python_version`과 `z3_version`을 기록한다.
- NuSMV 2.6.0 실행 명령 확인 (직접 설치 또는 docker 래퍼 스크립트; 마지막 인자로 .smv 경로를 받는 실행 파일이면 된다)
- `make freeze-check` 로 bench 동결 해시 확인. 판정 코드(`judging/`)의 동결은 `JUDGE_FROZEN_MANIFEST.sha256`이 맡고, `judge`가 시작할 때 대조한다(5절).

## 1. 생성 단계 (bench, 기존 절차 그대로)
`bench/run_pipeline.py`와 `bench/score3.py`의 사용법은 각 파일 머리말과 `bench/NL2FRET_PROMPT_v8_DICT_SMOKE.md`를 따른다. 이 패키지는 bench를 수정하지 않는다.
판정 입력으로 필요한 세 파일을 `inputs/`에 둔다.
- `units.json` : {"units":[{"item","arm","rep","status","texts":[...]}]}
- `fret_ltl_gen.jsonl` : 문장별 FRET 컴파일 결과 (sentence, parser_ok, ltl_pt, ltl_ft)
- `fret_realizability_gen.jsonl` : 문장별 Kind2 결과 (item_id, arm, rep, sentence, result)
형식 예시는 `data/example_*` 파일.

## 2. 판정
1. `make selfcheck NUSMV="NuSMV" OUT=runs/r1` : 5쌍 점검. 실패하면 엔진을 쓰지 않는다 (판정 명령도 자동으로 거부한다).
2. `make judge OUT=runs/r1 NUSMV="NuSMV"` : 시작할 때 판정 코드를 `JUDGE_FROZEN_MANIFEST.sha256`과 대조하고(다르면 거부, 5절), 쌍마다 `judge_records.jsonl`에 추가 기록, `smv/`에 질의 파일 저장. 중단 후 같은 명령으로 재개된다(기록된 쌍은 건너뛴다). 강제 종료로 마지막 줄이 중간에 끊겼으면 시작할 때 그 줄을 `judge_records.discarded_tail.txt`로 옮기고(stderr에 한 줄 안내) 해당 쌍을 다시 판정한다. 재개한 실행의 `run_header.json`은 처음 시작 때의 것이 그대로 남는다.
3. `make aggregate OUT=runs/r1` : `aggregate.json` 생성 (arm별, stratum별, 쌍 결과 분포).

옵션: `--mode anchor|lex|strict|free` (정렬 층, 기본 anchor), `--cap 128` (구간 확장 상한), `--aux` (보조 sat/valid 질의), `--timeout 120`, `--allow-unfrozen` (개발용 우회, 5절). `make judge`에는 `JUDGE_ARGS`로 넘긴다(예: `make judge OUT=runs/r1 NUSMV="NuSMV" JUDGE_ARGS="--timeout 600"`). 래퍼 스크립트를 쓰는 경우 래퍼 안의 시간 제한은 `--timeout`보다 길어야 하고, 가상 머신의 시계가 호스트보다 빠를 수 있으므로 여유를 `--timeout`의 2 % 이상으로 둔다.

## 3. 샌드박스 교차검증 (NuSMV 없이)
`python -m nl2fret_judge judge --engine z3 ...` : 구간 길이가 horizon(기본 8) 이하인 쌍만 판정되고 나머지는 N/M(converter_limit)이 된다. NuSMV 결과와 판정된 쌍에서 비교한다.

## 4. 기록물
`run_header.json`(엔진 버전, 입력 해시(`units`, `ltl`, `rlz`, `reference`), 설정, 인터프리터와 z3 버전, 판정 코드의 파일별 sha256과 전체 해시(`code_sha256`, `code_tree_sha256`), SMV 템플릿 식별자와 질의식(`smv_template_id`, `query_templates`), 동결 상태(`frozen` 등)), `judge_records.jsonl`(쌍별 전체 기록: 원 식, 원자, 질의 원문 출력, 정렬 사상, AP 불일치 기록, 참조 부분별 시도 요약 `reference_trials`), `smv/*.smv`(선택되지 않은 참조 부분의 질의 파일 포함), 재개 때 끊긴 줄이 있었으면 `judge_records.discarded_tail.txt`. 필드의 목록은 `docs/DESIGN.md` 7절, 기록 형식의 변경은 부록 A-2와 A-3.

판정 결과가 UND인 경우는 정렬이 없는 쌍(같은 유형의 대응 변수가 없거나, 있어도 서로 다른 변수로 짝지을 수 없는 쌍 포함)이고, N/M은 엔진이 판정하지 못한 쌍(`converter_limit`, `syntax`, `timeout`, `nusmv_output`, `no_verdict`, `other`)이다. 둘 다 집계에서 미판정(unjudged)이다.

## 5. 동결 후 실행 절차 (v1.2.0 이후: 코드를 바꾸지 않고 실험만 돌린다)

이 패키지는 판정 코드를 동결해서 전달한다. 패키지 루트의 `JUDGE_FROZEN_MANIFEST.sha256`이 `judging/nl2fret_judge/*.py`와 `judging/legacy/*.py`의 sha256을 담고 있고, `judge`가 시작할 때 현재 코드와 대조한다(`docs/DESIGN.md` 부록 A-3). 아래 순서만 따른다.

(가) 입력 3개를 준비한다. 패키지 루트의 `inputs/`에 `units.json`, `fret_ltl_gen.jsonl`, `fret_realizability_gen.jsonl`을 둔다(형식은 1절과 `data/example_*`). `bench/`가 만드는 `units_scored.jsonl`, `fret_ltl.jsonl`, `fret_realizability.jsonl`은 형식이 다르다(예: units는 JSONL이고 `item_id`와 `variants` 아래에 문장이 있으며, 실현가능성 파일에는 `rep`가 null인 기준 문장 줄이 섞여 있어 `units.load_units`가 읽지 못한다). 이 형식으로 바꾸는 코드는 패키지에 없다. 준비한 파일의 sha256은 실행 헤더의 `inputs`에 기록된다. 코드가 동결된 그대로인지 따로 확인하려면 패키지 루트에서 `shasum -a 256 -c JUDGE_FROZEN_MANIFEST.sha256`(Linux는 `sha256sum -c`)을 실행한다.

(나) `make selfcheck NUSMV="<NuSMV 명령>" OUT=runs/<이름>`. 5쌍이 모두 PASS여야 한다(`judge`도 시작할 때 같은 점검을 하고 실패하면 거부한다).

(다) `make judge OUT=runs/<이름> NUSMV="<NuSMV 명령>"`. 시작할 때 코드를 매니페스트와 대조한다. 거부되면(종료 코드 2, 어느 파일이 다른지 stderr에 나온다) 코드가 바뀐 것이므로 실험하지 말고 패키지를 다시 풀어서 쓴다. 실행이 시작되면 `runs/<이름>/run_header.json`에서 `"frozen": true`와 `frozen_manifest_sha256`을 확인하고, 그 값을 실험 기록에 남긴다.

(라) `make aggregate OUT=runs/<이름>`. arm별, stratum별 단위 결과와 쌍 결과 분포가 `aggregate.json`에 쓰인다. `units.json`의 단위에 `stratum`이 없으면 `by_stratum`에는 `stratum: null` 한 줄(전체 단위)만 나온다.

(마) 재개. 중단되면 같은 `OUT`으로 (다)의 명령을 다시 실행한다. 기록된 쌍은 건너뛰고, 강제 종료로 마지막 줄이 끊겼으면 그 줄을 `judge_records.discarded_tail.txt`로 옮기고 해당 쌍을 다시 판정한다(2절). 기본 `OUT`은 분 단위 시각을 포함하므로 재개하려면 `OUT`을 직접 지정해서 처음과 같은 값을 쓴다. 재개한 실행의 `run_header.json`은 처음 시작 때의 것이 그대로 남는다.

(바) 코드를 바꾸지 않는다. `judging/`의 파일, `JUDGE_FROZEN_MANIFEST.sha256`, `bench/`를 수정하지 않는다. 매니페스트는 `make release`로 다시 만들 수 없다(이미 있으면 거부한다). `--allow-unfrozen`(`make judge ... JUDGE_ARGS=--allow-unfrozen`)은 개발용 우회이고 그 실행의 헤더는 `frozen: false`이므로 동결된 결과로 쓰지 않는다. 우회 옵션으로 코드를 바꾼 뒤 같은 `OUT`을 이어 돌리지도 않는다(재개한 실행의 헤더는 처음 값이라 드러나지 않는다). 코드를 바꿔야 하면 이 패키지를 고치지 말고 새 폴더에서 버전을 올려 새로 릴리스한다.

`make release`는 코드를 만든 쪽이 마지막에 한 번만 실행하는 명령이다. 전달된 패키지에서는 이미 실행되어 있으므로 다시 실행할 필요가 없다.
