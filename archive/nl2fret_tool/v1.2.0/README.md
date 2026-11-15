# NL2FRET 도구 패키지

자연어 요구사항을 반정형 템플릿(MASTeR, EARS 등)을 거쳐 FRETish로 변환하고, NASA FRETish 기준(reference)과 NuSMV 질의로 판정하는 전체 도구.

버전: 1.2.0 (판정 모듈 `judging/nl2fret_judge`, 판정 코드 동결본). 변경 이유와 근거는 `CHANGELOG.md`, 기록 형식과 동결 장치는 `docs/DESIGN.md` 부록 A-2, A-3.

## 구성
- `bench/` : 변환, FRET 컴파일, 실현가능성(Kind2), 점수 산출 파이프라인 (v8 동결본, 수정 금지, `make freeze-check`로 해시 확인)
- `judging/nl2fret_judge/` : 판정 모듈 (정렬, 불리언 추상화, NuSMV 질의, 역할 판정, AP 불일치 기록, 기록기, 집계, 코드 동결 대조 `freeze.py`)
- `judging/legacy/` : 정렬 후보 생성에 쓰는 judge2/4/5 (기존 연구 코드, 경로 하드코딩만 수정)
- `JUDGE_FROZEN_MANIFEST.sha256` : 판정 코드(`judging/nl2fret_judge/*.py`, `judging/legacy/*.py`)의 파일별 sha256. `judge`가 시작할 때 대조하고, 다르면 실행을 거부한다. 이후 코드를 바꾸지 않고 실험만 돌린다.
- `data/reference/` : 정답 키(61 항목, FRET 컴파일 LTL 포함), 신호 사전, z3 대조용 쌍 샘플
- `data/example_*` : v8 사전 실험 단위, 문장별 LTL, 실현가능성 결과 (판정 동작 예시용)
- `docs/DESIGN.md` : 설계 문서, `docs/RUNBOOK.md` : 실행 절차
- `tests/` : 샌드박스 테스트 (z3 엔진, NuSMV 불필요)

## 판정 요약
역할 정의: Sound(GT->Pred)와 Compl(Pred->GT) 모두 성립하면 SAME, Compl만 성립하면 PROOF, Sound만 성립하면 REFUTE, 둘 다 실패하면 NEITHER. 정렬이 없으면(같은 유형의 대응 변수가 없거나 서로 다른 변수로 짝지을 수 없는 경우 포함) UND, 엔진이 판정하지 못하면 N/M. 모든 단위는 분모에 남는다.

## 동결 후 실행 절차
(자세한 것은 `docs/RUNBOOK.md` 5절)
- (가) 입력 3개 준비: `inputs/units.json`, `inputs/fret_ltl_gen.jsonl`, `inputs/fret_realizability_gen.jsonl` (형식은 `data/example_*`와 RUNBOOK 1절).
- (나) `make selfcheck NUSMV="<NuSMV 명령>" OUT=runs/<이름>` : 5쌍이 모두 PASS여야 한다.
- (다) `make judge OUT=runs/<이름> NUSMV="<NuSMV 명령>"` : 시작할 때 코드를 매니페스트와 대조한다(다르면 종료 코드 2로 거부). `runs/<이름>/run_header.json`에서 `"frozen": true`를 확인한다.
- (라) `make aggregate OUT=runs/<이름>`
- (마) 재개: 중단되면 같은 `OUT`으로 (다)를 다시 실행한다(기록된 쌍은 건너뛴다). 기본 `OUT`은 시각을 포함하므로 재개하려면 `OUT`을 직접 지정한다.
- (바) 코드를 바꾸지 않는다(`judging/`, `JUDGE_FROZEN_MANIFEST.sha256`, `bench/`). `--allow-unfrozen`은 개발용 우회이며 그 실행은 `frozen: false`로 기록되어 동결된 결과로 쓰지 않는다. 코드를 바꿔야 하면 새 폴더에서 버전을 올려 새로 릴리스한다.

## 검증 상태
샌드박스에서 확인함: 자기점검 5쌍(z3 엔진), 기존 쌍 610개 중 판정된 쌍에서 저장된 z3 역할과 불일치 0건, v8 문장 252쌍에서 기존 판정과 판정된 쌍 불일치 0건.
Mac에서 확인함(2026-11-10, NuSMV 2.6.0 Docker 이미지): v1.0.0으로 NuSMV 자기점검 5쌍 PASS, v8 문장 252쌍 전체 실행(약 36분), NuSMV와 z3 모두 판정된 126쌍에서 역할 불일치 0건. v1.1.0 패치 실행에서 같은 252쌍을 다시 돌려 v1.0.0 기록과 비교했고, 다른 것은 정렬 후보 없음 6쌍(N/M에서 UND)뿐이었다(`CHANGELOG.md`).
Mac에서 확인함(2026-11-11, v1.2.0): 릴리스 전 코드와 릴리스된 코드가 같은 상태에서 NuSMV 자기점검 5쌍 PASS, v8 문장 252쌍을 NuSMV(약 37분)와 z3로 다시 돌려 v1.1.0 기록과 비교했고 모든 쌍의 모든 필드가 같았다(헤더의 새 필드만 다름). 릴리스 후 `make judge` 10쌍 확인 실행이 `frozen: true`로 기록되었다. 이 zip을 풀어서 `make freeze-check`, `make test`(48 passed), `shasum -a 256 -c JUDGE_FROZEN_MANIFEST.sha256`을 확인했다(`CHANGELOG.md`).
확인하지 못함: Docker FRET/Kind2 단계, Spot 교차검증, 실제 61항목 데이터(입력 3개가 저장소에 없다. 형식은 `docs/RUNBOOK.md` 5절).
