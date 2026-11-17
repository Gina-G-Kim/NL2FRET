# NL2FRET 도구 설계 (릴리스 2.0)

표기: [확정] 사용자가 정했거나 발표 방식을 그대로 따르는 것, [결정] 이 문서에서 기존 규칙에 따라 정한 것, [미결] 측정 또는 사용자 결정이 남은 것
이 문서는 2026-11-10의 설계 문서(보관: `archive/nl2fret_tool_docs/v1.4/docs/DESIGN.md`)를 릴리스 2.0 구조에 맞춰 다시 쓴 것이다. 판정 부분(4절부터 7절과 부록)은 판정기 코드가 같으므로 그대로 두었고, 생성과 실행 부분은 2.0의 배치 에이전트 구조로 바꿨다.
연구 질문, 정답과 딕셔너리의 역할, 결정 사항(주 지표, 에이전트 정의, 알려진 한계)은 `docs/V20_BATCH_DESIGN.md` 맨 위가 규범이다.

## 1. 한 줄 정의

자연어 요구사항을 (선택적으로 템플릿을 거쳐) FRETish로 바꾸고, 공식 FRET으로 LTL로 컴파일한 뒤, NASA 전문가 FRETish의 LTL과 NuSMV 양방향 함의로 비교하여 SAME, PROOF, REFUTE, NEITHER 역할을 매긴다. 핵심 비교는 템플릿 경로(Template+G, FixedTemplate+R2) 대 Direct이고 보조 비교는 템플릿 5종 사이이다.

## 2. 전체 흐름

| 단계 | 이름 | 입력 | 처리 | 출력 | 실패 처리 |
|---|---|---|---|---|---|
| S0 | 입력 | 챌린지별 자연어 요구사항 (61개 항목), (확장 켜짐이면) 딕셔너리 | `src/nl2fret/data/lm_items.jsonl` | 항목 | 해당 없음 |
| S1 | 템플릿 변환 (단계 A) | 챌린지의 자연어 전체 | 에이전트 1개가 MASTeR, EARS, Adv-EARS, SPIDER, Boilerplate 중 하나로 변환 (Direct는 생략) | 템플릿 문장, 미반영 내용 | 호출 실패 기록, 거절은 `declined` |
| S2 | FRETish 생성 (단계 B, D, S) | 자연어 또는 템플릿 문장 | Direct(D), 템플릿 후 자유 변환(B, +G), 템플릿 후 규칙 조립(S, +R2) (3절) | FRETish 문장 | 규칙 실패 코드 기록, 자유 경로로 되돌림 |
| S3 | 파서 피드백 (F1..F5) | FRETish | 공식 FRET 파서가 수락 또는 거절, 거절 문장은 파서 메시지와 함께 되돌려 최대 5회 | 수락 문장 (변형 vf) | 한도 후에도 거절이면 실패 |
| S3b | 왕복 (RT1) | 수락 문장, FRET의 영어 설명 | 에이전트가 설명을 입력과 대조해 답변을 다시 냄. 새 답변은 파서가 모든 문장을 수락할 때만 채택 | 변형 rt (주 변형) | 채택하지 않음 |
| S4 | 입력 생성 | 호출 기록 | 변형 v0, vf, rt의 단위와 문장별 LTL (공식 파서가 과거시제, 미래시제로 컴파일) | `inputs_<변형>/` | 컴파일 실패는 판정불가 |
| S5 | 이름 정렬 | 생성 LTL, 딕셔너리(확장) | 4절 | 정렬된 식 쌍 | 대응 불가는 N/M |
| S6 | 판정 | 정렬된 식 쌍 | NuSMV 질의 3개(Equiv, Sound, Compl). 5절 | 역할, N/M, 반례 기록 | 변환기 한도, 시간 초과는 N/M |
| S7 | 집합 Realizable (보조) | 방식, 챌린지, 반복의 최종 문장 전체 | 한 요구사항 집합으로 FRET 실현가능성 검사. 정수 리터럴 정규화(N-LIT, 기본 켜짐)를 거친 결과(normalized)가 주, 거치지 않은 결과(raw)가 보조 | realizable, unrealizable, unknown, empty | 함수 적용 문장은 제외하고 건수 기록 |
| S8 | 집계 | 판정 결과 | 6절 | 방식과 변형별 부분 성공 수, 변형 간 이득과 손실 | 해당 없음 |

모든 에이전트 호출은 격리된 새 `claude` 프로세스이며 호출 단위는 (방식, 챌린지, 반복, 단계)이다. 에이전트의 정의와 격리 조건은 `docs/V20_BATCH_DESIGN.md` 1절과 0.2절이 규범이다.

## 3. S2: FRETish 생성 경로 (2.0의 11개 approach)

| 경로 | 흐름 | 규칙표 사용 | 비고 |
|---|---|---|---|
| Direct (`DIRECT`) | 자연어를 바로 FRETish | 없음 | 비교 기준 |
| 템플릿 후 규칙 글 (`<템플릿>+G`) | 템플릿 문장을 LLM이 FRETish로. 규칙표 글을 시스템 프롬프트에 붙임 | `prompts3.py`의 `guide_rules_text()`가 `tpl_rules.py`의 `RULES`에서 생성 | 템플릿 5종 |
| 템플릿 후 규칙 조립 (`<템플릿>+R2`) | 스크립트가 규칙으로 FRETish를 조립하고 모델은 슬롯 값만 채움. 조립이 안 되는 구절은 자유 경로(BF)로 | `RULES`를 코드가 직접 실행 | 템플릿 5종 |

- [확정] 딕셔너리는 확장(`src/nl2fret/ext/dictionary/`)이며 모든 방식에 똑같이 준다. 성능을 올리는 장치가 아니라 실험 조건이고, 결과는 이 딕셔너리를 준 조건의 성능으로만 보고한다.
- 코드에는 이전 시험용 방식(`+R`, `+V`, `+V6`, `+D`, `PARA`)이 남아 있으나 2.0 실행에는 쓰지 않는다.
- 알려진 불일치: `guide_rules_text()`가 만드는 +G 프롬프트에 "+R2 방식 전용"이라고 적힌 `R2-TIME` 규칙이 섞여 들어간다 (2026-11-10 문서의 기록. 그 뒤 수정 여부는 이 개정에서 확인하지 못함).

## 4. S5: 이름 정렬 (판정기 `src/nl2fret_judge/dict_align.py`와 `align.py`)

| 층 | 규칙 | 지위 |
|---|---|---|
| 이름 고정 (주 층) | 신호 사전의 이름이 같으면 같은 변수로 간주. 산술 비교는 불리언 원자로 추상화(`c_<해시>`), 불리언 변수는 `b_` 접두 | [확정] 주 지표 |
| AP 불일치 기록 (저자 규칙) | 저자 코드의 조건 `vars(GT) ⊆ vars(Pred)`를 질의 종류별로 계산하여 `ap_check` 필드로 남김 | [확정] 기록 전용. 판정에는 반영하지 않음 |
| 자유 재명명, lex, strict | 사전 밖 변수의 대응을 추정 | [확정] 보조(상한 지표). 주 지표와 합산 금지 |
| skeleton 판정 | 구조 수준 비교 | [확정] 보조 |
| DEGEN | 모순이거나 항진인 식 | [확정] 보조 라벨. 논문에 없는 요소이므로 주 역할에 섞지 않음 |

- 2.0: 이름 정렬이 읽는 딕셔너리는 확장 `dictionary`가 정한다. 켜짐이면 딕셔너리 v1 파일, 꺼짐이면 항목 없는 머리글 파일(모든 식별자 `oov`, 이름을 바꾸지 않음). 판정기가 `--dictionary`를 필수 인자로 받기 때문이다.
- [미결] AP 불일치 규칙을 판정에 반영할지. 반영 여부는 `ap_rule_recording` 실행 결과를 본 뒤 정한다. 이 지시문은 작성만 되었고 실행 여부는 알 수 없다.
- 한계: 산술 원자(`absReal(x) > 50`과 `x > 50.0`)의 관계를 변환기가 모른다. 생성 98쌍에서 judge4와의 불일치 4쌍이 이 유형인 것은 가설이다.

## 5. S6: 판정 방식 (Danso et al., SecDev '26 방식, 판정기 `src/nl2fret_judge/`)

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

판정기 개발 시점의 측정값 [확정, 당시 보고서 값. 2.0에서 다시 측정하지 않음]
- 통제 쌍 512: N/M 32 제외 480/480이 기대와 일치, 잘못된 방향 0.
- 생성 문장 98쌍: N/M 8, judge4와 역할 일치 86, 불일치 4.
- N/M 사유: 창 경계 128 초과 32, 질의 시간 초과 8.

## 6. S8: 지표와 분모 (2.0)

- 부분 성공 = SAME 또는 PROOF (`docs/V20_BATCH_DESIGN.md` 3절). 주 지표는 엄격 판정 하나이다.
- 변형 v0(첫 답변), vf(파서 피드백 뒤), rt(왕복 뒤, 주 변형)를 같은 판정기와 같은 설정으로 각각 판정하고, `tools/rt_effect.py`가 방식과 변형별 부분 수와 성공 수, 같은 (항목, 반복, 부분)에서 변형 사이의 이득과 손실을 센다.
- 집합 Realizable는 보조 지표이다. 판정불가(N/M)와 UND는 분모에서 빼지 않고 따로 건수를 보고한다.
- 논문과 비교하는 표에서만 N/M을 제외한 Eq-Acc(= Equiv / (Equiv + 비동치))를 쓰고, 항상 같은 쌍 집합 위에서 N/M 포함 값을 병기한다. 논문 부록의 Eq-Acc 계산식은 본문과 평균 12.15%p 달라서, 논문 값을 재현 목표로 삼지 않는다 [결정, 2026-11-10 문서].
- 판정기 간 비교(judge4 대 NuSMV)는 N/M이 아닌 쌍으로 제한한 값과 전체 n 기준 값을 따로 적는다.
- 알려진 한계: 정의 용어를 쓰는 문장은 과소평가될 수 있고, 기준 문장 자기 자신 쌍 129쌍 중 4쌍에서 서로 다른 부분이 SAME으로 나오는 거짓 SAME이 관찰되었다. 둘 다 판정기의 성질이며 모든 방식에 똑같이 적용된다.

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

1. 규칙, 프롬프트, 판정 정의의 코드는 릴리스 태그(git)로 고정한다. 실행 기록(`gen/snapshot/`)에 실행 시점의 코드와 프롬프트 사본, 프롬프트 해시를 남기고 `tpl_rules.py`, `fretlint.py`가 첫 시작 뒤 바뀌면 중단한다. (코드 파일 해시 목록 `FROZEN_MANIFEST.sha256`은 2026-11-17에 없앴다.)
2. 파서 지문(공식 파서가 기준 문장 111개에서 내는 결과의 sha256)을 `data/reference/parser_fingerprint.pin`에 고정하고 `gen`이 시작할 때 비교한다.
3. 입력은 61개 항목이고 정답 필드는 모델 입력에 넣지 않는다. 반복 3회, 모델 `sonnet`, `--effort medium`, 시드 20261116.
4. 각 단계는 1회 실행하고 중단된 실행의 재개만 허용한다. 결과를 본 뒤 규칙을 바꾸지 않는다.
5. 변경은 `docs/V20_BATCH_DESIGN.md`에 날짜와 함께 사전 등록한 뒤에 한다.

## 9. 구현 현황 (경로는 도구 루트 `nl2fret_tool/` 기준)

| 구성요소 | 상태 | 위치 |
|---|---|---|
| 배치 생성 파이프라인, 격리 호출, 왕복, 규칙표, 린트, 프롬프트 | 동작함 | `src/nl2fret/` |
| 판정기 (정렬, 추상화, NuSMV 질의, 역할, 기록) | 동작함 | `src/nl2fret_judge/`, `src/legacy/` |
| FRET 파서, 실현가능성(Kind2) | 동작함 | Docker 이미지 `fret-lab`, 호출 코드 `src/nl2fret/fret_check/` |
| 집합 Realizable와 N-LIT | 동작함 | `src/nl2fret/fret_check/group_rlz.py`, `fret_check/tools/litnorm.py` |
| 딕셔너리 확장 | 동작함 | `src/nl2fret/ext/dictionary/` |
| 시험 | pytest 통과 | `tests/` |
| 실행 스크립트 | 동작함 | `scripts/` |
| AP 규칙 기록 | 지시문 작성만, 실행 여부 알 수 없음 | `NL2FRET_PROMPT_AP_RULE_RECORDING` (이 저장소에 없음) |
| judge3, `sk.py`, `rq.py` | 이 Mac에 없음 | 다른 환경의 `d8res`, `ltlpack`에 일부 |

## 10. 남은 항목

아래는 2026-11-10 문서의 항목 중 아직 열려 있는 것이다. 상태는 그 문서의 기록이며 이후 바뀌었는지 이 개정에서 확인하지 못했다.

| 번호 | 항목 | 결정 방법 |
|---|---|---|
| 1 | 유한 trace 의미(FRET 과거시제)와 NuSMV 무한 경로 의미의 일치 | 작은 쌍에서 유한 trace를 직접 열거해 NuSMV 판정과 비교 |
| 2 | 저자 SMV 템플릿(`VAR` boolean + `ASSIGN init/next`)과 우리 템플릿(`VAR`만)의 동일성 | 저자에게 소스 요청 또는 두 템플릿의 판정 비교 |
| 3 | AP 불일치 N/M 규칙의 판정 반영 | `ap_rule_recording` 실행 후 결정 |
| 4 | N/M 비율 감소를 위한 창 경계 상향 | cap 변경 실험 (속도와 크기 영향은 알 수 없음) |
| 5 | 그림(SVG) 갱신 | 3절의 구분과 4절, 5절의 판정 구조를 반영 |
| 6 | RQ4(템플릿 단계 유실 정보 기록) | 설계만 있음. S1 출력의 `unmapped_content`를 장부 범주로 쓰는 안 |

이미 해결된 이전 항목: 파이프라인과 NuSMV 판정기의 연결(`judge-parts`가 `run_batch.sh judge`로 연결됨), 도구 코드의 저장소 포함(`src/`).

## 11. RQ와 단계의 대응

| RQ | 쓰는 단계 출력 |
|---|---|
| RQ1 오류와 의미 손실 | S3 파서 오류 유형, S6 역할, S1 `unmapped_content` |
| RQ2 템플릿이 중간 단계일 때의 효과 | DIRECT 대비 템플릿 방식의 S6 성공률(같은 단위 쌍 비교) |
| RQ3 요구 유형별 구조 | 케이스의 `stratum`과 `family`별 S6 결과 |
| RQ4 (계획) 유실 정보 기록 | S1 출력 |

---
## 부록 A. 구현 시 확정된 사항 (v1.0.0)

- 정렬 실패는 역할 `UND`(`und_reason`, 예: atomization_mismatch)로 기록하고, 엔진이 판정하지 못한 경우는 `nm=true`(`nm_reason`: converter_limit, syntax, timeout, nusmv_output, no_verdict, other)로 기록한다. 둘 다 "미판정"으로 분모에 남는다.
- 주 분모는 전체 단위. 판정된 단위만 쓴 값은 문헌 비교용 보조값으로만 같이 낸다.
- 참조식 전처리: FRET의 `<b><i>` 표시 제거, 괄호 없이 우선순위로 출력된 식은 완전 괄호식으로 재출력(judge.clean_markup).
- 정렬 탐색은 sound/compl 질의로 후보를 비교하고(둘 다 성립 0점, 하나 1점, 둘 다 실패 2점, 0점이면 즉시 종료), 선택된 후보에만 equiv 질의를 실행한다.
- 단위 결과: success(SAME/PROOF이며 같은 문장이 realizable), partial(REFUTE 또는 비실현), failure(NEITHER, 파서 거부, 문장 없음), unjudged(UND/NM).
