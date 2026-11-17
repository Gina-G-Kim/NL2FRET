# v1.4 재시험 (관행 명시 버전)

판정 기준, 지표 정의, 알려진 한계는 `docs/ANALYSIS_PLAN.md`가 정한다(실행 결과를 보기 전에 고정). 이 문서는 무엇이 바뀌는지와 실행 순서만 적는다.

## 구조: approach를 늘리지 않는다
v1.3과 같은 11개 approach(DIRECT 1, 템플릿 +G 5, 템플릿 +R2 5)를 그대로 쓰고 프롬프트 버전만 v1.3에서 v1.4로 올린다. +V 같은 변형 arm이나 조건 A/B 분기를 만들지 않는다. 비교는 항상 "같은 11개 approach의 v1.3 대 v1.4"이다.

## 가설 (실행 전 고정)
H: v1.3의 큰 격차(NEITHER 36/39 등)의 주된 원인은 모델 능력이 아니라, NL이 시간적 의도(조건이 trigger인지, 조건이 참일 때마다 성립해야 하는지)를 정하지 않는다는 정보 부족이다.
근거: (1) 112 기준 행 중 NL에 조건 단어가 있는 행 52개, 기준이 조건 키워드를 유지한 행 9개. (2) FRET 공식 문서 condition.md가 조건을 regular(upon, when, where, if)와 holding(whenever)으로 정의한다. NASA 저자들이 같은 모호성을 FRET 시뮬레이터로 확인하고 `always satisfy (조건 => 응답)`으로 다시 쓴 기록: Mavridou et al., RE 2020, NTRS 20205000433, AP-003c. (3) v1.3 FSM에서 기준 39개 부분이 모두 EVERY_TIME 읽기인데 생성은 11개 중 9개 approach에서 EDGE 100%(분석기 `analyze_run.py`로 재계산).
사용자 승인: NASA와 NASA 연구진의 연구에서 보인 관행은 사용해도 된다(2026-11-15).

## v1.3에서 v1.4로 바뀌는 것 (이것뿐, 플래그 4개와 실행 옵션 1개)
| 변경 | 적용 arm | 내용 |
|---|---|---|
| 의도 선언 (`--intent-decl`) | 11개 전부 | NASA 논문 문장을 원문 그대로 인용하고 "이 과제에서 조건의 의도된 의미"라고 선언. 형식 선택은 모델의 몫. Direct와 +G는 FRETish 프롬프트 끝에, +R2는 슬롯 프롬프트 끝에 들어간다 |
| 조립 코드의 조건 키워드 (`--intent-decl`에 포함, `tpl_rules.INTENT_COND`) | +R2 5개 | 트리거 성격의 템플릿 절을 `when`/`if` 대신 `whenever`로 조립(규칙 `R2-COND-INTENT`, 출처 SOURCE). 공식 파서 확인: `whenever c ... immediately r` = `always satisfy c => r` (`H(c -> r)`), v1.3의 `when c ... immediately r`은 상승 에지만 요구 |
| +G 규칙 글 정합 (`--g-parity`) | +G 5개 | 규칙 글에서 `R-DEFTIME` 삭제(+R2에 없는 규칙이고 근거가 정답 풀 통계) |
| +R2 타이밍 슬롯 (`--tm-source-only`) | +R2 5개 | 도구 작성자의 선택 절차 V-2, V-3(스스로 "FRETish 출처에 없다"고 적음)과 그 절차용 맥락 필드(has_trigger, has_state)를 제거하고, 공식 문서 인용과 Adam et al. 2023의 사실 한 줄만 남긴다 |
| 근거 있는 규칙만 (`--sourced-rules-only`) | 11개 중 +G 5개, +R2 5개 | 근거를 만들 수 없는 사상 9개(R-EARS-WHERE, R-ADV-WHERE, R-SP-AFTERUNTIL, R-SP-RESP, R-SP-PREC, R-SP-BRESP, R-SP-BINV, R-SP-MINDUR, R-DEFTIME)를 도구가 정하지 않는다. +G 규칙문에서 빼고, +R2 조립은 거절(`rule_no_mapping`, `no_source:<규칙>`)해 자유 경로로 보낸다. 나머지 DEFAULT 30개는 문서 인용, 공식 파서 검증, 목표 형식 강제, 거절 중 하나의 근거가 있다(`ownership_table.py`, lint P-1b) |
| 단계 A 재사용 (`STAGEA_FROM=runs/fsm_20261113/gen`, 옵션) | 템플릿 10개 | v1.3의 단계 A 출력을 복사해 v1.3 대 v1.4 차이에서 변환 재생성 잡음을 뺀다. 프롬프트 해시가 다르면 중단 |
보충문(`--guide-sup`)과 D-5는 이 시험에 쓰지 않는다(기본 꺼짐). 플래그를 모두 끄면 v1.3 프롬프트와 바이트 단위로 같다(테스트가 해시로 확인).

## 귀속 (arm을 늘리지 않고 분리하는 방법)
- 결정 소유권 표(`tools/ownership_table.py`, 코드에서 생성)가 approach마다 결정 지점(조건 종류, 범위, 타이밍, 응답, 구성요소)을 누가 정하는지(모델, 규칙 글을 읽는 모델, 스크립트)를 보여 준다.
- DIRECT: 의도 선언만 바뀐다. +G: 의도 선언과 R-DEFTIME 삭제. +R2: 조건 키워드(스크립트), 타이밍 슬롯 프롬프트, 의도 선언. 결정 지점별 지표(`reading_same`, `ntiming_same`)로 분리한다. +R2의 읽기는 스크립트가 정하므로 H1 읽기 기준은 모델이 정하는 6개 approach에서만 센다.

## 실행 범위
- fsm: 13항목 x 11 x 3회 = 429단위. v1.3 결과(`runs/fsm_20261113`)가 이미 있어 v1.4만 새로 돌린다.
- confirm(선택): 비 FSM 48항목 x 11 x 1회 = 528단위, v13과 v14 둘 다 돌려야 한다(합 1056). 깨끗한 보류 집합이 아니다(`ANALYSIS_PLAN.md` 2절).

## 실행 순서 (Mac)
1. `make test`(34건), `make freeze-check`.
2. `python3 -m nl2fret.tools.ownership_table --fret-docs $FRETDOCS --out runs/ownership` (0 위반이어야 함), `python3 -m nl2fret.tools.rule_semantics_check --parser docker --engine nusmv --out runs/rule_semantics/result.json` (5개 검증 모두 PASS여야 함)
3. `ENGINE=nusmv bash scripts/run_intent.sh controls fsm v14` (판정기 대조, NuSMV 수치)
4. `bash scripts/run_intent.sh dryrun fsm v14`(429단위), `FRETDOCS=... PAPERRAW=... bash scripts/run_intent.sh lint fsm v14`
5. `STAGEA_FROM=runs/fsm_20261113/gen bash scripts/run_intent.sh all fsm v14` (gen, inputs, judge, trace, analyze)
6. 기준선 분석: `bash scripts/run_intent.sh analyze fsm v13 runs/fsm_20261113`
7. 비교: `BASE=runs/fsm_20261113/analysis bash scripts/run_intent.sh compare fsm v14 <v14 RUN>`


## 판정 조건 (대조 결과로 고정)
- 판정과 대조 모두 `CAP=512`(기본값 128은 NN-N3, NN-N4의 시간 창 200을 변환하지 못해 양성 대조가 3/112 실패). 판정기 코드는 바꾸지 않고 기존 `--cap` 옵션만 쓴다(`run_intent.sh`가 `CAP` 환경변수로 전달, 기본 512).
- 비교 기준 v1.3은 LLM을 다시 부르지 않고 같은 `CAP=512`, NuSMV로 판정 단계만 다시 실행해 `BASE`로 쓴다.
- 대조 결과(NuSMV 2.5.4): 양성 3종 0/112 거짓 실패, 항진식 0/112, 부정 0/112, 모순식 112/112 거짓 성공(엄격 성공이 걸러냄), 이동 33부분 중 6.

## 수정 이력 (이 패키지 수정판)
- `inputs`가 실행의 플래그(`snapshot/run_info.json`)를 읽어 재생한다(`make_judge_inputs.apply_run_flags`). 이전에는 v1.4 실행을 v1.3 기본값으로 재생해 `KeyError: 'slots'`가 났다.
- 재개 시 플래그가 첫 시작과 다르면 `run_pipeline.py`가 중단한다(`check_flags`).
- `run_intent.sh`: 경로를 호출한 폴더 기준 절대 경로로 풀고, 기본 실행 폴더 이름에서 날짜를 뺐으며, `copybase` 단계(판정 기록을 빼고 복사)와 `GENARGS`를 더했다.
- `rule_semantics_check.py`: 질의 폴더를 `--out` 옆으로, `--workdir` 옵션, 형태 하나가 실패해도 나머지를 판정, 엔진이 역할을 못 내면 메시지.
