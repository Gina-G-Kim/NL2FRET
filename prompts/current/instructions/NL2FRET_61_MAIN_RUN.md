# 프롬프트: 본 실험 생성 실행 (록히드마틴 61개 항목, 동결 bench)

아래 전체를 Mac의 LLM 에이전트(Claude Code)에게 `nl2fret_tool_v1.2.zip`과 함께 전달한다. 이 실행은 최종 프로토콜의 본 실험 생성 단계이며 **1회만** 한다. LTL 컴파일, 실현가능성, 판정은 이 단계에서 하지 않는다 (생성이 끝난 뒤 별도 지시로 한다).

---

너는 실행자다. 생성 문장의 의미 판단, 방식 우열 판단, 원인 해석을 하지 않는다. 관측한 값만 적는다. 한국어로 쓰고 이모지와 em dash를 쓰지 않는다. 모르는 것은 "알 수 없습니다"라고 쓴다.

## 1. 절대 규칙
1. `nl2fret_tool_v1.2.zip`의 `bench/`(동결 38개 파일, `FROZEN_MANIFEST.sha256`)의 어떤 파일도 수정하지 않는다. 오류가 나면 고치지 말고 원문을 `CHANGELOG.md`에 적고 멈춘 뒤 사용자에게 알린다.
2. 정답(기준 FRETish)은 이 작업 환경에 없다. 찾지 않는다. (`data/reference/`는 판정 도구 쪽 자료이며 이 단계에서 열지 않는다.)
3. 모델 응답이 JSON으로 읽히지 않은 호출은 고치거나 다시 부르지 않고 그대로 기록한다.
4. 결과가 나빠 보이거나 이상해 보여도 같은 항목, 방식, 반복을 다시 돌리지 않는다. 프로세스가 죽거나 한도로 멈춘 경우의 재개(같은 명령 재실행)만 허용한다. `--reset-clock`, `--retry-errors`는 쓰지 않는다.
5. 실행 결과를 보고 방식, 반복 수, 항목, 프롬프트, 규칙을 바꾸지 않는다.
6. git 명령 금지. 사용자 환경 정보(경로, 계정)를 보고서에 필요 이상으로 쓰지 않는다.
7. 작업 폴더는 `experiments/` 아래 다음 번호 규칙(`NNN_이름`, 다음 번호 019)으로 새로 만든다. 도구 zip은 쓰기 가능한 새 사본으로 풀고, 원본 zip은 건드리지 않는다. 폴더는 `/Users` 아래여야 한다(Colima 마운트).

## 2. 범위 (결정되어 있음, 되묻지 않는다)
- 항목: `bench/data/lm_items.jsonl` 61개 (록히드마틴 챌린지 10개).
- **실행 A** (61개 항목 전체, 반복 3): 방식 16개
  DIRECT, PARA, MASTeR, EARS, Adv-EARS, SPIDER, Boilerplate, MASTeR+R2, EARS+R2, Adv-EARS+R2, SPIDER+R2, Boilerplate+R2, DIRECT+V, MASTeR+V, EARS+V, Boilerplate+V
  = 61 x 16 x 3 = 2928 단위.
- **실행 B** (같은 결과 폴더, 반복 3): 신호 사전 방식 3개 DIRECT+D, MASTeR+D, EARS+D. `+D` 방식은 모든 항목에 신호 사전이 있어야 하는데 7번 챌린지(`07_AP`, 10개 항목)에는 사전이 없어서, 이 10개를 뺀 **51개 항목**에만 돌린다 (`--only-id`로 51개 id를 지정). 51 x 3 x 3 = 459 단위. 템플릿 단계(stage A)는 같은 결과 폴더의 같은 키 `항목|템플릿|반복|A`로 기본 방식과 공유되므로 `MASTeR` 대 `MASTeR+D` 등은 같은 템플릿 문장 위의 비교다.
- 총 3387 단위. 시간은 확인하지 못했다. v6 주 실행이 2379단위에 약 14시간(11/2 17:39 - 11/3 07:20)이었으므로 단위 수에 비례하면 약 20시간으로 추정한다(추측). 한도 대기가 더 붙을 수 있다.
- V6 방식, +G, +U, +R(R2 아님)은 쓰지 않는다.

## 3. 순서

### 3.1 환경 확인
```bash
pwd                     # /Users 아래여야 함
docker info >/dev/null && docker image ls fret-lab
python3 -c "import fretparse,json;print(json.dumps(fretparse.compile_texts(['when a b shall satisfy c','when a b shall every 5 seconds satisfy c'],'docker',None),indent=1))"
claude --version
```
첫 문장 `ok: true`, 둘째 `ok: false`가 아니면 원문을 `FRET_NOTES.md`에 적고 멈춘다. `claude --version`과 사용 모델 인자(`sonnet`)를 기록한다.

### 3.2 동결 확인 (`bench/`에서)
```bash
sha256sum -c FROZEN_MANIFEST.sha256        # 38개 모두 OK 여야 함
sha256sum FROZEN_MANIFEST.sha256 | tee MAIN_FROZEN.sha256
```
기대값 (v8 패키지의 값, 아래와 다르면 멈춘다):
- FROZEN_MANIFEST.sha256 176b144fe280158e05a4ec4a5aa9c7e912fab067b8e989ccacd12a2f2f16e571
- tpl_rules.py 3177a05383c401eeee67a7cb7433591d46ce3d2f36a1fa3f9ca260cc58bee488
- fretlint.py df339e40d5f7c1a59d2ae7d3a8449b3962daf36c36b62972964566adf4b6b5df
- prompts3.py 19b3c737b953e102f6967971a17d4937e4b25c6dc8a4f08aac14a0179e66534d
- prompts/fretish_guide.md 00366ed670c54279371ae290f6cac36dd57e280ce286e8fff947953c3dbc30c4
- data/lm_items.jsonl a8314c94aa81110bf62410300f0d2749a10574aff0871a7b2a15ea569f565200
- data/sigdict.json a190a714c61622b24fd93dcfb83001b3e45fc66c83315c3a6f50b04d2dfd7cf3
(v7 TEST 지시문의 prompts3.py 값 `c57d01ab...`과 매니페스트 값 `3e8f0a0f...`은 v8에서 `+D` 방식이 추가되어 바뀐 것이 맞다. 이 문서의 값을 쓴다.)

### 3.3 모의 시험과 사전 확인 (한도와 도커를 쓰지 않음)
```bash
python3 -I tools/selftest.py          # SELFTEST_OK
python3 cli.py --selftest             # cli selftest ok
export MOCK_STATE_DIR=/tmp/mock_main; rm -rf /tmp/mock_main results_mock
python3 run_pipeline.py --data data/lm_items.jsonl --limit-items 8 --claude-bin ./mock_claude.py --parser mock --results results_mock --reps 1 --arms DIRECT PARA MASTeR EARS Adv-EARS SPIDER Boilerplate MASTeR+R2 EARS+R2 Adv-EARS+R2 SPIDER+R2 Boilerplate+R2 DIRECT+V MASTeR+V EARS+V Boilerplate+V | tail -3
python3 tools/dev_record.py results_mock | head -15
rm -rf results_mock
```
통과 기준: 마지막 상태 `finished_all`, 중복 `stage_key` 0.

실행 B를 사전에 확인한다.
1. `data/lm_items.jsonl`에서 `challenge`가 `07_AP`로 시작하는 항목 id 10개와 나머지 51개 id를 뽑아 `ids_B.txt`로 저장한다 (결과를 보고 고르지 않고 챌린지 번호로만 정한다).
2. `--dry-run`을 실행 A와 실행 B 각각에 돌려 단위 수(2928, 459)와 프롬프트 해시를 기록한다.
3. `run_pipeline.py`의 코드(`--only-id`, `snapshot`, `units_state`)를 읽어, 같은 결과 폴더에서 실행 B가 실행 A의 stage A 행을 재사용하는지, 그리고 `snapshot/`(`run_info.json`, `items_used.jsonl` 등)을 덮어쓰는지 확인한다. 같은 폴더의 두 번째 실행이 코드에서 거부되면 수정하지 말고 멈추고 보고한다.

### 3.4 실행 A
```bash
mkdir -p results_main
nohup caffeinate -i python3 run_pipeline.py --data data/lm_items.jsonl --results results_main --reps 3 --block 1 --hours 40 \
  --arms DIRECT PARA MASTeR EARS Adv-EARS SPIDER Boilerplate MASTeR+R2 EARS+R2 Adv-EARS+R2 SPIDER+R2 Boilerplate+R2 DIRECT+V MASTeR+V EARS+V Boilerplate+V \
  --model sonnet --cli-extra "--safe-mode --effort medium" > results_main/console_A.log 2>&1 &
```
- 진행 확인: `tail -3 results_main/run.log`, `cat results_main/run_state.json`.
- 죽거나 한도로 멈추면 같은 명령을 다시 실행한다 (이어서 진행됨).
- 종료 상태가 `finished_all` 또는 `stopped_deadline`이면 다음으로 간다. `stopped_deadline`이면 사용자에게 알리고 `--hours`를 늘려 같은 명령으로 이어 갈지 묻는다 (스스로 바꿔 시작하지 않는다).
- 실행 A가 끝나면 `snapshot/`을 `snapshot_A/`로 통째로 복사해 보존한다.

### 3.5 실행 B (실행 A가 `finished_all`이 된 뒤에만)
```bash
nohup caffeinate -i python3 run_pipeline.py --data data/lm_items.jsonl --results results_main --reps 3 --block 1 --hours 12 \
  --only-id $(cat ids_B.txt) --arms DIRECT+D MASTeR+D EARS+D \
  --model sonnet --cli-extra "--safe-mode --effort medium" > results_main/console_B.log 2>&1 &
```
- 같은 방식으로 진행을 확인하고 재개한다. 끝나면 `snapshot/`을 `snapshot_B/`로 복사한다.
- 실행 B가 끝난 뒤 `calls.jsonl`에서 실행 A의 행이 하나도 바뀌지 않았는지 확인한다 (실행 B 시작 전 `calls.jsonl`의 줄 수와 sha256을 기록해 두고, 앞부분이 그대로인지 비교).

### 3.6 기록
```bash
python3 tools/dev_record.py results_main > results_main/MAIN_RECORD.md
```
`MAIN_RECORD.md` 끝에 덧붙인다: 각 실행의 시작과 종료 시각, 한도 사건 횟수, 재개 횟수, `claude --version`, 이 문서에서 벗어난 점과 이유, 단위 수 점검(기대 2928 + 459 = 3387, 실제 `calls.jsonl` 기준), 항목 id 점검(모두 `LM-`로 시작하고 61개, 개발셋 id `N-`, `X-` 없음).

## 4. 전달
`results_main`을 zip으로 묶어 전달한다 (`calls.jsonl`, `parser_cache.jsonl`, `run_state.json`, `run.log`, `console_A.log`, `console_B.log`, `snapshot_A/`, `snapshot_B/`, `MAIN_RECORD.md`, `ids_B.txt`). 해석 문장은 쓰지 않는다. zip의 sha256과 `calls.jsonl`의 sha256을 보고한다.

## 5. 최종 보고 형식
1. 환경(OS, `claude --version`, 모델 인자, Docker 이미지), 동결 확인 결과(3.2의 각 해시와 `OK` 수)
2. 모의 시험과 사전 확인 결과 (dry-run 단위 수, 프롬프트 해시, `--only-id` 코드 확인 결과)
3. 실행 A와 B: 시작과 종료, 소요 시간, 한도 사건, 재개 횟수, 종료 상태, 단위 수
4. 단위 상태 분포 (`tools/dev_record.py`가 만드는 표 그대로: 방식별, 파서 통과, 되먹임 횟수, 파이프라인 실패 코드)
5. 이상 징후 (호출 실패, JSON 읽기 실패 수, 코드가 거부한 것, 이 문서와 다르게 한 점)
6. 확인하지 못한 항목과 이유
7. 산출물 경로와 sha256