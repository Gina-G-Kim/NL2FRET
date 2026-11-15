# NL2FRET v8 신호 사전 스모크 지시문

대상은 이 폴더(`bench/`)의 Claude Code입니다. 같은 요구사항을 신호 사전 없이, 있이 생성했을 때 무엇이 달라지는지 짝지어 기록하는 작은 시험입니다. 방식 간 우열이나 비율의 의미를 결론 내리는 시험이 아니며, 사전 조건이 코드와 프롬프트에서 제대로 작동하는지와 사전 이름이 실제 출력에 쓰이는지를 보는 시험입니다. 이 실행의 결과를 본 뒤에 규칙이나 프롬프트를 바꾸지 않습니다.

## 1. 역할과 절대 규칙
1. 당신은 실행자입니다. 생성 문장의 의미 판단, 방식 우열 판단, 원인 해석을 하지 않습니다. 관측한 값만 적습니다.
2. 이 폴더의 모든 파일(코드, `prompts/`, `templates/`, `data/`)을 수정하지 않습니다. 오류가 나면 원문을 `CHANGELOG.md`에 적고 멈춘 뒤 사용자에게 알립니다.
3. 정답(기준 FRETish)은 이 폴더에 없습니다. 찾지 않습니다.
4. 모델 응답이 JSON으로 읽히지 않은 호출은 고치거나 다시 부르지 않고 기록합니다.
5. 한국어로 답하고 이모지와 em dash를 쓰지 않습니다. 모르는 것은 "알 수 없습니다"라고 씁니다.
6. 이 실행은 1회만 합니다. 결과가 나쁘거나 이상해 보여도 같은 항목을 다시 돌리지 않습니다. 프로세스가 죽거나 한도로 멈춘 경우의 재개만 허용합니다.
7. 사용자의 환경 정보(경로, 계정)를 보고서에 필요 이상으로 쓰지 않습니다.

## 2. 무엇이 새로운가 (v7 TEST 묶음 대비)
- 방식 접미사 `+D`: FRETish를 쓰는 단계(DIRECT는 단계 D, 템플릿 방식은 단계 B)의 시스템 프롬프트에 규칙 D-1 내지 D-4를 더하고, 사용자 프롬프트 끝에 해당 챌린지의 신호 사전을 붙입니다(`prompts3.py`의 `D_RULES`, `common.py`의 `sigdict_block`).
- 신호 사전(`data/sigdict.json`)은 Lockheed Martin 챌린지 요구사항 문서의 신호 표(Input Scope, Output Scope 표와 4번 챌린지의 정의 표)를 칸 단위로 그대로 옮긴 것입니다. 항목별 선별, 다시 쓰기, 관련도 정렬을 하지 않았습니다. 생성 방법은 `tools/make_sigdict.py`에 있습니다(원문 docx는 이 폴더에 없음).
- 템플릿 단계(stage A)는 `+D` 방식이 기본 방식과 공유합니다(같은 반복에서 같은 템플릿 문장). 따라서 `EARS` 대 `EARS+D`는 같은 템플릿 문장 위의 비교입니다.
- 사전은 FRETish 단계에만 주고 템플릿 단계에는 주지 않습니다.
- 7번(autopilot) 챌린지는 신호 표가 비어 있거나 요구사항 문장이 들어 있어 사전을 만들지 않았고, 이번 시험 항목에서 뺐습니다.
- `+V`, `+R` 계열은 이번에 쓰지 않습니다(사전 효과를 다른 장치와 섞지 않기 위함).

## 3. 범위
- 항목: `data/dict8_items.jsonl` 18개 (7번을 뺀 9개 챌린지에서 파일 순서로 처음 2개씩. 결과를 보고 고르지 않았음).
- 방식 6개: DIRECT, DIRECT+D, MASTeR, MASTeR+D, EARS, EARS+D.
- 반복 2회, 216단위. 호출은 모의 실행 기준 364건(단계 A 72, 단계 B 144, 단계 D 72, 되먹임 76).
- 소요는 약 1에서 2시간(추측입니다), 한도 대기가 더 붙을 수 있습니다.

## 4. 순서

4.1 환경 확인
```bash
pwd                     # /Users 아래여야 함
docker info >/dev/null && docker image ls fret-lab
python3 -c "import fretparse,json;print(json.dumps(fretparse.compile_texts(['when a b shall satisfy c','when a b shall every 5 seconds satisfy c'],'docker',None),indent=1))"
```
첫 문장 `ok: true`, 둘째 `ok: false`가 아니면 원문을 `FRET_NOTES.md`에 적고 멈춥니다.

4.2 동결 확인
```bash
sha256sum -c FROZEN_MANIFEST.sha256        # 모든 줄 OK 여야 함 (__pycache__ 는 제외됨)
sha256sum FROZEN_MANIFEST.sha256 | tee SMOKE_FROZEN.sha256
```
`FROZEN_MANIFEST.sha256` 자체의 기대값: 176b144fe280158e05a4ec4a5aa9c7e912fab067b8e989ccacd12a2f2f16e571
다르면 멈춥니다.

4.3 모의 시험 (한도와 도커를 쓰지 않음)
```bash
python3 -I tools/selftest.py          # SELFTEST_OK
python3 cli.py --selftest             # cli selftest ok
export MOCK_STATE_DIR=/tmp/mock_d8; rm -rf /tmp/mock_d8 results_mock
python3 run_pipeline.py --data data/dict8_items.jsonl --claude-bin ./mock_claude.py --parser mock --results results_mock --reps 1 --limit-items 6 --arms DIRECT DIRECT+D MASTeR MASTeR+D EARS EARS+D | tail -3
python3 tools/dev_record.py results_mock | head -15
rm -rf results_mock
```
통과 기준: 마지막 상태 `finished_all`, 중복 `stage_key` 0.

4.4 본 실행
```bash
mkdir -p results_dict8
nohup caffeinate -i python3 run_pipeline.py --data data/dict8_items.jsonl --results results_dict8 --reps 2 --block 1 --hours 8 \
  --arms DIRECT DIRECT+D MASTeR MASTeR+D EARS EARS+D \
  --model sonnet --cli-extra "--safe-mode --effort medium" > results_dict8/console.log 2>&1 &
```
- 진행 확인: `tail -3 results_dict8/run.log`, `cat results_dict8/run_state.json`.
- 프로세스가 죽거나 한도로 멈추면 같은 명령을 다시 실행합니다. `--reset-clock`은 쓰지 않습니다.
- 종료 상태가 `finished_all` 또는 `stopped_deadline`이면 다음으로 갑니다.

4.5 기록 생성
```bash
python3 tools/dev_record.py results_dict8 > results_dict8/DEV_RECORD.md
python3 tools/dict_usage.py results_dict8 >> results_dict8/DEV_RECORD.md
```
`DEV_RECORD.md` 끝에 덧붙입니다: 시작과 종료 시각, 한도 사건 횟수, `claude --version`, 이 문서에서 벗어난 점과 이유.

## 5. 전달
`results_dict8` 폴더를 zip으로 묶어 사용자에게 전달합니다(`calls.jsonl`, `parser_cache.jsonl`, `run_state.json`, `run.log`, `snapshot/`, `DEV_RECORD.md` 포함). 해석 문장은 쓰지 않습니다. LTL 컴파일과 판정은 전달 후 별도로 합니다.
```bash
zip -r results_dict8.zip results_dict8
```
