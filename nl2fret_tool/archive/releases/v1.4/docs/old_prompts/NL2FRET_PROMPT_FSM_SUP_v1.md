# NL2FRET v1.4 가이드 보강 시험 지시문

대상은 Mac의 Claude Code입니다. 한국어로 답하고 이모지와 em dash를 쓰지 않으며, 모르는 것은 "알 수 없습니다"라고 씁니다.

## 절대 규칙
1. 실행자입니다. 결과의 의미 판단, 방식 우열 판단, 원인 해석을 하지 않고 관측값만 적습니다.
2. 패키지의 `bench/`, `judging/`, `data/`, `docs/` 파일을 수정하지 않습니다. 오류가 나면 원문을 `CHANGELOG.md`에 적고 멈춘 뒤 사용자에게 알립니다.
3. 결과가 나빠 보여도 같은 단위를 다시 돌리지 않습니다. 프로세스 중단이나 한도로 멈춘 경우의 재개(같은 명령 재실행)만 허용합니다.
4. 이전 실행(`runs/fsm_20261113`)은 기준선입니다. 열거나 복사하되 수정하지 않습니다.

## 순서
1. 환경 확인: python3, docker, NuSMV, claude CLI, fret-lab 이미지. 없는 것이 있으면 멈추고 알립니다.
2. `make test`(29건 통과), `make freeze-check`가 OK인지 확인합니다.
3. `docs/V14_GUIDE_SUPPLEMENT.md`를 읽습니다. 그 문서의 '기본값으로 가정한 결정'(+R2 재실행 제외, +G의 R-DEFTIME 삭제)을 사용자가 승인했는지 확인합니다. 승인이 없으면 멈춥니다. 파서 관측 한 줄은 v1.4에서 삭제되었습니다.
3-1. FRET 저장소(NASA-SW-VnV/fret, 커밋 cf0f913)의 `fret-electron/docs/_media/user-interface/examples` 경로를 `FRETDOCS`로 지정해 `SUP=1 FRETDOCS=... bash exp/fsm/run_fsm.sh lint`를 실행합니다. 6개 점검(P-1..P-6) 중 하나라도 FAIL 또는 SKIPPED이면 멈추고 출력 원문을 알립니다.
4. `SUP=1 bash exp/fsm/run_fsm.sh dryrun`: 단위 수 234(6 arm x 13 x 3)인지 확인합니다. 다르면 멈춥니다.
5. `SUP=1 bash exp/fsm/run_fsm.sh gen`(내부에서 --guide-sup --g-parity 적용), 이어서 `inputs`, `judge`, `trace`를 같은 방식으로 돌립니다.
6. 보고: `runs/fsm_sup_*/summary.md`와, 같은 arm 6개에 대해 v1.3 결과(`runs/fsm_20261113/summary.md`)의 역할 수와 성공 수를 나란히 표로 적습니다. 해석은 적지 않습니다.
7. 결과 폴더를 zip으로 묶고 경로를 알립니다.


## 추가 (v1.4 재시험, 2026-11-15)
위 순서 대신 `docs/V14_INTENT_TEST.md`의 "실행 순서 (Mac)" 1~7번을 그대로 따릅니다. approach는 11개(DIRECT, +G 5, +R2 5)로 v1.3과 같고 늘리지 않습니다. 판정 기준은 `docs/ANALYSIS_PLAN.md`이며 해석은 적지 않습니다.
- 3번(controls)은 NuSMV로 돌리고 `controls.md`를 그대로 보고합니다.
- 4번 dryrun이 429단위가 아니거나 lint가 FAIL 또는 SKIPPED이면 멈추고 출력을 알립니다.
- v1.3 결과(`runs/fsm_20261113`)는 다시 돌리지 않고 6번의 분석만 합니다.
- confirm(48항목)은 사용자가 지시했을 때만 `confirm v13`, `confirm v14` 순서로 실행합니다.
- 보고: `analysis.md`와 `comparison.md` 원문을 그대로 첨부합니다.
