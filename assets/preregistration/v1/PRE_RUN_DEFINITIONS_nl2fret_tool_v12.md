# PRE_RUN_DEFINITIONS: nl2fret_tool v1.2 최종 패치와 동결 (2026-11-11)

이 문서는 코드를 고치기 전에 쓴다. 비교와 시험에 쓰는 스크립트는 해당 단계를 실행하기 전에 해시를 고정하고(`notes/PIN_*.sha256`), 결과를 본 뒤 이 문서의 정의와 스크립트를 바꾸지 않는다. 바꿔야 하면 바꾼 이유와 시각을 `notes/CHANGELOG.md`에 남기고 보고서에 적는다.

## 1. 범위와 원칙

- 지시문: `docs/NL2FRET_TOOL_V12_FREEZE.md` (사본, `notes/INSTRUCTION.sha256`). 금지 사항, 수정 허용 파일, 최종 보고 형식은 지시문을 따른다.
- 이 저장소의 원칙을 지시문의 경로나 명령보다 우선한다: git 명령을 쓰지 않는다, 판정 의미를 바꾸지 않는다, 결과를 보정하거나 쌍을 제외하지 않는다, 각 단계는 1회 실행하고 중단 재개만 허용한다, 관측만 적고 결론을 내리지 않는다, 확인하지 못한 것은 "확인하지 못함"으로 적는다.
- CPU: 컨테이너 1개(`--cpus=1`), NuSMV 질의는 한 번에 하나, 호스트 쪽 모든 명령은 `nice -n 10`과 최소 환경(`scripts/cleanenv.sh`), 에이전트를 쓰지 않는다, 끝나면 컨테이너와 프로세스를 남기지 않는다.
- 언어: 코드 주석, 독스트링, 출력 라벨은 영어. 패키지 안의 문서(README, CHANGELOG, DESIGN, RUNBOOK)는 기존대로 한국어. 이 실험 폴더의 문서도 한국어.

## 2. 기준 상태

- (가) 입력 zip: v1.1 실행이 전달한 `nl2fret_tool_v1.1.zip`(sha256 826a07f9...f406f485, `notes/INPUT_ZIP.sha256`). `bench/pristine/nl2fret_tool/`에 풀고 읽기 전용으로 둔다. 파일 72개의 해시 목록(`notes/PKG_V11_FILES.sha256`)은 v1.1 빌드 기록(`nl2fret_tool_v11/notes/PKG_V11_ZIP_FILES.sha256`)과 같아야 한다(`logs/step0_2_unzip_hashes.log`).
- (나) 비교 기준 기록: v1.1 실행(`experiments/nl2fret_tool_v11`)의 `runs/nusmv_v8`, `runs/z3_v8`을 `inputs/baseline_v11/`에 복사했다(`notes/BASELINE_V11.sha256`). v1.1 증거 zip 안의 같은 파일과 sha256이 일치함을 확인했다. 지시문 사전 준비 2의 "기준 기록이 있으면 쓴다"에 해당하므로 v1.1 코드로 새 기록을 만들지 않는다. 이 기록을 만든 코드는 (가)의 v1.1 패키지다(헤더 `version` 1.1.0, `inputs.rlz` 있음).
- (다) 환경: venv(Python 3.12.14, pyenv)를 고정된 `requirements.txt`(z3-solver==5.3.3.0, pytest==9.2.0)로 설치하고 `pip freeze`를 기록한다(`notes/PIP_FREEZE_V12.txt`). v1.1 실행의 venv와 같아야 한다(`notes/PIP_FREEZE_V11_RUN.txt`). NuSMV 2.6.0은 이전 실행과 같은 Docker 이미지 `cst-nusmv:local`(Colima), `--cpus=1`, 래퍼 `scripts/bin/NuSMV`(컨테이너 이름만 `nusmv-tool-v12`, 컨테이너 안 timeout은 도구 timeout + 5초).

## 3. 지시문과 다르게 정한 순서

- 지시문의 사전 준비는 1(zip 풀기, freeze-check, make test), 2(기준 기록), 3(requirements 고정) 순서다. 이 실행은 3의 고정을 1의 시험보다 먼저 한다. 이유: v1.1의 `requirements.txt`는 버전을 고정하지 않아서 새 venv에 z3-solver 5.4.0.0이 깔리고, 그 환경에서 한 시험은 기준 기록(5.3.3.0)의 환경과 달라진다. 고정한 파일로 venv를 만들면 그 파일이 실제로 설치 가능한지도 같이 확인된다. 풀어낸 v1.1 패키지(`bench/pristine`)는 그대로 두고 시험만 한다.
- 지시문의 "pytest는 지금 설치된 버전"은 새 폴더에는 설치된 것이 없으므로, v1.1 실행 venv에 설치되어 있던 버전(9.2.0)으로 읽는다.
- 입력 3개는 패키지의 `data/example_*`(v8 예시)를 작업 트리의 `inputs/`에 복사해 쓴다(`inputs/`는 git 무시 대상이고 zip에 넣지 않는다). 해시는 기준 기록과 같아야 한다.

## 4. 변경 범위

- 수정 대상: `judging/nl2fret_judge/__init__.py`(버전 1.2.0), `engines.py`(`SMV_TEMPLATE_ID` 상수 한 줄), `judge.py`(RANK), `cli.py`(헤더, `release`, `--allow-unfrozen`), `Makefile`(`release` 대상, `JUDGE_ARGS`), `requirements.txt`(고정), `tests/test_patch_v11.py`(버전 단언 두 줄), `docs/DESIGN.md`, `docs/RUNBOOK.md`, `README.md`, `CHANGELOG.md`.
- 새 파일: `judging/nl2fret_judge/freeze.py`(코드 해시, 매니페스트, 대조), `tests/test_patch_v12.py`, 마지막에 `JUDGE_FROZEN_MANIFEST.sha256`(`make release`).
- 고치지 않는 것: `bench/`, `judging/legacy/`, `data/`, `judging/nl2fret_judge/`의 `align.py`, `abstraction.py`, `ltl_engines.py`, `ap_check.py`, `selfcheck.py`, `units.py`, `aggregate.py`, `recorder.py`.
- `engines.py`는 판정 로직 파일이지만 `SMV_TEMPLATE_ID` 상수만 더하고 `spec_text`, `smv_file_text`, 엔진 코드는 바꾸지 않는다. 질의 SMV 파일 해시가 기준과 같은지(회귀 비교)로 확인한다.

## 5. 구현 규칙

### 5.1 코드 파일 집합과 해시 (패치 1, 2 공통)

- `CODE_FILES` = `judging/nl2fret_judge/*.py`와 `judging/legacy/*.py`(재귀 없음). 패키지 루트 기준 상대 경로(구분자 `/`), 경로 오름차순.
- 매니페스트 텍스트 = 파일마다 한 줄 `<sha256 소문자 16진 64자><공백 2개><상대 경로>\n`(`sha256sum -c` 형식, 주석 줄 없음).
- 헤더의 `code_sha256` = 같은 순서의 목록 `[{"file": 상대 경로, "sha256": ...}, ...]`. `code_tree_sha256` = 매니페스트 텍스트(UTF-8)의 sha256 = 위 줄들을 순서대로 이어 붙인 것의 sha256. 따라서 `make release`가 쓴 파일의 sha256과 같다.

### 5.2 헤더 필드 (패치 1)

`run_header.json`에 추가(기존 필드는 그대로, 키 이름과 값 정의):

- `python_version`: `platform.python_version()`. 기존 `python`은 호환을 위해 남기며 값이 같다.
- `z3_version`: 설치된 `z3-solver` 배포판 버전(`importlib.metadata`, `pip freeze`가 보이는 값). 배포판 정보가 없으면 `import z3`가 되는 경우 `z3.get_version_string()`, 둘 다 안 되면 null.
- `code_sha256`, `code_tree_sha256`: 5.1.
- `smv_template_id`: 문자열 `"single_ltlspec_v1"`(`engines.SMV_TEMPLATE_ID`). 뜻: 질의마다 SMV 파일 하나, 내용은 `MODULE main`, `VAR`(원자마다 `<이름> : boolean;`, 원자가 없으면 `dummy_ap`), `LTLSPEC <질의식>` 한 줄. 테스트가 이 구조를 고정한다.
- `query_templates`: `{"equiv", "sound", "compl", "sat", "valid"}` 각각 `spec_text(kind, "GS", "RS")`가 돌려준 문자열 그대로(GS = 생성식 자리, RS = 기준식 자리).
- `frozen`(bool), `frozen_manifest_sha256`(매니페스트 파일의 sha256, 파일이 없으면 null), `frozen_check`(`match`, `mismatch`, `absent`, `invalid`: 실제 대조 결과), `allow_unfrozen`(bool), `frozen_diff`(대조가 `mismatch` 또는 `invalid`일 때만: `modified`, `missing`, `extra` 목록 또는 `error`).
- `frozen` = (`frozen_check == "match"` 이고 `--allow-unfrozen`을 쓰지 않음). 지시문 그대로: 매니페스트가 일치하면 true, 우회 옵션을 쓰면 false. 매니페스트가 아직 없으면(릴리스 전) false이고 실행은 거부하지 않는다.
- 재개한 실행의 `run_header.json`은 처음 시작 때의 것이 그대로 남는다(기존 동작, 바꾸지 않는다).

### 5.3 동결 장치 (패치 2)

- `python -m nl2fret_judge release`(= `make release`): 5.1의 매니페스트를 패키지 루트의 `JUDGE_FROZEN_MANIFEST.sha256`에 쓴다. 이미 있으면 쓰지 않고 stderr에 거부 문구를 내고 종료 코드 2(파일은 그대로). 쓸 때는 배타적 생성(`open(..., "x")`)이다.
- `judge`는 시작할 때(엔진과 출력 폴더를 만들기 전) 매니페스트를 대조한다. 없으면(`absent`) 그대로 진행. 있고 일치하면(`match`) 진행. 있으나 다르거나(`mismatch`: 내용이 바뀐 파일, 없어진 파일, 목록에 없는 새 `.py`) 읽을 수 없으면(`invalid`) `--allow-unfrozen`이 없을 때 stderr에 문구와 차이 목록을 내고 종료 코드 2, 출력 폴더는 만들지 않는다. `--allow-unfrozen`이 있으면 stderr에 경고를 내고 진행한다.
- 대조의 범위는 코드 파일 해시이며 변조 방지가 아니라 실수로 바뀐 코드의 사용을 막는 장치다. 독립 확인은 `shasum -a 256 -c JUDGE_FROZEN_MANIFEST.sha256`(패키지 루트에서).
- `selfcheck`와 `aggregate`는 대조하지 않는다(지시문이 `judge`만 정했다).
- 시험은 임시 디렉터리의 패키지 사본에서만 한다. 실제 트리의 `make release`는 마지막 단계에서 한 번만 실행하고, 거부 시험(이미 있는 매니페스트)은 사본에서 한다.

### 5.4 선택 순위 (패치 3)

- `RANK = {"SAME": 0, "PROOF": 1, "REFUTE": 1, "NEITHER": 2, "N/M": 3, "UND": 4}`. `rank_of(rec)`: `rec["nm"]`이 참이면 `RANK["N/M"]`, `rec["role"] == "UND"`이면 `RANK["UND"]`, 아니면 `RANK[rec["role"]]`. `best_over_references`는 이를 쓰고 나머지(같은 순위에서는 먼저 시도한 부분, 첫 SAME에서 멈춤)는 그대로다.
- 동작 불변의 근거: v1.1의 `RANK.get(role, 3 if role is None else 4)`와 도달 가능한 여섯 상태(SAME, PROOF, REFUTE, NEITHER, N/M, UND)에서 같은 값(테스트), 그리고 회귀 비교의 `reference_part`와 `reference_trials`가 기준과 같음.

## 6. 회귀 비교의 정의 (NuSMV와 z3 공통, 기준 = v1.1 기록)

기준 기록과 새 기록을 `pair_id`로 맞춘다. 두 쪽의 `pair_id` 집합과 순서가 같아야 한다(252개). 지시문: 허용 차이는 헤더의 새 필드뿐이다.

- 비교에서 제외하는 필드(환경 또는 비결정): 기록의 `elapsed_sec_total`, 질의의 `elapsed_sec`, 질의의 `cmd`, `reference_trials` 항목 질의의 `elapsed_sec`. 이 밖의 기록 필드는 모두 같아야 한다(`reference_trials` 전체와 `smv_sha256` 목록 포함).
- 등급 A (중단 기준, 지시문의 "역할, 정렬 사상, 원자, 질의 판정"): `role`, `nm`, `nm_reason`, `und_reason`, `equiv`, `sound`, `compl`, `alignment`(전 필드), `atoms_gt`, `atoms_pred`, `atoms_union`, `atom_abstraction`, `reference_part`, `reference_trials`의 모든 필드, 질의의 `kind`, `spec_text`, `smv_sha256`, `verdict`, 질의 수. 등급 A에 차이가 하나라도 있으면 이후 단계를 중단하고 차이 전체를 보고한다.
- 등급 B (보고, 0이어야 함): 그 밖의 필드(`stdout`, `stderr`, `exit_code`, `timed_out`, `reason`, `ap_check`, `nm_detail`, `executed`, `query_mode`, 식 필드 등). 하나라도 있으면 "허용 차이는 헤더의 새 필드뿐"을 어긴 것이므로 표로 보고한다(중단하지는 않는다).
- NuSMV timeout 쌍 9개는 기준에서 `nm_reason == "timeout"`이다. 이번에도 같아야 하며 달라지면 등급 A로 센다.
- `smv/`(NuSMV): 기준 파일 이름 1060개와 새 `smv/`의 이름 집합이 같아야 하고 모든 파일의 내용 해시가 이름과 같아야 한다.
- 헤더: 평탄화한 키별 비교. 허용: 5.2의 새 키 전부, 그리고 필연적인 `version`(1.1.0에서 1.2.0)과 `started_at`. 새 키의 값은 스크립트가 독립적으로 다시 계산해 확인한다(`code_sha256`은 작업 트리 파일의 sha256, `code_tree_sha256`은 5.1의 정의, `smv_template_id`와 `query_templates`는 고정 기대값, `python_version`은 기존 `python`과 같음, `z3_version`은 `notes/PIP_FREEZE_V12.txt`의 z3-solver, 릴리스 전 실행은 `frozen` false와 `frozen_check` absent). 허용되지 않은 헤더 차이는 보고하고, `inputs.*`가 다르면 입력이 다른 것이므로 중단한다.
- 집계: `make aggregate`의 `aggregate.json`을 기준 `aggregate.json`과 비교한다. `by_arm`, `by_stratum`, `pair_outcomes`가 모두 같아야 한다(NuSMV 단위 결과 52/16/54/94, z3 48/16/50/102, 전체 216단위).
- 정지 기준: 등급 A 차이가 있는 쌍의 수 = 0, 허용되지 않은 헤더 차이 = 0.

## 7. 동결 확인 실행 (지시문 "동결과 전달" 1)

- `make release`를 한 번 실행한 직후에 한다. 입력은 `inputs/frozen_check_units.json`: v8 예시 단위를 파일 순서로 훑으며 기준 timeout 쌍이 있는 단위를 건너뛰고, 고른 단위의 기준 기록이 10개 이상이 될 때까지 단위를 그대로 복사한다(`scripts/make_inputs.py`, 단위 내용은 편집하지 않는다). 나머지 두 입력은 회귀 실행과 같은 파일.
- 명령: `make judge OUT=runs/frozen_check UNITS=inputs/frozen_check_units.json NUSMV=...`(기본 옵션, NuSMV).
- 기대: 헤더의 `frozen` true, `frozen_check` match, `frozen_manifest_sha256` = 매니페스트 파일의 sha256 = 헤더의 `code_tree_sha256` = 회귀 실행(릴리스 전) 헤더의 `code_tree_sha256`(회귀가 릴리스될 코드와 같은 코드로 돈 것을 뜻함). 기록은 6절의 기준으로 기준 기록의 해당 쌍과 비교한다.
- 임시 사본(zip을 풀어낸 사본)에서 한다: (가) `shasum -a 256 -c JUDGE_FROZEN_MANIFEST.sha256`, (나) `make freeze-check`, `make test`, (다) 코드 파일 한 개를 바꾸면 `judge`(z3 엔진, 작은 입력)가 종료 코드 2로 거부하고 `--allow-unfrozen`이면 실행되며 헤더에 `frozen` false, `frozen_check` mismatch가 남는지, (라) `make release`를 다시 부르면 거부되는지.

## 8. 패치 4 탐색 정의 (`scripts/patch4_scan.py`, 읽기 전용)

- 형식 기준(`data/example_*`와 `units.py`): units는 JSON 문서 `{"units": [...]}` 또는 목록이며 모든 단위에 `item`, `arm`, `rep`, `status`, `texts`. ltl은 JSONL이며 모든 줄에 `sentence`, `parser_ok`, `ltl_pt`, `ltl_ft`(예시의 키 합집합과 같은지도 적는다). rlz는 JSONL이며 모든 줄에 `item_id`, `arm`, `rep`, `sentence`, `result`(`units.load_units`가 모든 줄에 `int(rep)`를 하므로 `rep`가 null인 줄이 있으면 읽지 못한다).
- A단계: 저장소(`~/nl2semiformal`) 전체에서 정확히 `units.json`, `fret_ltl_gen.jsonl`, `fret_realizability_gen.jsonl`인 파일(의존성 폴더 제외)과 패키지 예시와의 sha256 일치 여부. B단계: `experiments/` 아래 `results*`, `rq` 폴더의 `units*.json*`, `fret_ltl*.jsonl`, `fret_realizability*.jsonl`의 형식 점검과 61개 항목(`bench/data/lm_items.jsonl`) 포함 여부. C단계: 항목-계층 표의 위치.
- 파일을 복사하거나 변환하거나 이름이 비슷한 파일로 대체하지 않는다. 만들 방법은 `bench/` 문서의 명령만 적고 실행하지 않는다.

## 9. 압축 규칙

- `nl2fret_tool_v1.2.zip`: 패키지 폴더(`nl2fret_tool/`)를 담되 `runs/`, `inputs/`, `work/`, `venv/`, 캐시(`__pycache__`, `.pytest_cache`, `*.pyc`, `.DS_Store`)는 제외한다(`inputs/`는 원본 zip에도 없었다). 매니페스트는 포함한다. 압축 직후 풀어서 파일 목록과 내용이 작업 트리와 같은지, 7절의 시험이 통과하는지 확인한다.
- 증거 zip은 별도로 만든다(보고서, 지시문 사본, 노트, 스크립트, 로그, diff, 실행 결과; venv와 work 제외).

## 10. 시작 시점에 알고 있는 확인하지 못할 항목

- Docker FRET/Kind2 단계, 실제 61개 항목 데이터로의 실행, 다른 머신에서의 timeout 재현성은 확인하지 않는다.
- `judge4.py`/`ctl*.py` 계열 원본이 없는 것과 무관하게, 이 실행은 패키지에 들어 있는 `judging/legacy/`만 쓴다.
