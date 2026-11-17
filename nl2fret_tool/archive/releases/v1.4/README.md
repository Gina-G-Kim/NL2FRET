# NL2FRET 도구 패키지 (v1.4)

자연어 요구사항을 반정형 템플릿(MASTeR, EARS 등)을 거쳐 FRETish로 변환하고, NASA FRETish 기준(reference)과 NuSMV 질의로 판정하는 전체 도구.

## 구성
- `bench/` : 변환, FRET 컴파일, 실현가능성(Kind2), 점수 산출 파이프라인 (v8 동결본, 수정 금지, `make freeze-check`로 해시 확인)
- `judging/nl2fret_judge/` : 판정 모듈 (정렬, 불리언 추상화, NuSMV 질의, 역할 판정, AP 불일치 기록, 기록기, 집계)
- `judging/legacy/` : 정렬 후보 생성에 쓰는 judge2/4/5 (기존 연구 코드, 경로 하드코딩만 수정)
- `data/reference/` : 정답 키(61 항목, FRET 컴파일 LTL 포함), 신호 사전, z3 대조용 쌍 샘플
- `data/example_*` : v8 사전 실험 단위, 문장별 LTL, 실현가능성 결과 (판정 동작 예시용)
- `docs/DESIGN.md` : 설계 문서, `docs/RUNBOOK.md` : 실행 절차
- `tests/` : 샌드박스 테스트 (z3 엔진, NuSMV 불필요)

## 판정 요약
역할 정의: Sound(GT->Pred)와 Compl(Pred->GT) 모두 성립하면 SAME, Compl만 성립하면 PROOF, Sound만 성립하면 REFUTE, 둘 다 실패하면 NEITHER. 정렬이 없으면 UND, 엔진이 판정하지 못하면 N/M. 모든 단위는 분모에 남는다.

## 검증 상태
샌드박스에서 확인함: 자기점검 5쌍(z3 엔진), 기존 쌍 610개 중 판정된 쌍에서 저장된 z3 역할과 불일치 0건, v8 문장 252쌍에서 기존 판정과 판정된 쌍 불일치 0건.
확인하지 못함(Mac 필요): 실제 NuSMV 자기점검, NuSMV로 전체 실행, Docker FRET/Kind2 단계, Spot 교차검증.

## v1.3 추가
- 고정 데이터셋과 사전 반영(`data/`), FSM 시험(`docs/EXPERIMENT_FSM.md`, `exp/fsm/run_fsm.sh`)
- FRET 거절 시 버리지 않고 누적 로그로 재시도, 사전 전 arm 투입, 부분 단위 판정, NEITHER 이하 반례 기록
- 단계별 추적 `bench/tools/trace_report.py`(`docs/TRACE_FORMAT.md`)
- 데이터 버전업 절차 `docs/DATA_VERSIONING.md`
- 주의: v1.3에서 `bench/`가 바뀌어 동결 해시를 재생성함(`bench/FROZEN_MANIFEST.sha256`)

## v1.4 추가
- `bench/prompts/fretish_guide_supplement.md`: FRET 공식 문서 인용 보충문 + 사전 규칙 D-5 (`--guide-sup`, 기본 꺼짐). 설명과 결정 필요 사항은 `docs/V14_GUIDE_SUPPLEMENT.md`
- 실행: `SUP=1 bash exp/fsm/run_fsm.sh all` (Direct와 규칙 글 arm만)
