# 프롬프트: 비교 가능성 시험 (동결 도구 v1.2.0, 탐색적 보조 실행 021)

아래 전체를 Mac의 LLM 에이전트에게 전달한다. 패키지(`nl2fret_comparability_test_pack.zip`)에는 이 프롬프트, 도구 `nl2fret_tool_v1.2.zip`, 입력 3개(`inputs/`), 기준 해시(`baseline/BASELINE_020_SHA256.txt`)가 들어 있다. 020 실험 폴더(`experiments/020_lm61_main_judge/`)와 `results_main_judge.zip`은 Mac에 이미 있다.

---

## 0. 목적과 전제 (보고서 첫 줄에 그대로 적는다)

이 실행은 본 실험(019)의 판정 결과(020, 모드 anchor)를 본 뒤에 하는 "탐색적 보조 실행"이다. 020의 결과는 사전 정의된 주 결과이고 이 실행으로 바뀌지 않는다. 이 실행의 목적은 판정 쌍의 38.9%가 UND이고 NEITHER의 98.7%가 생성 식과 기준 식의 원자 집합이 달라서 생기는 문제(020 REPORT와 이후 분석)가 변수 이름 대응 규칙 때문인지, 어휘와 무관한 구조 수준에서는 비교가 되는지를 측정하는 것이다.

측정할 질문은 셋이다.
1. 이름 대응 규칙을 바꾸면(모드 free) 어느 정도 비교 가능한 쌍이 늘고 역할이 어떻게 바뀌는가 (상한 측정).
2. 현재 SAME, PROOF, REFUTE가 이름 바꾸기 규칙에 얼마나 의존하는가 (모드 strict, 견고성 점검).
3. 어휘와 무관한 골격(스코프, trigger 대 holding, 타이밍, 응답 형태) 수준에서 생성 문장과 기준이 얼마나 일치하는가.

너는 동결된 판정 도구를 실행하는 에이전트다. 확인하지 못한 것은 "확인하지 못함"으로 적고 추측으로 채우지 마라. 이모지와 em dash를 쓰지 마라. 해석은 쓰지 않는다(표, 정의, 한계만). 어느 방식이 낫다는 판단과 원인 설명을 하지 마라. 정해진 것은 되묻지 말고 따라라.

## 1. 금지 사항
- 도구(`nl2fret_tool_v1.2.zip`의 모든 파일, `bench/`, `judging/`, `judging/legacy/` 포함)를 수정하지 마라. 쓰기 가능한 새 사본을 풀어서 쓰고, `make freeze-check`와 판정 도구의 동결 매니페스트 대조가 실행 전후 모두 OK여야 한다. `--allow-unfrozen`을 쓰지 마라. 모든 새 기록 헤더가 `frozen: true`여야 한다.
- 020의 산출물(`results_main_judge`, `runs/merged` 등)을 수정하거나 덮어쓰지 마라. 읽기만 한다. 새 산출물은 새 폴더 `experiments/021_comparability_test/`에만 쓴다.
- 입력 파일을 수정하거나 단위, 문장을 제외하지 마라.
- 결과를 보고 모드, cap, timeout, 규칙을 바꾸지 마라. 사용할 설정은 아래에 정해져 있다(cap 128, timeout 120초, NuSMV 엔진).
- 도구 안의 `legacy/` 코드(judge2, judge4, judge5)는 읽고 가져다 쓰기만 한다(import). 수정 금지.
- git 명령 금지.

## 2. 사전 확인 (판정 기록을 열어 보기 전)
1. 입력 3개의 sha256을 `inputs/SHA256SUMS`와 대조한다 (units `2a130c99...`, ltl `52df6740...`, rlz `5602692b...`). 도구 zip sha256은 `430ff36588f1559180a75472f7a08b15061c330e67a84f5fa250324bbabb367e`다. 020의 합친 `judge_records.jsonl`과 `aggregate.json`이 `baseline/BASELINE_020_SHA256.txt`와 같은지 확인한다(다르면 보고하고 중단).
2. 새 zip 사본을 풀고 `make freeze-check`, 판정 매니페스트 해시(기대 `1fda2c1982c14c7ae7363c8c5ced72c11d0019afe9804a5693a35cae15aa154b`), 파일 해시 목록을 기록한다.
3. 환경은 020과 같게 준비한다: `experiments/020_lm61_main_judge/notes/OPERATIONS.md`, `scripts/shard_units.py`, `merge_judge.py`, `launch.sh`, `container.sh`를 읽고 같은 방식(NuSMV 래퍼, 컨테이너 `--cpus=1`, 컨테이너 안 timeout 125초, `nice`, `caffeinate`, 4분할 라운드로빈)을 쓴다. 020 폴더나 스크립트가 없으면 "확인하지 못함"으로 보고하고 중단한다(새로 만들어 쓰지 마라).
4. `make test`, `make selfcheck`(NuSMV, 5쌍 PASS)를 실행한다. 실패하면 중단한다.
5. `PRE_RUN_DEFINITIONS_021.md`를 쓴다. 내용은 3절과 4절의 정의를 그대로 담는다. 이 파일과 4절 스크립트의 sha256을 기록하고 고정한다. 새 모드의 판정 기록을 열어 보기 전에 고정해야 한다.

## 3. 단계 A: 이름 대응 모드 (도구 코드 변경 없음)

`make judge`는 `--mode`를 받지 않으므로 `judging/`에서 모듈을 직접 호출한다.
`python3 -m nl2fret_judge judge --engine nusmv --nusmv <래퍼> --out <OUT> --units <units> --ltl <ltl> --rlz <rlz> --mode <모드>` (`--cap 128`은 기본값이므로 명시해도 같다.)

도구 코드의 모드 설명(`judging/nl2fret_judge/align.py`):
- anchor: 이름과 타입이 기준에 있는 생성 변수는 그대로 두고 나머지만 단사 대응. 020의 주 설정.
- lex, strict: anchor에 어휘 제약을 더함. 더 엄격한 쪽.
- free: 모든 생성 변수를 단사 대응(고정 없음). 상한. 단 코드상 생성 변수 수가 기준보다 크거나 기준이 3개 이상 많으면 UND가 된다.

실행 순서와 규모:
1. `free`: 전체 입력(단위 3387, 판정 쌍 3999 기대)을 020과 같은 4분할로 실행한다. 분할마다 별도 OUT과 별도 NuSMV 컨테이너를 쓴다. 중단되면 같은 명령으로 재개하고 헤더가 처음 값임을 적는다.
2. `strict`: 같은 방식으로 전체 입력을 실행한다.
3. 음성 대조: 단위 300개를 시드 `20261112`로 무작위 추출하고(재현 가능한 방법으로 추출 규칙을 파일에 적는다), 각 단위의 `item`을 다른 항목 id로 바꾼 `units_control.json`을 만든다(문장 `texts`는 그대로, 항목마다 다른 항목이 되도록 고정 규칙으로). 이 입력에서 `anchor`와 `free` 모드로 판정한다. 기준이 틀린 짝이라 SAME이 나오면 그것이 가짜 일치다. 가짜 일치율을 모드별로 보고한다. 이 대조는 도구의 실 입력 형식과 같으므로 `--ltl`, `--rlz`는 원래 파일을 그대로 쓴다(문장 키로만 읽힌다. 읽지 못하는 항목이 있으면 그 이유를 적고 대조에서 그 단위를 빼되 몇 개인지 보고한다).
4. 각 모드의 4분할 기록을 `pair_id` 기준으로 합치고(중복 0 확인), `make aggregate`에 해당하는 `aggregate` 명령을 합친 폴더에서 실행한다. 020의 합치는 절차(`merge_judge.py`)를 그대로 따른다.

판정 쌍 수는 모드마다 020과 같은 3999여야 한다. 다르면 원인 목록을 적는다.

## 4. 단계 B: 어휘와 무관한 골격 비교 (도구 밖 스크립트)

`judging/legacy/judge5.py`의 `skeleton_compare(gen_pt, ref_pt)`를 읽기 전용으로 가져다 쓴다. 이 함수의 정의(도구 코드의 설명): 시간 연산자가 없는 가장 큰 부분식을 하나의 불투명한 원자로 바꾸고, 남은 골격(스코프, trigger 대 holding, 타이밍, 응답 형태)을 `judge4.compare`로 비교한다(유한 구간 z3). 골격 판정은 "짝지어진 불투명 원자가 같은 상태 술어를 뜻한다는 전제에서" 성립한다. 이 전제는 검증되지 않는다. 표 주석에 반드시 쓴다.

스크립트 `scripts/skeleton_eval.py`:
1. 입력은 `inputs/units.json`, `inputs/fret_ltl_gen.jsonl`과 도구의 기준 파일(`data/reference/lm_reference_with_ltl.jsonl`)이다. 020과 같은 쌍 집합(`parser_ok`이고 LTL이 있는 문장, `pair_id` 형식 `item|arm|rep|문장인덱스`)을 쓴다. 기준 쪽은 도구의 `best_over_references`가 반복하는 것과 같은 기준 부분, 버전 전체를 쓴다(`judge.py`를 읽고 같은 규칙으로 구현한다. 다르게 하면 그 차이를 보고).
2. 기준 부분마다 `skeleton_compare`를 실행하고, 도구의 `RANK`와 같은 순서(같음, 더 엄격 또는 더 느슨, 포함 관계 없음)로 가장 좋은 것을 쌍의 골격 결과로 쓴다. 클래스 이름과 순서는 `judge2.py`, `judge4.py`, `judge5.py`를 읽고 표로 정의 문서에 적는다(예: equivalent*는 골격 SAME, stronger_under_renaming과 generated_stronger는 골격 PROOF, weaker_under_renaming과 generated_weaker는 골격 REFUTE, incomparable*는 골격 NEITHER, atomization_mismatch와 unsupported와 시간 초과는 골격 미판정). 방향(stronger가 PROOF인지)은 코드의 정의를 읽고 확인해서 적고, 확인하지 못하면 "확인하지 못함"으로 둔다.
3. 출력은 `skeleton_records.jsonl`(쌍마다 한 줄: pair_id, 골격 클래스, ngen, nref, gen_skel, ref_skel, 선택된 기준 부분)이다.
4. 단위 결과는 도구의 관대한 규칙과 같게 정의한다: 단위 안 가장 좋은 문장의 골격 결과. success = 골격 SAME 또는 PROOF, partial = 골격 REFUTE, failure = 골격 NEITHER, 파서 거부, 문장 없음, unjudged = 골격 미판정. 분모는 항상 전체 단위(3387, 방식별 183 또는 153)다. 실현가능성은 이 지표에 넣지 않는다(구조만). 판정된 단위만 분모인 값을 병기한다.
5. 같은 문장이 여러 단위에서 다른 골격 결과를 받았는지 점검한다(결정성, 0이어야 함).

## 5. 단계 C: 집계 (판정 기록은 읽기만, 스크립트는 고정 후 사용)

표 1. 모드별 쌍 역할 분포(anchor는 020 기록을 그대로 사용, free, strict, 골격). 분모는 전체 쌍 3999이고 UND, N/M 사유별 개수를 넣는다.
표 2. 전이 행렬(행: anchor 역할, 열: free 역할 / strict 역할). 특히 UND에서 비교 가능한 역할로 바뀐 쌍 수, NEITHER에서 SAME, PROOF, REFUTE로 바뀐 쌍 수, SAME에서 다른 역할로 바뀐 쌍 수.
표 3. 음성 대조의 역할 분포(모드별). SAME 개수와 비율이 가짜 일치율이다.
표 4. 방식별 단위 성공률: 도구의 `aggregate`(관대한 규칙)를 anchor(020), free, strict에 대해, 그리고 "anchor와 free 중 좋은 쪽"(상한, 쌍 단위로 RANK가 더 좋은 쪽을 택해 도구 밖 스크립트로 계산)에 대해 나란히. 방식 19개 전부, 분모 전체와 판정된 단위만 분모인 값을 같이.
표 5. 방식별 골격 단위 결과(success, partial, failure, unjudged, 성공률). 같은 표를 `n_parts` = 1과 2 이상으로 나누어, 그리고 stratum(conditional, invariant, timed, scoped)별로. 부분이 여러 개인 항목에서 "어느 한 문장이라도 일치"가 모든 부분을 만족한다는 뜻이 아님을 주석에 쓴다.
표 6. 골격 NEITHER 쌍 중 trigger 대 holding 패턴(020 `rq_aggregate.py`의 RQ1c 정의와 같은 규칙, 해당 코드가 있으면 가져다 쓰고 없으면 정의를 적고 구현)의 비율.
표 7. 골격 결과와 anchor 역할의 교차표(3999쌍).
표 8. 방식 쌍 비교는 020과 같은 항목 단위 부트스트랩(시드 `20261112`와 비교 이름으로 고정, 5000회, 항목 안에서 반복 평균, 95% 구간, 020의 `scripts/rq_aggregate.py`의 함수를 읽기 전용으로 가져다 쓴다. 가져올 수 없으면 같은 규칙으로 구현하고 그 사실을 적는다)를 골격 단위 성공률에 적용한다. 비교 목록은 020의 RQ2c 표와 같다(DIRECT 대비 각 방식, PARA 대비 각 템플릿, +R2, +V, +D 대 기본). 모든 방식이 판정된 항목만 쓰는 짝 비교는 별도 표로 하고 남은 항목 수를 적는다.

해석은 쓰지 않는다. 한계는 다음을 반드시 적는다: free는 상한이고 가짜 일치 가능성이 있다(표 3으로 정량화), 골격 결과는 원자 내용이 같다는 검증되지 않은 전제 위에 있다, 골격 비교는 유한 구간 z3이고 도구의 NuSMV 판정과 엔진이 다르다, 61개 항목은 사전 관찰된 자료다, 기준은 NASA FRETish 하나다.

## 6. 점검
- 모든 새 헤더 `frozen: true`, `code_tree_sha256`이 매니페스트 해시와 같음, 모드가 각각 free, strict, anchor(대조)로 기록됨.
- 쌍 수 3999(모드마다), 중복 `pair_id` 0, 같은 (항목, 문장)의 판정 불일치 0(모드마다).
- 020 anchor 기록과 이번 anchor 대조(단계 3의 대조)는 다른 입력이므로 비교하지 않는다. 대신 free, strict 실행에서 anchor와 같은 이름 규칙으로 정의되는 쌍(이름이 모두 같은 경우, 즉 대응이 항등인 쌍)의 역할이 020과 같은지 샘플 점검하고 결과를 적는다.
- 실행 전후 `make freeze-check`와 판정 매니페스트 OK.
- 소요 시간(분할별, 모드별)과 NuSMV timeout 쌍 수를 적는다.

## 7. 최종 보고
1. 첫 줄: 이 실행이 020의 anchor 결과를 본 뒤의 탐색적 보조 실행임을 명시.
2. 환경, 분할 방식, 소요 시간.
3. 사전 확인과 점검 결과(6절).
4. 표 1부터 8(5절)과 정의 문서의 해시.
5. 이상 징후 목록(결정성 불일치, 기대와 다른 수, 실패한 부분, 가짜 일치 사례 5개 이상의 원문).
6. 확인하지 못한 항목과 이유.
7. 산출물 경로와 sha256: 합친 `judge_records.jsonl`(free, strict, 대조), `aggregate.json`들, `skeleton_records.jsonl`, `PRE_RUN_DEFINITIONS_021.md`, 스크립트, 표 파일(`tables_021.md`와 `.json`).
8. 사용자가 결정할 것(해석 없이 선택지만).
