# v1.4 재시험 설계 적용 (가이드 보강 + 규칙 글 정합)

설계 원문: 프로젝트 문서 `NL2FRET_retest_design_v1_4.md`. 이 문서는 구현된 것과 기본값으로 가정한 결정을 적는다.

## 구현된 변경 (v1.3 결과는 기준선으로 그대로 보존)
| 항목 | 내용 | 켜는 법 |
|---|---|---|
| 공식 문서 인용만의 보충문 | `bench/prompts/fretish_guide_supplement.md`. 문장마다 출처 파일(condition.md, scope.md, timing.md, temporal_condition_explanations.md; FRET 저장소 커밋 cf0f913)을 구역 제목에 명시. 파서 관측 줄 삭제, 기존 가이드와 중복 삭제, NL에서 구조를 고르는 규칙 없음 | `--guide-sup` |
| 규칙 글 정합 | +G 규칙 글에서 `R-DEFTIME` 한 줄만 뺀다. 이 줄은 +R2에는 없고 +G에만 있던 규칙이다. 조립 코드는 바뀌지 않는다 | `--g-parity` |
| 사전 규칙 D-5 | 사전 Description 열의 "prior value"를 이전 시점 값으로 읽는다 | `--guide-sup`에 포함 |
| 사전 점검 P-1..P-6 | `bench/tools/prompt_lint.py`. 규칙 출처 장부, +G 대 코드 규칙 ID 정합, 보충문 중복과 도구 관측 문구, 인용 원문 대조(28개), 기준 읽기 성향(참고), 기준 FRETish 6-gram 누출 | `run_fsm.sh lint` (환경변수 FRETDOCS) |

두 플래그가 꺼진 상태의 프롬프트는 v1.3과 바이트 동일하다(`tests/test_v9.py::test_default_prompts_equal_v13_hashes`, v1.3 run_info의 해시와 대조).

## 적용 범위
- 6 arm(Direct, +G 5종) x 13항목 x 3회 = 234 단위. +R2 arm은 다시 돌리지 않으며 슬롯 프롬프트도 바꾸지 않는다.
- 실행: `FRETDOCS=<FRET docs 경로> SUP=1 bash exp/fsm/run_fsm.sh lint` 후 `SUP=1 bash exp/fsm/run_fsm.sh all`. 결과는 `runs/fsm_sup_*`.

## 기본값으로 가정한 결정 (사용자 확인 전)
1. +R2 재실행 제외. 2. +G에서 `R-DEFTIME` 삭제. 3. 확인 집합(비 FSM 48항목, 864 단위)과 잡음 대조(117 단위)는 아직 포함하지 않음.

## 알려진 한계
- 단계 A(템플릿 변환)는 다시 생성되며 비결정성이 있다. 차이에는 단계 A 변동이 섞인다.
- 보충문이 Direct의 조건 종류 선택을 바꿀지는 알 수 없습니다(추측입니다: 효과는 작을 것).
- SPIDER 표현 불가(79단위)와 판정기 한계는 바뀌지 않는다.
