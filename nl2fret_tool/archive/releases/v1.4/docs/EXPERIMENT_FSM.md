# FSM 시험 (v1.3)

목적: 새 데이터셋과 사전으로 파이프라인 전체(템플릿, FRETish, FRET 도구, LTL, NuSMV 판정)가 끝까지 도는지 확인한다. 범위는 01_FSM 챌린지 13항목뿐이다.

## 구성
- 항목: `bench/data/lm_items_fsm.jsonl` 13개 (`python3 bench/tools/build_inputs.py`로 `data/dataset`에서 생성)
- 방식 3가지 (아래 11개 arm)
  - Direct: `DIRECT`
  - 규칙 글: `<템플릿>+G` (템플릿 규칙 글을 시스템 프롬프트에 넣고 FRETish를 자유 생성)
  - 규칙 조립: `<템플릿>+R2` (슬롯 값만 모델이 채우고 스크립트가 FRETish를 조립)
  - 템플릿 5개: MASTeR, EARS, Adv-EARS, SPIDER, Boilerplate. 규칙 글과 규칙 조립은 템플릿마다 모두 돌린다. PARA는 대조군이며 템플릿이 아니므로 뺀다.
- 반복 3회, 단위 수 13 x 11 x 3 = 429 (실행 전 `dryrun`이 같은 값을 출력해야 한다)
- 사전: 모든 arm의 변환 입력에 주고(`--dict-all`), 판정 단계에서 생성 신호명을 사전 이름으로 정렬한다(`dict_align`, 기록에 exact, aliased, oov 남김).

## FRET 도구 되먹임 (v1.3 변경)
- 버리기(drop) 규칙을 없앴다. 어떤 문장이든 FRET 도구에 넣고, 거절되면 FRET 원문 메시지로 다시 쓰게 한다.
- 되먹임 프롬프트에는 그 단위의 FRET 시도 로그 전체(누적)가 들어간다. 모델은 이전 시도와 거절 사유를 모두 본다.
- 규칙 조립 arm에서 규칙 층이 문장을 못 만들면 규칙 글(+G) 자유 경로로 넘긴다(`fallback`, 라운드 0은 실패한 규칙 시도로 기록).
- 반복 상한 `NL2FRET_MAX_ROUNDS`(기본 5)는 무한 반복 방지용 안전장치다. 상한에 닿으면 `cap_reached`로 기록한다. 이 값은 해석한 것이며(추측입니다) 필요하면 환경 변수로 바꾼다.

## 판정과 반례
- 부분(part) 단위로 판정한다. 부분의 대표는 가장 좋은 쌍(SAME < PROOF < REFUTE < NEITHER < N/M < UND), 성공은 SAME 또는 PROOF.
- NEITHER, UND, N/M 판정에는 NuSMV 반례를 기록한다: `judge/counterexamples.jsonl`과 각 `judge_records.jsonl` 행의 `counterexamples`, `counterexample_status`.
  - `recorded`, `engine_gave_no_trace`, `not_available:<사유>`, `not_needed` 중 하나. 실제 NuSMV 트레이스는 Mac에서만 얻는다(샌드박스는 z3로 흐름만 확인).

## 단계별 추적
`bench/tools/trace_report.py --run RUN`이 단위마다 `RUN/trace/units/*.md`와 `RUN/trace/unit_trace.jsonl`을 만든다. 형식은 `docs/TRACE_FORMAT.md`.

## 실행
```
bash exp/fsm/run_fsm.sh dryrun       # 호출 계획만 (429 단위 확인)
bash exp/fsm/run_fsm.sh gen          # Claude Code CLI 생성 + FRET 도구
bash exp/fsm/run_fsm.sh inputs       # 문장별 LTL, 단위 목록
bash exp/fsm/run_fsm.sh judge        # NuSMV 자기점검 + 부분 판정
bash exp/fsm/run_fsm.sh trace        # 단계별 추적 + summary.md
```
환경 변수: `MODEL`(sonnet), `REPS`(3), `PARSER`(docker), `NUSMV`, `ENGINE`(nusmv). 중단 후 같은 명령으로 재개된다.

## 샌드박스에서 확인한 것과 못 한 것
- 확인: 모의 모델 + node FRET 파서 + z3로 39단위 흐름, 단위 테스트 14건 통과.
- 못 함: 실제 Claude 호출, Docker FRET, NuSMV 실행과 실제 반례 트레이스. Mac에서 확인해야 한다.
