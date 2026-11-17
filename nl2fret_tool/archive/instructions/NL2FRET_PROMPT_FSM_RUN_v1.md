# NL2FRET FSM 시험 지시문 (v1.3)

대상은 Mac의 Claude Code입니다. 두 가지를 순서대로 합니다: (가) 메인 디렉터리의 데이터셋과 사전을 버전업, (나) FSM 시험 실행. 한국어로 답하고 이모지와 em dash를 쓰지 않으며, 모르는 것은 "알 수 없습니다"라고 씁니다.

## 절대 규칙
1. 실행자입니다. 결과의 의미 판단, 방식 우열 판단, 원인 해석을 하지 않고 관측값만 적습니다.
2. 이 패키지의 `bench/`, `judging/`, `data/` 코드와 프롬프트를 수정하지 않습니다. 오류가 나면 원문을 `CHANGELOG.md`에 적고 멈춘 뒤 사용자에게 알립니다.
3. 결과가 나빠 보여도 같은 단위를 다시 돌리지 않습니다. 프로세스 중단이나 한도로 멈춘 경우의 재개(같은 명령 재실행)만 허용합니다.
4. 모델 응답을 고치거나 다시 부르지 않습니다. FRET 도구 거절 후 재시도는 파이프라인이 하는 것이며 수동으로 하지 않습니다.

## (가) 메인 디렉터리 버전업
`docs/DATA_VERSIONING.md`를 따릅니다.
1. 메인 디렉터리 위치를 사용자에게 확인합니다(모르면 묻습니다).
2. 자산별(dataset, dictionary, reference) 현재 버전 K를 `VERSIONS.md`에서 읽고(없으면 알 수 없음으로 적고 사용자에게 묻습니다), 현재 파일을 `archive/<자산>/vK/`로 옮깁니다.
3. 이 패키지의 `data/dataset/*`, `data/dictionary/*`, `data/reference/*`를 메인 디렉터리에 v(K+1)로 둡니다.
4. `VERSIONS.md`에 자산, 버전, 경로, sha256, 사유, 사용 실험을 추가합니다. 사유: 데이터셋 고정(61 항목, 기준 112행), 사전 564 항목. 사용 실험: FSM 시험 v1.3.
5. 삭제하지 않습니다. 옮기기만 합니다.

## (나) FSM 시험
`docs/EXPERIMENT_FSM.md`가 설계입니다. 순서:
1. 환경: `python3 --version`, `docker --version`, `NuSMV -help | head -2`(또는 docker NuSMV 래퍼), `claude --version`, `docker image ls | grep fret-lab`를 확인해 보고합니다. 없는 것이 있으면 멈추고 알립니다.
2. 테스트: `make test` 14건 통과 확인. `make freeze-check`가 OK인지 확인.
3. `bash exp/fsm/run_fsm.sh dryrun`: 단위 수가 429(13 x 11 x 3)인지 확인합니다. 다르면 멈춥니다.
4. `bash exp/fsm/run_fsm.sh gen` (오래 걸릴 수 있음, 한도 대기 가능. 중단 시 같은 명령으로 재개).
5. `bash exp/fsm/run_fsm.sh inputs`, 그 다음 `bash exp/fsm/run_fsm.sh judge`. 자기점검(selfcheck)이 실패하면 멈추고 보고합니다.
6. `bash exp/fsm/run_fsm.sh trace`.
7. 확인 항목(관측만 보고): `runs/fsm_*/summary.md` 전체 표, 단위 수, NEITHER 이하 판정 수 대비 `counterexamples.jsonl` 행 수와 `counterexample_status` 분포(recorded, engine_gave_no_trace, not_available), FRET 거절 2회 이상 단위 수, cap_reached 수, fallback 수, 사전 oov 수.
8. 무작위 3단위의 `trace/units/*.md`를 열어 S0 내지 S6 블록과 로그 경로가 실제 파일에 존재하는지 확인해 보고합니다.

## 보고
`REPORT_FSM.md`에 위 관측값을 표로 적고 실행 환경 요약, 오류 원문, 재개 이력을 덧붙입니다. 해석은 적지 않습니다. 결과 폴더 `runs/fsm_*`을 zip으로 묶어 사용자에게 경로를 알립니다.
