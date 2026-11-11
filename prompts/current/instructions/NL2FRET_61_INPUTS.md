# 프롬프트: 본 실험 입력 3개 만들기 (61개 항목, 동결 도구용)

아래 전체를 Mac의 LLM 에이전트에게 전달한다. 도구(`nl2fret_tool_v1.2.zip`)는 동결 상태이며 이 작업에서 수정하지 않는다.

---

너는 61개 Lockheed Martin 항목의 bench 실행 결과를 동결된 판정 도구의 입력 형식으로 변환하는 에이전트다. 확인하지 못한 것은 "확인하지 못함"으로 적고, 추측으로 채우지 마라. 이모지와 em dash는 쓰지 마라. 코드에 대한 사실 주장은 쓰기 전에 코드에서 확인해라.

## 금지 사항
- `nl2fret_tool_v1.2.zip` 안의 어떤 파일도 수정하지 마라 (`JUDGE_FROZEN_MANIFEST.sha256`, `make freeze-check` 전후 OK).
- 단위, 문장, 항목을 임의로 제외하거나 값을 보정하지 마라. 변환은 형식 변환과 키 이름 맞춤만 한다.
- 변환 스크립트는 도구 밖(실험 폴더의 `scripts/`)에 두고, 실행 전에 스크립트와 정의 문서의 해시를 기록해라.
- git 명령 금지.

## 목표 형식 (동결된 도구가 읽는 형식)
도구 코드(`judging/nl2fret_judge/units.py`)를 읽고 아래를 먼저 확인해라. 차이가 있으면 코드가 우선이다.
1. `units.json`: `{"units": [{"item", "arm", "rep", "status", "texts": [...], "stratum"(선택)}]}`. `texts`는 그 단위의 최종 FRETish 문장 목록.
2. `fret_ltl_gen.jsonl`: 문장별 한 줄. 키 `sentence`, `parser_ok`, `ltl_pt`, `ltl_ft`.
3. `fret_realizability_gen.jsonl`: 문장별 한 줄. 키 `item_id`, `arm`, `rep`, `sentence`, `result`. `rep`가 null인 줄(기준 문장)은 도구가 읽지 못하므로 이 파일에 넣지 않는다.
`data/example_*_v8.*` 파일이 형식 예시이고, v8 예시를 만든 변환 코드의 흔적은 아래 2번에서 찾는다.

## 원천
- 61개 항목 결과는 `experiments/nl7/results_lm`(이전 확인 결과)에 bench 고유 형식으로 있다. 다른 위치에 더 적합한 최종 결과가 있는지(가장 최근 완료된 61개 항목 전체 실행인지) 폴더 이름, 수정 시각, 로그로 확인하고 근거를 적어라. 확신이 없으면 후보를 표로 보고하고 중단해라 (임의로 고르지 마라).
- 단위 구성(item x arm x rep)과 "최종 문장"의 정의는 `bench/units3.py`의 `derive`와 `variant(rec, "vf")`를 읽어서 확인해라. v8 예시가 어떤 변형(`vf` 등)을 최종 문장으로 썼는지는 `rlz_dict8.py`(저장소 안에 있으면)나 `data/example_units_v8.json`과 원천 v8 결과를 대조해서 확인해라. 같은 규칙을 61개 항목 데이터에 적용한다.
- 문장 키의 `#v0|vn|vf` 같은 접미사가 무엇인지는 코드에서 확인하고, 접미사를 떼어 문장 원문으로 만들 때의 규칙을 정의 문서에 적어라.

## 단계
1. 원천 확인: 위 원천 후보와 최종 선택 근거를 보고한다. 단위 수(항목 x arm x rep)를 bench의 자체 집계 결과(예: score 출력)와 대조해 일치하는지 확인한다.
2. 정의 문서 작성: 변환 규칙(어떤 변형을 최종 문장으로 쓰는지, 접미사 처리, status 값, 기준 문장 줄 제외, `stratum` 매핑 출처)을 `PRE_RUN_DEFINITIONS.md`에 쓰고 해시를 고정한다.
3. 변환 스크립트 작성과 실행. 먼저 v8 예시 원천에 같은 스크립트를 돌려 `data/example_*_v8.*` 파일과 바이트 단위(또는 필드 단위)로 같은 결과가 나오는지 확인한다. 같지 않으면 차이를 보고하고 본 데이터 변환으로 넘어가지 마라 (이것이 변환 규칙이 옳다는 증거다).
4. 본 데이터 변환 후 검증:
   - 단위 수, 항목 수(61 기대), arm 목록, 반복(rep) 수, 문장 수
   - 모든 단위가 `units.json`에 있는지 (`texts`가 빈 단위, 파서 거부 단위 포함)
   - `fret_ltl_gen.jsonl`에 `units.json`의 모든 문장이 있는지, 없는 문장 수
   - `fret_realizability_gen.jsonl`의 문장 대응 누락 수 (도구는 누락을 `not_run`으로 보므로 누락은 보고한다)
   - 도구로 `units.load_units`가 오류 없이 읽는지 (읽기 전용 호출)
   - `stratum`: 항목별 계층 정보가 저장소에 있으면(예: 항목 메타데이터) 매핑 출처를 적고 `units.json`에 넣는다. 없으면 `stratum`을 넣지 않고 "없음"으로 보고한다 (도구는 `stratum: null` 한 줄로 집계한다).
5. 소규모 시험: 이 입력에서 항목 2개(첫 항목과 참조 부분이 가장 많은 항목)만 담은 부분 입력을 별도 폴더에 만들어 `make selfcheck`, `make judge`(z3 엔진으로도 가능)가 오류 없이 도는지 확인한다. 부분 입력은 본 입력과 파일 이름을 구분해라.


## 데이터 분리 검증 (본 실험 = 록히드마틴 61개 항목만)
연구 설계: 규칙과 프롬프트 개발에는 개발셋(`data/dev_items.jsonl`, NASA technical report 및 타 연구 94개 항목: 출처 CP22, TC4, WF23, IR20, PLC23, MLV, DRONE, UC69)만 쓰고, 시험셋은 NASA Lockheed Martin 61개 항목이다. 입력 3개가 이를 어기지 않았음을 아래로 확인하고 보고해라.
1. `units.json`의 모든 항목 id가 `LM-`로 시작하고 서로 다른 항목이 정확히 61개인지.
2. 개발셋 항목 id(`N-`, `X-`로 시작)가 하나도 없는지. 개발셋 파일이 저장소에 있으면 id 교집합과, 원문 자연어(공백과 대소문자 정규화 후)의 완전 일치 교집합이 0인지. 0이 아니면 목록을 보고한다.
3. 원천 폴더가 개발 실행(`results_dev`) 또는 사전 점검(`results_pre`, `results_mock`)이 아니라 61개 항목 본 실행임을 폴더 이름과 `run_state.json`, 항목 목록으로 확인.
4. 사전 점검, 모의, 개발 실행의 문장이 `fret_ltl_gen.jsonl`에 섞여 있지 않은지 (문장 키가 `units.json`에 없는 줄의 수).

## 최종 보고
1. 원천 위치와 선택 근거 (후보 표)
2. 변환 규칙 요약과 `PRE_RUN_DEFINITIONS.md`의 해시
3. v8 예시 재현 결과 (같음 또는 차이 목록)
4. 본 데이터 통계표 (단위, 항목, arm, rep, 문장, 누락, `stratum` 유무)
5. 소규모 시험 결과
6. 산출물 경로와 sha256: `units.json`, `fret_ltl_gen.jsonl`, `fret_realizability_gen.jsonl`
7. 데이터 분리 검증 결과 (위 4항목)
8. 확인하지 못한 항목과 이유, 사용자가 결정해야 할 것