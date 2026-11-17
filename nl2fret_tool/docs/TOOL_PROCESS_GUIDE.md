# NL2FRET 도구 프로세스

## 0. 연구 질문과 역할

- 연구 질문: 안전이 중요한 소프트웨어에는 형식 명세(LTL)가 필요하지만, LTL을 쓰려면 전문가의 도메인 지식이 필요하다. FRET은 구조화된 영어인 FRETish를 LTL로 바꾸지만 좋은 FRETish를 쓰는 일은 여전히 사람이 한다. LLM으로 이를 자동화하려는 기존 시도는 전문가 지식이라는 한계 때문에 완전 자동화에 이르지 못했다. 이 연구는 템플릿(반정형 중간 형태)을 거치면 이 한계가 줄어드는지 확인한다
- 핵심 비교: 템플릿 경로(Template+G, FixedTemplate+R2) 대 Direct. 보조 비교: 템플릿 5종 사이
- 측정: 생성한 FRETish를 FRET이 컴파일한 LTL이 전문가(NASA) FRETish의 LTL과 같은 뜻(SAME)인지, 또는 그것을 함의(PROOF)하는지
- 정답: NASA FRETish. NASA가 FRET을 만들었고 권위가 있어서 정답으로 쓴다. NASA FRETish는 자연어만으로는 알 수 없는 정보(변수 이름, 정의 용어)를 쓴다
- 딕셔너리: 성능을 올리는 장치가 아니라 모든 방식에 똑같이 주는 실험용 확장(추가 첨부)이다. 결과는 이 딕셔너리를 준 조건의 성능으로만 보고한다 (1.7절)

## 1. 전체 구조

### 1.1 처리 흐름

```text
[입력] 챌린지 1개의 자연어 요구사항 전체 (항목 여러 건)
   |
   v
[에이전트 호출] 방식, 템플릿, 챌린지, 반복마다 에이전트 1개 (독립된 claude 프로세스)가 챌린지의 모든 항목에 한 번에 답함
   |   Direct    : 자연어 -> FRETish
   |   규칙 글   : 자연어 -> 템플릿 문장 (단계 A) -> FRETish (단계 B)
   |   규칙 조립 : 자연어 -> 템플릿 문장 (단계 A) -> 구절별 식 (단계 S) -> 스크립트가 FRETish 조립
   v
[파서 피드백] FRET 공식 파서가 문장을 수락 또는 거절
   |   거절 -> 파서 메시지와 힌트를 에이전트에 전달 -> 수정 답변 (최대 5회)
   v
[키워드 점검 KC 1회] 문장의 키워드 그룹과 그 그룹의 공식 참조 문서를 에이전트에 전달 -> 키워드를 비교한 답변
   v
[왕복 1회] 수락된 문장마다 FRET의 영어 설명을 에이전트에 전달 -> 입력과 대조한 답변 (KC 답이 채택됐으면 그 답에서 시작)
   v
[변형] v0 (첫 답변), vf (파서 피드백 뒤), kc (키워드 점검 뒤), rt (왕복 뒤) 네 벌의 문장
   v
[LTL] 변형마다 수락 문장에서 LTL 포뮬라 도출 (과거시제, 미래시제)
   v
[판정] 신호 이름 정렬 -> NuSMV 질의 3개 (equiv, sound, compl) -> 역할 SAME / PROOF / REFUTE / NEITHER
   v
[반례] 질의 거짓 시 NuSMV 반례를 로그로 기록 -> 사용자에게 제공
   v
[집합 Realizable] 방식, 챌린지, 반복의 최종 문장 전체를 요구사항 집합 1개로 FRET 실현가능성 검사
   v
[효과 집계] 변형 간 성공 부분의 이득과 손실
```

### 1.2 에이전트 구조

- 에이전트 1개 = 새로 시작한 `claude` 프로세스 1개 (상태 비저장). 스크립트가 입력을 쓰고, 에이전트가 JSON 객체 1개를 답하고, 스크립트가 그 객체만 보관 (`--json-schema`)
- 격리: 허용한 환경 변수만 전달, 빈 임시 작업 폴더, `--tools "" --no-session-persistence --setting-sources "" --disable-slash-commands --strict-mcp-config`
- 격리 검사 (`agent_call.isolation_probe`): 첫 호출 전에 실행, 허용 항목(`StructuredOutput`, `userEmail`) 밖의 항목이 보이면 실행 중단. 기록 `isolation_probe.json` (항목 이름만)
- 에이전트의 정의: 변환에 쓸모 있는 기억 정보가 (템플릿, 입력 데이터 종류)마다 독립으로 분리된 단위가 에이전트 1개이다. 같은 범위 안에서 여러 호출로 나누어도 에이전트 1개로 센다. 구현은 호출을 (시스템 프롬프트, 챌린지, 반복, 단계)로 묶고 같은 묶음 안에서만 정보를 넘기므로 이 정의를 만족한다. 단계 B는 단계 A의 템플릿 문장만 본다
- 에이전트 호출 1회의 단위 = (방식, 챌린지, 반복, 단계). 챌린지의 모든 요구사항이 한 호출에 들어감
  - Direct: 챌린지마다 에이전트 1개, FRETish 가이드
  - Template (+G): 템플릿과 챌린지마다 에이전트, 단계 A (자연어 -> 템플릿 문장) 뒤 단계 B (템플릿 문장 -> FRETish), 템플릿 가이드와 FRETish 가이드
  - FixedTemplate (+R2): Template과 같은 범위, 단계 B 대신 규칙 조립
  - 단계 A는 (템플릿, 챌린지, 반복)마다 1회이며 +G와 +R2가 공유. 단계 B는 템플릿 문장만 읽음
- 배치 응답: `{"results":[{"id","answer"}]}`. 응답에서 빠진 id는 한 번 더 요청 (`--batch-retries 1`, 모든 방식에 같음). 항목별 행은 `calls.jsonl`에 기록
- 유효한 JSON이면서 FRETish 목록이 빈 응답은 `declined` (단계 A: 상태 `declined`, 단계 B: 상태 `ok`와 오류 `declined`, 판정 코드 `no_output`)

### 1.3 변환 방식

| 방식 | 템플릿 | arm 이름 | 에이전트 단계 | 스크립트 단계 |
|---|---|---|---|---|
| Direct | - | `DIRECT` | D | - |
| 규칙 글 (Template) | MASTeR, EARS, Adv-EARS, SPIDER, Boilerplate | `<템플릿>+G` 5개 | A, B | - |
| 규칙 조립 (FixedTemplate) | MASTeR, EARS, Adv-EARS, SPIDER, Boilerplate | `<템플릿>+R2` 5개 | A, S | 구절 분해, FRETish 조립 |

- 단계 A: 자연어 -> 템플릿 문장
- 단계 D: 자연어 -> FRETish (Direct)
- 단계 B: 템플릿 문장 -> FRETish (규칙 글)
- 단계 S: 구절 -> 식 (규칙 조립의 슬롯 값)
- 단계 F1..F5: 파서 피드백 재호출
- 단계 KC1: 키워드 점검 1회 (RT1 앞)
- 단계 RT1: 왕복 1회
- 규칙 조립에서 스크립트가 문장을 만들 수 없는 구절(비활성 규칙 구절 `no_source:*`)은 규칙 글 경로(`fallback`)로 변환
- 단위 = 항목 x 방식 x 반복. 호출 단위는 (방식, 챌린지, 반복, 단계)

### 1.4 피드백과 변형

1. 파서 피드백 (최대 5회): FRET 공식 파서가 모든 문장을 수락 또는 거절. 거절 문장은 파서 메시지와 함께 에이전트에 돌아감
2. 키워드 점검 (KC1, 1회, 점검 단계이며 피드백이 아님): 문장의 키워드 그룹(범위, 조건, 타이밍)을 FRET 파서 필드로 정하고, 그 그룹의 공식 참조 문서(FRETish 가이드의 줄)를 에이전트에 주고 자기 키워드를 비교해 같은 스키마로 다시 답하게 함. 채택 규칙은 왕복과 같음 (`kc_adopted`)
3. 왕복 (RT1, 1회, KC 답이 채택됐으면 그 답에서 시작): FRET이 수락 문장마다 영어 설명을 작성. 에이전트가 설명을 입력과 나란히 읽고 같은 스키마로 다시 답함. 채택 규칙: 왕복 답변의 문장이 모두 공식 파서에 수락될 때만 파서 피드백 뒤의 답변을 대체
4. 에이전트로 되돌아가는 정보: 파서 판정과 힌트(파서 피드백), 키워드 그룹과 공식 참조 문서(키워드 점검), FRET의 영어 설명(왕복)

| 변형 | 문장 | 판정 입력 폴더 |
|---|---|---|
| v0 | 첫 답변 | `inputs_v0/`, `judge_v0/` |
| vf | 파서 피드백 뒤 | `inputs_vf/`, `judge_vf/` |
| kc | 키워드 점검 뒤 (채택되지 않으면 vf와 같음) | `inputs_kc/`, `judge_kc/` |
| rt | 왕복 뒤 (주 변형, 채택되지 않으면 왕복의 입력과 같음) | `inputs_rt/`, `judge_rt/` |

- 네 변형은 같은 판정기(NuSMV)로 판정 (`NO_KC=1`이면 kc 변형이 없음)
- 성공 = SAME 또는 PROOF (부분 단위)
- 효과 집계(P13): 방식과 변형별 성공 부분 수, 같은 (항목, 반복, 부분)에서 변형 사이의 이득과 손실
- 보조 지표: 챌린지 단위 집합 Realizable (P12). 판정은 문장 단위로 따로 수행

### 1.5 프로세스 목록

| 번호 | 프로세스 | 입력 | 출력 | 실행 |
|---|---|---|---|---|
| P1 | 입력 데이터 준비 | 데이터셋, 딕셔너리 | 항목 파일, 기준 파일, 딕셔너리 텍스트, FRETish 참고문 | `src/nl2fret/tools/build_inputs.py` |
| P2 | 실행 전 점검 | 패키지 | 시험, 해시, lint, 파서 지문, 격리 검사 결과 | `scripts/run_batch.sh pin` |
| P3 | 프롬프트 조립 | 가이드, 템플릿, 고정 문장 | 시스템 프롬프트 12개 | `run_batch.sh gen` (시작 시) |
| P4 | 템플릿 변환 (단계 A) | 자연어 | 템플릿 문장 | `run_batch.sh gen` |
| P5 | FRETish 변환 (단계 D, B, S) | 자연어 또는 템플릿 문장 | FRETish 문장 | `run_batch.sh gen` |
| P6 | FRET 검증과 파서 피드백 (단계 F1..F5) | FRETish 문장 | 수락 문장, 오류 로그 | `run_batch.sh gen` |
| P7a | 키워드 점검 (단계 KC1) | 수락 문장, 키워드 그룹, 참조 문서 | 점검 답변 | `run_batch.sh gen` |
| P7 | 왕복 (단계 RT1) | 수락 문장, FRET 설명 | 왕복 답변 | `run_batch.sh gen` |
| P8 | LTL 도출과 판정 입력 생성 | 호출 기록 | 변형별 단위, 문장별 LTL | `run_batch.sh inputs` |
| P9 | 신호 이름 정렬 | 생성 LTL, 딕셔너리, 기준 LTL | 정렬된 식 쌍 | `run_batch.sh judge` |
| P10 | 판정 (엄격) | 정렬된 식 쌍 | 역할, 질의 결과 | `run_batch.sh judge` |
| P11 | 반례 기록 | 거짓 질의 | 반례 로그 | `run_batch.sh judge` |
| P12 | 집합 Realizable (raw, normalized) | 변형 rt의 최종 문장 | 집합별 실현가능성 결과 | `run_batch.sh group` |
| P13 | 효과 집계 | 변형별 판정 결과 | 이득과 손실 표 | `run_batch.sh effect` |
| P14 | 자산 버전 관리 | 입력 데이터, 프롬프트 | 버전 색인 | `VERSIONS.md` |

### 1.6 용어

| 용어 | 뜻 |
|---|---|
| 에이전트 | 호출마다 새로 시작하는 `claude` 프로세스 1개 (P2의 격리 검사 대상) |
| 배치 | 한 에이전트 호출에 들어가는 챌린지의 항목 묶음 |
| 챌린지 | 항목의 출처 묶음. Lockheed Martin(LM) 사이버물리 챌린지 문제 10개 중 하나 (예 `06_EB`) |
| 항목 | 자연어 요구사항 1건 (`id`, `raw_nl`, `family`, `challenge`) |
| 단위 | 항목 x 방식 x 반복 |
| 부분 | 항목의 기준 요구사항 1개. 항목 하나가 여러 부분을 가질 수 있음 |
| 템플릿 | 요구사항 문장 서식 (MASTeR, EARS, Adv-EARS, SPIDER, Boilerplate) |
| 규칙 글 | 템플릿 구절을 FRETish 필드로 옮기는 규칙 목록을 문장으로 적어 프롬프트에 포함한 것 |
| 규칙 조립 | 같은 규칙 목록을 스크립트(`src/nl2fret/tpl_rules.py`)가 실행하는 것 |
| 슬롯 | 규칙 조립에서 에이전트가 채우는 구절별 식 |
| 딕셔너리 | 챌린지별 신호 이름 표 (이름, 종류, 방향, 타입, 설명) |
| 피드백 | 파서가 거절한 문장에 오류 로그를 붙여 에이전트를 다시 부르는 단계 F1..F5 |
| 왕복 | 수락 문장의 FRET 영어 설명을 에이전트에 보여 주고 다시 답하게 하는 단계 RT1 |
| fallback | 규칙 조립이 문장을 만들 수 없을 때 규칙 글 경로로 변환하는 처리 |
| 변형 | 판정 대상 문장의 시점: v0 (첫 답변), vf (파서 피드백 뒤), kc (키워드 점검 뒤), rt (왕복 뒤) |
| 키워드 점검 | 문장의 키워드 그룹과 그 그룹의 공식 참조 문서를 에이전트에 보여 주고 다시 답하게 하는 단계 KC1 (피드백이 아님) |
| 역할 | SAME (기준과 동치), PROOF (생성식이 기준식보다 강함), REFUTE (생성식이 기준식보다 약함), NEITHER (서로 다른 의미), UND (비교 불가), N/M (엔진 판정 실패) |
| 집합 Realizable | 방식, 챌린지, 반복의 최종 문장 전체를 요구사항 집합 1개로 검사한 FRET 실현가능성 결과 |
| LTL 포뮬라 | 선형 시간 논리 식. FRET 공식 파서가 FRETish 문장에서 도출 (과거시제 `ltl_pt`, 미래시제 `ltl_ft`) |
| NuSMV | 모델 검사기. 두 LTL 식 사이의 함의를 질의 |
| `$RUN` | 실행 결과 폴더 `runs/<실행 이름>/` |

### 1.7 확장 모듈과 알려진 한계

- 확장 모듈: 핵심에는 고리만 있고(`src/nl2fret/ext/__init__.py`, 플래그 `--ext`, 환경 변수 `EXT`) 내용은 확장 폴더에 있다. 지금 확장은 `dictionary` 하나 (`src/nl2fret/ext/dictionary/`, 설명 `README.md`)
  - 켜짐(`run_batch.sh`의 기본, `EXT=dictionary`): FRETish 단계의 시스템 프롬프트에 딕셔너리 규칙이 들어가고 사용자 메시지에 딕셔너리 글이 붙으며, 판정기는 딕셔너리 v1 파일을 `--dictionary`로 받는다
  - 꺼짐(`EXT=`): 프롬프트에 딕셔너리 블록이 없다. 동결된 판정기가 `--dictionary`를 필수 인자로 선언하므로 판정기에는 항목이 없는 머리글 파일(`$RUN/ext_off_dictionary.csv`)을 넘기고, 이때 모든 식별자는 `oov`이며 이름을 바꾸지 않는다
  - 별칭 열(`alias_of`, `alias_evidence`)은 선택 덧씌우기(`src/nl2fret/ext/dictionary/overlays/v2/`, 기본 꺼짐)이고 핵심은 이 열을 읽지 않는다
- 판정 기준: 엄격 판정 하나가 주 지표이다 (`run_batch.sh judge`). Realizable은 N-LIT(기본 켜짐)의 normalized 결과가 주, raw 결과가 보조이다
- 알려진 한계: 정의 용어를 쓰는 문장은 과소평가될 수 있다. 기준 문장 자기 자신 쌍에서 서로 다른 부분이 SAME으로 나온 거짓 SAME이 129쌍 중 4쌍에서 관찰되었다. 둘 다 이전 판정기의 성질이며 모든 방식에 똑같이 적용된다
- 철회한 기능(J+def 판정 변형, 딕셔너리 v2의 판정 입력 사용)은 `archive/removed_features/`에 있고 `README.md`에 이유와 복원 방법이 있다

## 2. 예제

예제 항목 `LM-06_EB-N1` (챌린지 `06_EB`, 반복 0). 같은 챌린지의 `LM-06_EB-N4`와 한 배치에 들어가 에이전트 호출 1회에 함께 답해진다. 모든 값은 `$RUN`의 실제 파일에서 읽은 것이다 (`$RUN` = `batch_06EB_remeasure2`).

이 실행은 2026-11-17 정리(확장 모듈 도입, J+def 철회) 전에 한 것이다. 정리 뒤에도 판정기 코드, 입력 데이터, 딕셔너리 v1은 같다. 시스템 프롬프트는 2026-11-17의 논문 규칙 반영(`prompts/INDEX.md`) 전의 것이고, 그 뒤 도구는 12개 프롬프트를 만든다. 효과 집계 값은 그 실행의 엄격 판정 집계 파일(`rt_effect_strict.json`)에서 읽었으며, 현재 도구는 같은 집계를 `rt_effect.json` 하나로 쓴다. 정리 뒤 확인 실행(06_EB, 반복 1, 확장 켜짐)은 `gen`부터 `effect`까지 통과했다 (생성이 달라 예제 값은 이 확인 실행에서 읽지 않았다).

### 2.1 요구사항

`src/nl2fret/data/lm_items.jsonl`의 행

```text
id: LM-06_EB-N1
challenge: 06_EB
family: 06_EB
raw_nl: When the determinant of B(inv(Wp’)B’ is <= 1e-12 as indicated by ridge_on set to True, the inversion of the B(inv(Wp’)B’ matrix should be accurate to 6 digits precision in that each element in the check output matrix is within a 1e-6 tolerance with respect to the elements of a 3x3 identity matrix.
```

### 2.2 기준

`data/reference/lm_reference_with_ltl.jsonl`의 이 항목: 부분 1개, 부분 1의 버전 1개

```text
reqid: EB-001
fretish: EB shall always satisfy (det_3x3(B_11*B_11 + B_12*B_12 + B_13*B_13 + B_14*B_14 + B_15*B_15 , B_11*B_21 + B_12*B_22 + B_13*B_23 + B_14*B_24 + B_15*B_25 , B_11*B_31 + B_12*B_32 + B_13*B_33 + B_14*B_34 +...
ltl 출처: FRET parser (FretSemantics.js)
```

### 2.3 딕셔너리 (예제에 쓰이는 이름)

`data/dictionary/lm_dictionary.csv`: 챌린지 `06_EB` 153행. 열: challenge, name, direction, type, dims, description, sources, components, kind, definition, model_signal

```text
{"name": "B", "direction": "Input", "type": "Double/double", "dims": "3x5", "description": "The control effectiveness matrix of size 3x5", "kind": "signal"}
{"name": "B_11", "direction": "Input", "type": "double", "dims": "", "description": "element of B", "kind": "element", "model_signal": "B"}
```

### 2.4 예제에서 보이는 흐름

| 방식 | 파서 피드백 | v0 문장 | vf 문장 | rt 문장 | 역할 (vf) |
|---|---|---|---|---|---|
| `DIRECT` | 1회 (거절 1) | 0문장 | 1문장 | 1문장 | UND |
| `EARS+G` | 0회 (거절 0) | 1문장 | 1문장 | 1문장 | UND |
| `EARS+R2` | 1회 (거절 1) | 0문장 | 1문장 | 1문장 | NEITHER |

- v0, vf, rt 열은 변형별 `units.json`의 `texts` 문장 수. 파서가 거절한 첫 답변은 v0 문장 수 0
- 단위 수: 챌린지 06_EB의 항목 2개 x 방식 11개 = 22단위, `inputs_*/units.json`의 전체 단위 671개 중 미완료 649개 (다른 챌린지, 이번 실행의 호출 대상 밖)

## 3. 프로세스별 설명

### P1. 입력 데이터 준비

- 하는 일
  - 항목 파일 (`id`, `raw_nl`, `family`, `challenge`) 생성: 61항목, 챌린지 10개
  - 데이터셋, 딕셔너리, 기준 파일 준비
  - FRETish 참고문 `src/nl2fret/prompts/fretish_reference.md`를 FRET 공식 필드 문서 전문으로 생성
- 입력: 챌린지 문서, 데이터셋 원본, FRET 공식 문서
- 출력
  - `src/nl2fret/data/lm_items.jsonl` (61행), `lm_items_fsm.jsonl` (13행), `lm_items_nonfsm.jsonl` (48행)
  - `data/dataset/lm_dataset_final.jsonl` (61항목)
  - `data/dictionary/lm_dictionary.csv` (564행)
  - `data/reference/lm_reference_with_ltl.jsonl` (61행)
  - `src/nl2fret/prompts/fretish_reference.md`
- 코드: `src/nl2fret/tools/build_inputs.py`, `data/dataset/build_dataset.py`, `data/dictionary/build_dict.py`, `src/nl2fret/tools/make_sigdict.py`, `src/nl2fret/tools/build_fretish_reference.py`
- 예제: 2.1절 항목 행, 2.2절 기준, 2.3절 딕셔너리 행

### P2. 실행 전 점검

- 하는 일
  - 시험: `python3 -m pytest tests -q` (패키지 루트)
  - 도구 코드의 고정: 릴리스 태그(`v2.0`, git). 해시 목록은 2026-11-17에 없앴다 (`archive/removed_features/`)
  - 프롬프트 lint (`src/nl2fret/tools/prompt_v15_lint.py`, 프롬프트 12개: Direct 1, 1단계 5, 2단계 +G 5, +R2 슬롯 1)
    - V-COMPLETE: FRET 문법의 모든 키워드가 FRETish 단계와 슬롯 프롬프트에 있음 (대상: 단계 D, B, S 프롬프트. 1단계 프롬프트는 템플릿 변환용)
    - V-PROVENANCE: 도구가 만든 규칙, 의도 문단, 이름 규칙의 표지 검출
    - V-LEAK: 기준 FRETish 문장과 30자 이상의 기준 응답, 조건 문장의 프롬프트 포함 검출
    - V-STATUS: `sources_v15.json`의 문서별 확인 상태
    - V-STYLE: 도구가 쓴 프롬프트 문장에서 주석, 완화, 부정, 시험대 문장 검출
  - FRET 파서 지문: 기준 FRETish 111문장(중복 제거, 파일 순서)을 공식 파서로 컴파일하고 (ok, ltl_ft, ltl_pt) 해시를 `data/reference/parser_fingerprint.pin`과 대조. 이 컴퓨터에서 처음이면 `WRITEPIN=1 bash scripts/run_batch.sh pin`으로 고정. `gen`은 시작 때 같은 대조를 하고 불일치면 중단
  - docker 파서와 node 파서의 지문 비교: `parser_fingerprint.py --backend docker --dump a.json`, `--backend node --dump b.json`, `--compare a.json b.json` (node 쪽은 환경 변수 `FRET_PARSER_JS`, `NL2FRET_NODE_PARSER`, `NODE_PATH` 필요)
  - 격리 검사: `gen`의 첫 호출 전에 에이전트에게 보이는 항목을 묻고 허용 항목(`StructuredOutput`, `userEmail`) 밖의 항목이 있으면 중단
- 입력: 패키지 전체, `data/reference/lm_reference_with_ltl.jsonl`, `src/nl2fret/prompts/sources_v15.json`
- 출력: `$RUN/parser_fingerprint.json` (`pin` 단계의 덤프), `$RUN/gen/isolation_probe.json`, `data/reference/parser_fingerprint.pin`
- 코드: `src/nl2fret/tools/prompt_v15_lint.py`, `src/nl2fret/fret_check/parser_fingerprint.py`, `src/nl2fret/agent_call.py` (`isolation_probe`, `ALLOWED_VISIBLE`), `scripts/run_batch.sh`, `tests/`
- 외부 도구: Docker 이미지 `fret-lab:latest` (FRET 공식 파서), node (파서 비교), `claude` CLI
- 예제

시험

```text
82 passed in 2.50s
```

프롬프트 lint 출력의 끝

```text
V-STATUS Boilerplate: verified
V-COMPLETE checked 7 of 12 prompts (stage A prompts excluded)
RESULT PASS (12 prompts)
```

파서 지문

```text
backend=docker sentences=111 fingerprint=6b05c991a62383977cd31b78458d700aedfd564b4536515975786075f1710562
pin MATCH
```

격리 검사 기록 `$RUN/gen/isolation_probe.json`

```text
ok: True
visible: ['userEmail']
env_names: ['HOME', 'LOGNAME', 'PATH', 'SHELL', 'TMPDIR', 'USER']
flags: ['--tools', '', '--no-session-persistence', '--setting-sources', '', '--disable-slash-commands', '--strict-mcp-config']
model: sonnet, extra: --effort medium
```

### P3. 프롬프트 조립

- 하는 일
  - 실행 시작 시 단계별 시스템 프롬프트 12개 조립, 해시 기록 (규칙 조립의 fallback 프롬프트는 +G 프롬프트와 같은 것이라 파일이 따로 없고 호출 기록의 단계 이름은 BF)
  - 배치 규칙 문단 `BATCH_RULES`를 모든 시스템 프롬프트 끝에 추가 (`batch_system`)
  - 사용자 메시지는 호출마다 단계별 함수로 생성하고 항목마다 `### id: <id>` 머리를 붙여 한 메시지에 묶음
- 입력
  - 고정 문장: `src/nl2fret/common.py` (`TASK_A`, `TASK_D`, `TASK_B_V15`, `RULES_COMMON_V15`, `RULES_A_V15`, `SCHEMA_A_V15`, `SCHEMA_B_V15`, `NOTATION_V15`, `NOTATION_FRETISH_V15`), `src/nl2fret/prompts3.py` (`D_RULES_V15`, `D5_RULE_V15`, `SLOT_SYSTEM_V15`, `SLOT_D_RULES_V15`)
  - FRETish 가이드 `src/nl2fret/prompts/fretish_reference.md` (FRET 공식 필드 문서 전문)
  - 템플릿 가이드 5개 `src/nl2fret/templates_v15/{masteR,ears,adv_ears,spider,boilerplate}.md`
  - 규칙 글 = 규칙표 `src/nl2fret/tpl_rules.py`의 `RULES` 설명
  - 출처 정보 `src/nl2fret/prompts/sources_v15.json` (프롬프트 밖)
- 출력: `$RUN/gen/snapshot/system_prompt_*.txt` 12개, `$RUN/gen/snapshot/run_info.json` (프롬프트 해시, 옵션)
- 메인 디렉터리 사본: `prompts/current/system_prompts/` (같은 12개와 `MANIFEST.csv`, `scripts/render_prompts.py`로 생성, `--run-info`로 실행의 해시와 대조)
- 코드: `src/nl2fret/batch_pipeline.py` (`batch_system`, `block_text`), `src/nl2fret/run_pipeline.py` (`build_prompts`), `src/nl2fret/prompts3.py` (`build_system_A3`, `build_system_B3`, `build_system_D3`, `slot_system_r2`), `src/nl2fret/common.py` (`build_system`)
- 프롬프트 구성 (`prompts/current/system_prompts/`, 실행 시 `$RUN/gen/snapshot/`과 동일)

| 파일 | 단계 | 구성 (순서) | 바이트 |
|---|---|---|---|
| `system_prompt_A_<템플릿>.txt` (5개) | A | TASK, GENERAL RULES, OUTPUT SCHEMA, TEMPLATE SPECIFICATION, NOTATION OF THE SPECIFICATION | MASTeR 7769, EARS 7320, Adv-EARS 4988, SPIDER 7324, Boilerplate 5747 |
| `system_prompt_D_none.txt` (1개) | D | TASK, GENERAL RULES, OUTPUT SCHEMA, FRETISH GUIDE, NOTATION OF THE FRETISH GUIDE, 딕셔너리 규칙 | 38624 |
| `system_prompt_B_<템플릿>+G.txt` (5개) | B | TASK, GENERAL RULES, OUTPUT SCHEMA, FRETISH GUIDE, NOTATION OF THE FRETISH GUIDE, TEMPLATE SPECIFICATION, NOTATION OF THE SPECIFICATION, 규칙 글, 딕셔너리 규칙 | MASTeR 44337, EARS 43888, Adv-EARS 41556, SPIDER 43892, Boilerplate 42315 |
| `system_prompt_S2_none.txt` (1개) | S | TASK, SLOT NAMES, FRETish 필드 문서 (조건, 타이밍, 응답, 내장 함수, 시간 조건, 파서 출력의 의미), NOTATION OF THE FRETISH GUIDE, 딕셔너리 규칙 | 29856 |

- 사용자 메시지 형식

| 단계 | 사용자 메시지 | 생성 함수 |
|---|---|---|
| A | `ITEMS: <n>` + 항목마다 `### id:` + `NATURAL LANGUAGE REQUIREMENT:` + 자연어 | `user_prompt_A`, `block_text` |
| D | 항목마다 자연어 + 딕셔너리 표 | `user_prompt_D` |
| B | 항목마다 `TEMPLATE:` + 템플릿 이름 + 번호 붙인 템플릿 문장 + 딕셔너리 표 | `user_prompt_B` |
| S | 항목마다 구절 목록과 슬롯 요청 + 딕셔너리 표 | `user_prompt_S` |
| F1..F5 | 원래 사용자 메시지 + `FRET FEEDBACK LOG` (시도별 답과 FRET 판정, 누적) | `user_prompt_feedback_log` |
| KC1 | `ITEMS: <n>` + `KC_HEAD` + 항목마다 `### id:`, `ITEM`, `input`, `sentence n`, `groups` + 발동한 그룹의 참조 문서(배치에서 한 번씩) + `KC_TAIL` + 딕셔너리 표 | `kc_stage.block_text` |
| RT1 | 원래 사용자 메시지 + `ROUND TRIP` + 내 답변 + 문장별 FRET 설명 | `rt_stage.body` |

- 실행 옵션 (`run_batch.sh gen`이 `batch_pipeline.py`에 전달)

| 옵션 | 효과 |
|---|---|
| `--dict-all` | 모든 방식의 FRETish 단계에 딕셔너리 표(사용자 메시지)와 딕셔너리 규칙(시스템 프롬프트) 추가 |
| `--g-parity` | 규칙 글에서 규칙 `R-DEFTIME` 제외 |
| `--tm-source-only` | 규칙 조립의 타이밍 슬롯 안내를 공식 문서 인용 사실로 구성 |
| `--sourced-rules-only` | 근거 있는 규칙만 활성. 비활성 규칙 구절은 조립 거절 후 규칙 글 경로로 이동 |
| `--fret-reference` | 공식 FRET 필드 문서 전문(`fretish_reference.md`)을 FRETish 프롬프트에, `templates_v15/`를 템플릿 설명에 사용 |
| `--stageb-sees-raw` | 단계 B에 원문 자연어도 전달 (이번 실행 설정에 미포함) |
| `--env-pass <이름>...` | 에이전트 프로세스에 추가로 전달할 환경 변수 이름 |
| `--only-challenge <id>` | 지정한 챌린지만 호출 (`run_batch.sh`의 `ONLY`) |

- 예제: 단계 A 호출 (템플릿 EARS, 챌린지 06_EB)의 사용자 메시지 앞부분

```text
ITEMS: 2

### id: LM-06_EB-N1
NATURAL LANGUAGE REQUIREMENT:
When the determinant of B(inv(Wp’)B’ is <= 1e-12 as indicated by ridge_on set to True, the inversion of the B(inv(Wp’)B’ matrix should be accurate to 6 digits precision in that each element in the check output matrix is within a 1e-6 tolerance with respect to the elemen...
```

### P4. 템플릿 변환 (단계 A)

- 하는 일
  - (템플릿, 챌린지, 반복)마다 에이전트 1개가 챌린지의 모든 항목을 템플릿 문장으로 변환
  - 같은 템플릿의 +G와 +R2가 결과 공유 (템플릿 5개 = 호출 5회)
  - 응답: `{"results": [{"id": ..., "answer": {"sentences": [...], "choices": [...]}}]}`, 항목별로 `calls.jsonl`에 1행
- 입력: 시스템 프롬프트 `system_prompt_A_<템플릿>.txt`, 사용자 메시지 (자연어 2항목)
- 출력: `$RUN/gen/calls.jsonl`의 단계 `A` 행, `$RUN/gen/batch_calls.jsonl`의 호출 기록 (원응답, 토큰, 소요 시간)
- 코드: `src/nl2fret/batch_pipeline.py` (`phase_A`, `execute`, `run_group`), `src/nl2fret/agent_call.py` (`call_agent`)
- 예제

호출 기록 (`batch_calls.jsonl`)

```text
batch_id: A|06_EB|EARS|0|66a6d44c|0
n: 2  n_answered: 2  attempts: 1  wall_s: 8.974
order: ['LM-06_EB-N1', 'LM-06_EB-N4']
```

`LM-06_EB-N1`의 단계 A 답 (템플릿 EARS)

```text
sentences: ["When the determinant of B(inv(Wp')B' is <= 1e-12 as indicated by ridge_on set to True, the system shall ensure the inversion of the B(inv(Wp')B' matrix is accurate to 6 digits precision such that each element in the check output matrix is within a 1e-6 tolerance with respect to the elements of a 3x3 identity matrix."]
```

### P5. FRETish 변환

#### P5-1. Direct (단계 D)

- 하는 일: 챌린지의 자연어 항목 전체를 FRETish로 변환하는 에이전트 호출 1회
- 입력: 시스템 프롬프트 `system_prompt_D_none.txt`, 사용자 메시지 (자연어와 딕셔너리 표)
- 출력: 단계 `D` 행 (`parsed.fretish` 목록, `fields`, `choices`, `unmapped_content`)
- 예제: `LM-06_EB-N1`의 Direct 첫 답

```text
Whenever ridge_on the EB shall always satisfy abs(check_1_1 - 1) <= eps6 & abs(check_1_2) <= eps6 & abs(check_1_3) <= eps6 & abs(check_2_1) <= eps6 & abs(check_2_2 - 1) <= eps6 & abs(check_2_3) <= eps6 & abs(check_3_1) <= eps6 & abs(check_3_2) <= eps6 & abs(check_3_3 - 1) <= eps6
```

#### P5-2. 규칙 글 (단계 B)

- 하는 일: 단계 A의 템플릿 문장을 FRETish로 변환 (템플릿 가이드, FRETish 가이드, 규칙 글 사용)
- 입력: 시스템 프롬프트 `system_prompt_B_<템플릿>+G.txt`, 사용자 메시지 (템플릿 이름, 템플릿 문장, 딕셔너리 표)
- 출력: 단계 `B` 행
- 예제: `LM-06_EB-N1`의 EARS+G 첫 답

```text
when det_B_BT <= eps12 & ridge_on EB shall satisfy absReal(check_1_1 - 1) <= eps6 & absReal(check_1_2 - 0) <= eps6 & absReal(check_1_3 - 0) <= eps6 & absReal(check_2_1 - 0) <= eps6 & absReal(check_2_2 - 1) <= eps6 & absReal(check_2_3 - 0) <= eps6 & absReal(check_3_1 - 0) <= eps6 & absReal(check_3_2 - 0) <= eps6 & absReal(check_3_3 - 1) <= eps6
```

#### P5-3. 규칙 조립 (단계 S와 스크립트)

- 하는 일
  - 스크립트가 템플릿 문장을 구절로 분해하고 (`parse_template`) 슬롯 요청 생성 (`slot_requests`)
  - 에이전트가 구절별 식(슬롯 값)을 답함 (단계 S)
  - 스크립트가 슬롯 값을 검사하고 (`lint_slots`) FRETish 문장 조립 (`assemble`)
  - 문장을 만들 수 없는 구절은 규칙 글 경로로 변환 (`fallback`, 프롬프트는 `system_prompt_B_<템플릿>+G.txt`와 같고 호출 기록의 단계 이름은 BF)
- 입력: 시스템 프롬프트 `system_prompt_S2_none.txt`, 사용자 메시지 (구절 목록, 슬롯 요청, 딕셔너리 표)
- 출력: 단계 `S` 행 (`parsed.slots`), 조립된 FRETish 문장 (`$RUN/inputs_*/units.json`의 `texts`)
- 코드: `src/nl2fret/tpl_rules.py` (`parse_template`, `slot_requests`, `lint_slots`, `assemble`), `src/nl2fret/batch_pipeline.py` (`phase_first`, `phase_fallback`)
- 예제: `LM-06_EB-N1`의 EARS+R2

슬롯 값 (단계 S 답)

```text
{"1": {"c1": "det_B_BT <= eps12 & ridge_on", "r": "absReal(check_1_1-1)<eps6 & absReal(check_1_2)<eps6 & absReal(check_1_3)<eps6 & absReal(check_2_1)<eps6 & absReal(check_2_2-1)<eps6 & absReal(check_2_3)<eps6 & absReal(check_3_1)<eps6 & absReal(check_3_2)<eps6 & absReal(check_3_3-1)<eps6", "ck": "when", "tm": "immediately"}}
```

스크립트가 조립한 문장 (파서 피드백 뒤, 변형 vf)

```text
when det_B_BT <= eps12 system shall immediately satisfy absReal(check_11 - 1) < eps6 & absReal(check_12) < eps6 & absReal(check_13) < eps6 & absReal(check_21) < eps6 & absReal(check_22 - 1) < eps6 & absReal(check_23) < eps6 & absReal(check_31) < eps6 & absReal(check_32) < eps6 & absReal(check_33 - 1) < eps6
```

### P6. FRET 검증과 파서 피드백

- 하는 일
  - 모든 문장을 FRET 공식 파서(`FretSemantics.compile`)에 입력하여 수락 또는 거절 판정, 수락 문장은 LTL 포뮬라와 FRET의 영어 설명 획득
  - 거절 문장이 있는 단위는 에이전트를 다시 호출 (단계 F1..F5)
  - 피드백 메시지: 원래 사용자 메시지 + `FRET FEEDBACK LOG` (시도마다 이전 답과 문장별 FRET 판정, 메시지, 힌트를 누적)
  - 수락될 때까지 반복, 최대 5회 (`NL2FRET_MAX_ROUNDS`)
  - 규칙 조립의 슬롯 오류(`slot_lint`)도 같은 방식으로 피드백
  - 각 라운드는 같은 단계(방식, 챌린지, 반복)의 거절 단위를 한 배치로 묶음
- 입력: 방식별 문장, `src/nl2fret/fretlint.py`의 힌트 문장
- 출력: 단계 `F1`..`F5` 행, `$RUN/gen/parser_cache.jsonl` (문장별 파서 결과 캐시)
- 코드: `src/nl2fret/batch_pipeline.py` (`phase_rounds`), `src/nl2fret/run_pipeline.py` (`do_compile`, `history_of`), `src/nl2fret/fretparse.py`, `src/nl2fret/fretlint.py`, `src/nl2fret/units3.py` (`needs_feedback`), `src/nl2fret/fret_check/tools/fret_compile.py`, `src/nl2fret/fret_check/tools/fretjs/fret_parse_full.js`
- 외부 도구: Docker 이미지 `fret-lab:latest`
- 예제: `LM-06_EB-N1`의 Direct

첫 답의 문장은 `abs(...)`를 포함하여 거절됨. 단계 F1 메시지의 FRET 판정 부분

```text
FRET verdict per sentence:
1. REJECTED: 'Whenever ridge_on the EB shall always satisfy abs(check_1_1 - 1) <= eps6 & abs(check_1_2) <= eps6 & abs(check_1_3) <= eps6 & abs(check_2_1) <= eps6 & abs(check_2_2 - 1) <= eps6 & abs(check_2_3) <= eps6 & abs(check_3_1) <= eps6 & abs(check_3_2) <= eps6 & abs(check_3_3 - 1) <= eps6'
   message: These reserved letter combinations cannot be used: abs, abs, abs, abs, abs, abs, abs, abs, abs.
   hint: The function names abs and max (and min) are reserved. Use absReal(x) for the absolute value; max and min cannot be used, express the condition with comparisons and | instead.
```

단계 F1 답 (수락 문장)

```text
Whenever ridge_on the EB shall always satisfy absReal(check_1_1 - 1) <= eps6 & absReal(check_1_2) <= eps6 & absReal(check_1_3) <= eps6 & absReal(check_2_1) <= eps6 & absReal(check_2_2 - 1) <= eps6 & absReal(check_2_3) <= eps6 & absReal(check_3_1) <= eps6 & absReal(check_3_2) <= eps6 & absReal(check_3_3 - 1) <= eps6
```

호출 기록 (`batch_calls.jsonl`)

```text
batch_id: F1|06_EB|DIRECT|0|0e58114a|0
n: 1  n_answered: 1
```

- 이 챌린지의 단위별 피드백 횟수 (`units.json`): Adv-EARS+G 1, Adv-EARS+R2 1, Boilerplate+G 1, Boilerplate+R2 3, DIRECT 1, EARS+G 0, EARS+R2 1, MASTeR+G 2, MASTeR+R2 1, SPIDER+G 4, SPIDER+R2 2

### P7a. 키워드 점검 (단계 KC1)

- 하는 일 (점검 단계이며 FRET 파서 실패 로그를 받아 다시 쓰는 피드백이 아님. 결정 `docs/V20_BATCH_DESIGN.md` 11절)
  - 대상: 마지막 답의 문장이 모두 공식 파서에 수락된 단위 (왕복과 같음)
  - 문장마다 키워드 그룹을 기계적으로 정함: FRET 파서 출력의 필드 `scope.type`, `condition`, `qualifier_word`, `timing`과 위치 범위 `scopeTextRange`, `timingTextRange` (`$RUN/gen/kc_fields.jsonl` 캐시). 파서 출력이 없을 때만 문장의 어휘 토큰으로 정하고 `via`에 기록
  - 그룹: COND (upon, when, where, if, whenever, unless), TIMING_POINT (타이밍 생략, immediately, initially, at the first/same/next timepoint, finally, at the last timepoint, eventually, always, never), TIMING_DURATION (within, for, after), TIMING_STOP (until, before), SCOPE (범위 키워드가 있을 때, 범위 생략은 발동하지 않음)
  - 그룹이 있는 문장만 목록에 넣고, 배치 전체에 그룹이 없으면 건너뜀 (`kc_skipped`)
  - 에이전트에게 원래 입력, 자신의 답의 문장과 그룹, 발동한 그룹의 공식 참조 문서(배치에서 한 번씩)를 주고 같은 스키마로 다시 답하게 함. 에이전트 범위는 왕복과 같음. 규칙 조립(+R2) 단위는 조립된 문장을 보고 슬롯 답(S2 프롬프트)을 다시 냄
  - 채택 규칙: KC 답의 문장이 모두 수락될 때만 채택 (`kc_adopted`), 아니면 vf가 남고 변형 kc는 vf와 같음. 왕복은 채택된 kc 답에서 시작
  - 기록: 호출 행의 열 `kc_groups`, 단위 상태의 `kc_adopted`, `kc_changed`, `kc_skipped`, `run_info.json`의 `kc_doc_sha` (그룹별 참조 문서 sha256)
- 입력: 방식별 마지막 답, 공식 파서 필드, 참조 문서 `src/nl2fret/prompts/kc/KC_*.md`
- 출력: 단계 `KC1` 행, `$RUN/gen/kc_fields.jsonl`
- 코드: `src/nl2fret/kc_stage.py` (`groups_for`, `plan`, `block_text`, `with_kc`, `chain`), `src/nl2fret/batch_pipeline.py` (`phase_kc`, 끄는 옵션 `--no-kc`, `run_batch.sh`의 `NO_KC=1`)
- 고정 문구 (코드 상수, V-STYLE 린트 대상)

```text
KC_HEAD:
CHECK OF KEYWORDS
Below is your current answer. For each sentence, the keyword groups of its keywords are listed, followed by the reference text of the FRETish guide for each listed group. Compare the keyword that the sentence uses with every other keyword of its group.

KC_TAIL:
Return the complete answer again in exactly the JSON schema of the first answer. A sentence stays unchanged when the comparison confirms its keywords.
```

- 예제: 이 도구에는 KC 단계로 실행한 결과가 아직 없어서 실행에서 읽은 예제 값이 없다 (규칙: 예제는 실제 파일에서 읽음). 메시지 조립은 단위 시험과 모델 호출 없는 점검(`tests/test_v20_kc.py`)으로 확인했다

### P7. 왕복 (단계 RT1)

- 하는 일
  - 마지막 답의 문장이 모두 공식 파서에 수락된 단위가 대상. 시작하는 답은 채택된 KC 답, 없으면 vf 답
  - 파서가 각 문장에 대해 쓰는 영어 설명을 수집 (`descriptions.jsonl` 캐시)
  - 에이전트에게 원래 사용자 메시지, 자신의 답, 문장별 FRET 설명을 주고 같은 스키마로 다시 답하게 함
  - 채택 규칙: 왕복 답의 문장이 모두 수락될 때만 채택 (`rt_adopted`)
- 입력: 방식별 마지막 답, FRET 설명
- 출력: 단계 `RT1` 행, `$RUN/gen/descriptions.jsonl`
- 코드: `src/nl2fret/rt_stage.py` (`applicable`, `descriptions`, `body`, `with_rt`), `src/nl2fret/batch_pipeline.py` (`phase_rt`)
- 예제: `LM-06_EB-N1`의 Direct

FRET이 쓴 영어 설명 (`descriptions.jsonl`)

```text
SCOPE: in the interval defined by the entire execution. | TRIGGER: every point in the interval where (ridge_on) is true. | REQUIRED BEHAVIOR: for every trigger, (absReal ( check_1_1 - 1 ) must hold at all time points between (and including) the trigger and the end of the interval.
```

왕복 답 (수락 문장)

```text
Whenever ridge_on the EB shall always satisfy absReal(check_1_1 - 1) <= eps6 & absReal(check_1_2) <= eps6 & absReal(check_1_3) <= eps6 & absReal(check_2_1) <= eps6 & absReal(check_2_2 - 1) <= eps6 & absReal(check_2_3) <= eps6 & absReal(check_3_1) <= eps6 & absReal(check_3_2) <= eps6 & absReal(check_3_3 - 1) <= eps6
```

호출 기록 (`batch_calls.jsonl`)

```text
batch_id: RT1|06_EB|DIRECT|0|0e58114a|0
n: 2  n_answered: 2
```

### P8. LTL 도출과 판정 입력 생성

- 하는 일
  - 호출 기록에서 단위(항목 x 방식 x 반복)별 최종 문장과 상태 재구성 (라운드, 거절 횟수, 피드백 횟수, fallback)
  - 변형마다 문장 선택: v0 = 첫 답변, vf = 파서 피드백 뒤, rt = 왕복 뒤
  - 문장을 FRET 공식 파서로 컴파일해 LTL 포뮬라(과거시제, 미래시제) 도출
  - 실행 옵션은 `$RUN/gen/snapshot/run_info.json`에서 읽어 적용
- 입력: `$RUN/gen/calls.jsonl`, `$RUN/gen/parser_cache.jsonl`, `$RUN/gen/snapshot/run_info.json`, 항목 파일 `src/nl2fret/data/lm_items.jsonl`
- 출력 (변형 v0, vf, kc, rt 각각)
  - `$RUN/inputs_<변형>/units.json` (단위 목록: 항목, 방식, 반복, 상태, 문장, 피드백 횟수, fallback, 거절 횟수, 미완료 여부)
  - `$RUN/inputs_<변형>/fret_ltl_gen.jsonl` (문장별 `parser_ok`, `ltl_pt`, `ltl_ft`)
  - `$RUN/inputs_<변형>/unit_state.jsonl` (단위별 전체 라운드 기록)
- 코드: `src/nl2fret/tools/make_judge_inputs.py` (`--variant`), `src/nl2fret/units3.py`, `src/nl2fret/rt_stage.py` (`with_rt`), `src/nl2fret/fret_check/tools/fret_compile.py`
- 예제: `LM-06_EB-N1`의 Direct 단위 (`inputs_<변형>/units.json`)

```text
v0: status=parse_error status_code=expr_reserved_abs_max texts=0 n_feedback=1
vf: status=parsed texts=1 n_feedback=1 n_rejected_sentence_attempts=1
rt: status=parsed texts=1
```

`inputs_vf/fret_ltl_gen.jsonl`의 문장 하나 (같은 단위)

```text
sentence: Whenever ridge_on the EB shall always satisfy absReal(check_1_1 - 1) <= eps6 & absReal(check_1_2) <= eps6 & absReal(check_1_3) <= eps6 & abs...
parser_ok: True
ltl_pt: (H ((H (! ridge_on)) | (((((((((absReal((check_1_1 - 1)) <= eps6) & (absReal(check_1_2) <= eps6)) & (absReal(check_1_3) <= eps6)) & (absReal(check_2_1) <= eps6)) & (absReal((check_2_2 - 1)) <= eps6)) ...
ltl_ft: (LAST V (ridge_on -> (LAST V (((((((((absReal((check_1_1 - 1)) <= eps6) & (absReal(check_1_2) <= eps6)) & (absReal(check_1_3) <= eps6)) & (absReal(check_2_1) <= eps6)) & (absReal((check_2_2 - 1)) <= e...
```

### P9. 신호 이름 정렬

- 하는 일
  - 생성 LTL의 식별자를 챌린지 딕셔너리와 대조: `exact` (딕셔너리 이름, 유지), `aliased` (대소문자, 밑줄 차이를 무시하면 딕셔너리 이름 1개와 일치, 딕셔너리 이름으로 변경), `oov` (딕셔너리 밖, 유지하고 목록화)
  - 생성 변수와 기준 변수의 대응 결정 (anchor 모드: 이름과 타입이 기준에 있는 변수는 이름 유지, 나머지는 같은 타입의 미사용 기준 변수에 1대1 대응)
  - 대응 후보 0개: 역할 UND (`atomization_mismatch`)
- 입력: `$RUN/inputs_<변형>/fret_ltl_gen.jsonl`, 딕셔너리 `data/dictionary/lm_dictionary.csv`, 기준 LTL `data/reference/lm_reference_with_ltl.jsonl`
- 출력: 판정 기록의 `dict_alignment` (exact, aliased, oov), `alignment` (모드, 대응표, 후보 수)
- 코드: `src/nl2fret_judge/dict_align.py`, `align.py`, `abstraction.py`, `ap_check.py`
- 예제

변형 vf의 EARS+R2 쌍 (`LM-06_EB-N1|EARS+R2|0|s0|p1|v1`)

```text
dict_alignment: {"exact": ["check_11", "check_12", "check_13", "check_21", "check_22", "check_23", "check_31", "check_32", "check_33", "det_B_BT", "eps12", "eps6"], "aliased": {}, "oov": []}
alignment: {"mode": "anchor", "n_candidates": 15, "n_tried": 15, "und": null, "anchored": 11}
alignment.mapping: {"check_11": "check_11", "check_12": "check_12", "check_13": "check_13", "check_21": "check_21", "check_22": "check_22", "check_23": "check_23", "check_31": "check_31", "check_32": "check_32", "check_33": "check_33", "eps12": "eps12", "eps6": "eps6", "det_B_BT": "B_11"}
```

변형 vf의 Direct 쌍 (`LM-06_EB-N1|DIRECT|0|s0|p1|v1`): 대응 후보 0개

```text
role: UND
und_reason: atomization_mismatch
nm_detail: {"message": "too many renamings"}
alignment: {"mode": "anchor", "mapping": null, "n_candidates": 0, "n_tried": 0, "und": null}
```

### P10. 판정

- 하는 일
  - 단위의 각 문장을 기준 부분의 모든 버전과 쌍으로 판정
  - 쌍마다 LTL을 불리언 식으로 추상화한 뒤 NuSMV 질의 3종 실행
    - `equiv`: 기준 <-> 생성
    - `sound`: 기준 -> 생성 (거짓이면 ALARM: 기준은 성립, 생성은 위반)
    - `compl`: 생성 -> 기준 (거짓이면 MISS: 생성은 성립, 기준은 위반)
  - 질의 결과로 역할 결정, 부분의 대표 = 버전 중 가장 좋은 역할 (SAME < PROOF < REFUTE < NEITHER < N/M < UND)
  - 부분 성공 = SAME 또는 PROOF
  - 변형 v0, vf, kc, rt를 같은 판정기와 같은 설정으로 각각 판정
  - 판정기의 `aliased` 처리 (`src/nl2fret_judge/dict_align.py`): 생성 식의 식별자 중 딕셔너리 이름이 아니면서 대소문자와 밑줄을 무시한 철자가 딕셔너리 이름 1개와 같은 것을 그 이름으로 바꿈. 기준 식은 바꾸지 않고, 역할과 성공(SAME 또는 PROOF) 계산에 영향 없음

| sound | compl | 역할 | 뜻 |
|---|---|---|---|
| 성립 | 성립 | SAME | 기준과 동치 |
| 거짓 | 성립 | PROOF | 생성식이 기준식보다 강함 |
| 성립 | 거짓 | REFUTE | 생성식이 기준식보다 약함 |
| 거짓 | 거짓 | NEITHER | 서로 다른 의미 |
| 정렬 후보 0개 | - | UND | 비교 불가 (`und_reason`) |
| 엔진 판정 실패 | - | N/M | 시간 초과 등 (`nm_reason`) |

- 입력: `$RUN/inputs_<변형>/units.json`, `fret_ltl_gen.jsonl`, 기준 `data/reference/lm_reference_with_ltl.jsonl`, 딕셔너리 `data/dictionary/lm_dictionary.csv`
- 출력 (변형별 `$RUN/judge_<변형>/`): `judge_records.jsonl` (쌍별 기록), `part_results.jsonl` (부분별 대표), `counterexamples.jsonl`, `smv/<sha256>.smv` (질의 파일), `run_header.json`, `work/`
- 코드: `src/nl2fret_judge/cli.py` (`judge-parts`), `parts.py`, `judge.py`, `engines.py`, `ltl_engines.py`, `recorder.py`, `units.py`, `selfcheck.py` (`make selfcheck`), `src/legacy/judge2.py`, `judge4.py`, `judge5.py`, `judge_pt.py` (정렬 후보 생성)
- 외부 도구: NuSMV 2.6.0 (Docker 이미지 `cst-nusmv:local`, 빌드 `external/docker/cst-nusmv/`), 질의당 시간 제한 120초, 시간 구간 확장 상한 `--cap`
- 판정 설정: 모드 `anchor`, 엔진 `nusmv`, 엔진 버전 `NuSMV 2.6.0 (compiled on Wed Oct 14 15:36:56 2015)`, 판정기 버전 `1.0.0`
- 예제: `LM-06_EB-N1`의 쌍별 결과

| 방식 | 변형 | 기준 버전 | 역할 | 질의 | 반례 상태 |
|---|---|---|---|---|---|
| `DIRECT` | vf | v1 | UND | - | not_available:atomization_mismatch |
| `DIRECT` | rt | v1 | UND | - | not_available:atomization_mismatch |
| `EARS+G` | v0 | v1 | UND | - | not_available:atomization_mismatch |
| `EARS+G` | vf | v1 | UND | - | not_available:atomization_mismatch |
| `EARS+G` | rt | v1 | UND | - | not_available:atomization_mismatch |
| `EARS+R2` | vf | v1 | NEITHER | compl 15, equiv 1, sound 15 | recorded |
| `EARS+R2` | rt | v1 | NEITHER | compl 15, equiv 1, sound 15 | recorded |

- 질의 열은 쌍의 질의 개수 (시간 구간 확장마다 `sound`, `compl` 질의를 반복하고 마지막에 `equiv` 질의 1개)
- 판정 기록이 없는 (방식, 변형) 조합은 비교 가능한 문장이 없는 단위 (v0의 Direct, EARS+R2는 첫 답이 거절되어 문장 0개)

부분 결과 (`$RUN/judge_vf/part_results.jsonl`, EARS+R2 단위)

```text
{"n_sentences": 1, "n_parts": 1, "n_parts_success": 0, "all_parts_success": false}
parts[0]: {"part": 1, "n_versions": 1, "role": "NEITHER", "success": false, "representative": {"pair_id": "LM-06_EB-N1|EARS+R2|0|s0|p1|v1", "sentence_index": 0, "version": 1, "reference_id": "EB-001"}}
```

### P11. 반례 기록

- 하는 일
  - 거짓인 질의마다 NuSMV 반례(상태열)를 파싱해 질의 종류별로 기록
  - 반례 종류: `sound` (ALARM), `compl` (MISS), `equiv` (두 식이 다름)
  - 상태: `recorded` (반례 있음), `not_needed` (SAME), `not_available:<사유>` (UND 등 질의가 없는 쌍)
- 입력: 판정의 질의 결과와 NuSMV 출력
- 출력: `$RUN/judge_<변형>/counterexamples.jsonl` (쌍별 반례 목록), 판정 기록의 `counterexample_status`, `counterexamples`
- 코드: `src/nl2fret_judge/engines.py` (반례 파서), `judge.py`, `parts.py`
- 예제: 변형 vf의 EARS+R2 쌍 (`LM-06_EB-N1|EARS+R2|0|s0|p1|v1`)

```text
status: recorded
required: True
role: NEITHER
counterexamples: 3개, 첫 항목의 키: ['kind', 'meaning', 'smv_path', 'smv_sha256', 'spec_text', 'trace']
```

### P12. 집합 Realizable

- 하는 일
  - 한 (방식, 챌린지, 반복)의 최종 문장(변형 rt)을 공식 파서가 수락한 것만 모아 요구사항 집합 1개로 구성 (컴포넌트 이름 `SYS` 하나, 집합 자신의 문장으로 만든 변수 표 하나)
  - 사용자 정의 함수 적용이 있는 문장은 모델링할 수 없어 제외하고 수를 기록 (`n_excluded_function`)
  - FRET CLI `fretCLI realizability <프로젝트> <컴포넌트> --solver kind2 --timeout <초> --json` 실행 (Docker 이미지 안)
  - 같은 챌린지의 기준 FRETish(부분의 첫 버전) 집합 `REFERENCE`를 같은 방식으로 검사
  - 입력 정규화 N-LIT (`src/nl2fret/fret_check/tools/litnorm.py`): 문장의 조건과 응답 구간(파서의 `conditionTextRange`, `responseTextRange`)에서, double 변수 또는 실수 리터럴과 같은 산술식이나 비교에 쓰인 정수 리터럴 `n`을 `n.0`으로 변경. 타이밍, 범위, 컴포넌트 텍스트와 판정용 문장, 모델 피드백 문장은 변경 대상 밖. 변환한 문장은 공식 파서로 다시 컴파일하고 변수표를 다시 만들어 두 번째 집합 작업으로 검사
  - 주 지표는 normalized, 보조 지표는 raw. 결과 열: `result`와 `raw_result`(CLI 원값)는 normalized의 값(주), `result_raw`, `cli_result_raw`, `error_raw` (변환 없음, 보조), `result_normalized`, `cli_result_normalized` (변환 뒤), `cli_result_raw`, `cli_result_normalized`, `n_literals_converted`, `n_sentences_changed`, `type_changes` (두 변수표에서 타입이 달라진 변수). 변환할 리터럴이 없는 집합은 한 번만 검사
  - 결과 값: `realizable`, `unrealizable`, `unknown` (CLI가 ERROR 또는 UNKNOWN을 출력하거나 JSON이 없음), `empty` (남은 문장 없음), `not_run` (`--dry-run`)
  - 결과의 용도: 보조 지표 (변환과 문장 단위 판정에서 분리)
- 입력: `$RUN/inputs_rt/`, 기준 `data/reference/lm_reference_with_ltl.jsonl`
- 출력: `$RUN/group_rlz.jsonl` (집합마다 1행)
- 코드: `src/nl2fret/fret_check/group_rlz.py`, `src/nl2fret/fret_check/tools/litnorm.py`, `src/nl2fret/fret_check/tools/fret_rlz.py`, `src/nl2fret/fret_check/tools/fretexpr.py`, `src/nl2fret/fret_check/tools/fret_import.js`, 변수 표 규칙 `src/nl2fret/fret_check/variable_policy.md`
- 외부 도구: Docker 이미지 `fret-lab:latest` (FRET CLI, Kind2)
- 예제: 챌린지 06_EB, 반복 0

| 집합 | 문장 수 | 제외 | 변환 리터럴 | 결과 raw | 결과 normalized | CLI의 `result` (raw / normalized) |
|---|---|---|---|---|---|---|
| `Adv-EARS+G` | 2 | 0 | 0 | realizable | realizable | REALIZABLE / REALIZABLE |
| `Adv-EARS+R2` | 2 | 0 | 3 | unknown | realizable | ERROR / REALIZABLE |
| `Boilerplate+G` | 2 | 0 | 3 | unknown | unknown | ERROR / ERROR |
| `Boilerplate+R2` | 2 | 0 | 3 | unknown | unknown | ERROR / ERROR |
| `DIRECT` | 2 | 0 | 3 | unknown | realizable | ERROR / REALIZABLE |
| `EARS+G` | 2 | 0 | 9 | unknown | realizable | ERROR / REALIZABLE |
| `EARS+R2` | 2 | 0 | 3 | unknown | realizable | ERROR / REALIZABLE |
| `MASTeR+G` | 2 | 0 | 3 | unknown | realizable | ERROR / REALIZABLE |
| `MASTeR+R2` | 2 | 0 | 3 | unknown | realizable | ERROR / REALIZABLE |
| `REFERENCE` | 1 | 1 | 0 | realizable | realizable | REALIZABLE / REALIZABLE |
| `SPIDER+G` | 2 | 0 | 3 | unknown | realizable | ERROR / REALIZABLE |
| `SPIDER+R2` | 2 | 0 | 3 | unknown | realizable | ERROR / REALIZABLE |

- CLI 출력은 JSON 객체이며 `systemComponents[0]`의 `monolithic.result` 또는 `compositional.result` 값(`UNCHECKED`가 아닌 쪽) `"REALIZABLE"`, `"UNREALIZABLE"`을 `realizable`, `unrealizable`로 기록하고 그 밖의 값(`"ERROR"` 등)은 `unknown`으로 기록
- 집합 `DIRECT`의 CLI 출력, 문장 그대로 (raw) (`$RUN/group_rlz_container.log`에서 읽음)

```text
monolithic.result: UNCHECKED
compositional.result: ERROR
compositional.connectedComponents: cc0 requirements=['R1'] result=ERROR error={}
compositional.connectedComponents: cc1 requirements=['R2'] result=REALIZABLE error=''
```

- 집합 `DIRECT`의 CLI 출력, 정수 리터럴 정규화 뒤 (normalized)

```text
monolithic.result: UNCHECKED
compositional.result: REALIZABLE
compositional.connectedComponents: cc0 requirements=['R1'] result=REALIZABLE error=''
compositional.connectedComponents: cc1 requirements=['R2'] result=REALIZABLE error=''
```

- 정규화 전후의 요구사항 R1 문장 (`DIRECT`, 앞부분)

```text
raw       : Whenever ridge_on the EB shall always satisfy absReal(check_1_1 - 1) <= eps6 & absReal(check_1_2) <= eps6 & absReal(check_1_3) <= eps6 & absReal(check...
normalized: Whenever ridge_on the EB shall always satisfy absReal(check_1_1 - 1.0) <= eps6 & absReal(check_1_2) <= eps6 & absReal(check_1_3) <= eps6 & absReal(che...
```

### P13. 효과 집계

- 하는 일
  - 변형 v0, vf, kc, rt의 `part_results.jsonl`을 읽어 방식과 변형별 단위 수, 부분 수, 성공(SAME 또는 PROOF) 부분 수와 비율 집계
  - 같은 (항목, 반복, 부분)에서 변형 사이에 실패 -> 성공(이득), 성공 -> 실패(손실)가 된 부분 수 집계
  - 산출: 개수와 비율
  - `--only-item <id>...`, `--only-challenge <챌린지>...`: 지정한 항목, 챌린지의 부분만 집계 (일부 항목만 호출한 실행용, `run_batch.sh effect`는 `ONLY`를 전달)
- 입력: `$RUN/judge_v0/`, `judge_vf/`, `judge_kc/`, `judge_rt/`의 `part_results.jsonl`
- 출력: `$RUN/rt_effect.json` (판정 `judge_*`로 집계, 한 가지 기준) (`per_arm`, `pairs`)
- 코드: `src/nl2fret/tools/rt_effect.py`
- 예제: Direct

```text
per_arm.DIRECT: {"v0": {"parts": 2, "success": 0}, "vf": {"parts": 2, "success": 0}, "rt": {"parts": 2, "success": 0}}
pairs: {"v0->vf": {"common_parts": 2, "gain": 0, "loss": 0}, "v0->rt": {"common_parts": 2, "gain": 0, "loss": 0}, "vf->rt": {"common_parts": 2, "gain": 0, "loss": 0}}
```

- 부분 수 2는 `ONLY=06_EB`로 집계한 챌린지 06_EB의 부분 수 (`ONLY`가 없으면 `inputs_*/units.json`의 전체 단위, 미완료 단위 포함의 부분을 집계)

### P14. 자산 버전 관리

- 하는 일
  - 입력 데이터와 프롬프트 자산의 버전 등록 (`assets/<자산>/v<N>/`), 이전 버전은 `archive/`로 이동
  - `VERSIONS.md`의 현재 버전, 경로, 변경 사유, 변경을 일으킨 실험 열 갱신
- 입력: 수정한 자산, `VERSIONS.md`
- 출력: `assets/`, `archive/`, `VERSIONS.md`
- 위치: `VERSIONS.md`(맨 위에 버전업 규칙), `assets/`, `archive/README.md`

## 4. 파일 목록

### 4.1 외부 도구

| 구성 | 버전 | 위치와 호출 | 프로세스 |
|---|---|---|---|
| Claude Code CLI | 2.1.274 (Claude Code) | 실행 파일 `claude`, 호출 코드 `src/nl2fret/agent_call.py` (`claude -p --output-format json --system-prompt <프롬프트> --json-schema <스키마> --tools "" --no-session-persistence --setting-sources "" --disable-slash-commands --strict-mcp-config`), 모델 인자 `sonnet`, `--effort medium` | P2, P4-P7 |
| FRET 공식 파서와 CLI | FRET v3.1.0 | Docker 이미지 `fret-lab:latest`, 빌드 레시피 `external/docker/fret-lab/` (`Dockerfile`, `fret.sh`, `README.md`, `LICENSE`) | P2, P6-P8, P12 |
| Kind2 | fret-lab 이미지 안 | `fretCLI realizability ... --solver kind2` | P12 |
| NuSMV | 2.6.0 | Docker 이미지 `cst-nusmv:local`, 빌드 레시피 `external/docker/cst-nusmv/` (`Dockerfile`, `nusmv_context.sha256`, `README.md`) | P10, P11 |
| z3-solver | 5.3.3.0 | Python 패키지 (`pyproject.toml`의 의존성 `z3-solver`, 추가 `test`의 `pytest`; 버전은 예제 실행 환경의 값) | P10 |
| node | 호스트 | FRET 파서의 호스트 실행 (파서 지문 비교) | P2 |
| Python | 3.10 이상 | `pip install -e ".[test]"`로 `pyproject.toml`의 패키지를 설치한 환경 | 전체 |
| NuSMV 호출 래퍼 | - | `assets/experiment_scripts/v1/NuSMV_docker_wrapper.sh` (컨테이너 `cst-nusmv:local`로 NuSMV 실행, `NUSMV` 변수) | P10, P11 |

### 4.2 코드

경로 기준: `nl2fret_tool/`. 프로세스 열은 3절의 번호. 보조는 3절의 흐름 밖에서 쓰는 도구

| 파일 | 역할 | 프로세스 |
|---|---|---|
| `Makefile` | 명령 모음 (`install`, `test`, `build`, `selftest`, `selfcheck`, `clean`) | 점검 |
| `data/dataset/build_dataset.py` | 데이터셋 파일 생성 | P1 |
| `data/dictionary/build_dict.py` | 딕셔너리 파일 생성 | P1 |
| `pyproject.toml` | PyPA 프로젝트 정의: 빌드 시스템(setuptools), 메타데이터, 의존성(`z3-solver`, 추가 `test`), 진입점 `nl2fret-batch`, `nl2fret-run`, `nl2fret-judge`, 패키지 데이터, pytest 설정. 버전은 `VERSION` | 점검 |
| `scripts/build_cases.py` | 실험 폴더의 데이터에서 입력 케이스(`data/cases/`) 생성 | 점검 |
| `scripts/render_prompts.py` | 프로젝트 프롬프트 파일(`prompts/current/system_prompts/`)을 코드에서 다시 만들고 디스크 파일과 대조 (`--check`) | 점검 |
| `scripts/run_batch.sh` | v2.0 단계 실행 (`pin`, `gen`, `inputs`, `judge`, `group`, `effect`, `all`; 환경 변수 `EXT`로 확장 모듈 선택, 기본 `dictionary`) | P2-P13 |
| `scripts/run_fsm.sh` | v1.3 흐름의 단계 실행 (`lint`, `dryrun`, `gen`, `inputs`, `judge`, `trace`) | P2-보조 |
| `scripts/run_intent.sh` | v1.4 단계 실행 (`lint`, `dryrun`, `gen`, `inputs`, `judge`, `trace`, `controls`, `analyze`, `compare`) | P2-보조 |
| `scripts/run_selftests.sh` | 기존 자체 시험과 ltlpack 자체 시험 실행 (모델 호출, Docker 없음) | 점검 |
| `scripts/verify_lm_docx.py` | 록히드마틴 케이스의 원문 docx 대조 점검 | 점검 |
| `src/legacy/judge2.py` | 정렬 후보 생성용 기존 판정 코드 (z3 경계 검사 확장) | P9 |
| `src/legacy/judge4.py` | 정렬 후보 생성용 기존 판정 코드 (반례 포함) | P9 |
| `src/legacy/judge5.py` | 구조 수준 PROOF/REFUTE 비교 | P9 |
| `src/legacy/judge_pt.py` | 과거시제 LTL의 z3 경계 동치 검사 | P9 |
| `src/nl2fret/__init__.py` | 패키지 표시 파일 (`__version__`을 설치된 메타데이터에서 읽음) | 점검 |
| `src/nl2fret/agent_call.py` | 격리된 에이전트 호출 1회 (`claude` 프로세스: 허용 환경 변수, 빈 작업 폴더, 도구 없음, 세션 없음, JSON 스키마 답변), 격리 검사 `isolation_probe` | P2, P4-P7 |
| `src/nl2fret/batch_pipeline.py` | v2.0 생성 파이프라인 본체: 방식, 템플릿, 챌린지, 반복마다 에이전트 호출, 단계 A, D, B, S, 파서 피드백, 왕복, 호출 기록, 재개 | P3-P7 |
| `src/nl2fret/cli.py` | Claude Code CLI 호출, 세션 한도 감지와 대기, 재시도, 호출 기록 쓰기 | P4-P7 |
| `src/nl2fret/common.py` | 공통 프롬프트 문장(v1.4 판과 `--fret-reference`용 `*_V15` 판), 시스템 프롬프트 조립 `build_system`, 사용자 프롬프트(A, B, D), 출력 JSON 파서 | P3-P5 |
| `src/nl2fret/ext/__init__.py` | 확장 모듈 고리: 이름 검증(`parse`)과 `DICTIONARY`; 핵심은 이름만 안다 | P2 |
| `src/nl2fret/ext/dictionary/README.md` | 확장 `dictionary`의 역할, 인터페이스, 켜는 방법 | P1 |
| `src/nl2fret/ext/dictionary/__init__.py` | 확장 `dictionary` 패키지 표시 파일 | P1 |
| `src/nl2fret/ext/dictionary/attach.py` | 확장 `dictionary`의 붙이는 쪽: `prompt_block(챌린지)`(FRETish 단계가 받는 딕셔너리 글), `rendered`, `missing`, `switch_on` | P1, P4 |
| `src/nl2fret/ext/dictionary/build.py` | 확장 `dictionary`의 갱신 쪽: `verify`, `record`, `update`, `overlay` | P1 |
| `src/nl2fret/ext/dictionary/judge_input.py` | 확장 `dictionary`의 판정 쪽: `judge-parts`의 `--dictionary` 인자 (켜짐: 딕셔너리 v1 파일, 꺼짐: 항목 없는 머리글 파일) | P9 |
| `src/nl2fret/ext/dictionary/overlays/v2/alias_evidence.json` | 덧씌우기 v2의 별칭 근거 (후보 42쌍, 근거 있음 9쌍, 알 수 없음 33쌍) | P1 |
| `src/nl2fret/ext/dictionary/overlays/v2/build_alias_v2.py` | 덧씌우기 v2 생성: NASA 요구사항의 Originally comments와 현재 fulltext의 토큰 대조로 근거가 있는 별칭 쌍만 열 `alias_of`, `alias_evidence`에 기록 | P1 |
| `src/nl2fret/ext/dictionary/overlays/v2/build_dict.py` | 딕셔너리 v1 생성기의 사본 (`data/dictionary/build_dict.py`와 같음) | P1 |
| `src/nl2fret/ext/dictionary/overlays/v2/lm_dictionary.csv` | 선택 덧씌우기(기본 꺼짐): 별칭 열 `alias_of`, `alias_evidence`가 있는 딕셔너리 (별칭 쌍 9개) | P1 |
| `src/nl2fret/ext/dictionary/versions/v1/EVIDENCE.json` | 딕셔너리 v1 근거 기록 (행 수, 열, 챌린지별 행 수, 생성기 이름) | P1 |
| `src/nl2fret/extract_files.py` | 프롬프트 문서의 파일 블록 추출과 해시 확인 | 보조 |
| `src/nl2fret/fret_check/__init__.py` | 패키지 표시 파일 | 점검 |
| `src/nl2fret/fret_check/check.py` | 파서 수락 문장의 실현가능성 판정 기록 | 보조 |
| `src/nl2fret/fret_check/group_rlz.py` | 챌린지 단위 집합 Realizable 검사 (`fretCLI realizability`, kind2), raw와 normalized 두 열 | P12 |
| `src/nl2fret/fret_check/parser_fingerprint.py` | FRET 파서 지문 계산, 고정(`--write-pin`), 대조(`--check`), 두 덤프 비교(`--compare`) | P2 |
| `src/nl2fret/fret_check/tools/__init__.py` | 패키지 표시 파일 | 점검 |
| `src/nl2fret/fret_check/tools/fret_compile.py` | Docker `fret-lab`에서 FRET 파서 실행, LTL 출력 | P6, P8 |
| `src/nl2fret/fret_check/tools/fret_import.js` | FRET 프로젝트 가져오기 스크립트 (컨테이너 안에서 요구사항과 변수 문서를 FRET 저장소에 적재) | P12 |
| `src/nl2fret/fret_check/tools/fret_rlz.py` | FRET 실현가능성 검사: 변수 표 작성, FRET 프로젝트 문서 작성, `fretCLI realizability` 일괄 실행, CLI JSON 요약 | P12 |
| `src/nl2fret/fret_check/tools/fretexpr.py` | FRET 출력 식 파서 (집합 검사의 변수 표 작성에 사용) | P12 |
| `src/nl2fret/fret_check/tools/fretjs/fret_parse_full.js` | 컨테이너 안에서 `FretSemantics.compile` 실행 | P6 |
| `src/nl2fret/fret_check/tools/fretjs/fret_parse_node.js` | 호스트 node에서 `FretSemantics.compile` 실행 (docker 파서와의 지문 비교용) | P2 |
| `src/nl2fret/fret_check/tools/fretjs/stub/product-iterable/index.js` | 파서 실행에 필요한 모듈의 대체 파일 | P6 |
| `src/nl2fret/fret_check/tools/litnorm.py` | 문장 텍스트 규칙: 조건과 응답 구간 추출, N-LIT 정수 리터럴 정규화 | P12 |
| `src/nl2fret/fretlint.py` | FRETish 식 검사 규칙, FRET 오류 메시지별 힌트 | P5, P6 |
| `src/nl2fret/fretparse.py` | FRET 공식 파서 호출(Docker)과 디스크 캐시, 모의 파서 | P6 |
| `src/nl2fret/kc_stage.py` | 점검 단계 KC: 파서 필드로 문장의 키워드 그룹 결정(어휘 대체), 메시지 조립(`KC_HEAD`, `KC_TAIL`), 채택 규칙, 단위 상태와 변형 사슬(`chain`) | P7a |
| `src/nl2fret/mock_claude.py` | 오프라인 시험용 가짜 `claude` CLI | 보조 |
| `src/nl2fret/paths.py` | 위치 상수: `PACKAGE`(패키지 폴더), `PROJECT`(연구 데이터가 있는 프로젝트 루트, 환경 변수 `NL2FRET_HOME`으로 바꿈) | P1 |
| `src/nl2fret/prompts/kc/KC_COND.md` | KC 참조 문서 (COND): FRETish 가이드의 줄 사본에 표제를 붙인 것 | P7a |
| `src/nl2fret/prompts/kc/KC_SCOPE.md` | KC 참조 문서 (SCOPE): FRETish 가이드의 줄 사본에 표제를 붙인 것 | P7a |
| `src/nl2fret/prompts/kc/KC_TIMING_DURATION.md` | KC 참조 문서 (TIMING_DURATION): FRETish 가이드의 줄 사본에 표제를 붙인 것 | P7a |
| `src/nl2fret/prompts/kc/KC_TIMING_POINT.md` | KC 참조 문서 (TIMING_POINT): FRETish 가이드의 줄 사본에 표제를 붙인 것 | P7a |
| `src/nl2fret/prompts/kc/KC_TIMING_STOP.md` | KC 참조 문서 (TIMING_STOP): FRETish 가이드의 줄 사본에 표제를 붙인 것 | P7a |
| `src/nl2fret/prompts3.py` | 방식(arm) 정의, 규칙 글 텍스트, 슬롯 프롬프트, 피드백 프롬프트, 옵션 변수(`DICT_ALL`, `FRET_REFERENCE`, `G_PARITY`, `TM_SOURCE_ONLY`, `SOURCED_ONLY`) | P3, P5, P6 |
| `src/nl2fret/rt_stage.py` | 왕복 단계: FRET의 영어 설명 수집, 왕복 프롬프트, 채택 규칙 | P7 |
| `src/nl2fret/run_pipeline.py` | v1.4 생성 파이프라인 (문장 단위 호출). v2.0 배치 파이프라인이 `build_prompts`, 단위 상태 재구성(`units_state`), 컴파일(`do_compile`) 함수를 가져다 씀 | P3, P6 |
| `src/nl2fret/score3.py` | 단위 점수와 실패 기록 (v3) | 보조 |
| `src/nl2fret/score_lm.py` | LM 벤치 점수 | 보조 |
| `src/nl2fret/tools/__init__.py` | 패키지 표시 파일 | 점검 |
| `src/nl2fret/tools/analyze_run.py` | 엄격 성공, 결정 지점, 원인 라벨 분석 | 보조 |
| `src/nl2fret/tools/build_fretish_reference.py` | FRET 공식 필드 문서 전문으로 `src/nl2fret/prompts/fretish_reference.md` 생성 | P1, P3 |
| `src/nl2fret/tools/build_inputs.py` | 항목 파일, 딕셔너리 텍스트, 기준 파일 생성 | P1 |
| `src/nl2fret/tools/compare_runs.py` | 두 실행의 항목 단위 부호 검정 비교 | 보조 |
| `src/nl2fret/tools/decision_points.py` | FRETish 문장의 결정 지점(범위, 조건 종류, 타이밍, 읽기) 판독 | 보조 |
| `src/nl2fret/tools/dev_record.py` | 개발 실행 관측 기록 | 보조 |
| `src/nl2fret/tools/dict_usage.py` | 생성 식별자의 딕셔너리 이름 사용 수 집계 | 보조 |
| `src/nl2fret/tools/fret_semantics_probe.js` | FRET 공식 파서가 문장에 대해 쓰는 영어 설명과 미래시제 포뮬라 출력 | 보조 |
| `src/nl2fret/tools/judge_controls.py` | 판정기 대조 (정답을 아는 쌍으로 오판 비율 측정) | P2 |
| `src/nl2fret/tools/make_judge_inputs.py` | 호출 기록에서 판정 입력(단위, 문장별 LTL, 단위 상태) 생성. 실행 옵션은 `snapshot/run_info.json`에서 읽음. `--variant v0|vf|rt` | P8 |
| `src/nl2fret/tools/make_preflight_items.py` | 예비 시험용 6항목 파일 생성 | P1 |
| `src/nl2fret/tools/make_sigdict.py` | LM 챌린지 문서(.docx)에서 딕셔너리 표 추출 | P1 |
| `src/nl2fret/tools/mock_fret.py` | 오프라인 시험용 가짜 실현가능성 결과 | 보조 |
| `src/nl2fret/tools/ownership_table.py` | 결정 소유권 표 생성, 근거 없는 활성 규칙 검사 | P2 |
| `src/nl2fret/tools/preflight_check.py` | 예비 시험 결과 검사 P1..P25 | 보조 |
| `src/nl2fret/tools/prompt_lint.py` | 프롬프트 lint P-1..P-6 | P2 |
| `src/nl2fret/tools/prompt_v15_lint.py` | 프롬프트 lint V-COMPLETE, V-PROVENANCE, V-LEAK, V-STATUS, V-STYLE (프롬프트 12개) | P2 |
| `src/nl2fret/tools/rt_effect.py` | 변형 v0, vf, kc, rt의 부분 성공 수와 변형 간 이득, 손실 집계, 키워드 선택 분포(`--keyword-inputs`) (`--only-item`, `--only-challenge`) | P13 |
| `src/nl2fret/tools/rule_probe.py` | 규칙 출력 모양의 파서 수락 조사 | P2 |
| `src/nl2fret/tools/rule_semantics_check.py` | 규칙 의미 검증 (FRET 파서 LTL 동치를 NuSMV로 확인) | P2 |
| `src/nl2fret/tools/selftest.py` | 규칙 층 골든 문장 시험 | P2 |
| `src/nl2fret/tools/smoke3_check.py` | 시범 실행 점검 표 | 보조 |
| `src/nl2fret/tools/timing_semantics.py` | 조건 종류와 타이밍 형태의 의미 표 `src/nl2fret/data/timing_semantics.json` 생성 (FRET 파서 LTL과 판정 엔진 사용) | 보조 |
| `src/nl2fret/tools/trace_report.py` | 단위별 추적 파일과 요약 표 생성 | 보조 |
| `src/nl2fret/tpl_rules.py` | 규칙표 52개, 템플릿 문장 분해, 슬롯 요청, 슬롯 검사, FRETish 조립 | P5 |
| `src/nl2fret/units3.py` | 호출 기록에서 단위 상태(라운드, 거절, fallback) 재구성 | P6, P8 |
| `src/nl2fret_judge/__init__.py` | 판정 모듈 버전 표기 | P10 |
| `src/nl2fret_judge/__main__.py` | 판정 모듈 실행 진입점 | P10 |
| `src/nl2fret_judge/abstraction.py` | LTL의 불리언 추상화 | P9, P10 |
| `src/nl2fret_judge/aggregate.py` | 판정 기록 집계 | P10 |
| `src/nl2fret_judge/align.py` | 변수 대응 후보 생성 (anchor 모드) | P9 |
| `src/nl2fret_judge/ap_check.py` | 원자 집합 불일치 기록 | P9 |
| `src/nl2fret_judge/cli.py` | 명령 `selfcheck`, `judge`, `judge-parts`, `aggregate` | P10 |
| `src/nl2fret_judge/dict_align.py` | 딕셔너리 정렬 (exact, aliased, oov) | P9 |
| `src/nl2fret_judge/engines.py` | NuSMV와 z3 질의 엔진, 질의 파일 작성, 반례 파서 | P10, P11 |
| `src/nl2fret_judge/judge.py` | 쌍 판정, 역할 결정, 반례 상태 | P10, P11 |
| `src/nl2fret_judge/ltl_engines.py` | LTL 파서와 NuSMV 구문 변환 | P10 |
| `src/nl2fret_judge/parts.py` | 부분 단위 판정, 대표 쌍 선택, 반례 기록 파일 | P10, P11 |
| `src/nl2fret_judge/recorder.py` | 판정 기록 파일 작성과 재개 | P10 |
| `src/nl2fret_judge/selfcheck.py` | 자기점검 5쌍 | P10 |
| `src/nl2fret_judge/units.py` | 단위와 기준 로드 | P10 |
| `tests/data/kc_parser_fields.json` | KC 시험용으로 기록한 공식 파서 출력 필드 (2026-11-17) | 점검 |
| `tests/test_inputs_flags.py` | `inputs`가 실행의 옵션(`snapshot/run_info.json`)으로 단위를 재생하는지 시험 | 점검 |
| `tests/test_judge.py` | 판정 모듈 시험 | 점검 |
| `tests/test_spider_table2.py` | SPIDER 표 2 형태의 분해와 조립 시험 | 점검 |
| `tests/test_v14_tools.py` | 재개 옵션 고정, 실행기 경로, 규칙 의미 검증 작업 폴더 시험 | 점검 |
| `tests/test_v15_lint.py` | 프롬프트 lint 통과 시험 | 점검 |
| `tests/test_v15_reference.py` | `--fret-reference`가 공식 필드 문서 전문을 추가하고 옵션이 꺼지면 v1.4 프롬프트와 바이트가 같은지 시험 | 점검 |
| `tests/test_v16_batch.py` | 에이전트 호출, 배치 응답, 왕복, 집합 검사, 격리 허용 항목 시험 | 점검 |
| `tests/test_v20_ext.py` | 확장 `dictionary` 켜짐과 꺼짐 시험 (프롬프트, 사용자 블록, 판정 인자, `run_batch.sh`) | 점검 |
| `tests/test_v20_kc.py` | 점검 단계 KC 시험: 그룹 결정, 채택 규칙, 메시지 조립, 참조 문서의 줄 단위 검사, 키워드 분포 | 점검 |
| `tests/test_v20_measure.py` | N-LIT 규칙과 `run_batch.sh` 단계 시험 | 점검 |
| `tests/test_v9.py` | 생성 파이프라인, 규칙, 프롬프트 시험 | 점검 |

- 이전 릴리스: `archive/releases/v1.4/` (11개 방식 FSM 시험), `archive/releases/v1.2.0/` (그 릴리스의 폴더 `judging`에 있는 동결 판정 코드와 `JUDGE_FROZEN_MANIFEST.sha256`)
- 메인 디렉터리의 보조 코드: `scripts/render_prompts.py` (시스템 프롬프트 파일 렌더링), `scripts/build_cases.py`, `scripts/verify_lm_docx.py`

### 4.3 프롬프트

| 파일 | 내용 | 사용 단계 |
|---|---|---|
| `src/nl2fret/prompts/fretish_reference.md` | FRET 공식 필드 문서 전문 (FRETish 가이드) | D, B, S |
| `src/nl2fret/prompts/sources_v15.json` | 참고문과 템플릿의 출처, 확인 상태 | 점검 |
| `src/nl2fret/templates_v15/masteR.md` | MASTeR 템플릿 설명 | A, B |
| `src/nl2fret/templates_v15/ears.md` | EARS 템플릿 설명 | A, B |
| `src/nl2fret/templates_v15/adv_ears.md` | Adv-EARS 템플릿 설명 | A, B |
| `src/nl2fret/templates_v15/spider.md` | SPIDER 템플릿 설명 | A, B |
| `src/nl2fret/templates_v15/boilerplate.md` | Boilerplate 템플릿 설명 | A, B |
| `src/nl2fret/common.py` | 코드 내 프롬프트 문장 (`TASK_A`, `TASK_D`, `TASK_B_V15`, `RULES_COMMON_V15`, `RULES_A_V15`, `SCHEMA_A_V15`, `SCHEMA_B_V15`, `NOTATION_V15`, `NOTATION_FRETISH_V15`, 사용자 메시지 형식) | A, D, B |
| `src/nl2fret/prompts3.py` | 코드 내 프롬프트 문장 (`D_RULES_V15`, `D5_RULE_V15`, `SLOT_SYSTEM_V15`, `SLOT_D_RULES_V15`, 피드백 문장 `LOG_HEAD`, `LOG_TAIL`, `FEEDBACK_TAIL`) | D, B, S, F |
| `src/nl2fret/batch_pipeline.py` | 배치 규칙 문단 `BATCH_RULES` | 전체 |
| `src/nl2fret/rt_stage.py` | 왕복 문장 `RT_HEAD`, `RT_TAIL` | RT1 |
| `src/nl2fret/agent_call.py` | 격리 검사 문장 `PROBE_SYSTEM`, `PROBE_USER` | P2 |
| `src/nl2fret/tpl_rules.py` | 규칙 글의 원본: 규칙표 `RULES` (규칙 ID, 설명, 근거 유형) | B, S |
| `src/nl2fret/fretlint.py` | 피드백에 붙는 FRET 오류별 힌트 문장 | F |
| `src/nl2fret/prompts/fretish_guide.md`, `fretish_guide_supplement.md`, `intent_declaration.md`, `src/nl2fret/templates/*.md` | v1.4 판 가이드, 보충문, 의도 선언, 템플릿 (`--fret-reference` 꺼짐 때 사용) | 보조 |

- 조립된 시스템 프롬프트 12개: `$RUN/gen/snapshot/system_prompt_*.txt` (P3의 표), 해시 `$RUN/gen/snapshot/run_info.json`
- 메인 디렉터리 사본 (내용 동일): `prompts/current/fretish_guide.md`, `prompts/current/templates/{adv_ears,boilerplate,ears,masteR,spider}.md`, `prompts/current/sources_v15.json`, `prompts/current/system_prompts/`
- 메인 디렉터리 색인과 도구: `prompts/INDEX.md`, `scripts/render_prompts.py`

### 4.4 입력 데이터

경로 기준: `nl2fret_tool/`. 프로세스 열은 3절의 번호

| 파일 | 내용 | 프로세스 |
|---|---|---|
| `data/audit/item_validity_audit.csv` | 항목 타당성 감사표 (분석의 층화에 사용) | 보조 |
| `data/dataset/lm_dataset_final.jsonl` | 데이터셋 61항목: 자연어, 출처, 기준 부분과 버전(FRETish, LTL) | P1 |
| `data/dataset/lm_dataset_table.xlsx` | 데이터셋 표 (엑셀) | P1 |
| `data/dictionary/lm_dictionary.csv` | 딕셔너리 v1: 564행 (챌린지 10개), 열 11개 (확장 `dictionary`의 기본 딕셔너리) | P1, P9, P10 |
| `data/example_fret_ltl_gen_v8.jsonl` | 판정 입력 형식 예시: 문장별 LTL | 보조 |
| `data/example_fret_realizability_gen_v8.jsonl` | 판정 입력 형식 예시: 실현가능성 | 보조 |
| `data/example_units_v8.json` | 판정 입력 형식 예시: 단위 | 보조 |
| `data/reference/lm_reference_with_ltl.jsonl` | 기준 61행 (부분, 버전, LTL) | P9, P10 |
| `data/reference/pairs_sample.jsonl` | 판정기 교차검증용 쌍 표본 | 보조 |
| `data/reference/parser_fingerprint.pin` | 이 컴퓨터에서 고정한 FRET 파서 지문 (기준 FRETish 111문장) | P2 |
| `data/reference/sigdict.json` | 챌린지별 딕셔너리 표 텍스트 | P1 |
| `src/nl2fret/data/dict8_items.jsonl` | v8 딕셔너리 시험 항목 | 보조 |
| `src/nl2fret/data/lm_items.jsonl` | 항목 파일 61행 (`id`, `raw_nl`, `family`, `challenge`) | P1, P4-P8 |
| `src/nl2fret/data/lm_items_fsm.jsonl` | FSM 챌린지 항목 13행 | P1, P4-P8 |
| `src/nl2fret/data/lm_items_nonfsm.jsonl` | 비 FSM 항목 48행 | P1 |
| `src/nl2fret/data/rule_semantics_results.json` | 규칙 의미 검증 결과 | P2 |
| `src/nl2fret/data/rule_sources.json` | 규칙 근거 장부 (인용문, 출처) | P2 |
| `src/nl2fret/data/sigdict.json` | LLM 입력용 챌린지별 딕셔너리 표 | P5 |
| `src/nl2fret/data/timing_semantics.json` | 조건 종류와 타이밍 형태 조합의 의미 표 | 보조 |
| `src/nl2fret/fret_check/variable_policy.md` | 실현가능성 검사의 변수 표 작성 규칙 | 보조 |
| `src/nl2fret/prompts/fretish_reference.md` | FRET 공식 필드 문서 전문 (문법 `Requirement.g4`, writingReqs, scope, condition, component, timing, probability, response, 내장 함수) | P1, P3 |
| `src/nl2fret/prompts/sources_v15.json` | FRETish 참고문과 템플릿 5개의 출처, 확인 상태 (프롬프트 밖에 보관) | P2, P3 |
| `src/nl2fret/templates_v15/adv_ears.md` | Adv-EARS 템플릿 설명 | P3, P4 |
| `src/nl2fret/templates_v15/boilerplate.md` | Boilerplate 템플릿 설명 | P3, P4 |
| `src/nl2fret/templates_v15/ears.md` | EARS 템플릿 설명 | P3, P4 |
| `src/nl2fret/templates_v15/masteR.md` | MASTeR 템플릿 설명 (원본 문헌에서 옮긴 판) | P3, P4 |
| `src/nl2fret/templates_v15/spider.md` | SPIDER 템플릿 설명 | P3, P4 |

- 메인 디렉터리 사본 (내용 동일): `assets/dataset/v1/`, `assets/dictionary/v1/`, `assets/reference/v1/`
- 버전 색인: `VERSIONS.md`

### 4.5 실행 결과 폴더 구조 (`$RUN`)

```text
$RUN/
  gen/                P2-P7a  calls.jsonl, batch_calls.jsonl, parser_cache.jsonl, kc_fields.jsonl, descriptions.jsonl, run_state.json, run.log, isolation_probe.json, snapshot/
  inputs_v0/          P8      units.json, fret_ltl_gen.jsonl, unit_state.jsonl
  inputs_vf/          P8      (같은 구성)
  inputs_kc/          P8      (같은 구성, 키워드 점검 뒤)
  inputs_rt/          P8      (같은 구성)
  judge_v0/           P9-P11  judge_records.jsonl, part_results.jsonl, counterexamples.jsonl, run_header.json, smv/, work/
  judge_vf/           P9-P11  (같은 구성)
  judge_kc/           P9-P11  (같은 구성)
  judge_rt/           P9-P11  (같은 구성)
  ext_off_dictionary.csv      P10 (확장이 꺼졌을 때만: 항목 없는 머리글 파일)
  group_rlz_container.log     P12 (CLI 원출력)
  group_rlz.jsonl     P12
  rt_effect.json      P13
  parser_fingerprint.json     P2 (pin 단계의 덤프)
```

### 4.6 문서

| 파일 | 내용 |
|---|---|
| `docs/V20_BATCH_DESIGN.md` | v2.0 배치 실행 설계와 사전 등록 사항 (에이전트 구조, 격리 허용 항목, 피드백, 변형과 지표, 고정값, 명령) |
| `docs/DESIGN.md` | 도구 설계 (릴리스 2.0, 판정 설계 포함) |
| `docs/RUNBOOK.md` | 실행 절차 (설치, 점검, 배치 실행, 확장 모듈) |
| `README.md` | 도구 개요 |
| `VERSION` | 도구 버전 `v2.0` |
| `pyproject.toml` | PyPA 프로젝트 정의 (의존성, 진입점, 패키지 데이터) |
| `.gitignore` | git 제외 목록 |
| `runs/batch_smoke/` | 패키지가 가져온 배치 실행 기록 (3개 방식, 2항목, 06_EB) |

- 도구 폴더의 파일 표 밖 구성: `prompts/`(현재 프롬프트 파일과 색인), `assets/`(버전별 자산 사본), `archive/`(이전 릴리스 `releases/`, 철회 기능 `removed_features/`, 이전 판 문서 `nl2fret_tool_docs/`, `process_lifecycle_doc/`), `data/cases/`(입력 케이스), `external/docker/`(FRET과 NuSMV 이미지 레시피), 버전 색인 `VERSIONS.md`
- 프로젝트 루트(`nl2semiformal/`)의 문서: `README.md`, `STRUCTURE.md` (저장소 구조)
