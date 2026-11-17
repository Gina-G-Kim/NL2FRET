# 실행 절차 (릴리스 2.0)

설계와 사전 등록은 `docs/V20_BATCH_DESIGN.md`, 단계별 설명은 프로젝트 루트의 `docs/TOOL_PROCESS_GUIDE.md`이다. 이 문서는 실행 순서만 적는다.

## 0. 준비 (한 번)
- Python 3.10 이상. 도구 루트(`nl2fret_tool/`)에서 가상환경을 만들고 설치한다.
  ```
  python3 -m venv .venv && . .venv/bin/activate
  pip install -e ".[test]"        # src 레이아웃의 편집 가능 설치: 패키지 nl2fret, nl2fret_judge (+ 옆 폴더 legacy), 의존성 z3-solver, pytest
  ```
  스크립트(`scripts/*.sh`)는 환경 변수 `PYTHON`(기본 `python3`)으로 인터프리터를 고른다. 가상환경을 켜지 않으면 `PYTHON=$PWD/.venv/bin/python`을 준다.
- NuSMV 2.6.0 실행 명령. 마지막 인자로 `.smv` 경로를 받는 실행 파일이면 된다 (직접 설치 또는 docker 래퍼). 환경 변수 `NUSMV`로 지정한다.
- Docker 이미지 `fret-lab` (공식 FRET 파서, 실현가능성 CLI, Kind2). `PARSER=docker`가 기본이다.
- 로그인된 `claude` CLI (구독 로그인 유지, 격리 검사는 `StructuredOutput`과 `userEmail` 두 항목만 허용).

## 1. 점검 (모델 호출 없음)
```
make test                      # pytest 전체 (z3 엔진, NuSMV 불필요)
python -m nl2fret.ext.dictionary.build verify    # 딕셔너리 v1, sigdict.json 일치
```

## 2. 배치 실행 `scripts/run_batch.sh STEP [RUN_DIR]`
`STEP` = `pin | gen | inputs | judge | group | effect | all`. `RUN_DIR` 기본값은 `runs/batch_<날짜>`.

| 단계 | 하는 일 | 모델 호출 |
|---|---|---|
| `pin` | 공식 파서 지문을 계산해 `data/reference/parser_fingerprint.pin`과 비교 (`WRITEPIN=1`이면 처음 한 번 저장) | 없음 |
| `gen` | 방식, 챌린지, 반복마다 에이전트 호출 (단계 A, B, D, S, 파서 피드백 F1..F5, 점검 단계 KC1과 왕복 RT1). 먼저 파서 지문을 검사하고 격리 검사를 한다 | 있음 |
| `inputs` | 변형 v0, vf, kc, rt의 `units.json`, `fret_ltl_gen.jsonl` 생성 | 없음 |
| `judge` | 변형마다 `nl2fret_judge judge-parts` (NuSMV) | 없음 |
| `group` | 방식, 챌린지, 반복의 최종 문장 집합 Realizable (raw, normalized) | 없음 |
| `effect` | 변형 간 부분 성공의 이득과 손실 집계 `rt_effect.json` | 없음 |

환경 변수: `MODEL`(sonnet), `REPS`(3), `PARSER`(docker), `NUSMV`, `ENGINE`(nusmv), `ONLY`(챌린지 id 목록, 부분 실행), `ENVPASS`, `CLI_EXTRA`(기본 `--effort medium`), `EXT`(확장 모듈, 기본 `dictionary`, `EXT=`이면 끔), `NO_KC`(`1`이면 점검 단계 KC를 끔, 기본은 켬), `PYTHON`.

예 (06_EB 한 챌린지, 반복 1):
```
ONLY=06_EB REPS=1 NUSMV=/path/to/NuSMV bash scripts/run_batch.sh all runs/batch_06EB
```
`gen`은 이어 하기를 지원한다 (같은 `RUN_DIR`로 다시 실행). 호출 한도 대기와 응답 거절은 `gen/run.log`에 남는다.

## 3. 확장 모듈
`EXT=dictionary`(기본): 딕셔너리 블록과 규칙이 FRETish 단계에 붙고 판정기는 딕셔너리 v1을 받는다. `EXT=`: 프롬프트에 딕셔너리가 없고 판정기에는 항목 없는 머리글 파일을 넘긴다. 자세한 설명은 `src/nl2fret/ext/dictionary/README.md`.

## 4. 판정만 따로 실행
```
nl2fret-judge selfcheck --engine nusmv --nusmv "$NUSMV" --out runs/judge_selfcheck
nl2fret-judge judge-parts --engine nusmv --nusmv "$NUSMV" --out runs/judge --units inputs/units.json --ltl inputs/fret_ltl_gen.jsonl \
  --reference data/reference/lm_reference_with_ltl.jsonl --dictionary data/dictionary/lm_dictionary.csv --mode anchor
nl2fret-judge aggregate --out runs/judge --units inputs/units.json --ltl inputs/fret_ltl_gen.jsonl --rlz inputs/fret_realizability_gen.jsonl
```
(`python -m nl2fret_judge ...`도 같다. `judge-parts`는 `--dictionary`가 필수 인자이다.)

## 5. 결과 폴더
`$RUN/gen/`(calls.jsonl, batch_calls.jsonl, parser_cache.jsonl, descriptions.jsonl, run_state.json, isolation_probe.json, snapshot/), `inputs_v0|vf|rt/`, `judge_v0|vf|rt/`, `group_rlz.jsonl`, `rt_effect.json`. `runs/`는 git 추적에서 제외한다.

## 6. 이전 시험 스크립트 (릴리스 1.3, 1.4 계열)
`scripts/run_fsm.sh`(FSM 시험), `scripts/run_intent.sh`(의도 선언 시험)은 문장 단위 호출 파이프라인 `nl2fret.run_pipeline`을 쓴다. 사용법은 각 파일 머리말과 `archive/nl2fret_tool_docs/v1.4/docs/V14_INTENT_TEST.md`를 따른다.

## 7. 실험으로 실행할 때 (028번부터의 규칙)
1. 새 폴더 `experiments/NNN_slug/`를 만들고 `experiments/000_INDEX.md`에 한 줄 추가한다. `inputs/`에 필요한 데이터, 테스트 패키지 zip, `testnote.md` 사본만 둔다. 도구 코드 사본은 두지 않는다.
2. 도구는 `nl2fret_tool/`에서 실행하고 결과는 `runs/NNN_slug/`에 나온다 (`bash scripts/run_batch.sh all runs/NNN_slug`).
3. 끝나면 `runs/NNN_slug/`의 사본을 `experiments/NNN_slug/results/`에 두고 (`REPORT.md`, 사전 등록과 변경 기록 `notes/`, 로그 `logs/`도 같은 폴더에), 사용자에게 줄 zip을 `experiments/NNN_slug/zips/`에 만든다.
4. FRET을 부르는 `group` 단계는 `src/nl2fret/fret_check/work/`에 임시 파일을 쓴다. 메인 폴더에서 돌린 뒤에는 그 폴더를 비운다.

