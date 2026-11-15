# NL2FRET 도구 전체 프로세스 설계 (최종안, 2026-11-10)

표기: [확정] 사용자가 정했거나 발표 방식을 그대로 따르는 것, [결정] 이 문서에서 기존 규칙에 따라 정한 것, [미결] 측정 또는 사용자 결정이 남은 것, [알 수 없음] 확인하지 못한 것.
근거 문서: NL2FRET_JUDGE_HANDOFF, NL2FRET_PROMPT_NUSMV_PAPER_TEST, NL2FRET_PROMPT_JUDGE_RECORDING, NL2FRET_PROMPT_AP_RULE_RECORDING, NL2FRET_ltl_judge_literature_map, NL2FRET_ltl_engines_results, NL2FRET_v8_report.

## 1. 한 줄 정의

자연어 요구사항을 (선택적으로 템플릿을 거쳐) FRETish로 바꾸고, 공식 FRET으로 LTL로 컴파일한 뒤, NASA 기준 FRETish의 LTL과 NuSMV 양방향 함의로 비교하여 성공, 부분 성공, 실패, 판정불가로 나눈다.

## 2. 전체 흐름

| 단계 | 이름 | 입력 | 처리 | 출력 | 실패 처리 |
|---|---|---|---|---|---|
| S0 | 입력 | 록히드마틴 케이스 61개(lockheed_martin 49 + fsm 12), 챌린지별 신호 사전 | 케이스 정리본(`data/cases/`)을 읽음 | 케이스 레코드 | 해당 없음 |
| S1 | 템플릿 변환 | 자연어 | LLM이 MASTeR, EARS, Adv-EARS, SPIDER, Boilerplate 중 하나로 변환 (DIRECT 방식은 생략) | 템플릿 문장, 요구 유형, 미반영 내용 | 호출 실패 기록 |
| S2 | FRETish 생성 | 자연어 또는 템플릿 문장, (+D이면) 신호 사전 | 방식별 LLM 변환 또는 규칙 조립 (3절) | FRETish 문장 | 규칙 실패 코드 기록 |
| S3 | 형식 관문 | FRETish | 공식 FRET 파서. 거부 시 오류를 피드백으로 주고 최대 2회 재변환 | 통과 문장 또는 거부 | 2회 후에도 거부면 실패 |
| S4 | 현실화 가능성 | 통과 문장 | Kind2 realizability | realizable, unrealizable, unknown, not_run | unrealizable와 unknown은 실패 |
| S5 | LTL 컴파일 | 통과 문장 | FRET이 과거시제와 미래시제 LTL로 컴파일. 기준 FRETish도 같은 방식 | 생성 LTL, 기준 LTL | 컴파일 실패는 판정불가 |
| S6 | 어휘 정렬 | 두 LTL | 이름 고정(주): 신호 사전 이름이 같으면 같은 변수. 4절 | 정렬된 식 쌍, AP 기록 | 대응 불가는 N/M |
| S7 | 판정 | 정렬된 식 쌍 | NuSMV 질의 3개(Equiv, Sound, Compl). 5절 | 역할, N/M, 원시 기록 | 변환기 한도 초과, 시간 초과는 N/M |
| S8 | 집계 | 판정 기록 | 지표와 분모 규칙. 6절 | RQ별 표 | 해당 없음 |

## 3. S1, S2: FRETish 생성 경로

| 경로 | 흐름 | 규칙표 사용 | 비고 |
|---|---|---|---|
| DIRECT | 자연어를 바로 FRETish | 없음 | 기준 방식 |
| 템플릿 후 자유 변환 | 템플릿 문장을 LLM이 FRETish로 | 없음 | 템플릿 5종 |
| 템플릿 후 규칙 글 (+G) | 규칙표 글을 시스템 프롬프트에 붙여 LLM이 변환 | `prompts3.py`의 `guide_rules_text()`가 `tpl_rules.py`의 `RULES`에서 생성 | v3에서만 실행됨 (MASTeR, EARS, Adv-EARS 각 204회) |
| 템플릿 후 규칙 조립 (+R, +R2) | 스크립트가 규칙으로 조립하고 모델은 불리언 식 슬롯만 채움 | `RULES` 51개를 코드가 직접 실행 | v6 이후 평가의 주 규칙 방식 |
| +V, +V6 | 원칙 기반 지침을 프롬프트에 추가 | 원칙 V-1 ~ V-6 | v7 개발 결과 +V6는 +V와 구분되지 않아 TEST에서 제외 |
| +D | 위 방식에 신호 사전을 함께 제공 | 해당 없음 | v8 사전 실험은 DIRECT, MASTeR, EARS만 |

- [결정] 그림의 경로 3("템플릿 후 규칙 참조")은 코드의 +G에 해당한다. 평가의 주 규칙 방식은 +R, +R2이므로 그림에 이 둘을 구분하여 표기한다.
- [확정] 모든 방식에서 신호 사전의 이름만 쓰게 한다. 사전 제공 여부는 +D 방식으로 분리한다.
- 알려진 불일치: `guide_rules_text()`가 만드는 +G 프롬프트에 "+R2 방식 전용"이라고 적힌 `R2-TIME` 규칙이 섞여 들어간다. 지금 코드로 +G를 다시 실행하면 이 규칙이 포함되므로, 재실행 전에 제외해야 한다.

## 4. S6: 어휘 정렬

| 층 | 규칙 | 지위 |
|---|---|---|
| 이름 고정 (주 층) | 신호 사전의 이름이 같으면 같은 변수로 간주. 산술 비교는 불리언 원자로 추상화(`c_<해시>`), 불리언 변수는 `b_` 접두 | [확정] 주 지표 |
| AP 불일치 기록 (저자 규칙) | 저자 코드의 조건 `vars(GT) ⊆ vars(Pred)`를 질의 종류별로 계산하여 `ap_check` 필드로 남김 | [확정] 기록 전용. 판정에는 반영하지 않음 |
| 자유 재명명, lex, strict | 사전 밖 변수의 대응을 추정 | [확정] 보조(상한 지표). 주 지표와 합산 금지 |
| skeleton 판정 | 구조 수준 비교 | [확정] 보조 |
| DEGEN | 모순이거나 항진인 식 | [확정] 보조 라벨. 논문에 없는 요소이므로 주 역할에 섞지 않음 |

- [미결] AP 불일치 규칙을 판정에 반영할지. 반영 여부는 `ap_rule_recording` 실행 결과를 본 뒤 정한다. 이 지시문은 작성만 되었고 실행 여부는 알 수 없다.
- 한계: 산술 원자(`absReal(x) > 50`과 `x > 50.0`)의 관계를 변환기가 모른다. 생성 98쌍에서 judge4와의 불일치 4쌍이 이 유형인 것은 가설이다.

## 5. S7: 판정 방식 (Danso et al., SecDev '26 방식)

정의 [확정]
- Equiv: GT ⇔ Pred. Sound: GT ⇒ Pred. Compl: Pred ⇒ GT.
- 질의마다 SMV 파일 하나, LTLSPEC 하나. NuSMV 2.6.0은 한 파일의 LTLSPEC 결과를 선언 순서와 다르게 출력하므로 출력 순서로 대응시키지 않는다(이전 NuSMV 경로의 45쌍 어긋남은 이 순서 가정과 일치했다. 원인은 가설).
- 추상화된 과거시제 식에 대해 `G(...)` 형태로 검사한다.

역할 대응 [확정, 코드 판독으로 확인]

| Sound | Compl | 역할 | 의미 |
|---|---|---|---|
| 성립 | 성립 | SAME | 동치 |
| 불성립 | 성립 | PROOF | 생성이 더 강함 |
| 성립 | 불성립 | REFUTE | 생성이 더 약함 |
| 불성립 | 불성립 | NEITHER | 다른 이야기 |
| 질의 실패 | | N/M | 검사 불가 |

N/M 사유 코드 [확정]: `converter_limit`(창 경계 128 초과), `syntax`, `timeout`(질의당 120초), `nusmv_output`, `no_verdict`, `other`.

교차 검증
- z3 유한 구간 판정(judge4, horizon 8)은 교차검증용으로만 둔다. [알 수 없음] judge4 코드는 Mac 저장소에 없다. 이 환경(`d8res`, `ltlpack`)에만 일부가 있다.
- Spot은 미래시제 식에 대한 교차검증으로만 쓴다. Spot은 과거시제 문법을 읽지 못한다.

현재까지의 측정값 [확정, 보고서 값]
- 통제 쌍 512: N/M 32 제외 480/480이 기대와 일치, 잘못된 방향 0.
- 생성 문장 98쌍: N/M 8, judge4와 역할 일치 86, 불일치 4.
- N/M 사유: 창 경계 128 초과 32, 질의 시간 초과 8.

## 6. S8: 지표와 분모

| 지표 | 정의 | 분모 |
|---|---|---|
| 성공 | SAME 또는 PROOF이고, 같은 문장이 realizable | 전체 단위 [결정] |
| 부분 성공 | REFUTE | 전체 단위 |
| 실패 | NEITHER, 파서 거부, unrealizable, unknown | 전체 단위 |
| 판정불가 | N/M | 전체 단위에 남기고 따로 건수 보고 |
| 논문 비교용 Eq-Acc | Equiv / (Equiv + 비동치), N/M 제외 | 같은 쌍 집합 위에서 계산 |

- [결정] 주 지표의 분모는 전체 단위로 한다. 근거는 이 프로젝트의 기존 규칙(모든 단위가 분모에 남고 unknown, unrealizable, 파서 거부는 실패)이다. JUDGE_HANDOFF의 제안("N/M 제외를 주 지표, 포함을 병기")과 방향이 반대이므로, 사용자가 그 제안을 택하면 두 줄의 순서만 바꾸면 된다.
- [결정] 논문과 비교하는 표에서만 N/M을 제외한 값을 쓰고, 항상 같은 쌍 집합 위에서 N/M 포함 값을 병기한다. 논문 부록의 Eq-Acc 계산식은 본문과 평균 12.15%p 달라서, 논문 값과 직접 대조할 때는 "계산식 불명확"을 명시한다([알 수 없음]).
- 판정기 간 비교(judge4 대 NuSMV)는 N/M이 아닌 쌍으로 제한한 값과 전체 n 기준 값을 따로 적는다.

## 7. 기록 계층 (재현과 사후 감사용)

쌍마다 한 줄씩 `judge_records.jsonl`에 남기며, 모든 집계는 이 파일에서 다시 계산할 수 있어야 한다.

| 구분 | 필드 |
|---|---|
| 식 | `gt_pt`, `pred_pt`, `gt_ft`, `pred_ft`, `atoms_gt`, `atoms_pred`, `atoms_union`, `atom_abstraction`, `ap_dictionary` |
| 판정 | `equiv`, `sound`, `compl`, `role`, `nm`, `nm_reason`, `nm_detail` |
| 질의 | `kind`, `spec_text`, `smv_sha256`, `verdict`, `stdout`, `stderr`, `exit_code`, `elapsed_sec`, `timed_out`, `cmd`, `query_mode` |
| AP 규칙 | `ap_check`(`vars_gt`, `vars_pred`, `equal`, `gt_subset_pred`, `pred_subset_gt`, `nm_by_kind`, `nm_pair_any`, `nm_pair_all`) |
| 헤더 | NuSMV 버전, 변환기와 판정 코드의 sha256, cap, 시간 제한, SMV 템플릿 식별자, 입력 sha256 |

- `judge_recording` 확인 실행(27쌍, 질의 81개, 14초)에서 판정 불변(R1), 필드 존재(R2), SMV 해시 일치(R3), stdout 비어 있으면 verdict null(R5), 기록 유무에 따른 출력 동일(R6)을 확인했다. R4는 변환식이 같은 9쌍을 제외한 18쌍에 한해 충족한다.
- 이 기록이 있어야 가능한 사후 분석(지금은 실행하지 않음): 분모 두 가지의 정확도, 유한 trace 열거와 NuSMV 판정의 일치, SMV 템플릿 변형 비교, 창 경계 변경에 따른 N/M 변화, 출력 순서 문제의 감사.

## 8. 평가 실행 프로토콜

1. 규칙과 판정 정의를 파일로 쓰고 sha256으로 동결한다(`tpl_rules.py`, `fretlint.py`, `prompts3.py`, 판정 정의, `PRE_RUN_DEFINITIONS.md`). 실행 중 변경되면 중단한다.
2. 각 단계는 1회만 실행하고 프로세스 중단 시의 재개만 허용한다. 결과를 본 뒤 규칙을 바꾸지 않는다.
3. 입력은 `data/cases/`의 61개(49 + 12)이고, 정답 필드는 입력에 넣지 않는다.
4. 반복 횟수는 설계상 3회다. v8 사전 실험은 18개 항목, 2회였다.
5. 방식 범위(제안): DIRECT, 템플릿 5종 자유 변환, +R2, +V, +D. v7 TEST 방식 16개에 +D를 더한 구성이다.
6. 판정은 5절의 NuSMV 경로, 교차검증은 judge4와 Spot, 보조 지표는 4절의 보조 층.

## 9. 구현 현황

| 구성요소 | 상태 | 위치 |
|---|---|---|
| 케이스 정리본 | 완료 | GitHub `data/cases/` |
| 변환 러너, 규칙표, 린트, 프롬프트 | 동작함 | `experiments/*/bench` (GitHub 비추적) |
| FRET 파서, Kind2 | 동작함 | Docker 이미지 `fret-lab` |
| NuSMV 논문 방식 판정 `paper_judge.py` | 구현, 통제 480/480 | `experiments/nusmv_paper` |
| 판정 기록 확장 | 구현, 27쌍 확인 | `experiments/judge_recording` |
| AP 규칙 기록 | 지시문 작성만, 실행 여부 알 수 없음 | `NL2FRET_PROMPT_AP_RULE_RECORDING` |
| judge3, judge4, judge5, `sk.py`, `rq.py` | Mac에 없음 | 이 환경 `d8res`와 `ltlpack`에 일부 |
| 파이프라인과 판정기 연결 | 미확인 | 아래 10절 |

## 10. 마무리를 위한 미결 항목 (우선순위 순)

| 번호 | 항목 | 결정 방법 |
|---|---|---|
| 1 | 파이프라인과 NuSMV 판정기 연결 (판정기를 부르는 방식이 judge4 없이 동작하는지) | 연결 코드를 만들어 61개 중 18개 사전 실험 결과에 한 번 실행 |
| 2 | 유한 trace 의미(FRET 과거시제)와 NuSMV 무한 경로 의미의 일치 | 작은 쌍에서 유한 trace를 직접 열거해 NuSMV 판정과 비교. 과거시제만 쓰는 식이면 일치할 가능성이 높다는 것은 추론이다 |
| 3 | 저자 SMV 템플릿(`VAR` boolean + `ASSIGN init/next`)과 우리 템플릿(`VAR`만)의 동일성 | 저자에게 소스 요청 또는 두 템플릿의 판정 비교 |
| 4 | AP 불일치 N/M 규칙의 판정 반영 | `ap_rule_recording` 실행 후 결정 |
| 5 | N/M 비율(통제 6.2%, 생성 8.2%) 감소를 위한 창 경계 상향 | cap 변경 실험(속도와 크기 영향은 알 수 없음) |
| 6 | GitHub 저장소에 도구 코드가 없는 문제 | `experiments/` 제외 규칙 조정 또는 코드를 `src/`로 복사 |
| 7 | 그림(SVG) 갱신 | 3절의 +G와 +R 구분, 4절과 5절의 판정 구조를 반영해 다시 그림 |
| 8 | RQ4(템플릿 단계 유실 정보 기록) | 설계만 있음. S1 출력의 `unmapped_content`를 장부 범주로 쓰는 안이 v7 DEV0 분석에 있음 |

## 11. RQ와 단계의 대응

| RQ | 쓰는 단계 출력 |
|---|---|
| RQ1 오류와 의미 손실 | S3 파서 오류 유형, S7 역할, S1 `unmapped_content` |
| RQ2 템플릿이 중간 단계일 때의 효과 | DIRECT 대비 템플릿 방식의 S7 성공률(같은 단위 쌍 비교) |
| RQ3 요구 유형별 구조 | 케이스의 `stratum`과 `family`별 S7 결과 |
| RQ4 (계획) 유실 정보 기록 | S1 출력 |


---
## 부록 A. 구현 시 확정된 사항 (v1.0.0)

- 정렬 실패는 역할 `UND`(`und_reason`, 예: atomization_mismatch)로 기록하고, 엔진이 판정하지 못한 경우는 `nm=true`(`nm_reason`: converter_limit, syntax, timeout, nusmv_output, no_verdict, other)로 기록한다. 둘 다 "미판정"으로 분모에 남는다.
- 주 분모는 전체 단위. 판정된 단위만 쓴 값은 문헌 비교용 보조값으로만 같이 낸다.
- 참조식 전처리: FRET의 `<b><i>` 표시 제거, 괄호 없이 우선순위로 출력된 식은 완전 괄호식으로 재출력(judge.clean_markup).
- 정렬 탐색은 sound/compl 질의로 후보를 비교하고(둘 다 성립 0점, 하나 1점, 둘 다 실패 2점, 0점이면 즉시 종료), 선택된 후보에만 equiv 질의를 실행한다.
- 단위 결과: success(SAME/PROOF이며 같은 문장이 realizable), partial(REFUTE 또는 비실현), failure(NEITHER, 파서 거부, 문장 없음), unjudged(UND/NM).
