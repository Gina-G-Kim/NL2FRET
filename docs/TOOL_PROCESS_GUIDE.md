# NL2FRET 도구 프로세스

## 1. 전체 구조

### 1.1 처리 흐름

```text
[입력] 자연어 요구사항 1건
   |
   v
[변환] 11개 방식으로 FRETish 문장 생성
   |   Direct    : 자연어 -> LLM -> FRETish
   |   규칙 글   : 자연어 -> LLM -> 템플릿 문장 -> LLM (FRETish 가이드, 규칙 글) -> FRETish
   |   규칙 조립 : 자연어 -> LLM -> 템플릿 문장 -> 스크립트 (구절 분해) -> LLM (구절별 식)
   |               -> 스크립트 (FRETish 조립) -> FRETish
   v
[검증] FRET 공식 파서에 문장 입력
   |   거절 -> 오류 메시지와 힌트를 LLM에 전달 -> 수정 문장 재입력 (수락까지 반복, 최대 5회)
   v
[LTL] 수락 문장에서 LTL 포뮬라 도출 (과거시제, 미래시제)
   v
[판정] 기준(NASA FRETish)의 LTL 포뮬라와 비교
   |   신호 이름 정렬 -> NuSMV 질의 3개 (equiv, sound, compl) -> 역할 SAME / PROOF / REFUTE / NEITHER
   v
[반례] 질의 거짓 시 NuSMV 반례를 로그로 기록 -> 사용자에게 제공
```

### 1.2 변환 방식

| 방식 | 템플릿 | arm 이름 | LLM 단계 | 스크립트 단계 |
|---|---|---|---|---|
| Direct | - | `DIRECT` | D | - |
| 규칙 글 | MASTeR, EARS, Adv-EARS, SPIDER, Boilerplate | `<템플릿>+G` 5개 | A, B | - |
| 규칙 조립 | MASTeR, EARS, Adv-EARS, SPIDER, Boilerplate | `<템플릿>+R2` 5개 | A, S | 구절 분해, FRETish 조립 |

- 단계 A: 자연어 -> 템플릿 문장 (템플릿마다 1회, 같은 템플릿의 규칙 글과 규칙 조립이 결과 공유)
- 단계 D: 자연어 -> FRETish (Direct)
- 단계 B: 템플릿 문장 -> FRETish (규칙 글)
- 단계 S: 구절 -> 식 (규칙 조립의 슬롯 값)
- 단계 F1..F5: FRET 거절 뒤 피드백 재호출
- 단위 = 항목 x 방식 x 반복. FSM 시험 13항목 x 11방식 x 3반복 = 429단위
- 규칙 조립에서 스크립트가 문장을 만들 수 없는 구절(비활성 규칙 구절 `no_source:*`)은 규칙 글 경로(`fallback`)로 변환

### 1.3 결정 주체

| 결정 지점 | Direct | 규칙 글 | 규칙 조립 |
|---|---|---|---|
| 조건 종류 (`when`, `whenever`, `if`) | 모델 | 모델 (규칙 글이 제약) | 스크립트 (v1.4: `whenever`) |
| 범위 (scope) | 모델 | 모델 (규칙 글이 제약) | 스크립트 |
| 타이밍 | 모델 | 모델 (규칙 글이 제약) | 타이밍 구절이 있으면 스크립트, 비어 있으면 모델 (슬롯 값) |
| 응답 구절 | 모델 | 모델 (규칙 글이 제약) | 모델 (슬롯 값) |
| 구성요소 | 모델 | 모델 | 스크립트 |
| 문장 표면 형식 | 모델 (FRETish 가이드) | 모델 (FRETish 가이드) | 스크립트 |

- 근거: 결정 소유권 표 (P2, `nl2fret_tool/bench/tools/ownership_table.py` 출력)
- 규칙 글 = 템플릿 구절을 FRETish 필드로 옮기는 규칙 목록(`R-EARS-WHEN` 등)을 문장으로 적어 프롬프트에 포함한 것
- 규칙 조립 = 같은 규칙 목록을 스크립트(`nl2fret_tool/bench/tpl_rules.py`)가 실행하는 것

### 1.4 프로세스 목록

| 번호 | 프로세스 | 입력 | 출력 | 실행 |
|---|---|---|---|---|
| P1 | 입력 데이터 준비 | 데이터셋, 딕셔너리 | 항목 파일, 기준 파일, 딕셔너리 텍스트 | `bench/tools/build_inputs.py` |
| P2 | 실행 전 점검 | 규칙표, 프롬프트, 기준, FRET 공식 문서 | 점검 결과 5종 | `ownership_table.py`, `rule_semantics_check.py`, `run_intent.sh` `lint`, `dryrun`, `controls` |
| P3 | 프롬프트 조립 | 가이드, 템플릿 가이드, 규칙, 의도 선언 | 시스템 프롬프트 17개 | `run_intent.sh gen` (시작 시 자동) |
| P4 | 템플릿 변환 (단계 A) | 자연어, 프롬프트 A | 템플릿 문장 | `run_intent.sh gen` |
| P5 | FRETish 변환 (단계 D, B, S) | 자연어 또는 템플릿 문장, 프롬프트 D, B, S2 | FRETish 문장 | `run_intent.sh gen` |
| P6 | FRET 검증과 피드백 (단계 F1..F5) | FRETish 문장 | 수락 문장, 오류 로그 | `run_intent.sh gen` |
| P7 | LTL 도출과 판정 입력 생성 | 호출 기록, 파서 결과 | 단위 파일, 문장별 LTL 파일 | `run_intent.sh inputs` |
| P8 | 신호 이름 정렬 | 생성 LTL, 딕셔너리, 기준 LTL | 정렬된 식 쌍 | `run_intent.sh judge` |
| P9 | 판정 | 정렬된 식 쌍 | 역할, 부분 결과 | `run_intent.sh judge` |
| P10 | 반례 기록 | NuSMV 질의 결과 | 반례 트레이스 | `run_intent.sh judge` |
| P11 | 추적 보고와 요약 | 위 단계의 기록 | 단위별 추적 파일, 요약 표 | `run_intent.sh trace` |
| P12 | 분석과 버전 비교 | 판정 기록, 판정기 대조 결과 | 분석 표, 비교 표 | `run_intent.sh` `analyze`, `compare` |
| P13 | 자산 버전 관리 | 수정한 자산 | 새 버전 폴더, 버전 색인 | 수동 |

- `run_intent.sh` = `nl2fret_tool/exp/fsm/run_intent.sh`, 형식 `bash exp/fsm/run_intent.sh <단계> fsm v14 <RUN 절대 경로>` (단계: `lint`, `dryrun`, `gen`, `inputs`, `judge`, `trace`, `controls`, `analyze`, `compare`)

### 1.5 용어

| 용어 | 뜻 |
|---|---|
| 항목 | 자연어 요구사항 1건 (예 `LM-01_FSM-N13`) |
| arm | 변환 방식의 코드 이름 (예 `DIRECT`, `EARS+G`, `EARS+R2`) |
| 슬롯 | 규칙 조립에서 LLM이 채우는 구절별 FRETish 식 (P5-3) |
| 피드백 | FRET 거절 뒤 오류 로그를 붙여 LLM을 다시 부르는 단계 F1..F5 (P6) |
| fallback | 규칙 조립이 문장을 만들 수 없을 때 규칙 글 경로로 변환하는 처리 |
| 템플릿 | 요구사항 문장 형식 5종 (MASTeR, EARS, Adv-EARS, SPIDER, Boilerplate) |
| FRETish | NASA FRET 도구의 구조화 영어. 형식 `[범위] [조건] 구성요소 shall [타이밍] satisfy 응답` |
| FRET 공식 파서 | FRETish 문장의 문법 검사와 LTL 변환을 수행하는 NASA FRET의 `FretSemantics.compile` |
| LTL 포뮬라 | 시간 논리식. FRET이 과거시제(`ltl_pt`)와 미래시제(`ltl_ft`) 두 가지로 출력 |
| 기준 (reference) | NASA가 작성한 FRETish 문장과 FRET이 컴파일한 LTL. 항목마다 부분과 버전 보유 |
| 부분, 버전 | 부분 = 항목 기준의 요구사항 단위, 버전 = 한 부분의 서로 다른 기준 문장 |
| 딕셔너리 | 챌린지별 신호 이름 표 (이름, 종류, 방향, 타입, 설명) |
| 단위 | 항목 x 방식 x 반복 |
| 역할 | 생성식과 기준식의 관계 (SAME, PROOF, REFUTE, NEITHER, UND, N/M). 정의 = P9 |
| 반례 | 질의가 거짓임을 보이는 NuSMV 상태열 |
| NuSMV | 모델 검사기 (2.6.0) |
| 호출 키 | `항목|방식|반복|단계` 형식의 호출 식별자 (예 `LM-01_FSM-N13|DIRECT|0|D`) |

## 2. 예제

- 예제 값: v1.4로 항목 `LM-01_FSM-N13`을 실행해 얻은 기록 (반복 0)

### 2.1 요구사항

```text
항목: LM-01_FSM-N13 (챌린지 01_FSM)
자연어: The sensor shall change states from TRANSITION to NOMINAL when the autopilot is requesting support (request) and the autopilot reports the correct active mode (mode).
출처: hbourbouh/lm_challenges original_models/1_fsm/1_fsm_reqs.docx, Requirements #13
```

- 항목 파일 위치: `nl2fret_tool/bench/data/lm_items_fsm.jsonl`, 원본 `nl2fret_tool/data/dataset/lm_dataset_final.jsonl`

### 2.2 기준

```text
기준 부분 1, 버전 1 (FSM-013)
  FRETish: FSM_Sensor shall always satisfy (senstate = sen_transition_state & request & activeMode) => SENSTATE = sen_nominal_state
  LTL (과거시제): (H ((((senstate = sen_transition_state) & request) & activeMode) -> (SENSTATE = sen_nominal_state)))
  LTL (미래시제): (LAST V ((((senstate = sen_transition_state) & request) & activeMode) -> (SENSTATE = sen_nominal_state)))
기준 부분 1, 버전 2 (FSM-013@FiniteStateMachine)
  FRETish: FSM shall always satisfy (senstate = sen_transition_state & request) => SENSTATE = sen_nominal_state
  LTL (과거시제): (H (((senstate = sen_transition_state) & request) -> (SENSTATE = sen_nominal_state)))
  LTL (미래시제): (LAST V (((senstate = sen_transition_state) & request) -> (SENSTATE = sen_nominal_state)))
```

- 위치: `nl2fret_tool/data/reference/lm_reference_with_ltl.jsonl`
- 부분 1개, 버전 2개. 생성 문장은 버전마다 비교되고, 부분의 결과는 가장 좋은 버전의 결과

### 2.3 딕셔너리 (예제에 쓰이는 이름)

| 이름 | 종류 | 방향 | 타입 | 구성요소 | 설명 또는 정의 |
|---|---|---|---|---|---|
| `request` | signal | Input | Boolean/boolean | FSM_Sensor | Secondary indication from autopilot on current mode of operation. |
| `activeMode` | signal | Input | boolean | FSM_Sensor | - |
| `mode` | signal | Input | Boolean/boolean | FSM_Sensor | Indication from autopilot on current mode of operation. |
| `senstate` | signal | Input | Double/double | FSM_Sensor | Sensor State variable, Indication of prior value. |
| `SENSTATE` | signal | Input/Output | Integer/double | FSM_Sensor | Sensor State |
| `sen_transition_state` | constant | Internal | double | FSM_Sensor | 정의 1.0 |
| `sen_nominal_state` | constant | Internal | double | FSM_Sensor | 정의 0.0 |
| `FSM_Sensor` | component | - | - | FSM_Sensor | FRET component that the requirement sentences name as subjec ... |
| `FSM` | component | - | - | FSM | FRET component that the requirement sentences name as subjec ... |

- 위치: `nl2fret_tool/data/dictionary/lm_dictionary.csv` (01_FSM 45행), LLM 입력용 표 `nl2fret_tool/bench/data/sigdict.json`의 키 `01`

### 2.4 예제에서 보이는 흐름

- Direct: FRET 거절 2회, 피드백 2회 후 수락, 역할 v1 SAME/v2 UND
- 규칙 글 (EARS+G): FRET 거절 1회, 피드백 1회 후 수락, 역할 v1 NEITHER/v2 UND
- 규칙 조립 (EARS+R2): 슬롯 오류 1회, 피드백 1회 후 조립 문장 수락, 역할 v1 PROOF/v2 UND
- 11개 방식의 결과 종합 = P11

## 3. 프로세스별 설명

v1.4 실행 명령 순서 (`nl2fret_tool/`에서 실행):

```text
python3 bench/tools/build_inputs.py                                                              # P1
python3 bench/tools/ownership_table.py --fret-docs $FRETDOCS --out <소유권 표 폴더>                 # P2
python3 bench/tools/rule_semantics_check.py --parser docker --engine nusmv --nusmv $NUSMV --out <JSON 경로>   # P2
bash exp/fsm/run_intent.sh lint     fsm v14 $RUN
bash exp/fsm/run_intent.sh dryrun   fsm v14 $RUN
NUSMV=$NUSMV ENGINE=nusmv CAP=512 CTRLDIR=<판정기 대조 폴더> bash exp/fsm/run_intent.sh controls fsm v14 $RUN
STAGEA_FROM=<기준선 gen 폴더> bash exp/fsm/run_intent.sh gen fsm v14 $RUN
bash exp/fsm/run_intent.sh inputs   fsm v14 $RUN
NUSMV=$NUSMV ENGINE=nusmv CAP=512 bash exp/fsm/run_intent.sh judge   fsm v14 $RUN
bash exp/fsm/run_intent.sh trace    fsm v14 $RUN
NUSMV=$NUSMV ENGINE=nusmv CTRLDIR=<판정기 대조 폴더> bash exp/fsm/run_intent.sh analyze fsm v14 $RUN
BASE=<기준선 analysis 폴더> bash exp/fsm/run_intent.sh compare fsm v14 $RUN
```

- `$RUN` = 실행 결과 폴더의 절대 경로 (스크립트가 `bench/` 또는 `judging/`로 이동한 뒤 경로를 해석)
- `$FRETDOCS` = FRET 공식 문서 10개 파일 폴더 (P2 입력)
- `$NUSMV` = NuSMV 2.6.0을 호출하는 실행 파일 (마지막 인자로 `.smv` 경로를 받음, Docker 래퍼 `assets/experiment_scripts/v1/NuSMV_docker_wrapper.sh`)
- `<기준선 ...>` = 비교 기준 실행(v1.3)의 폴더

### P1. 입력 데이터 준비

- 하는 일
  - 자연어 요구사항 61항목과 항목별 기준(NASA FRETish 문장, FRET 컴파일 LTL)을 항목 파일로 정리
  - FSM 챌린지 13항목 파일과 비 FSM 48항목 파일 분리
  - 챌린지별 딕셔너리 표를 LLM 입력용 텍스트로 변환
- 입력: `nl2fret_tool/data/dataset/lm_dataset_final.jsonl`, `nl2fret_tool/data/dictionary/lm_dictionary.csv`
- 출력
  - `nl2fret_tool/bench/data/lm_items.jsonl` (61행), `lm_items_fsm.jsonl` (13행), `lm_items_nonfsm.jsonl` (48행)
  - `nl2fret_tool/bench/data/sigdict.json`, `nl2fret_tool/data/reference/sigdict.json` (챌린지 번호별 딕셔너리 표 텍스트)
  - `nl2fret_tool/data/reference/lm_reference_with_ltl.jsonl` (기준, 61행)
- 코드: `nl2fret_tool/bench/tools/build_inputs.py` (원본 파일 생성: `nl2fret_tool/data/dataset/build_dataset.py`, `nl2fret_tool/data/dictionary/build_dict.py`, 딕셔너리 원문 추출: `nl2fret_tool/bench/tools/make_sigdict.py`)
- 메인 디렉터리 사본: `assets/dataset/v1/`, `assets/dictionary/v1/`, `assets/reference/v1/` (파일 내용 동일)
- 예제

```text
nl2fret_tool/bench/data/lm_items_fsm.jsonl (1행):
{"id": "LM-01_FSM-N13", "raw_nl": "The sensor shall change states from TRANSITION to NOMINAL when the autopilot is requesting support (request) and the autopilot reports the correct active mode (mode).", "family": "01_FSM", "challenge": "01_FSM"}

nl2fret_tool/data/reference/lm_reference_with_ltl.jsonl (1행의 구조):
{"id": "LM-01_FSM-N13", "challenge": "01_FSM", "mapping_basis": "rationale", "gt_parts": [[{"reqid": "FSM-013", "fretish": "FSM_Sensor shall always satisfy (senstate = sen_transition_state & request & activeMode) => SENSTATE = sen_nominal_state", "ltl_pt": "...", "ltl_ft": "..."}, {"reqid": "FSM-013@FiniteStateMachine", "fretish": "FSM shall always satisfy (senstate = sen_transition_state & request) => SENSTATE = sen_nominal_state", "ltl_pt": "...", "ltl_ft": "..."}]]}

nl2fret_tool/bench/data/sigdict.json 의 키 "01" (처음 4행 / 전체 46행):
name | kind | direction | type | description | definition
activeMode | signal | Input | boolean |  | 
apfail | signal | Input | Boolean/boolean | Failure indication from an external source | 
good | signal | Input/Output | Boolean/boolean | Prior sensor output.  When false indicates a detected fault. ; False indicates an unsafe situation where a hazard may exist | 
```

### P2. 실행 전 점검

- 하는 일
  - 결정 소유권 표: 규칙 52개가 결정하는 지점(조건 종류, 범위, 타이밍, 응답, 구성요소)과 결정 주체(모델, 규칙 글을 읽는 모델, 스크립트) 산출, 모든 활성 규칙의 근거 보유 확인
  - 규칙 의미 검증: 규칙이 전제하는 동치 5건을 FRET 파서의 LTL과 NuSMV로 확인
  - 프롬프트 lint P-1..P-6: 규칙 근거 장부, 규칙 글과 코드 규칙의 ID 일치, 보충문 중복, 인용 원문 일치, 기준 읽기 성향, 기준 FRETish 6-gram 누출 검사
  - 판정기 대조: 정답을 아는 쌍(기준 자신, 이중 부정, 자기 논리곱, 항진식, 모순식, 부정, 다른 부분의 기준)을 판정기에 입력해 오판 비율 측정
  - 호출 계획 확인 (dryrun): 항목 x 방식 x 반복 단위 수 출력
- 입력: 규칙표 `nl2fret_tool/bench/tpl_rules.py`, 규칙 근거 `nl2fret_tool/bench/data/rule_sources.json`, FRET 공식 문서 10개 파일(저장소 `NASA-SW-VnV/fret`의 커밋 `cf0f913`, 경로 `fret-electron/docs/_media/user-interface/examples`), 논문 대목 `nl2fret_tool/docs/paper_passage_AP003c.txt`, 기준 `nl2fret_tool/data/reference/lm_reference_with_ltl.jsonl`
- 출력: 소유권 표, 규칙 의미 검증 결과 JSON (`--out`로 지정, 도구 동봉본 `nl2fret_tool/bench/data/rule_semantics_results.json`), `prompt_lint.json`, 판정기 대조 폴더(`controls.jsonl`, `controls.md`, `controls_summary.json`), dryrun 출력
- 코드: `nl2fret_tool/bench/tools/ownership_table.py`, `rule_semantics_check.py`, `prompt_lint.py`, `judge_controls.py`, `selftest.py` (규칙 층 골든 문장 시험), `rule_probe.py` (규칙 출력 모양의 파서 수락 조사), `nl2fret_tool/exp/fsm/run_intent.sh`
- 데이터: `nl2fret_tool/bench/data/rule_sources.json`, `nl2fret_tool/bench/data/rule_semantics_results.json`, `nl2fret_tool/docs/controls_nusmv512/` (기대 대조표)
- 예제 (v1.4 시험 실행의 점검 출력)

예제 항목과의 연결
- 규칙 조립에서 예제의 `WHEN ...` 절은 규칙 `R-EARS-WHEN`으로 읽혀 조건 키워드 `whenever` (규칙 `R2-COND-INTENT`)로 조립됨
- 규칙 의미 검증 `S3` (`whenever p ... immediately r` = `always satisfy p => r`)가 예제 Direct 문장과 기준 문장의 동치(P9 역할 SAME)에 대응

소유권 표의 조건 종류 행 (소유권 표 출력)

```text
| decision point | DIRECT | +G (free FRETish) | +R2 (script assembly) |
| condition kind | model | model, rule text constrains | script (assembly keyword map R-*-WHEN/IF, R2-COND-INTENT) |
```

소유권 표의 규칙 집계

```text
rules: 52; by status: DEFAULT 39, OBSERVED 8, SOURCE 4, FRET 1
- active in v1.4 with evidence (official document quote and/or official parser check): 30
- switched off in v1.4 (--sourced-rules-only; the model decides these phrases): 9: R-EARS-WHERE, R-ADV-WHERE, R-SP-AFTERUNTIL, R-SP-RESP, R-SP-PREC, R-SP-BRESP, R-SP-BINV, R-SP-MINDUR, R-DEFTIME
- active in v1.4 with NO evidence (must be 0): 0: 
unclassified rules (must be 0): 0 []
evidence quotes verified verbatim in the FRET docs: 34; not found: []
```

규칙 의미 검증 (규칙 의미 검증 출력)

```text
S1a PASS upon, when, if, where give the same requirement (timing immediately)
S1b PASS upon, when, if, where give the same requirement (timing eventually)
S1c PASS upon, when, if, where give the same requirement (timing within)
S2 PASS `unless p` is `if !(p)`
S3 PASS `whenever p ... immediately r` is `always satisfy p => r`
```

프롬프트 lint (lint 출력)

```text
PASS     P-1 rule provenance
PASS     P-1b rule evidence quotes and decision points
PASS     P-2 +G vs R2 rule parity
PASS     P-3 guide duplication and tool observations
PASS     P-4 citation verbatim check
PASS     P-4b intent declaration quote
PASS     P-5 reference reading profile
PASS     P-6 answer-leak n-gram
```

판정기 대조 (판정기 대조 폴더의 `controls.md`)

| 대조 | n | SAME | PROOF | REFUTE | NEITHER | N/M | UND | 오판 비율 |
|---|---|---|---|---|---|---|---|---|
| C+ID | 112 | 112 | 0 | 0 | 0 | 0 | 0 | 0/112 |
| C+NN | 112 | 112 | 0 | 0 | 0 | 0 | 0 | 0/112 |
| C+AND | 112 | 112 | 0 | 0 | 0 | 0 | 0 | 0/112 |
| C-TAUT | 112 | 0 | 0 | 112 | 0 | 0 | 0 | 0/112 |
| C-CONTR | 112 | 0 | 112 | 0 | 0 | 0 | 0 | 112/112 |
| C-NEG | 112 | 0 | 0 | 0 | 112 | 0 | 0 | 0/112 |
| C-SHIFT | 33 | 6 | 0 | 0 | 21 | 0 | 6 | 6/33 |

- 대조 설명: C+ID 기준 자신, C+NN 이중 부정, C+AND 자기 논리곱 (기대 SAME) / C-TAUT 항진식, C-CONTR 모순식, C-NEG 부정, C-SHIFT 같은 항목의 다른 부분 (기대 성공 아님)

호출 계획 확인 (dryrun 출력)

```text
13 items x 11 arms x 3 reps = 429 units
```

### P3. 프롬프트 조립

- 하는 일
  - 실행 시작 시 단계별 시스템 프롬프트 17개 조립, 해시 기록
  - 사용자 메시지는 호출마다 단계별 함수로 생성
- 입력
  - 고정 문장: `nl2fret_tool/bench/common.py` (`TASK_A`, `TASK_B`, `TASK_D`, `RULES_COMMON`, `SCHEMA_A`, `SCHEMA_B`), `nl2fret_tool/bench/prompts3.py` (`SURFACE_RULE`, `SLOT_SYSTEM_R2`, `D_RULES`, `SLOT_D_RULES`, `GUIDE_HEAD`, 피드백 문장)
  - FRETish 가이드 `nl2fret_tool/bench/prompts/fretish_guide.md`
  - 템플릿 가이드 5개 `nl2fret_tool/bench/templates/{masteR,ears,adv_ears,spider,boilerplate}.md`
  - 규칙 글 = 규칙표 `nl2fret_tool/bench/tpl_rules.py`의 `RULES` 설명
  - 의도 선언 `nl2fret_tool/bench/prompts/intent_declaration.md`
- 출력: `$RUN/gen/snapshot/system_prompt_*.txt` 17개, `$RUN/gen/snapshot/run_info.json` (프롬프트 해시, 옵션)
- 메인 디렉터리 사본: `prompts/current/system_prompts/` (같은 17개와 `MANIFEST.csv`, `tools/render_prompts.py`로 생성)
- 코드: `nl2fret_tool/bench/run_pipeline.py` (`build_prompts`), `nl2fret_tool/bench/prompts3.py` (`build_system_A3`, `build_system_B3`, `build_system_D3`, `slot_system_r2`), `nl2fret_tool/bench/common.py` (`build_system`)
- 프롬프트 구성 (v1.4 실행 기준)

| 파일 (`prompts/current/system_prompts/`, 실행 시 `$RUN/gen/snapshot/`과 동일) | 단계 | 구성 (순서) | 크기 |
|---|---|---|---|
| `system_prompt_A_<템플릿>.txt` (5개) | A | TASK, GENERAL RULES, OUTPUT SCHEMA, TEMPLATE SPECIFICATION, SURFACE RULES | 바이트: MASTeR 5531, EARS 4048, Adv-EARS 5110, SPIDER 7475, Boilerplate 9851 |
| `system_prompt_D_none.txt` (1개) | D | TASK, GENERAL RULES, OUTPUT SCHEMA, FRETISH GUIDE, INTENT, SIGNAL DICTIONARY RULES | 10497 |
| `system_prompt_B_<템플릿>+G.txt` (5개) | B | TASK, GENERAL RULES, OUTPUT SCHEMA, FRETISH GUIDE, TEMPLATE SPECIFICATION, INTENT, MECHANICAL MAPPING RULES, SIGNAL DICTIONARY RULES | 바이트: MASTeR 16290, EARS 14703, Adv-EARS 15830, SPIDER 18360, Boilerplate 20452 |
| `system_prompt_S2_none.txt` (1개) | S | TASK, EXPRESSION SYNTAX, INTENT, SIGNAL DICTIONARY RULES | 4512 |
| `system_prompt_BF_<템플릿>.txt` (5개) | 규칙 조립의 fallback | 해당 `system_prompt_B_<템플릿>+G.txt`와 같은 내용 | 바이트: MASTeR 16290, EARS 14703, Adv-EARS 15830, SPIDER 18360, Boilerplate 20452 |

- 사용자 메시지 형식

| 단계 | 사용자 메시지 | 생성 함수 |
|---|---|---|
| A | `NATURAL LANGUAGE REQUIREMENT:` + 자연어 | `user_prompt_A` |
| D | `NATURAL LANGUAGE REQUIREMENT:` + 자연어 + `SIGNAL DICTIONARY` 표 | `user_prompt_D` |
| B | `TEMPLATE:` + 템플릿 이름 + `TEMPLATE SENTENCES:` + 번호 붙인 템플릿 문장 + `SIGNAL DICTIONARY` 표 | `user_prompt_B` |
| S | `ITEMS (JSON)` (구절 목록과 슬롯 요청) + `SIGNAL DICTIONARY` 표 | `user_prompt_S` |
| F1..F5 | 원래 사용자 메시지 + `FRET FEEDBACK LOG` (시도별 답과 FRET 판정, 누적) | `user_prompt_feedback_log` |

- v1.4 옵션 (`run_pipeline.py` 인자, v1.4 실행 설정)

| 옵션 | 효과 |
|---|---|
| `--dict-all` | 모든 방식의 FRETish 단계에 딕셔너리 표(사용자 메시지)와 딕셔너리 규칙 D-1..D-4(시스템 프롬프트) 추가 |
| `--intent-decl` | D, B(+G), S2 프롬프트에 의도 선언 추가, 규칙 조립의 조건 키워드를 `whenever`로 조립 (규칙 `R2-COND-INTENT`) |
| `--g-parity` | 규칙 글에서 규칙 `R-DEFTIME` 제외 |
| `--tm-source-only` | 규칙 조립의 타이밍 슬롯 안내를 공식 문서 인용 사실로 구성 |
| `--sourced-rules-only` | 근거 있는 규칙만 활성. 비활성 규칙 9개(`R-EARS-WHERE`, `R-ADV-WHERE`, `R-SP-AFTERUNTIL`, `R-SP-RESP`, `R-SP-PREC`, `R-SP-BRESP`, `R-SP-BINV`, `R-SP-MINDUR`, `R-DEFTIME`)에 해당하는 구절은 조립 거절 후 규칙 글 경로로 이동, 규칙 글 텍스트에서도 제외 |
| `--stage-a-from <이전 gen 폴더>` | 이전 실행의 단계 A 행 재사용 (프롬프트 해시 일치 시) |
| `--guide-sup` (꺼짐) | `fretish_guide_supplement.md` 추가 |

### P4. 템플릿 변환 (단계 A)

- 하는 일: 자연어 요구사항을 템플릿 5종의 문장으로 변환 (LLM 호출, 템플릿마다 1회)
- 입력: 시스템 프롬프트 `system_prompt_A_<템플릿>.txt` (템플릿 가이드 포함), 사용자 메시지 `NATURAL LANGUAGE REQUIREMENT: <자연어>`
- 출력: JSON `{"sentences", "requirement_type", "split_reason", "choices", "unmapped_content"}`, 기록 위치 `$RUN/gen/calls.jsonl` (호출 키 `항목|템플릿|반복|A`)
- 규모: 항목 x 템플릿 5 x 반복 = FSM 시험 195호출. v1.4 실행은 v1.3 실행의 195행을 복사해 재사용
- 코드: `nl2fret_tool/bench/run_pipeline.py` (`phase_A`, `reuse_stage_a`), `nl2fret_tool/bench/cli.py` (CLI 호출), `nl2fret_tool/bench/common.py` (`user_prompt_A`, `parse_output`)
- 프롬프트: `nl2fret_tool/bench/templates/*.md` 5개 (+ 표면 규칙 SA-1, SA-2)
- 예제

템플릿 5종의 변환 결과 (호출 키 `LM-01_FSM-N13|<템플릿>|0|A`)

```text
MASTeR      : IF the autopilot is requesting support (request) and the autopilot reports the correct active mode (mode), the sensor SHALL change states from TRANSITION to NOMINAL.
EARS        : WHEN the autopilot is requesting support (request) and the autopilot reports the correct active mode (mode), the sensor shall change states from TRANSITION to NOMINAL.
Adv-EARS    : When the autopilot is requesting support (request) and the autopilot reports the correct active mode (mode), the sensor shall change states from TRANSITION to NOMINAL.
SPIDER      : Globally, it is always the case that if the autopilot is requesting support (request) and the autopilot reports the correct active mode (mode) holds, then the sensor changes states from TRANSITION to NOMINAL eventually holds.
Boilerplate : If the autopilot is requesting support (request) and the autopilot reports the correct active mode (mode), the sensor shall change states from TRANSITION to NOMINAL.
```

호출 하나의 원본 답 (EARS, 호출 키 `LM-01_FSM-N13|EARS|0|A`)

```text
{"sentences":["WHEN the autopilot is requesting support (request) and the autopilot reports the correct active mode (mode), the sensor shall change states from TRANSITION to NOMINAL."],"requirement_type":"Event-driven","split_reason":"","choices":[{"point":"keyword for triggering condition","chosen":"WHEN"}],"unmapped_content":[]}
```

- 사용자 메시지: `NATURAL LANGUAGE REQUIREMENT:` + 자연어, 프롬프트 해시 `b58a1fa5caf235be`, `reused_from` = v1.3 실행의 같은 행

### P5. FRETish 변환

- 세 방식의 공통 출력 형식: JSON `{"fretish", "fields", "choices", "unmapped_content"}`

#### P5-1. Direct (단계 D)

- 하는 일: 자연어에서 LLM이 FRETish 가이드를 읽고 곧바로 FRETish 변환
- 입력: 시스템 프롬프트 `system_prompt_D_none.txt` (FRETish 가이드, 딕셔너리 규칙, 의도 선언), 사용자 메시지 (자연어 + 딕셔너리 표)
- 출력: FRETish 문장, 호출 키 `항목|DIRECT|반복|D`
- 예제

사용자 메시지 (`LM-01_FSM-N13|DIRECT|0|D`)

```text
NATURAL LANGUAGE REQUIREMENT:
The sensor shall change states from TRANSITION to NOMINAL when the autopilot is requesting support (request) and the autopilot reports the correct active mode (mode).

SIGNAL DICTIONARY (the same table for every requirement of the challenge, no selection; columns: name | kind | direction | type | description | definition):
name | kind | direction | type | description | definition
activeMode | signal | Input | boolean |  | 
apfail | signal | Input | Boolean/boolean | Failure indication from an external source | 
good | signal | Input/Output | Boolean/boolean | Prior sensor output.  When false indicates a detected fault. ; False indicates an unsafe situation where a hazard may exist | 
limits | signal | Input | Boolean/boolean | External indication to sensor on faulty condition impeding safe operation. | 
... (딕셔너리 표 45행)
```

LLM 답 (원본)

```text
{"fretish":["whenever (senstate = sen_transition_state) & request & mode FSM_Sensor shall immediately satisfy SENSTATE = sen_nominal_state"],"fields":[{"scope":"","condition":"whenever (senstate = sen_transition_state) & request & mode","component":"FSM_Sensor","timing":"immediately","response":"SENSTATE = sen_nominal_state"}],"choices":[{"point":"component for 'the sensor'","chosen":"FSM_Sensor"},{"point":"condition keyword for holding-condition intent","chosen":"whenever (not when)"},{"point":"representing prior state 'TRANSITION'","chosen":"senstate = sen_transition_state (prior-value input signal)"}],"unmapped_content":[]}
```

#### P5-2. 규칙 글 (단계 B)

- 하는 일: P4의 템플릿 문장을 LLM이 FRETish 가이드와 규칙 글을 읽고 FRETish로 변환
- 입력: 시스템 프롬프트 `system_prompt_B_<템플릿>+G.txt` (FRETish 가이드, 템플릿 가이드, 의도 선언, 규칙 글, 딕셔너리 규칙), 사용자 메시지 (템플릿 문장 + 딕셔너리 표)
- 출력: FRETish 문장, 호출 키 `항목|<템플릿>+G|반복|B`
- 예제

사용자 메시지 (`LM-01_FSM-N13|EARS+G|0|B`)

```text
TEMPLATE: EARS
TEMPLATE SENTENCES:
1. WHEN the autopilot is requesting support (request) and the autopilot reports the correct active mode (mode), the sensor shall change states from TRANSITION to NOMINAL.

SIGNAL DICTIONARY (the same table for every requirement of the challenge, no selection; columns: name | kind | direction | type | description | definition):
name | kind | direction | type | description | definition
activeMode | signal | Input | boolean |  | 
apfail | signal | Input | Boolean/boolean | Failure indication from an external source | 
good | signal | Input/Output | Boolean/boolean | Prior sensor output.  When false indicates a detected fault. ; False indicates an unsafe situation where a hazard may exist | 
limits | signal | Input | Boolean/boolean | External indication to sensor on faulty condition impeding safe operation. | 
... (딕셔너리 표 45행)
```

LLM 답 (원본 JSON의 `fretish`, `choices` 필드)

```text
fretish: ["whenever (request) & (mode) FSM_Sensor shall satisfy (senstate = sen_transition_state) & (SENSTATE = sen_nominal_state)"]
choices: [{"point": "condition keyword", "chosen": "whenever (holding condition) per challenge intent note"}, {"point": "component identifier", "chosen": "FSM_Sensor (dictionary component matching subject 'the sensor')"}, {"point": "response for 'change states from TRANSITION to NOMINAL'", "chosen": "conjunction of prior-state signal senstate=sen_transition_state and current-state signal SENSTATE=sen_nominal_state"}]
```

#### P5-3. 규칙 조립 (단계 S와 스크립트)

- 하는 일
  - 스크립트가 템플릿 문장을 구절로 분해 (`parse_template`), 구절마다 슬롯 이름 부여 (`slot_requests`)
  - LLM이 구절을 FRETish 식(슬롯 값)으로 변환
  - 스크립트가 슬롯 값 검사 (`lint_slots`) 후 규칙표대로 FRETish 문장 조립 (`assemble`)
  - 슬롯 오류는 P6의 피드백 대상, 비활성 규칙의 구절은 규칙 글 경로(`fallback`)로 이동
- 입력: 템플릿 문장, 시스템 프롬프트 `system_prompt_S2_none.txt`, 사용자 메시지 `ITEMS (JSON)` + 딕셔너리 표
- 출력: 슬롯 값 JSON, 조립된 FRETish 문장, 호출 키 `항목|<템플릿>+R2|반복|S`
- 코드: `nl2fret_tool/bench/tpl_rules.py` (`parse_template`, `slot_requests`, `lint_slots`, `assemble`, `RULES`), `nl2fret_tool/bench/fretlint.py` (식 검사 규칙), `nl2fret_tool/bench/prompts3.py` (`user_prompt_S`, `parse_slot_output`)
- 예제

스크립트가 템플릿 문장에서 읽은 구절 (`parse_template`)

```text
{"template": "EARS", "rules": ["R-EARS-WHEN"], "clauses": [{"kw": "WHEN", "kind": "trigger", "text": "the autopilot is requesting support (request) and the autopilot reports the correct active mode (mode)", "slot": "c1"}], "subject": "sensor"}
```

사용자 메시지 (`LM-01_FSM-N13|EARS+R2|0|S`, 딕셔너리 표 제외)

```text
ITEMS (JSON):
[
 {
  "i": 1,
  "template": "EARS",
  "context": {
   "subject": "sensor",
   "verb_phrase_is_slot_r": true
  },
  "slots": {
   "c1": "the autopilot is requesting support (request) and the autopilot reports the correct active mode (mode)",
   "r": "change states from TRANSITION to NOMINAL",
   "tm": "(choose always, immediately or eventually)"
  },
  "state_slots": []
 }
]
```

LLM 답: 슬롯 값 (원본)

```text
{"items": [{"i": 1, "slots": {"c1": "request & mode", "r": "senstate = sen_transition_state & SENSTATE = sen_nominal_state", "tm": "immediately"}}], "unmapped_content": []}
```

스크립트의 슬롯 검사 결과 (`lint_slots`)

```text
rule layer failure: [{'code': 'slot_lint', 'detail': 'c1:E-RESERVED:mode'}]
```

피드백(P6) 뒤 LLM의 슬롯 값 (`LM-01_FSM-N13|EARS+R2|0|F1`)과 스크립트가 조립한 FRETish 문장

```text
{"items": [{"i": 1, "slots": {"c1": "request & activeMode", "r": "senstate = sen_transition_state & SENSTATE = sen_nominal_state", "tm": "immediately"}}], "unmapped_content": []}

attempt 1 (F1): whenever request & activeMode sensor shall immediately satisfy senstate = sen_transition_state & SENSTATE = sen_nominal_state
```

### P6. FRET 검증과 피드백

- 하는 일
  - 단계 라운드마다 모든 FRETish 문장을 FRET 공식 파서(`FretSemantics.compile`, Docker 이미지 `fret-lab`)에 일괄 입력
  - 거절 문장의 FRET 원문 오류 메시지와 도구 힌트(파서 메시지는 `fretlint.py`의 `hints_for`, 슬롯 오류는 `prompts3.py`의 `HINT_PRE`)를 시도별로 누적한 `FRET FEEDBACK LOG` 작성
  - 누적 로그를 원래 사용자 메시지에 붙여 LLM 재호출 (F1, F2, ..., 최대 5회, 상한 도달 시 `cap_reached` 기록)
  - 전 문장 수락 시 종료
  - 규칙 조립의 슬롯 오류(`slot_lint`)도 같은 방식으로 피드백
- 입력: FRETish 문장 (또는 슬롯 값), 단계별 시스템 프롬프트 (P3), 누적 로그
- 출력: 수락 문장, 호출 기록 `$RUN/gen/calls.jsonl` (키 `...|F1` .. `...|F5`), 파서 결과 캐시 `$RUN/gen/parser_cache.jsonl`, 실행 상태 `$RUN/gen/run_state.json`
- 코드: `nl2fret_tool/bench/run_pipeline.py` (`phase_rounds`, `phase_fallback`, `history_of`), `nl2fret_tool/bench/fretparse.py`, `nl2fret_tool/bench/fret_check/tools/fret_compile.py`, `nl2fret_tool/bench/fret_check/tools/fretjs/fret_parse_full.js`, `nl2fret_tool/bench/units3.py`, `nl2fret_tool/bench/prompts3.py` (`user_prompt_feedback_log`), `nl2fret_tool/bench/fretlint.py`
- 외부 도구: Docker 이미지 `fret-lab:latest` (FRET v3.1.0, 빌드 `docker/fret-lab/`)
- 예제 (Direct, 거절 2회)

FRET 파서 판정 (추적 파일 S3 블록)

```text
- round 0 (D): REJECTED: whenever (senstate = sen_transition_state) & request & mode FSM_Sensor shall immediately satisfy SENSTATE = sen_nominal_state
  - FRET: extraneous input 'mode' expecting {'!', '~', '(', 'true', 'false', '-', AT, IF, ID, NUMBER}; mismatched input 'immediately' expecting {THE, ID}
- round 1 (F1): REJECTED: whenever ((senstate = sen_transition_state) & request & mode) FSM_Sensor shall immediately satisfy SENSTATE = sen_nominal_state
  - FRET: mismatched input 'mode' expecting {'!', '~', '(', 'true', 'false', '-', AT, IF, ID, NUMBER}
- round 2 (F2): accepted: whenever ((senstate = sen_transition_state) & request & activeMode) FSM_Sensor shall immediately satisfy SENSTATE = sen_nominal_state
- rejected sentence attempts: 2; feedback calls: 2; cap reached: False
```

F2 호출의 사용자 메시지 중 누적 로그 (`LM-01_FSM-N13|DIRECT|0|F2`)

```text
FRET FEEDBACK LOG (read every entry before you answer)
The official FRET parser has rejected 2 of your answers to this input so far. Each entry below is one of your answers followed by the verdict of the parser for each sentence.
The parser text is the original message of FRET. Do not repeat a sentence or a construct that appears as REJECTED in any entry of this log.

--- ATTEMPT 1 (D) ---
your answer:
(이전 답 JSON 생략)
FRET verdict per sentence:
1. REJECTED: 'whenever (senstate = sen_transition_state) & request & mode FSM_Sensor shall immediately satisfy SENSTATE = sen_nominal_state'
   message: extraneous input 'mode' expecting {'!', '~', '(', 'true', 'false', '-', AT, IF, ID, NUMBER}; mismatched input 'immediately' expecting {THE, ID}
   hint: A token was found where the grammar does not allow it (see the quoted token). Check keywords and punctuation: scope keywords in, before, after, notin, onlyIn, onlyBefore, onlyAfter; condition keywords when, whenever, if, upon, unless; one component identifier; the word shall; optional timing; the word satisfy; a Boolean expression.

--- ATTEMPT 2 (F1) ---
your answer:
(이전 답 JSON 생략)
FRET verdict per sentence:
1. REJECTED: 'whenever ((senstate = sen_transition_state) & request & mode) FSM_Sensor shall immediately satisfy SENSTATE = sen_nominal_state'
   message: mismatched input 'mode' expecting {'!', '~', '(', 'true', 'false', '-', AT, IF, ID, NUMBER}
   hint: The word mode is only allowed directly after the identifier of a scope, as in: in roll_hold mode. A scope takes ONE identifier. Do not use mode as a variable and do not put words between in and mode.
   hint: A token was found where the grammar does not allow it (see the quoted token). Check keywords and punctuation: scope keywords in, before, after, notin, onlyIn, onlyBefore, onlyAfter; condition keywords when, whenever, if, upon, unless; one component identifier; the word shall; optional timing; the word satisfy; a Boolean expression.

Return the corrected answer in exactly the same JSON schema as before, for ALL items. Keep accepted sentences unchanged. Change only what is needed to remove the
rejections, and do not change the meaning, names or numbers of the input. If something truly cannot be expressed, list it in "unmapped_content".
```

F2 답에서 LLM이 기록한 선택

```text
{"point": "identifier 'mode' is a reserved grammar keyword (scope syntax 'in <ID> mode'), always rejected as ID", "chosen": "substituted dictionary signal activeMode (same 'active mode' concept) in its place"}
```

- 예제 (규칙 글, 거절 1회)

FRET 파서 판정 (추적 파일 S3 블록)

```text
- round 0 (B): REJECTED: whenever (request) & (mode) FSM_Sensor shall satisfy (senstate = sen_transition_state) & (SENSTATE = sen_nominal_state)
  - FRET: no viable alternative at input '(mode'
- round 1 (F1): accepted: whenever (request) & (activeMode) FSM_Sensor shall satisfy (senstate = sen_transition_state) & (SENSTATE = sen_nominal_state)
- rejected sentence attempts: 1; feedback calls: 1; cap reached: False
```

F1 답에서 LLM이 기록한 선택 (`LM-01_FSM-N13|EARS+G|0|F1`)

```text
{"point": "identifier for '(mode)' parenthetical", "chosen": "activeMode (dictionary signal for active mode; 'mode' alone is a reserved word rejected by parser)"}
```

- 예제 (규칙 조립, 슬롯 오류 1회)

스크립트 판정 (추적 파일 S3 블록)

```text
- round 0 (S): did not reach FRET: None
- round 1 (F1): accepted: whenever request & activeMode sensor shall immediately satisfy senstate = sen_transition_state & SENSTATE = sen_nominal_state
- rejected sentence attempts: 0; feedback calls: 1; cap reached: False
```

F1 호출의 사용자 메시지 중 누적 로그 (`LM-01_FSM-N13|EARS+R2|0|F1`)

```text
FRET FEEDBACK LOG (read every entry before you answer)
The official FRET parser has rejected 1 of your answers to this input so far. Each entry below is one of your answers followed by the verdict of the parser for each sentence.
The parser text is the original message of FRET. Do not repeat a sentence or a construct that appears as REJECTED in any entry of this log.

--- ATTEMPT 1 (S) ---
your answer:
(이전 답 JSON 생략)
FRET verdict per sentence:
1. REJECTED: '(no sentence)'
   message: slot_lint: c1:E-RESERVED:mode
   hint: A slot value breaks the expression syntax listed in the task (see the message: E-WORD = a word instead of an operator, E-UNITINEXPR = a unit after a number, E-FUNC = a function that does not exist, E-BADCHAR = a character that is not allowed, E-MISSING = a slot was not answered). Fix the named slot only.
```

- `did not reach FRET` = 슬롯 오류로 파서에 입력되지 않은 시도

### P7. LTL 도출과 판정 입력 생성

- 하는 일
  - 호출 기록에서 단위(항목 x 방식 x 반복)별 최종 문장과 상태 재구성 (라운드, 거절 횟수, 피드백 횟수, fallback)
  - 단위의 최종 문장을 FRET 공식 파서로 컴파일해 LTL 포뮬라(과거시제, 미래시제) 도출
- 입력: `$RUN/gen/calls.jsonl`, `$RUN/gen/parser_cache.jsonl`, `$RUN/gen/snapshot/run_info.json` (실행 옵션), 항목 파일 `nl2fret_tool/bench/data/lm_items_fsm.jsonl`
- 출력
  - `$RUN/inputs/units.json` (단위 목록: 항목, 방식, 반복, 상태, 최종 문장, 피드백 횟수, fallback, 거절 횟수)
  - `$RUN/inputs/fret_ltl_gen.jsonl` (문장별 `parser_ok`, `ltl_pt`, `ltl_ft`)
  - `$RUN/inputs/unit_state.jsonl` (단위별 전체 라운드 기록)
- 코드: `nl2fret_tool/bench/tools/make_judge_inputs.py`, `nl2fret_tool/bench/units3.py`, `nl2fret_tool/bench/fret_check/tools/fret_compile.py`
- 예제

`$RUN/inputs/units.json`의 단위 하나

```text
{"item": "LM-01_FSM-N13", "arm": "DIRECT", "rep": 0, "status": "parsed", "texts": ["whenever ((senstate = sen_transition_state) & request & activeMode) FSM_Sensor shall immediately satisfy SENSTATE = sen_nominal_state"], "n_feedback": 2, "fallback": null, "cap_reached": false, "n_rejected_sentence_attempts": 2, "pending": false}
```

`$RUN/inputs/fret_ltl_gen.jsonl`의 문장 하나

```text
{"sentence": "whenever ((senstate = sen_transition_state) & request & activeMode) FSM_Sensor shall immediately satisfy SENSTATE = sen_nominal_state", "parser_ok": true, "ltl_pt": "(H ((((senstate = sen_transition_state) & request) & activeMode) -> (SENSTATE = sen_nominal_state)))", "ltl_ft": "(LAST V ((((senstate = sen_transition_state) & request) & activeMode) -> (SENSTATE = sen_nominal_state)))", "error": null}
```

### P8. 신호 이름 정렬

- 하는 일
  - 생성 LTL의 식별자를 챌린지 딕셔너리와 대조: `exact` (딕셔너리 이름, 유지), `aliased` (대소문자, 밑줄 차이를 무시하면 딕셔너리 이름 1개와 일치, 딕셔너리 이름으로 변경), `oov` (딕셔너리 밖, 유지하고 목록화)
  - 생성 변수와 기준 변수의 대응 결정 (anchor 모드: 이름과 타입이 기준에 있는 변수는 이름 유지, 나머지는 같은 타입의 미사용 기준 변수에 1대1 대응)
  - 대응 후보 0개: 역할 UND (`atomization_mismatch`)
- 입력: `$RUN/inputs/fret_ltl_gen.jsonl`, 딕셔너리 `nl2fret_tool/data/dictionary/lm_dictionary.csv`, 기준 LTL `nl2fret_tool/data/reference/lm_reference_with_ltl.jsonl`
- 출력: 판정 기록의 `dict_alignment` (exact, aliased, oov), `alignment` (모드, 대응표, 후보 수)
- 코드: `nl2fret_tool/judging/nl2fret_judge/dict_align.py`, `align.py`, `abstraction.py`, `ap_check.py`
- 예제

버전 1 쌍 (`LM-01_FSM-N13|DIRECT|0|s0|p1|v1`)의 딕셔너리 정렬과 변수 대응

```text
dict_alignment: {"exact": ["SENSTATE", "activeMode", "request", "sen_nominal_state", "sen_transition_state", "senstate"], "aliased": {}, "oov": []}
alignment: {"mode": "anchor", "n_candidates": 1, "anchored": 6, "und": null}
alignment.mapping: {"SENSTATE": "SENSTATE", "activeMode": "activeMode", "request": "request", "sen_nominal_state": "sen_nominal_state", "sen_transition_state": "sen_transition_state", "senstate": "senstate"}
```

버전 2 쌍 (`LM-01_FSM-N13|DIRECT|0|s0|p1|v2`): 생성식에 기준 버전 2에 없는 변수 `activeMode` 포함, 대응 후보 0개

```text
role: "UND"
und_reason: "atomization_mismatch"
nm_detail: {"message": "unmatched gen vars 1 > unmatched ref vars 0"}
alignment: {"mode": "anchor", "n_candidates": 0}
```

### P9. 판정

- 하는 일
  - 판정 전 자기점검 5쌍 (`identical`, `contrapositive`, `stronger_pred`, `weaker_pred`, `converse`) 실행
  - 단위의 각 문장을 기준 부분의 모든 버전과 쌍으로 판정
  - 쌍마다 LTL을 불리언 식으로 추상화한 뒤 NuSMV 질의 3개 실행
    - `equiv`: 기준 <-> 생성
    - `sound`: 기준 -> 생성 (거짓이면 ALARM: 기준은 성립, 생성은 위반)
    - `compl`: 생성 -> 기준 (거짓이면 MISS: 생성은 성립, 기준은 위반)
  - 질의 결과로 역할 결정, 부분의 대표 = 버전 중 가장 좋은 역할 (SAME < PROOF < REFUTE < NEITHER < N/M < UND)
  - 부분 성공 = SAME 또는 PROOF

| sound | compl | 역할 | 뜻 |
|---|---|---|---|
| 성립 | 성립 | SAME | 기준과 동치 |
| 거짓 | 성립 | PROOF | 생성식이 기준식보다 강함 |
| 성립 | 거짓 | REFUTE | 생성식이 기준식보다 약함 |
| 거짓 | 거짓 | NEITHER | 서로 다른 의미 |
| 정렬 후보 0개 | - | UND | 비교 불가 (`und_reason`) |
| 엔진 판정 실패 | - | N/M | 시간 초과 등 (`nm_reason`) |

- 입력: `$RUN/inputs/units.json`, `fret_ltl_gen.jsonl`, 기준 `nl2fret_tool/data/reference/lm_reference_with_ltl.jsonl`, 딕셔너리 `nl2fret_tool/data/dictionary/lm_dictionary.csv`
- 출력: `$RUN/judge/judge_records.jsonl` (쌍별 기록), `part_results.jsonl` (부분별 대표), `smv/<sha256>.smv` (질의 파일), `run_header.json`, `$RUN/judge_selfcheck/`
- 코드: `nl2fret_tool/judging/nl2fret_judge/cli.py` (`judge-parts`), `parts.py`, `judge.py`, `engines.py`, `ltl_engines.py`, `recorder.py`, `selfcheck.py`, `units.py`, `nl2fret_tool/judging/legacy/judge2.py`, `judge4.py`, `judge5.py`, `judge_pt.py` (정렬 후보 생성)
- 외부 도구: NuSMV 2.6.0 (Docker 이미지 `cst-nusmv:local`, 빌드 `docker/cst-nusmv/`), 질의당 시간 제한 120초, 시간 구간 확장 상한 `--cap 512`
- 예제

자기점검 (판정 실행 출력)

```text
PASS identical (True, True) SAME
PASS contrapositive (True, True) SAME
PASS stronger_pred (False, True) PROOF
PASS weaker_pred (True, False) REFUTE
PASS converse (False, False) NEITHER
SELFCHECK PASSED
```

예제 3개 단위의 쌍별 질의 결과 (`$RUN/judge/judge_records.jsonl`)

| 방식 | 기준 버전 | equiv | sound | compl | 역할 |
|---|---|---|---|---|---|
| `DIRECT` | v1 | 성립 | 성립 | 성립 | SAME |
| `DIRECT` | v2 | - | - | - | UND |
| `EARS+G` | v1 | 거짓 | 거짓 | 거짓 | NEITHER |
| `EARS+G` | v2 | - | - | - | UND |
| `EARS+R2` | v1 | 거짓 | 거짓 | 성립 | PROOF |
| `EARS+R2` | v2 | - | - | - | UND |

부분 결과 (`$RUN/judge/part_results.jsonl`, Direct 단위)

```text
{"part": 1, "n_versions": 2, "role": "SAME", "success": true, "representative": "LM-01_FSM-N13|DIRECT|0|s0|p1|v1", "pairs": [{"pair_id": "LM-01_FSM-N13|DIRECT|0|s0|p1|v1", "role": "SAME"}, {"pair_id": "LM-01_FSM-N13|DIRECT|0|s0|p1|v2", "role": "UND"}]}

n_parts_success: 1, all_parts_success: True
```

### P10. 반례 기록

- 하는 일
  - 거짓인 질의마다 NuSMV 반례(상태열)를 파싱해 질의 종류별로 기록
  - 반례 종류: `sound` (ALARM), `compl` (MISS), `equiv` (두 식이 다름)
  - 역할 NEITHER, UND, N/M은 반례 기록 대상 (`counterexample_required`), PROOF와 REFUTE는 거짓 질의가 있으면 함께 기록
  - 상태 코드: `recorded` (기록됨), `not_needed` (SAME), `not_available:<사유>` (UND, N/M)
- 입력: P9의 NuSMV 질의 결과
- 출력: `$RUN/judge/counterexamples.jsonl` (쌍별 반례), 판정 기록의 `counterexamples`, `smv/*.smv`
- 사용자 제공: `counterexamples.jsonl`, 단위별 추적 파일(`$RUN/trace/units/*.md`)의 S6 블록 (반례 종류, 상태 수, 질의 파일 경로)
- 코드: `nl2fret_tool/judging/nl2fret_judge/engines.py` (`parse_nusmv_trace`), `judge.py`, `parts.py`
- 예제 (규칙 글, 역할 NEITHER)

판정 기록 (`LM-01_FSM-N13|EARS+G|0|s0|p1|v1`)

```text
role: NEITHER
counterexample_required: true
counterexample_status: "recorded"
반례 종류와 상태 수: sound (5개 상태), compl (6개 상태), equiv (5개 상태)
```

`sound` 반례의 질의 파일 (`$RUN/judge/smv/09335b5a...smv`)

```text
MODULE main
VAR
  b_activeMode : boolean;
  b_request : boolean;
  c_508b8683df : boolean;
  c_a6c886cf2d : boolean;
LTLSPEC G (((H (((c_a6c886cf2d & b_request) & b_activeMode) -> c_508b8683df))) -> (((H (! (b_request & b_activeMode))) | (! ((! (c_a6c886cf2d & c_508b8683df)) S ((! (c_a6c886cf2d & c_508b8683df)) & (b_request & b_activeMode)))))))
```

`sound` 반례 (뜻: the reference holds and the generated formula is violated (ALARM))

| 상태 | b_activeMode | b_request | c_508b8683df | c_a6c886cf2d |
|---|---|---|---|---|
| 1.1 | TRUE | TRUE | TRUE | TRUE |
| 1.2 | TRUE | TRUE | FALSE | FALSE |
| 1.3 | TRUE | TRUE | FALSE | TRUE |
| 1.4 | FALSE | FALSE | FALSE | FALSE |
| 1.5 | FALSE | FALSE | FALSE | FALSE |

- 변수 의미: `b_*` = 신호(불리언), `c_*` = 비교식 하나(예 `senstate = sen_transition_state`). 대응표 = 판정 기록의 `atom_abstraction`: {"request": "b_request", "activeMode": "b_activeMode", "senstate = sen_transition_state": "c_a6c886cf2d", "SENSTATE = sen_nominal_state": "c_508b8683df"}

`$RUN/judge/counterexamples.jsonl`의 같은 쌍의 행 (필드)

```text
{"pair_id": "LM-01_FSM-N13|EARS+G|0|s0|p1|v1", "item": "LM-01_FSM-N13", "arm": "EARS+G", "rep": 0, "part": 1, "version": 1, "reference_id": "FSM-013", "role": "NEITHER", "required": true, "status": "recorded", "record": "judge_records.jsonl#LM-01_FSM-N13|EARS+G|0|s0|p1|v1"}
```

### P11. 추적 보고와 요약

- 하는 일
  - 단위마다 S0..S6 블록(입력, 템플릿, FRETish, FRET 루프, LTL, 딕셔너리 정렬, 판정)과 원본 로그 위치를 기록
  - 방식별 요약 표 생성 (단위 수, 부분 수, 성공 수, 역할 수, 거절 수, fallback 수)
- 입력: `$RUN/gen/`, `$RUN/inputs/`, `$RUN/judge/`
- 출력: `$RUN/trace/INDEX.md`, `$RUN/trace/units/<항목>__<방식>__rep<반복>.md` (429개), `$RUN/trace/unit_trace.jsonl`, `$RUN/summary.md`, `$RUN/summary.json`
- 코드: `nl2fret_tool/bench/tools/trace_report.py`, 형식 문서 `nl2fret_tool/docs/TRACE_FORMAT.md`
- 예제 (Direct 단위의 추적 파일 `$RUN/trace/units/LM-01_FSM-N13__DIRECT__rep0.md`)

```markdown
# LM-01_FSM-N13 | DIRECT | rep 0

## S0 input
- natural language: The sensor shall change states from TRANSITION to NOMINAL when the autopilot is requesting support (request) and the autopilot reports the correct active mode (mode).
- challenge: 01_FSM
- logs: `gen/snapshot/items_used.jsonl` (LM-01_FSM-N13); `data/dictionary/lm_dictionary.csv` (challenge 01_FSM); `gen/snapshot/run_info.json` (prompt_hashes)

## S2 fretish
- attempt 0 (D): whenever (senstate = sen_transition_state) & request & mode FSM_Sensor shall immediately satisfy SENSTATE = sen_nominal_state
- attempt 1 (F1): whenever ((senstate = sen_transition_state) & request & mode) FSM_Sensor shall immediately satisfy SENSTATE = sen_nominal_state
- attempt 2 (F2): whenever ((senstate = sen_transition_state) & request & activeMode) FSM_Sensor shall immediately satisfy SENSTATE = sen_nominal_state
- logs: `gen/calls.jsonl` (LM-01_FSM-N13|DIRECT|0|D); `gen/calls.jsonl` (LM-01_FSM-N13|DIRECT|0|F1); `gen/calls.jsonl` (LM-01_FSM-N13|DIRECT|0|F2)

## S3 fret_loop
- round 0 (D): REJECTED: whenever (senstate = sen_transition_state) & request & mode FSM_Sensor shall immediately satisfy SENSTATE = sen_nominal_state
  - FRET: extraneous input 'mode' expecting {'!', '~', '(', 'true', 'false', '-', AT, IF, ID, NUMBER}; mismatched input 'immediately' expecting {THE, ID}
- round 1 (F1): REJECTED: whenever ((senstate = sen_transition_state) & request & mode) FSM_Sensor shall immediately satisfy SENSTATE = sen_nominal_state
  - FRET: mismatched input 'mode' expecting {'!', '~', '(', 'true', 'false', '-', AT, IF, ID, NUMBER}
- round 2 (F2): accepted: whenever ((senstate = sen_transition_state) & request & activeMode) FSM_Sensor shall immediately satisfy SENSTATE = sen_nominal_state
- rejected sentence attempts: 2; feedback calls: 2; cap reached: False
- logs: `gen/parser_cache.jsonl` (sentence text)

## S4 ltl
- whenever ((senstate = sen_transition_state) & request & activeMode) FSM_Sensor shall immediately satisfy SENSTATE = sen_nominal_state
  - past time: (H ((((senstate = sen_transition_state) & request) & activeMode) -> (SENSTATE = sen_nominal_state)))
  - future time: (LAST V ((((senstate = sen_transition_state) & request) & activeMode) -> (SENSTATE = sen_nominal_state)))
- logs: `inputs/fret_ltl_gen.jsonl` (sentence)

## S5 dictionary_alignment
- sentence 0: {"exact": ["SENSTATE", "activeMode", "request", "sen_nominal_state", "sen_transition_state", "senstate"], "aliased": {}, "oov": []}
- logs: `judge/judge_records.jsonl` (pair_id -> dict_alignment)

## S6 judge
- part 1: representative role SAME (LM-01_FSM-N13|DIRECT|0|s0|p1|v1)
  - LM-01_FSM-N13|DIRECT|0|s0|p1|v1 (FSM-013): SAME equiv=True sound=True compl=True counterexample=not_needed
  - LM-01_FSM-N13|DIRECT|0|s0|p1|v2 (FSM-013@FiniteStateMachine): UND equiv=None sound=None compl=None counterexample=not_available:atomization_mismatch
- logs: `judge/judge_records.jsonl` (pair_id); `judge/smv/<smv_sha256>.smv` (query files); `judge/counterexamples.jsonl` (pair_id); `judge/part_results.jsonl` (LM-01_FSM-N13|DIRECT|0)
```

- 예제 (항목 `LM-01_FSM-N13` 반복 0의 11개 방식 결과)

| 방식 | 최종 FRETish 문장 | FRET 거절 | 피드백 | fallback | 역할 |
|---|---|---|---|---|---|
| `DIRECT` | `whenever ((senstate = sen_transition_state) & request & activeMode) FSM_Sensor shall immediately satisfy SENSTATE = sen_nominal_state` | 2 | 2 | - | v1 SAME/v2 UND |
| `MASTeR+G` | `whenever request & activeMode & senstate = sen_transition_state the FSM_Sensor shall satisfy SENSTATE = sen_nominal_state` | 1 | 1 | - | v1 REFUTE/v2 UND |
| `EARS+G` | `whenever (request) & (activeMode) FSM_Sensor shall satisfy (senstate = sen_transition_state) & (SENSTATE = sen_nominal_state)` | 1 | 1 | - | v1 NEITHER/v2 UND |
| `Adv-EARS+G` | `whenever (request) & (activeMode) FSM_Sensor shall immediately satisfy (senstate = sen_transition_state) & (SENSTATE = sen_nominal_state)` | 1 | 1 | - | v1 PROOF/v2 UND |
| `SPIDER+G` | `whenever (request) & (activeMode) FSM_Sensor shall eventually satisfy (senstate = sen_transition_state) & (SENSTATE = sen_nominal_state)` | 2 | 2 | - | v1 NEITHER/v2 UND |
| `Boilerplate+G` | `whenever (request) & (activeMode) FSM_Sensor shall immediately satisfy senstate = sen_transition_state & SENSTATE = sen_nominal_state` | 1 | 1 | - | v1 PROOF/v2 UND |
| `MASTeR+R2` | `whenever request & activeMode sensor shall immediately satisfy senstate = sen_transition_state & SENSTATE = sen_nominal_state` | 0 | 1 | - | v1 PROOF/v2 UND |
| `EARS+R2` | `whenever request & activeMode sensor shall immediately satisfy senstate = sen_transition_state & SENSTATE = sen_nominal_state` | 0 | 1 | - | v1 PROOF/v2 UND |
| `Adv-EARS+R2` | `whenever request & activeMode sensor shall immediately satisfy senstate = sen_transition_state & SENSTATE = sen_nominal_state` | 0 | 1 | - | v1 PROOF/v2 UND |
| `SPIDER+R2` | `system shall always satisfy (request & activeMode) => (senstate = sen_transition_state & SENSTATE = sen_nominal_state)` | 1 | 1 | no_source:R-SP-RESP | v1 PROOF/v2 UND |
| `Boilerplate+R2` | `whenever request & activeMode sensor shall immediately satisfy senstate = sen_transition_state & SENSTATE = sen_nominal_state` | 0 | 1 | - | v1 PROOF/v2 UND |

- FRET 거절 = FRET 파서가 거절한 문장 시도 수, 피드백 = 피드백 호출 수 (슬롯 오류 포함)

### P12. 분석과 버전 비교

- 하는 일
  - 분석 (`analyze`): 부분마다 관대 성공(SAME 또는 PROOF), 엄격 성공(관대 성공이면서 생성식이 만족 가능하고 이름 변경이 딕셔너리 정렬 범위 안인 것), 결정 지점(범위, 조건 종류, 타이밍, 읽기) 일치, 엄격 성공 외 부분의 원인 라벨 1개 산출
  - 비교 (`compare`): 기준선 분석과 새 분석에서 방식별, 항목별 비율(반복 x 부분 평균)을 만들고, 새 버전이 좋아진 항목 수를 한쪽 정확 부호 검정 (유의수준 0.05, 동률 제외)
  - 지표: `reading_same`, `ntiming_same` (결정 지점 일치), `strict` (엄격 성공), `lenient`, `same_only` (보고용)
- 입력: 분석 = `$RUN/judge/`, `$RUN/inputs/`, `$RUN/gen/calls.jsonl`, 판정기 대조 폴더, `nl2fret_tool/data/audit/item_validity_audit.csv`, 기준 / 비교 = 두 실행의 `analysis/` 폴더
- 출력: `$RUN/analysis/analysis.md`, `$RUN/analysis/part_analysis.jsonl`, `$RUN/comparison/comparison.md`, `$RUN/comparison/comparison.json`
- 코드: `nl2fret_tool/bench/tools/analyze_run.py`, `decision_points.py`, `compare_runs.py`, 기준 문서 `nl2fret_tool/docs/ANALYSIS_PLAN.md`
- 예제 (분석: 항목 `LM-01_FSM-N13` 반복 0)

`$RUN/analysis/part_analysis.jsonl` (부분 1, 반복 0)

| 방식 | 역할 | 관대 성공 | 엄격 성공 | 생성 (조건 / 타이밍 / 읽기) | 기준 (조건 / 타이밍 / 읽기) | 차이 지점 | 원인 라벨 |
|---|---|---|---|---|---|---|---|
| `DIRECT` | SAME | True | True | whenever / immediately / EVERY_TIME | none / always / EVERY_TIME | - | - |
| `EARS+G` | NEITHER | False | False | whenever / omitted / EVERY_TIME | none / always / EVERY_TIME | ntiming | DECISION:ntiming |
| `EARS+R2` | PROOF | True | True | whenever / immediately / EVERY_TIME | none / always / EVERY_TIME | - | - |

- 읽기 값: `EDGE` (조건이 거짓에서 참이 될 때 요구), `EVERY_TIME` (조건이 참인 동안 매번 요구), `UNCOND`, `UNLESS`

- 예제 (비교의 입력 비율: 항목 `LM-01_FSM-N13`, 기준선 v1.3 실행 3반복)

| 방식 | 엄격 성공 비율 | `reading_same` 비율 |
|---|---|---|
| `DIRECT` | 0/3 = 0.000 | 0/3 = 0.000 |
| `EARS+G` | 0/3 = 0.000 | 0/3 = 0.000 |
| `EARS+R2` | 0/3 = 0.000 | 0/3 = 0.000 |

- 같은 형식으로 11개 방식 전체의 비율 산출
- 기준선 분석 파일: 기준선 실행의 `analysis/part_analysis.jsonl`
- 새 실행 쪽 비율: `$RUN/analysis/part_analysis.jsonl`에서 같은 식으로 산출, 13개 항목의 비율쌍으로 부호 검정

### P13. 자산 버전 관리

- 하는 일
  - 자산(데이터셋, 딕셔너리, 기준 등)은 `assets/<자산>/v<N>/`에 파일과 `SHA256SUMS`로 보관
  - 자산 수정 시 `assets/<자산>/v<N+1>/` 생성, 이전 버전은 `archive/<자산>/v<N>/`로 이동
  - `VERSIONS.md`의 현재 버전, 경로, sha256, 변경 사유, 변경을 일으킨 실험 열 갱신
- 입력: 수정한 자산, `VERSIONS.md`
- 출력: `assets/`, `archive/`, `VERSIONS.md`
- 위치: `VERSIONS.md`, `assets/`, `archive/README.md`, 절차 문서 `nl2fret_tool/docs/DATA_VERSIONING.md`
- 예제 (예제 항목의 입력 데이터 3종의 등록 행)

| 자산 | 현재 버전 | 경로 | sha256 | 변경 사유 | 실험 |
|---|---|---|---|---|---|
| dataset | v1 | `assets/dataset/v1/` | `672be262e256a4ff806926c88043f1083de988992bb96e209f9b4fc6dc8f0274` | 데이터셋 고정(61 항목, 기준 112행, EB-N2 제외, EB-N4 추가, AP-1.2와 AP-1.8 복원, EUL-N1 7부, EUL-N4, EUL-N8에 NASA-lus 판 추가) | 023_fsm_run_v13 |
| dictionary | v1 | `assets/dictionary/v1/` | `ed334341445376396ccbd7c9340fed2c6776dc926b2cfbf59d0c4691da087e51` | 딕셔너리 564 항목 | 023_fsm_run_v13 |
| reference | v1 | `assets/reference/v1/` | `761bd6a0319df8be29cb570105164b5db970d3c34a3e350c22302938eaf195c3` | 데이터셋 고정(61 항목, 기준 112행)에서 만든 기준 파일과 딕셔너리 564 항목에서 만든 딕셔너리 | 023_fsm_run_v13 |

## 4. 파일 목록

### 4.1 외부 도구

| 구성 | 버전 | 위치와 호출 | 프로세스 |
|---|---|---|---|
| Claude Code CLI | 2.1.274 | 실행 파일 `claude`, 호출 코드 `bench/cli.py` (`claude -p --output-format json --system-prompt <프롬프트> --tools "" --no-session-persistence`), 모델 인자 `sonnet` | P4-P6 |
| FRET 공식 파서 | FRET v3.1.0 | Docker 이미지 `fret-lab:latest`, 빌드 레시피 `docker/fret-lab/` (`Dockerfile`, `fret.sh`, `README.md`, `LICENSE`) | P2, P6, P7 |
| NuSMV | 2.6.0 | Docker 이미지 `cst-nusmv:local`, 빌드 레시피 `docker/cst-nusmv/` (`Dockerfile`, `nusmv_context.sha256`, `README.md`) | P2, P9, P10, P12 |
| z3-solver | 5.3.3.0 | Python 패키지 (`nl2fret_tool/requirements.txt`: z3-solver, pytest) | P2, P9, P12 |
| Python | 3.10 이상 | `nl2fret_tool/requirements.txt`의 패키지를 설치한 환경 | 전체 |
| NuSMV 호출 래퍼 | - | `assets/experiment_scripts/v1/NuSMV_docker_wrapper.sh` (컨테이너 `cst-nusmv:local`로 NuSMV 실행, 판정 단계의 `NUSMV` 인자) | P2, P9, P10, P12 |

### 4.2 코드

경로 기준: `nl2fret_tool/`. 프로세스 열은 3절의 번호.

| 파일 | 역할 | 프로세스 |
|---|---|---|
| `bench/run_pipeline.py` | 생성 파이프라인 본체: 프롬프트 조립, 단계 A, D, B, S, F 호출 순서, 파서 연동, 호출 기록, 재개 | P3-P6 |
| `bench/cli.py` | Claude Code CLI 호출, 세션 한도 감지와 대기, 재시도 | P4-P6 |
| `bench/common.py` | 공통 프롬프트 문장, 시스템 프롬프트 조립 `build_system`, 사용자 프롬프트(A, B, D), 출력 JSON 파서 | P3-P5 |
| `bench/prompts3.py` | 방식(arm) 정의, 규칙 글 텍스트, 슬롯 프롬프트 S2, 피드백 프롬프트, v1.4 옵션 변수 | P3, P5, P6 |
| `bench/tpl_rules.py` | 규칙표 52개, 템플릿 문장 분해, 슬롯 요청, 슬롯 검사, FRETish 조립 | P5 |
| `bench/fretlint.py` | FRETish 식 검사 규칙, FRET 오류 메시지별 힌트 | P5, P6 |
| `bench/fretparse.py` | FRET 공식 파서 호출(Docker)과 디스크 캐시, 모의 파서 | P6 |
| `bench/units3.py` | 호출 기록에서 단위 상태(라운드, 거절, fallback) 재구성 | P6, P7 |
| `bench/fret_check/tools/fret_compile.py` | Docker `fret-lab`에서 FRET 파서 실행, LTL 출력 | P6, P7 |
| `bench/fret_check/tools/fretjs/fret_parse_full.js` | 컨테이너 안에서 `FretSemantics.compile` 실행 | P6 |
| `bench/fret_check/tools/fretjs/stub/product-iterable/index.js` | 파서 실행에 필요한 모듈의 대체 파일 | P6 |
| `bench/tools/build_inputs.py` | 항목 파일, 딕셔너리 텍스트, 기준 파일 생성 | P1 |
| `bench/tools/make_sigdict.py` | LM 챌린지 문서(.docx)에서 딕셔너리 표 추출 | P1 |
| `data/dataset/build_dataset.py` | 데이터셋 파일 생성 | P1 |
| `data/dictionary/build_dict.py` | 딕셔너리 파일 생성 | P1 |
| `bench/tools/make_preflight_items.py` | 예비 시험용 6항목 파일 생성 | P1 |
| `bench/tools/ownership_table.py` | 결정 소유권 표 생성, 근거 없는 활성 규칙 검사 | P2 |
| `bench/tools/rule_semantics_check.py` | 규칙 의미 검증 (FRET 파서 LTL 동치를 NuSMV로 확인) | P2 |
| `bench/tools/prompt_lint.py` | 프롬프트 lint P-1..P-6 | P2 |
| `bench/tools/judge_controls.py` | 판정기 대조 (정답을 아는 쌍으로 오판 비율 측정) | P2 |
| `bench/tools/selftest.py` | 규칙 층 골든 문장 시험 | P2 |
| `bench/tools/rule_probe.py` | 규칙 출력 모양의 파서 수락 조사 | P2 |
| `bench/tools/make_judge_inputs.py` | 호출 기록에서 판정 입력(단위, 문장별 LTL, 단위 상태) 생성 | P7 |
| `judging/nl2fret_judge/__init__.py` | 판정 모듈 버전 표기 | P9 |
| `judging/nl2fret_judge/__main__.py` | 판정 모듈 실행 진입점 | P9 |
| `judging/nl2fret_judge/cli.py` | 명령 `selfcheck`, `judge`, `judge-parts`, `aggregate` | P9 |
| `judging/nl2fret_judge/units.py` | 단위와 기준 로드 | P9 |
| `judging/nl2fret_judge/parts.py` | 부분 단위 판정, 대표 쌍 선택, 반례 기록 파일 | P9, P10 |
| `judging/nl2fret_judge/judge.py` | 쌍 판정, 역할 결정, 반례 상태 | P9, P10 |
| `judging/nl2fret_judge/dict_align.py` | 딕셔너리 정렬 (exact, aliased, oov) | P8 |
| `judging/nl2fret_judge/align.py` | 변수 대응 후보 생성 (anchor 모드) | P8 |
| `judging/nl2fret_judge/abstraction.py` | LTL의 불리언 추상화 | P8, P9 |
| `judging/nl2fret_judge/ap_check.py` | 원자 집합 불일치 기록 | P8 |
| `judging/nl2fret_judge/engines.py` | NuSMV와 z3 질의 엔진, 질의 파일 작성, 반례 파서 | P9, P10 |
| `judging/nl2fret_judge/ltl_engines.py` | LTL 파서와 NuSMV 구문 변환 | P9 |
| `judging/nl2fret_judge/recorder.py` | 판정 기록 파일 작성과 재개 | P9 |
| `judging/nl2fret_judge/selfcheck.py` | 자기점검 5쌍 | P9 |
| `judging/nl2fret_judge/aggregate.py` | 판정 기록 집계 | P9 |
| `judging/legacy/judge2.py` | 정렬 후보 생성용 기존 판정 코드 (z3 경계 검사 확장) | P8 |
| `judging/legacy/judge4.py` | 정렬 후보 생성용 기존 판정 코드 (반례 포함) | P8 |
| `judging/legacy/judge5.py` | 구조 수준 PROOF/REFUTE 비교 | P8 |
| `judging/legacy/judge_pt.py` | 과거시제 LTL의 z3 경계 동치 검사 | P8 |
| `bench/tools/trace_report.py` | 단위별 추적 파일과 요약 표 생성 | P11 |
| `bench/tools/analyze_run.py` | 엄격 성공, 결정 지점, 원인 라벨 분석 | P12 |
| `bench/tools/decision_points.py` | FRETish 문장의 결정 지점(범위, 조건 종류, 타이밍, 읽기) 판독 | P12 |
| `bench/tools/compare_runs.py` | 두 실행의 항목 단위 부호 검정 비교 | P12 |
| `exp/fsm/run_intent.sh` | v1.4 단계 실행 (`lint`, `dryrun`, `gen`, `inputs`, `judge`, `trace`, `controls`, `analyze`, `compare`) | P2-P12 |
| `exp/fsm/run_fsm.sh` | v1.3 흐름의 단계 실행 (`lint`, `dryrun`, `gen`, `inputs`, `judge`, `trace`) | P2-P11 |
| `Makefile` | 명령 모음 (`test`, `selfcheck`, `judge`, `aggregate`, `freeze-check`, `fsm-dryrun`, `fsm-all`) | P9 |
| `bench/FROZEN_MANIFEST.sha256` | `bench/` 파일의 해시 목록 (`make freeze-check`) | 점검 |
| `tests/test_judge.py` | 판정 모듈 시험 | 점검 |
| `tests/test_v9.py` | 생성 파이프라인, 규칙, 프롬프트 시험 | 점검 |
| `bench/score3.py` | 단위 점수와 실패 기록 (v3) | 보조 |
| `bench/score_lm.py` | LM 벤치 점수 | 보조 |
| `bench/extract_files.py` | 프롬프트 문서의 파일 블록 추출과 해시 확인 | 보조 |
| `bench/mock_claude.py` | 오프라인 시험용 가짜 `claude` CLI | 보조 |
| `bench/fret_check/check.py` | 파서 수락 문장의 실현가능성 판정 기록 | 보조 |
| `bench/fret_check/tools/fret_rlz.py` | FRET 실현가능성 검사 | 보조 |
| `bench/fret_check/tools/fretexpr.py` | FRET 출력 식 파서 | 보조 |
| `bench/fret_check/tools/fret_import.js` | FRET 프로젝트 가져오기 스크립트 | 보조 |
| `bench/tools/preflight_check.py` | 예비 시험 결과 검사 P1..P25 | 보조 |
| `bench/tools/smoke3_check.py` | 시범 실행 점검 표 | 보조 |
| `bench/tools/dict_usage.py` | 생성 식별자의 딕셔너리 이름 사용 수 집계 | 보조 |
| `bench/tools/dev_record.py` | 개발 실행 관측 기록 | 보조 |
| `bench/tools/mock_fret.py` | 오프라인 시험용 가짜 실현가능성 결과 | 보조 |

- 이전 릴리스(v1.2.0): `archive/nl2fret_tool/v1.2.0/` (동결 판정 코드 `judging/`, `JUDGE_FROZEN_MANIFEST.sha256`, 61항목 본 실행에 사용)
- 메인 디렉터리의 보조 코드: `tools/render_prompts.py` (시스템 프롬프트 파일 렌더링), `tools/build_cases.py`, `tools/verify_lm_docx.py`

### 4.3 프롬프트

| 파일 | 내용 | 사용 단계 |
|---|---|---|
| `nl2fret_tool/bench/prompts/fretish_guide.md` | FRETish 가이드: 문장 형태, 필드, 이름 규칙 | D, B |
| `nl2fret_tool/bench/prompts/fretish_guide_supplement.md` | FRET 공식 문서 인용 보충문 (`--guide-sup`, 꺼짐) | D, B |
| `nl2fret_tool/bench/prompts/intent_declaration.md` | 의도 선언: NASA 논문 인용으로 조건의 의도된 의미 선언 (`--intent-decl`) | D, B, S |
| `nl2fret_tool/bench/templates/masteR.md` | MASTeR 템플릿 가이드 | A, B |
| `nl2fret_tool/bench/templates/ears.md` | EARS 템플릿 가이드 | A, B |
| `nl2fret_tool/bench/templates/adv_ears.md` | Adv-EARS 템플릿 가이드 | A, B |
| `nl2fret_tool/bench/templates/spider.md` | SPIDER 템플릿 가이드 | A, B |
| `nl2fret_tool/bench/templates/boilerplate.md` | Boilerplate 템플릿 가이드 | A, B |
| `nl2fret_tool/bench/common.py` | 코드 내 프롬프트 문장: `TASK_A`, `TASK_B`, `TASK_D`, `RULES_COMMON`, `SCHEMA_A`, `SCHEMA_B`, 사용자 메시지 형식 | A, D, B |
| `nl2fret_tool/bench/prompts3.py` | 코드 내 프롬프트 문장: `SURFACE_RULE`, `SLOT_SYSTEM_R2`, `D_RULES`, `SLOT_D_RULES`, `GUIDE_HEAD`, 피드백 문장 (`LOG_HEAD`, `LOG_TAIL`, `FEEDBACK_TAIL`) | A, B, S, F |
| `nl2fret_tool/bench/tpl_rules.py` | 규칙 글의 원본: 규칙표 `RULES` (규칙 ID, 설명, 근거 유형) | B, S |
| `nl2fret_tool/bench/fretlint.py` | 피드백에 붙는 FRET 오류별 힌트 문장 | F |

- 조립된 시스템 프롬프트 17개: `$RUN/gen/snapshot/system_prompt_*.txt` (P3의 표), 해시 `$RUN/gen/snapshot/run_info.json`
- 메인 디렉터리 사본 (내용 동일): `prompts/current/fretish_guide.md`, `prompts/current/templates/{adv_ears,boilerplate,ears,masteR,spider}.md`, `prompts/current/system_prompts/system_prompt_A_{Adv-EARS,Boilerplate,EARS,MASTeR,SPIDER}.txt`
- 메인 디렉터리 색인과 도구: `prompts/INDEX.md`, `prompts/current/SHA256SUMS`, `tools/render_prompts.py`
- 지시문 보관: `prompts/current/instructions/` (현재 v1.4 지시문 `NL2FRET_PROMPT_FSM_V14_MAC.md`)

### 4.4 입력 데이터

| 파일 | 내용 | 프로세스 |
|---|---|---|
| `nl2fret_tool/data/dataset/lm_dataset_final.jsonl` | 데이터셋 61항목: 자연어, 출처, 기준 부분과 버전(FRETish, LTL) | P1 |
| `nl2fret_tool/data/dataset/lm_dataset_table.xlsx` | 데이터셋 표 (엑셀) | P1 |
| `nl2fret_tool/data/dictionary/lm_dictionary.csv` | 딕셔너리 564행 (챌린지 10개) | P1, P8 |
| `nl2fret_tool/data/reference/lm_reference_with_ltl.jsonl` | 기준 61행 (부분, 버전, LTL) | P8, P9 |
| `nl2fret_tool/data/reference/sigdict.json` | 챌린지별 딕셔너리 표 텍스트 | P1 |
| `nl2fret_tool/data/reference/pairs_sample.jsonl` | 판정기 교차검증용 쌍 표본 | 보조 |
| `nl2fret_tool/bench/data/lm_items.jsonl` | 항목 파일 61행 (`id`, `raw_nl`, `family`, `challenge`) | P1, P4-P7 |
| `nl2fret_tool/bench/data/lm_items_fsm.jsonl` | FSM 챌린지 항목 13행 | P1, P4-P7 |
| `nl2fret_tool/bench/data/lm_items_nonfsm.jsonl` | 비 FSM 항목 48행 | P1 |
| `nl2fret_tool/bench/data/sigdict.json` | LLM 입력용 챌린지별 딕셔너리 표 | P5 |
| `nl2fret_tool/bench/data/rule_sources.json` | 규칙 근거 장부 (인용문, 출처) | P2 |
| `nl2fret_tool/bench/data/rule_semantics_results.json` | 규칙 의미 검증 결과 | P2 |
| `nl2fret_tool/bench/data/dict8_items.jsonl` | v8 딕셔너리 시험 항목 | 보조 |
| `nl2fret_tool/data/audit/item_validity_audit.csv` | 항목 타당성 감사표 (분석의 층화에 사용) | P12 |
| `nl2fret_tool/data/example_units_v8.json` | 판정 입력 형식 예시: 단위 | 보조 |
| `nl2fret_tool/data/example_fret_ltl_gen_v8.jsonl` | 판정 입력 형식 예시: 문장별 LTL | 보조 |
| `nl2fret_tool/data/example_fret_realizability_gen_v8.jsonl` | 판정 입력 형식 예시: 실현가능성 | 보조 |
| `nl2fret_tool/bench/fret_check/variable_policy.md` | 실현가능성 검사의 변수 표 작성 규칙 | 보조 |
| `nl2fret_tool/docs/controls_nusmv512/controls.md` | 판정기 대조 기대표 (`controls.jsonl`, `controls_summary.json`, `v13_fsm_analysis.md` 포함) | P2 |
| `nl2fret_tool/docs/paper_passage_AP003c.txt` | 의도 선언 인용 대목 | P2 |

- 메인 디렉터리 사본 (내용 동일, `SHA256SUMS` 포함): `assets/dataset/v1/` (`lm_dataset_final.jsonl`, `lm_dataset_table.xlsx`, `build_dataset.py`), `assets/dictionary/v1/` (`lm_dictionary.csv`, `build_dict.py`), `assets/reference/v1/` (`lm_reference_with_ltl.jsonl`, `pairs_sample.jsonl`, `sigdict.json`)
- 버전 색인: `VERSIONS.md`

### 4.5 실행 결과 폴더 구조 (`$RUN`)

```text
$RUN/
  gen/                P4-P6   calls.jsonl, parser_cache.jsonl, run_state.json, run.log, limit_events.jsonl, probes.jsonl, snapshot/
  inputs/             P7      units.json, fret_ltl_gen.jsonl, unit_state.jsonl
  judge_selfcheck/    P9      자기점검 기록
  judge/              P8-P10  judge_records.jsonl, part_results.jsonl, counterexamples.jsonl, run_header.json, smv/, work/
  trace/              P11     INDEX.md, unit_trace.jsonl, units/*.md
  analysis/           P12     analysis.md, part_analysis.jsonl
  comparison/         P12     comparison.md, comparison.json
  summary.md, summary.json    P11
  prompt_lint.json            P2
  console_gen.log             gen 단계 출력
```

### 4.6 문서

| 파일 | 내용 |
|---|---|
| `nl2fret_tool/docs/DESIGN.md` | 판정 설계 |
| `nl2fret_tool/docs/RUNBOOK.md` | 판정 실행 절차 |
| `nl2fret_tool/docs/EXPERIMENT_FSM.md` | FSM 시험 설계 |
| `nl2fret_tool/docs/TRACE_FORMAT.md` | 단계별 추적 형식 |
| `nl2fret_tool/docs/ANALYSIS_PLAN.md` | 분석 계획과 성공 지표 정의 |
| `nl2fret_tool/docs/V14_INTENT_TEST.md` | v1.4 재시험 설계 (의도 선언, 규칙 글 정합, 근거 있는 규칙) |
| `nl2fret_tool/docs/V14_GUIDE_SUPPLEMENT.md` | v1.4 가이드 보충문 설계 |
| `nl2fret_tool/docs/DATA_VERSIONING.md` | 데이터 버전업 절차 |
| `nl2fret_tool/docs/old_prompts/` | 이전 실행 지시문 (`NL2FRET_PROMPT_FSM_RUN_v1.md`, `NL2FRET_PROMPT_FSM_SUP_v1.md`, `README.md`) |
| `nl2fret_tool/README.md` | 도구 개요 |
| `nl2fret_tool/VERSION` | 도구 버전 `v1.4` |
| `nl2fret_tool/requirements.txt` | Python 의존성 |
| `nl2fret_tool/.gitignore` | git 제외 목록 |
| `nl2fret_tool/NL2FRET_PROMPT_FSM_V14_MAC.md` | v1.4 재시험 실행 지시문 |
| `nl2fret_tool/bench/NL2FRET_PROMPT_v8_DICT_SMOKE.md` | v8 딕셔너리 시험 지시문 (프롬프트 문서 원본, `bench/extract_files.py`의 입력) |

- 메인 디렉터리 문서: `docs/PROCESS_LIFECYCLE.md` (v1.2.0 시기의 전 주기 문서), `STRUCTURE.md` (저장소 구조), `README.md`
