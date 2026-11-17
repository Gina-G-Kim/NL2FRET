# PRE_RUN_DEFINITIONS: 실행 전에 고정한 정의

이 파일은 확인 실행(`../../scripts/run_check.sh`)을 하기 전에 작성하고 해시(`../../notes/PRE_RUN.sha256`)로 고정했습니다. 실행 중과 실행 후에는 고치지 않습니다. 1절은 지시문(`../../docs/NL2FRET_JUDGE_RECORDING.md`) 7절을 그대로 옮긴 것이고, 2절 이후는 지시문이 열어 둔 부분과 이 머신의 사실 때문에 필요한 보충 정의입니다.

## 0. 정의를 정하기 전에 이미 한 일 (숨기지 않기 위해 적음)

- 저장된 자료만 읽은 것 (`make_targets.py` 출력): 확인 대상은 27쌍(자가 점검 5쌍, 통제 표본 22쌍, 변이 11종 x 2쌍)입니다. 기준(저장된 판정)에서 N/M인 쌍은 0쌍입니다. GT와 Pred의 텍스트가 같은 쌍은 9쌍입니다(`selfcheck|1`과 통제 8쌍: identity, rename_all, rename_first, rename_half 각 2쌍). GT와 Pred의 SMV 식이 같으면 sound와 compl의 LTLSPEC 텍스트가 같아집니다. 이것을 변환기 코드와 이전 실험의 `selfcheck.json` 1번 쌍(sound와 compl이 같은 SMV 파일 `q_337169dc8fc0.smv`)에서 알고 있었습니다. 그래서 R4를 2.5항처럼 두 가지로 보고하기로 정했습니다.
- NuSMV를 쓰지 않은 개발 중 시험: NuSMV 대신 스텁 스크립트를 넣은 오프라인 시험(스크래치패드, 12쌍: 정상, 비교 원자, 함수 원자, 창 한도 초과, 구문 오류, 시간 초과, 판정 없음, 큰 출력, 오류 종료, 추가 원자 선언, 거짓 판정)으로 기록 코드와 평가 코드를 점검했습니다. 실제 NuSMV 질의, 실제 대상 쌍, 재개 동작은 이 시험에 쓰지 않았습니다.

## 1. 지시문 7절 (그대로)

| 번호 | 기준 | 기록 |
|---|---|---|
| R1 | 확인 대상 모든 쌍에서 `equiv`, `sound`, `compl`, `role`, `nm`이 기준과 동일 (N/M 쌍은 `nm`이 같고 `nm_reason`이 같은 범주) | 예/아니오, 다른 쌍 id |
| R2 | 모든 기록 줄에 3.1의 필드가 존재 | 예/아니오, 누락 필드 |
| R3 | 모든 질의의 `smv_sha256` 파일이 실제로 존재하고 해시가 일치 | 예/아니오 |
| R4 | 한 쌍의 `spec_text` 3개가 서로 다름 | 예/아니오 |
| R5 | `stdout`이 비어 있는 질의의 `verdict`가 null | 예/아니오 |
| R6 | `--record-dir` 없이 실행했을 때 기존 동작과 출력이 같음 (표본 5쌍) | 예/아니오 |

R1이 하나라도 아니오이면 기록 코드 변경이 판정에 영향을 준 것입니다. 복사본을 원본에서 다시 복사해 되돌리고, 원인을 `RECORDING_CHANGES.md`에 적고 멈춥니다.

## 2. 보충 정의

### 2.1 확인 대상과 기준 (지시문 6절)

- 자가 점검 5쌍: 이전 실험 `results/selfcheck.json`의 `pairs` 5개. `pair_id`는 `selfcheck|1`부터 `selfcheck|5`, `group`은 `selfcheck`, `mutation`은 null. 기준은 그 파일에 저장된 판정(`got`, `nm`, `nm_reason`)입니다. 이 파일에는 role이 없으므로 기준 role은 저장된 sound와 compl에 이전 실험 코드의 `role_of`를 적용해 얻습니다(N/M이면 null).
- 통제 쌍 표본: 이전 실험 `results/d1_raw.jsonl`을 파일 순서로 읽으며 변이(`name`)마다 처음 2쌍. 변이가 11종이므로 22쌍입니다. 기준은 그 파일에 저장된 `equiv`, `sound`, `compl`, `role`, `nm`, `nm_reason`입니다. 수식 텍스트(`ref_pt`는 GT, `gen_pt`는 Pred, `ref_ft`, `gen_ft`)는 `pairs.jsonl`의 같은 id에서 가져오며, d1_raw의 `gt`, `pred`와 텍스트가 같은지 `make_targets.py`가 확인합니다. `group`은 `control`, `mutation`은 변이 이름입니다.
- 실행 순서: 자가 점검 5쌍, 이어서 통제 표본 22쌍(d1_raw 파일 순서). 지시문의 22쌍과 27쌍은 이 머신에서 실제로 22쌍과 27쌍입니다.

### 2.2 R1

- 기준이 N/M이 아닌 쌍: `equiv`, `sound`, `compl`, `role`, `nm`이 모두 같고 `nm_reason`이 둘 다 null이어야 합니다. 기준이 N/M인 쌍: `nm`이 같고 `nm_reason` 코드가 같아야 합니다(나머지 필드는 비교하지 않음).
- 사유 코드(범주): 이전 판정기의 `nm_reason` 문자열에서 정합니다. `converter limit`로 시작하면 `converter_limit`, `syntax`로 시작하면 `syntax`, `<질의>: timeout`이 있으면 `timeout`, `<질의>: nusmv output`이 있으면 `nusmv_output`, 문자열이 `no verdict`이면 `no_verdict`, 그 밖은 `other`이며 둘 이상이면 `+`로 잇습니다. 새 기록의 `nm_reason`은 이 코드이고 원래 문자열은 `nm_detail.message`에 둡니다. 기준의 코드는 같은 함수(`record_lib.reason_code`)로 기준 문자열에서 얻습니다.
- 기록 줄이 없는 쌍은 다른 쌍으로 셉니다.

### 2.3 R2

- "3.1의 필드"는 지시문 3.1 표의 21개입니다: run_id, pair_id, group, mutation, gt_pt, pred_pt, gt_ft, pred_ft, atoms_gt, atoms_pred, atoms_union, atom_abstraction, ap_dictionary, equiv, sound, compl, role, nm, nm_reason, nm_detail, queries. 존재는 키가 있다는 뜻이며 값은 null일 수 있습니다.
- 3.2의 질의 필드 12개(kind, spec_text, smv_sha256, smv_path, verdict, stdout, stderr, exit_code, elapsed_sec, timed_out, cmd, query_mode)의 존재는 R2 값에 넣지 않고 같은 표에 별도 항목으로 보고합니다.

### 2.4 R3

- "모든 질의"는 기록된 모든 `queries` 항목입니다(실행하지 않은 질의 포함. 그 질의의 파일은 쓰였을 SMV 텍스트).
- 일치는 파일 바이트의 sha256이 `smv_sha256`과 같고 파일 이름이 `<smv_sha256>.smv`인 것입니다.
- `smv_path`는 기록 디렉터리에 대한 상대 경로(`smv/<sha256>.smv`)입니다. 지시문의 `records/smv/<sha256>.smv`는 기록 디렉터리가 `records/`일 때 같은 파일이며, 이번 확인의 기록 디렉터리는 `records_check/`입니다.

### 2.5 R4

- R4 (지시문 문구 그대로): 질의 3개가 기록된 모든 쌍에서 `spec_text` 3개가 서로 다름. 값은 예/아니오이고 같은 텍스트가 있는 쌍의 id를 적습니다.
- R4 범위 한정 (보충, 같이 보고): GT의 SMV 식(`gt_smv_formula`)과 Pred의 SMV 식(`pred_smv_formula`)이 서로 다른 쌍으로 한정한 같은 검사. 이유는 0절의 관측(두 식이 같으면 sound와 compl의 텍스트가 같아짐)입니다.
- 질의가 3개 기록되지 않은 쌍(구문 오류, 변환기 한도)은 두 값의 대상에서 빼고 id를 따로 적습니다. 두 값 모두 기록으로만 보고하고 해석은 쓰지 않습니다.

### 2.6 R5

- 대상: 질의 기록 중 `stdout`이 빈 문자열인 모든 항목(실행하지 않은 질의 포함. 그 항목은 `stdout`을 빈 문자열로 둡니다). 그 항목의 `verdict`가 모두 null이어야 "예"입니다. 값은 예/아니오, 해당 질의 수, 위반 목록입니다.

### 2.7 R6

- 표본 5쌍은 `selfcheck|1`부터 `selfcheck|5`입니다.
- "기존 동작"은 원본과 바이트가 같은 복사본 `paper_judge_orig.py`의 `judge()`를 같은 입력과 같은 조건(NuSMV 래퍼, 질의당 120초, cap 128, 같은 `work/`)에서 이번 확인 중에 실행한 결과입니다.
- "출력"은 쌍마다 `judge()`가 돌려주는 dict(`equiv`, `sound`, `compl`, `nm`, `nm_reason`, `raw`: 질의별 `spec`, `smv`, `verdict`, `error`, `timeout`, `stdout`, `returncode`)에서 질의별 경과 시간 `sec`만 뺀 것입니다. `sec`는 두 실행 사이에 값이 다른 측정 시간이라 뺍니다.
- 기록 없는 실행은 `judge_cli.py`를 `--record-dir` 없이 실행하고 그 표준 출력의 쌍별 JSON 줄을 읽은 것입니다. 5쌍의 모든 줄이 원본 복사본의 결과와 같아야 "예"입니다.
- 보충(값 판정에는 넣지 않음): 같은 5쌍에서 기록을 켠 실행의 표준 출력 줄이 기록 없는 실행의 줄과 같은지.

### 2.8 시간 제한과 중단

- 질의당 120초(`--timeout 120`, 이전 실험과 같은 값). 한 질의가 시간 초과되면 판정기가 그 쌍의 남은 질의를 실행하지 않고 N/M으로 기록합니다(이전 실험과 같은 동작). 실행하지 않은 질의도 `queries`에 항목으로 남기고 `executed`를 false로 둡니다.
- 전체 60분 규칙: `--max-total-sec 3600`. 이 시간이 지나면 새 쌍을 시작하지 않고 종료 코드 4로 끝냅니다(이미 시작한 쌍은 끝까지 진행). 그때까지의 기록을 보고합니다.
- 예상 소요: 기록 실행 질의 최대 81개(27쌍 x 3), R6용 질의 최대 30개(5쌍 x 3 x 2). 이전 실험의 호출당 평균 약 1초로 추정하면 수 분이지만 알 수 없습니다.

### 2.9 단계 순서와 1회 규칙

- 단계는 `record`(27쌍 기록 실행), `off`(기록 없는 실행, 5쌍), `pristine`(원본 복사본, 5쌍), `evaluate`(R1부터 R6 계산) 순서이며 각 단계는 1회만 실행합니다. 한 단계가 종료 코드 0으로 끝나지 않으면 이후 단계는 실행하지 않고 원문을 `RECORDING_CHANGES.md`에 적습니다.

### 2.10 재개 동작 (지시문 4절 3항)

- 실행해서 확인하지 않습니다(스텁으로도 실행하지 않았습니다). 코드 판독 결과만 `RECORDING_CHANGES.md`에 적습니다.

### 2.11 기록 형식에서 정한 것 (지시문이 열어 둔 부분)

- `group` 값은 통제 `control`, 생성 `generated`, 자가 점검 `selfcheck`입니다.
- `nm_reason`은 2.2항의 사유 코드이고 `nm_detail`은 객체입니다(원래 문자열 `message`, 실패한 질의, cap, 시간 제한, 두 식의 최대 창 크기, 추상화 오류).
- `spec_text`는 SMV 파일에 쓴 줄 그대로 `LTLSPEC `와 식을 이은 문자열입니다.
- 출력 1 MB는 스트림(stdout, stderr)마다 1 MiB(1,048,576 바이트)입니다. 넘으면 앞 1,048,576 바이트와 `*_truncated`, `*_bytes`(전체 크기)를 기록합니다.
- 변환기가 SMV 텍스트를 만들지 못한 쌍(구문 오류, 변환기 한도)은 `queries`가 빈 배열입니다.
- 지시문 표에 없는 추가 필드: 쌍 단위 `gt_smv_formula`, `pred_smv_formula`, `template_id`, `cap`, `timeout_sec`, `recorded_at`. 질의 단위 `executed`, `skipped_reason`, `error`, `cmd_env`, `stdout_truncated`, `stderr_truncated`, `stdout_bytes`, `stderr_bytes`, `printed_specs`.
- 현재 SMV 템플릿의 식별자(`template_id`)는 `boolvars_single_ltlspec_v1`입니다(불리언 VAR 선언과 LTLSPEC 하나). 다른 템플릿은 구현하지 않습니다.
- 실행 식별자 `run_id`는 도구 호출마다 하나이며 형식은 `YYYYMMDDTHHMMSS-<해시 8자리>`입니다.

### 2.12 판정 로직이 바뀌지 않는다는 근거

- 판정을 정하는 코드는 `paper_judge_orig.py`와 같고, `paper_judge_rec.py`의 변경은 `PAPER_JUDGE_REC.diff`에 있습니다(템플릿 식별자 조회, 옆 채널 `sink`와 `sinks`, 보조 함수 `_text`). 옆 채널은 반환 dict를 바꾸지 않습니다. 변환기 `vendor/ltl_engines.py`는 원본 복사본 그대로입니다. 경험적 확인이 R1과 R6입니다.

### 2.13 환경과 보고 방식

- 컨테이너 `nusmv-judge-rec`(이미지 `cst-nusmv:local`), `/usr/bin/python3`의 `-I -B`, `nice -n 10`, 순차 실행, 끝나면 컨테이너 제거. 모델 호출과 에이전트는 없습니다.
- 보고서에는 관측만 적고 해석, 우열, 결론 문장은 쓰지 않습니다.
