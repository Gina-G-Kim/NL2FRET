# 실행 전 정의 (실행 A 시작 전에 고정, 결과를 본 뒤 바꾸지 않는다)

이 문서는 본 실험 생성 실행(`docs/NL2FRET_61_MAIN_RUN.md`)의 실행자 쪽 정의다. 지시 문서와 패키지(`bench/`)는 건드리지 않는다. 아래 정의는 관측과 운영에만 쓰며 방식의 우열이나 원인을 판단하지 않는다.

## 1. 실행 범위 (지시 문서 2절 그대로)
- 실행 A: 항목 61개 x 방식 16개 x 반복 3 = 2928 단위. 실행 B: 항목 51개(`ids_B.txt`, 챌린지 `07_AP` 제외) x 방식 3개(`+D`) x 반복 3 = 459 단위. 합계 3387 단위.
- 실행 명령은 `scripts/run_A.sh`, `scripts/run_B.sh`에 있다. 지시 문서의 명령과 같고, 다른 점은 5절에 적었다.

## 2. 단위와 단위 수 점검의 정의
- 단위 = (항목 id, 방식, 반복 번호). 반복 번호는 파이프라인이 0, 1, 2로 쓴다.
- 단위 수 점검: `calls.jsonl`과 `parser_cache.jsonl`에서 패키지의 `units3.derive`(파이프라인이 남은 일을 정할 때 쓰는 같은 함수)로 (항목, 방식, 반복) 조합마다 단위를 만들고, `pending`이 아닌 단위를 센다. 기대값은 실행 A 2928, 실행 B 459, 합계 3387. 같이 `calls.jsonl`의 행 수, 서로 다른 `stage_key` 수, 단계별 행 수를 적는다.
- 룰 계층이 템플릿 문장을 거부한 단위(`pipeline.code` 가 `A_failed` 또는 규칙 코드)는 호출이 없어도 단위로 센다(`derive`의 정의). 이것은 오류가 아니라 패키지가 기록하는 방식이다.
- 항목 id 점검: `calls.jsonl`의 서로 다른 `item_id` 수가 61이고 모두 `LM-`로 시작하며 `N-`, `X-`로 시작하는 것이 없다.

## 3. 보조 집계 (지시 문서 5-4항 관련, 계수만)
- `tools/dev_record.py`는 22줄이며 단계별 상태 표, 방식별 A/D 행과 파싱 오류 행 수, 모델 분포만 만든다. 지시 문서 5-4항이 말하는 "파서 통과, 되먹임 횟수, 파이프라인 실패 코드" 표는 이 파일이 만들지 않는다. 패키지 파일은 고치지 않는다. `dev_record.py` 출력은 그대로 `MAIN_RECORD.md`에 넣고, 그 뒤에 실행자 스크립트(`scripts/unit_table.py`)의 보조 집계를 "실행자 보조 집계, 패키지 파일 아님"이라고 밝혀 덧붙인다.
- 보조 집계의 정의(방식별 한 줄):
  - 단위 수: `derive`가 `pending`이 아닌 단위.
  - 파이프라인 실패 코드별 수: `derive` 결과의 `pipeline.code` 값 (없으면 `none`).
  - 되먹임 횟수별 단위 수: 단위의 라운드 수 - 1 (0, 1, 2).
  - 파서 통과 단위 수: `pipeline`이 없고, 마지막 라운드에 문장이 1개 이상 있으며, 마지막 라운드의 모든 문장이 파서 사전 검사와 공식 파서를 통과한 단위. (패키지의 `units3.round_failed`가 거짓인 경우.)
  - 마지막 라운드가 `call_failed` 인 단위 수.
- 의미 판단, 방식 비교, 정답 대조는 하지 않는다. 정답은 이 환경에 없다.

## 4. 점검과 운영 정의
- 점검 도구는 `scripts/health_check.py`(읽기 전용, 결과를 바꾸지 않음). 판정 값: OK, WAITING_LIMIT, FINISHED, STOPPED:<상태>, DEAD, STALE, ANOMALY:<내용>. 정의는 파일 머리말에 있다.
  - STALE: 프로세스는 있고 상태가 running인데 `run.log`, `calls.jsonl`, `run_state.json` 중 어느 것도 40분 넘게 갱신되지 않음.
  - ANOMALY: 프로세스는 살아 있고 `cli_error` 또는 `timeout` 행이 있거나, `parse_error` 비율이 5%를 넘거나, 도커가 응답하지 않거나, 디스크 여유가 5 GB 미만.
- 감시 도구는 `scripts/watchdog.py`. 시작한 뒤 새로 쌓인 `calls.jsonl` 행이 연속 3개 `cli_error` 또는 `timeout` 이면 파이프라인에 SIGTERM(정상 종료 신호)을 보내고 `notes/WATCHDOG_ALERT.txt`에 쓴다. 이유: 이 행들은 재시도되지 않으므로(지시 문서 규칙 4, `--retry-errors` 금지) 로그인이나 네트워크가 깨졌을 때 단위가 계속 소모되는 것을 3행에서 멈추기 위함이다. 이 도구는 아무것도 다시 시작하지 않고 결과를 고치지 않는다.
- 점검 주기: 실행 시작 직후 수 분 안에 첫 확인을 하고, 이후 약 30분마다 확인한다. 한도 대기 중에는 이 세션도 같은 구독의 한도 영향을 받으므로 점검이 늦어질 수 있다.
- 재개 규칙 (지시 문서 규칙 4, 3.4): 프로세스가 죽은 경우(DEAD, WATCHDOG_ALERT 없음)에만 같은 스크립트를 `scripts/launch.sh`로 다시 실행하고 `notes/resume_log.txt`에 시각과 이유를 적는다. 상태가 `stopped_deadline`, `stopped_projection`, `aborted_probe_errors`, WATCHDOG_ALERT이면 스스로 재개하지 않고 사용자에게 알린다. `--reset-clock`, `--retry-errors`는 쓰지 않는다.
- 이상이 보여도 같은 항목, 방식, 반복을 다시 돌리지 않고, 패키지 파일을 고치지 않는다. 오류 원문은 `notes/CHANGELOG.md`에 적는다.

## 5. 지시 문서와 다르게 하는 점 (실행 전에 정한 것)
1. 모든 실행 명령은 `scripts/cleanenv.sh`(`env -i`로 HOME, PATH, TZ, LANG만 유지)를 거친다. 이유: 이 작업을 하는 Claude Code 세션의 `CLAUDE_*` 환경 변수가 `claude` 호출에 새어 들어가는 것을 막기 위함. 인자와 파이프라인 동작은 바뀌지 않는다.
2. `nohup caffeinate -i ... &` 대신 `scripts/launch.sh`가 perl `setsid`와 `nohup`으로 터미널 세션에서 분리해 시작한다. `caffeinate -i`는 그대로 쓴다. 출력은 지시 문서와 같이 `results_main/console_A.log`(B는 `console_B.log`)에 쌓는다. 재개 때는 같은 파일에 이어 쓴다(`>>`). 지시 문서의 `>`와 달리 덮어쓰지 않는다.
3. 실행 B의 `--hours`: 지시 문서는 12이지만 파이프라인은 마감 시각을 결과 폴더의 첫 시작 시각(`start_epoch`, 실행 A의 시작)에서 `--hours` 시간 뒤로 계산한다(`run_pipeline.py`: `deadline = start_epoch + hours * 3600`). 실행 A가 12시간보다 오래 걸리면 `--hours 12`인 실행 B는 단위를 하나도 못 하고 `stopped_deadline`으로 끝난다. 그래서 B의 `--hours` 는 (실행 A 시작 이후 경과 시간을 올림한 값) + 12로 하고, 값은 `scripts/after_A.sh`가 한 번 계산해 `notes/B_HOURS.txt`에 적는다. 실행 B의 재개에도 같은 값을 쓴다.
4. 실행 A가 끝난 뒤 `snapshot/`을 `snapshot_A/`로 복사하는 일과 B 시작 전 `calls.jsonl` 줄 수와 sha256 기록은 `scripts/after_A.sh`가 한다. 같은 시점의 `calls.jsonl` 바이트 사본을 `notes/backup_calls_before_B.jsonl`에 보관한다(결과 폴더 밖, 전달물 아님).
5. 지시 문서가 요구하지 않은 감시 도구(`watchdog.py`)를 함께 돌린다(4절).
6. 3.1 내지 3.3 단계는 이미 실행해 `logs/`에 기록했다(`scripts/run_pre.sh`). 모의 시험 상태 폴더는 `/tmp`가 아니라 이 실험 폴더 안(`logs/mock_state`)에 두었다.

## 6. 하지 않는 것
방식, 반복, 항목, 프롬프트, 규칙, 코드를 바꾸지 않는다. 모델 응답이 JSON이 아니어도 고치거나 다시 부르지 않는다. 같은 항목, 방식, 반복을 다시 돌리지 않는다. 정답 자료를 찾지 않고 `data/reference/`를 열지 않는다. git 명령을 쓰지 않는다. 사용자 환경 정보(경로, 계정)를 보고서에 필요 이상으로 쓰지 않는다.
