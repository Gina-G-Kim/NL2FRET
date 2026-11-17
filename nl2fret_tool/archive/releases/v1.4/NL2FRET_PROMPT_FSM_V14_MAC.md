# NL2FRET v1.4 FSM 재시험 지시문 (할일 포함)

대상은 Mac의 Claude Code입니다. 한국어로 답하고 이모지와 em dash를 쓰지 않으며, 모르는 것은 "알 수 없습니다"라고 씁니다. 이 패키지 하나로 사전 할일(A), FSM 재시험(B), 분석과 비교(C), 보고(D)를 순서대로 합니다. 범위는 FSM 13항목(429단위)뿐입니다. confirm(비 FSM 48항목)은 사용자가 따로 지시하기 전에는 하지 않습니다.

## 절대 규칙
1. 실행자입니다. 결과의 의미 판단, 방식 우열 판단, 원인 해석, 가설 지지 여부 판정을 하지 않고 관측값만 적습니다. 가설 판정은 사용자가 `docs/ANALYSIS_PLAN.md`로 합니다.
2. `bench/`, `judging/`, `data/`, `docs/` 파일을 수정하지 않습니다. 오류가 나면 원문을 `CHANGELOG.md`에 적고 멈춘 뒤 사용자에게 알립니다. 오류를 피하려고 단위, 항목, approach를 제외하지 않습니다.
3. 결과가 나빠 보여도 같은 단위를 다시 돌리지 않습니다. 프로세스 중단이나 한도로 멈춘 경우의 재개(같은 명령 재실행)만 허용합니다.
4. approach는 11개(DIRECT, +G 5, +R2 5)로 고정입니다. 추가하거나 빼지 않습니다. 모델은 기본값(sonnet)입니다.
5. 모델 응답을 고치거나 다시 부르지 않습니다.
6. 기준선 `runs/fsm_20261113`은 수정하지 않습니다. 복사해서 씁니다. 이 폴더가 없으면 사용자에게 위치를 묻고 멈춥니다.
7. 아래 "기대값"과 다른 수가 나오면 그 사실을 그대로 적고 해당 단계에서 멈춥니다(고쳐서 진행하지 않습니다).

## A. 사전 할일 (실행 전 전부 통과해야 B로 갑니다)
A1. 환경 확인: `python3 --version`, `docker --version`, `NuSMV -help | head -2`, `claude --version`, `docker image ls | grep fret-lab`, `pdftotext -v`. NuSMV 버전을 적습니다(샌드박스 기준값은 2.5.4). 없는 것이 있으면 멈추고 알립니다.
A2. `make test`: 29건 통과. `make freeze-check`: 전부 OK(55개).
A3. 입력 준비:
   - FRET 문서: `git clone https://github.com/NASA-SW-VnV/fret` 후 커밋 `cf0f913`을 체크아웃하고 `fret-electron/docs/_media/user-interface/examples` 경로를 `FRETDOCS`로 지정합니다.
   - 논문 원문(P-4b): 프로젝트의 PDF `The_Ten_Lockheed_Martin_Cyber-Physical_Challenges_Formalized_Analyzed_and_Explained.pdf`가 있으면 `pdftotext -raw`로 텍스트를 만들어 `PAPERRAW`로 지정합니다. PDF가 없으면 `docs/paper_passage_AP003c.txt`를 `PAPERRAW`로 쓰고 그 사실을 보고합니다. NTRS의 RE2020AMFinal PDF는 해당 문장이 없으므로 쓰지 않습니다.
A4. 소유권 표와 규칙 의미 검증:
   - `python3 bench/tools/ownership_table.py --fret-docs $FRETDOCS` 기대값: 활성 근거 없는 규칙 0, 미분류 0, 인용 34개 일치, 못 찾은 것 없음.
   - `python3 bench/tools/rule_semantics_check.py --parser docker --engine nusmv --out runs/rule_semantics.json` 기대값: 5개 검증 모두 PASS.
A5. 판정기 대조(NuSMV): `ENGINE=nusmv CAP=512 CTRLDIR=runs/judge_controls_nusmv bash exp/fsm/run_intent.sh controls fsm v14` (수십 분 걸릴 수 있음). 결과 `controls.md`를 그대로 보고하고 `docs/controls_nusmv512/controls.md`와 비교합니다. 기대값: C+ID, C+NN, C+AND 거짓 실패 0/112, C-TAUT 0/112, C-NEG 0/112, C-CONTR 112/112(거짓 성공), C-SHIFT 33부분 중 6. 다르면 차이를 적고 멈춥니다(Mac의 NuSMV 버전이 다를 수 있음).
A6. 기준선 재판정(LLM 호출 없음, 판정만): v1.3 결과를 같은 조건 `CAP=512`로 다시 판정해 비교 기준으로 씁니다.
   - `cp -r runs/fsm_20261113 runs/fsm_20261113_cap512` 후, `bash exp/fsm/run_intent.sh judge fsm v13 runs/fsm_20261113_cap512` (inputs는 복사본에 이미 있어야 함. 없으면 `inputs` 단계를 먼저 같은 RUN으로 실행).
   - 그 다음 `CTRLDIR=runs/judge_controls_nusmv bash exp/fsm/run_intent.sh analyze fsm v13 runs/fsm_20261113_cap512`.
   - 기대값: 429부분, 관대 성공 18, 엄격 성공 17, SAME만 0, 원인 라벨 미분류 0, 천장(자기 비교 불가) 0. 원본 `runs/fsm_20261113`의 `summary.md` 성공 수와 arm별 관대 성공 수(DIRECT 1, Adv-EARS+R2 2, Boilerplate+G 6, Boilerplate+R2 3, EARS+R2 3, MASTeR+R2 3, 나머지 0)가 일치하는지 확인합니다.
A7. 사전 점검: `bash exp/fsm/run_intent.sh dryrun fsm v14`는 429단위(13 x 11 x 3)여야 합니다. `FRETDOCS=... PAPERRAW=... bash exp/fsm/run_intent.sh lint fsm v14`는 P-1부터 P-6까지(P-1b, P-4, P-4b 포함) 전부 PASS여야 합니다. FAIL이나 SKIPPED가 하나라도 있으면 멈추고 출력 원문을 알립니다.

## B. 재시험 실행 (v1.4, FSM만)
B1. 실행 폴더를 정합니다: `RUN=runs/fsm_v14_$(date +%Y%m%d)`.
B2. 단계별로 같은 RUN을 줍니다. 단계 A(템플릿 변환)는 v1.3 출력을 재사용합니다(프롬프트 해시가 다르면 스크립트가 중단하며, 그때는 멈추고 알립니다).
   - `STAGEA_FROM=runs/fsm_20261113/gen bash exp/fsm/run_intent.sh gen fsm v14 $RUN` (오래 걸림, 한도 대기 가능, 중단 시 같은 명령으로 재개)
   - `bash exp/fsm/run_intent.sh inputs fsm v14 $RUN`
   - `ENGINE=nusmv CAP=512 bash exp/fsm/run_intent.sh judge fsm v14 $RUN` (selfcheck 실패 시 멈추고 보고)
   - `bash exp/fsm/run_intent.sh trace fsm v14 $RUN`
B3. 실행 중 쌓이는 관측(오류 원문, 재개 이력, FRET 거절 2회 이상 단위 수, cap_reached 수, fallback 수와 `no_source:` 사유 분포, 사전 oov 수)을 기록합니다.

## C. 분석과 비교 (사전 선언 기준 그대로, 해석 없음)
C1. `CTRLDIR=runs/judge_controls_nusmv bash exp/fsm/run_intent.sh analyze fsm v14 $RUN`
C2. `BASE=runs/fsm_20261113_cap512/analysis bash exp/fsm/run_intent.sh compare fsm v14 $RUN`
C3. `$RUN/analysis.md`(또는 `analysis/analysis.md`)와 `$RUN/comparison/` 안의 보고 파일 원문을 그대로 첨부합니다. 요약, 판정, 우열 평가를 덧붙이지 않습니다.

## D. 보고
`REPORT_FSM_V14.md`에 다음을 표와 원문으로 적습니다. 해석은 적지 않습니다.
1. 환경(OS, python, docker, NuSMV 버전, claude CLI 버전, 모델)과 A1부터 A7까지 각 단계의 기대값 대비 관측값(일치 또는 불일치).
2. B의 `summary.md` 전체 표, 단위 수, 판정 역할 분포, `counterexamples.jsonl` 행 수와 `counterexample_status` 분포, B3 관측.
3. C의 `analysis.md`와 `comparison` 원문. arm별로 v1.3과 v1.4의 관대 성공, 엄격 성공, SAME만, `reading_same`, `ntiming_same`, 원인 라벨 표가 포함되어야 합니다.
4. 무작위 3단위의 `trace/units/*.md`에서 S0 내지 S6 블록과 로그 경로가 실제 파일에 있는지.
5. 오류 원문과 재개 이력(없으면 "없음").
결과 폴더(`runs/fsm_v14_*`, `runs/fsm_20261113_cap512`, `runs/judge_controls_nusmv`, `runs/rule_semantics.json`, `REPORT_FSM_V14.md`)를 zip으로 묶어 경로를 사용자에게 알립니다. 가설 H1, H2의 지지 여부는 적지 않습니다.
