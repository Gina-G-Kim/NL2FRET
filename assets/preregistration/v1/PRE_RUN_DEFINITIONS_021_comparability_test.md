# PRE_RUN_DEFINITIONS_021: 비교 가능성 시험 (동결 도구 v1.2.0, 탐색적 보조 실행 021), 2026-11-12

이 문서는 새 모드(free, strict)와 음성 대조의 판정 기록, 골격 비교 기록을 열어 보기 전에 쓰고 해시를 고정한다(`notes/PIN_pin1.sha256`). 고정 뒤 정의를 바꾸지 않는다. 바꿔야 하면 멈추고 사용자에게 알린다. 집계와 점검 스크립트(`tables_021.py`, `checks_021.py`, `post_run.sh`)는 판정이 도는 동안 합성 예시로 시험해서 만들고, 새 모드의 기록을 읽기 전에 두 번째 고정(`notes/PIN_pin2.sha256`)을 한다.

## 0. 목적과 전제 (보고서 첫 줄에 그대로 적는다)

이 실행은 본 실험(019)의 판정 결과(020, 모드 anchor)를 본 뒤에 하는 "탐색적 보조 실행"이다. 020의 결과는 사전 정의된 주 결과이고 이 실행으로 바뀌지 않는다. 목적은 판정 쌍의 38.9%가 UND이고 NEITHER의 98.7%가 생성 식과 기준 식의 원자 집합이 달라서 생기는 문제가 변수 이름 대응 규칙 때문인지, 어휘와 무관한 구조 수준에서는 비교가 되는지를 측정하는 것이다. 질문은 셋이다. (1) 이름 대응 규칙을 바꾸면(모드 free) 비교 가능한 쌍이 얼마나 늘고 역할이 어떻게 바뀌는가(상한). (2) 현재 SAME, PROOF, REFUTE가 이름 바꾸기 규칙에 얼마나 의존하는가(모드 strict, 견고성). (3) 어휘와 무관한 골격 수준에서 생성 문장과 기준이 얼마나 일치하는가.

## 1. 범위와 원칙

- 도구(`nl2fret_tool_v1.2.zip`의 모든 파일)는 수정하지 않는다. 쓰기 가능한 새 사본(`bench/nl2fret_tool/`)에서 실행하고 읽기 전용 원본 사본(`bench/pristine/`)과 대조한다. `make freeze-check`(bench 38개 파일, 매니페스트 `176b144f...e571`)와 판정 매니페스트(18개 파일, `1fda2c19...a154b`)는 실행 전후 모두 OK여야 한다. `--allow-unfrozen`을 쓰지 않는다. 모든 새 기록 헤더가 `frozen: true`여야 한다.
- 020의 산출물(`experiments/020_lm61_main_judge/`)은 읽기만 한다. 새 산출물은 `experiments/021_comparability_test/`에만 쓴다. 020의 스크립트 중 `shard_units.py`, `merge_judge.py`, `launch.sh`, `cleanenv.sh`, `bin/NuSMV`, `judge_checks.py`는 바이트 그대로 복사해 썼고(`notes/REUSED_FROM_020.txt`) `container.sh`는 컨테이너 이름 접두사만 `nusmv-021-`로 바꿨다. `scripts/rq_aggregate.py`는 읽기 전용으로 import한다(표 8의 부트스트랩, 비교 목록).
- 입력 3개(`units.json`, `fret_ltl_gen.jsonl`, `fret_realizability_gen.jsonl`)는 고치지 않고 단위와 문장을 빼지 않는다. 결과를 보고 모드, cap, timeout, 규칙을 바꾸지 않는다. 설정: NuSMV 엔진, cap 128, timeout 120초(모두 도구 기본값), 컨테이너 안 timeout 125초, 컨테이너 `--cpus=1`, `nice -n 10`, `caffeinate -i`, 4분할.
- 해석 문장(의미, 방식 우열, 원인 설명)은 쓰지 않는다. 표, 정의, 한계만 쓴다.
- git 명령을 쓰지 않는다. 계정 이메일은 어디에도 쓰지 않는다.

## 2. 단계 A: 판정 실행의 정의

모드(도구 코드 `judging/nl2fret_judge/align.py`를 읽고 적는다).

| 모드 | 정의 | UND가 되는 경우 (사유는 모두 `atomization_mismatch`) |
|---|---|---|
| anchor | 이름과 타입이 기준에 있는 생성 변수는 그대로(항등), 나머지만 같은 타입의 안 쓰인 기준 변수로 단사 대응. 020의 주 설정 | 안 맞춘 생성 변수가 안 맞춘 기준 변수보다 많음, 타입이 맞는 후보가 없음, 대응 후보가 120개 초과 |
| strict | anchor에 어휘 제약: 상수처럼 쓰인 이름은 어휘가 겹치는 기준 상수로만, 상수가 아닌 안 맞춘 변수는 대응하지 않음 | anchor의 경우, 어휘로 지지되는 대응이 없음(상수가 아닌 안 맞춘 생성 변수가 하나라도 있으면 UND) |
| free | 모든 생성 변수를 같은 타입의 기준 변수에 단사 대응(고정 없음). 상한 | 생성 변수가 기준 변수보다 많음, 기준이 생성보다 3개 이상 많음, 타입이 맞는 후보가 없음, 대응 후보가 120개 초과 |

생성과 기준의 변수 이름과 타입 집합이 같으면 세 모드 모두 항등 대응 하나만 후보다(코드 `candidates`의 첫 분기). 판정 쌍마다 도구가 기준 부분과 버전 전체를 차례로 시도하고(`best_over_references`, 첫 SAME에서 멈춤, 순위 SAME < PROOF = REFUTE < NEITHER < N/M < UND, 같으면 먼저 본 것) 후보 대응마다 sound와 compl 질의를 NuSMV로 돌린다.

실행 (1건 = 4분할 x 실행). 호출은 `scripts/run_judge_shard.sh`가 지시문대로 모듈을 직접 부른다: `cd judging && python -m nl2fret_judge judge --engine nusmv --nusmv <래퍼> --out ../runs/<태그>/shard<k> --units <분할 입력> --ltl ../inputs/fret_ltl_gen.jsonl --rlz ../inputs/fret_realizability_gen.jsonl --mode <모드> --cap 128` (timeout 120초는 기본값).

| 태그 | 모드 | 입력 | 기대 판정 쌍 |
|---|---|---|---|
| free | free | 전체 `units.json`(단위 3387)의 4분할(020과 같은 분할 파일, 바이트 같음 확인) | 3999 (분할 1031, 851, 1028, 1089) |
| strict | strict | 같음 | 3999 |
| ctrl_anchor | anchor | 음성 대조 입력 `units_control.json`(단위 300)의 4분할 | 339 (분할 88, 89, 83, 79) |
| ctrl_free | free | 같음 | 339 |

- 분할은 `shard_units.py`(항목 id 정렬 후 라운드로빈, 항목 통째로)로 만든다. 한 번에 도는 컨테이너는 4개 이하다(`run_queue.sh`의 `xargs -P 4`, VM CPU 4개): 컨테이너가 CPU를 나눠 쓰면 질의 시간이 늘어 120초 제한이 가짜 시간 초과가 될 수 있기 때문이다. 작업 순서: free 분할 1, 3, 2, 4, strict 분할 1, 3, 2, 4, ctrl_anchor 분할 1부터 4, ctrl_free 분할 1부터 4(앞 순서는 020의 분할 소요에서 긴 것부터).
- 중단되면 같은 대기열 명령으로 재개하고(기록된 쌍은 건너뜀) 헤더가 처음 값임을 적는다.
- 분할 4개의 기록은 020의 `merge_judge.py`(원본 줄 그대로, 단위 순서와 문장 인덱스 순서)로 합친다. 중복 `pair_id`가 있거나 단위에 없는 기록이 있거나 헤더가 `frozen: true`가 아니거나 `code_tree_sha256`이 `1fda2c19...`가 아니면 합치지 않고 보고한다. 합친 폴더에서 도구의 `aggregate` 명령을 실행한다(`--units`, `--ltl`, `--rlz`는 그 실행의 입력).
- 쌍 수는 위 표의 기대와 같아야 한다. 다르면 원인 목록을 적는다. 시간 초과 쌍은 N/M(timeout)으로 두고 설정을 바꿔 다시 돌리지 않는다.

## 3. 음성 대조의 정의 (`scripts/make_control_units.py`)

- 추출: `units.json`의 단위를 파일 순서대로 놓고 `random.Random(20261112).random()`을 단위마다 하나씩 받아(파이썬 문서가 버전 사이에 같게 유지한다고 보장하는 난수열) 가장 작은 300개를 뽑아 파일 순서로 쓴다. 추출 결과와 규칙은 `bench/nl2fret_tool/inputs/control/control_sampling.json`에 있다.
- 항목 바꾸기: 항목 id 61개를 오름차순으로 0부터 60까지 번호를 매겨 번호 i의 항목을 번호 (i + 31) mod 61의 항목으로 바꾼다(31은 61의 배수가 아니므로 모든 항목이 다른 항목이 되고, 일대일이라 (항목, 방식, 반복) 키가 유일하다). 문장(`texts`), 방식, 반복, status, stratum은 그대로다. `--ltl`, `--rlz`는 원래 파일을 쓴다(LTL은 문장 키, realizability는 (항목, 방식, 반복, 문장) 키로 읽히므로 대조 단위는 `not_run`이 되며 역할에는 영향이 없다).
- 가짜 일치 = 대조 판정 쌍 중 역할 SAME. 가짜 일치율 = SAME 쌍 수 / 대조 판정 쌍 수(분모는 모든 대조 쌍, UND와 N/M 포함). 같은 방식으로 SAME 또는 PROOF, SAME 또는 PROOF 또는 REFUTE의 비율도 적는다. 가짜 일치 사례: 모드별로 SAME 쌍 전부(모드마다 최대 20개)의 원문(생성 문장, 바뀐 항목, 기준 부분 id, 기준 문장 FRETish)을 적는다. 두 모드의 SAME 쌍 수의 합이 5 미만이면 같은 모드의 PROOF 쌍 중 앞에서부터(대조 입력 순서) 5개까지 더해 "PROOF 사례"로 따로 표시한다.

## 4. 단계 B: 골격 비교의 정의 (`scripts/skeleton_eval.py`)

- 함수: `judging/legacy/judge5.py`의 `skeleton_compare(gen_pt, ref_pt)`를 읽기 전용으로 import한다. 시간 연산자가 없는 가장 큰 부분식을 불투명한 원자 하나로 바꾸고(부정은 원자 밖에 둠) 남은 골격(스코프, trigger 대 holding, 타이밍, 응답 형태)을 `judge4.compare`로 비교한다(유한 구간 z3, 호라이즌은 기본 8이고 시간 창이 크면 더 커지며 시간 연산자가 전혀 없으면 4, 대응 후보 최대 120개, z3 시간 제한 4000ms 또는 후보가 여럿이면 800ms). 생성 골격의 원자 이름을 `g<n>`으로 바꿔 기준 골격의 원자(`s<n>`)와 겹치지 않게 하므로 항상 단사 대응 탐색(free와 같은 규칙: 생성 원자가 기준 원자보다 많거나 기준이 3개 이상 많으면 `atomization_mismatch`)을 한다. 골격 판정은 "짝지어진 불투명 원자가 같은 상태 술어를 뜻한다는 전제에서" 성립하며 이 전제는 검증되지 않는다.
- 쌍 집합: 020과 같다(`parser_ok`이고 `ltl_pt`가 있는 문장, `pair_id` = `항목|방식|반복|문장 인덱스`, 기대 3999쌍). 기준 쪽은 도구의 `units.load_reference`가 돌려주는 그 항목의 모든 부분과 버전(`data/reference/lm_reference_with_ltl.jsonl`, 같은 순서)을 `judge.best_over_references`와 같은 규칙(순위, 첫 SAME에서 멈춤, 같으면 먼저 본 것)으로 쓴다. 이 규칙과 다른 점은 없다(생성과 기준 식은 도구처럼 `clean_markup`을 거치지 않고 저장된 값 그대로 `skeleton_compare`에 넘긴다. `judge2.prep`이 `<b>`, `<i>` 태그를 스스로 벗긴다). 캐시 없이 쌍마다 다시 계산한다(같은 문장이 여러 단위에서 같은 결과를 받는지가 결정성 점검이다).
- 클래스 대응(방향은 `judge4.py`와 `judge.py`를 읽고 확인했다: MISS = 생성이 참이고 기준이 거짓인 흔적이 있음 = 생성이 더 느슨함(weaker), ALARM = 기준이 참이고 생성이 거짓인 흔적이 있음 = 생성이 더 엄격함(stronger). 도구 역할은 sound = 기준 → 생성이 항상 참 = ALARM 없음, compl = 생성 → 기준이 항상 참 = MISS 없음, PROOF = compl만 참(ALARM만 있음), REFUTE = sound만 참(MISS만 있음)):

| `judge4.compare`의 클래스 | 골격 역할 | 순위 | 의미 |
|---|---|---|---|
| `equivalent_bounded`, `equivalent_under_renaming` | SAME | 0 | MISS 없음, ALARM 없음 |
| `stronger_under_renaming`, `generated_stronger` | PROOF | 1 | ALARM만 있음(생성이 더 엄격) |
| `weaker_under_renaming`, `generated_weaker` | REFUTE | 1 | MISS만 있음(생성이 더 느슨) |
| `incomparable_under_renaming`, `incomparable` | NEITHER | 2 | MISS와 ALARM 모두 있음 |
| `unsupported` (연산자, 구문 오류, 솔버 unknown(시간 초과), 예외) | 골격 미판정(N/M 쪽) | 3 | 사유: `solver_unknown`(상세에 "solver unknown"이 있음) 또는 `unsupported` |
| `atomization_mismatch` | 골격 미판정(UND 쪽) | 4 | 사유: `atomization_mismatch` |

`under_renaming` 접미사는 최선의 대응이 항등이 아닐 때 붙는다. 알 수 없는 클래스 값은 미판정(N/M 쪽)으로 센다.
- 쌍의 골격 결과 = 기준 부분 전체에서 가장 좋은 것(위 순위). 출력 `skeleton_records.jsonl`: `pair_id`, `item`, `arm`, `rep`, `sentence_index`, `cls`(선택된 클래스), `skel_role`, `reason`, `detail`, `ngen`, `nref`, `gen_skel`, `ref_skel`, `reference_part`(선택된 기준 부분), `n_trials`, `trial_classes`, `elapsed_sec`.
- 단위 결과(도구의 관대한 규칙과 같음): 문장 클래스 = 골격 SAME 또는 PROOF는 success, REFUTE는 partial, NEITHER는 failure, 미판정은 unjudged, 파서 거부(공식 파서 거부 또는 `ltl_pt` 없음)는 failure. 단위 결과 = 도구의 `aggregate.unit_outcome`(success, partial, failure 순으로 있는 첫 것, 모두 unjudged면 unjudged, 문장이 없으면 failure). 분모는 항상 전체 단위(3387, 방식별 183 또는 153)다. 실현가능성은 넣지 않는다(구조만). "판정된 단위만 분모"인 값은 unjudged가 아닌 단위만의 비율이다.
- 결정성: 같은 (항목, 문장)이 여러 단위에서 다른 골격 결과(`skel_role`, `cls`)를 받은 것의 수(0이어야 하며 아니면 전부 보고).

## 5. 단계 C: 집계의 정의 (`scripts/tables_021.py`, 판정 기록은 읽기만)

공통: 쌍 라벨 = N/M(`nm` 참)이면 "N/M", 아니면 `role`(SAME, PROOF, REFUTE, NEITHER, UND). 사유: UND는 `und_reason`, N/M은 `nm_reason`. UND의 상세 분류는 `nm_detail.message`의 앞부분으로 한다(`gen vars`로 시작 = 생성 변수가 기준보다 많음(free), `reference has` = 기준이 3개 이상 많음(free), `unmatched gen vars` = 안 맞춘 생성 변수가 더 많음(anchor, strict), `type` = 타입 후보 없음, `too many renamings` = 후보 120개 초과, `no lexically supported counterpart` = 어휘 대응 없음(strict), `no injective renaming candidate` = 단사 후보 없음, 그 밖은 `other`). 020 anchor 기록은 `experiments/020_lm61_main_judge/bench/nl2fret_tool/runs/merged/judge_records.jsonl`(sha256 `221e79ed...`)을 읽기만 한다. 방식 순서와 비교 목록은 020의 `rq_aggregate.py`(`ARM_ORDER`, `comparisons`)를 따른다. 항목 구분(`n_parts`)은 도구의 기준 파일(`data/reference/lm_reference_with_ltl.jsonl`)의 `n_parts`(1: 51개 항목, 2 이상: 10개 항목), stratum은 `units.json`의 `stratum`이다. 소수는 반올림하며 분모는 항상 적는다.

- **표 1. 모드별 쌍 역할 분포.** 열: anchor(020), free, strict, 골격(역할은 4절의 골격 역할). 행: SAME, PROOF, REFUTE, NEITHER, UND(합과 사유별, UND 상세), N/M(합과 사유별), 합계. 분모는 전체 쌍 3999이다. 골격의 UND와 N/M은 4절의 미판정(UND 쪽, N/M 쪽)이며 사유는 `atomization_mismatch`, `solver_unknown`, `unsupported`다.
- **표 2. 전이 행렬.** 행은 anchor 역할(6개 라벨), 열은 free 역할, strict 역할(별도 행렬 둘). 쌍은 `pair_id`로 짝짓는다. 따로 적는 수: UND에서 비교 가능한 역할(SAME, PROOF, REFUTE, NEITHER)로 바뀐 쌍 수, NEITHER에서 SAME, PROOF, REFUTE로 바뀐 쌍 수, SAME에서 다른 역할로 바뀐 쌍 수(PROOF, REFUTE에서 다른 역할로 바뀐 쌍 수도 함께).
- **표 3. 음성 대조.** 모드별(ctrl_anchor, ctrl_free)로 쌍 수, 역할 분포(사유 포함), 가짜 일치율(3절), 그리고 3절의 가짜 일치 사례 원문. 대조 단위 수, 판정 쌍이 있는 단위 수.
- **표 4. 방식별 단위 성공률.** 도구의 `aggregate`(관대한 규칙: 단위 안 가장 좋은 문장, success = SAME 또는 PROOF이면서 같은 문장이 realizable)를 anchor(020), free, strict, 그리고 "anchor와 free 중 좋은 쪽"에 대해 나란히. 좋은 쪽 = 쌍마다 도구의 순위(`judge.rank_of`: N/M 3, UND 4, 그 밖은 역할 순위)가 더 좋은 기록을 택한다(같으면 anchor 기록). 택한 기록으로 도구의 `aggregate.aggregate`를 같은 단위와 realizability로 돌린다. 방식 19개 전부. 열: 단위, success, partial, failure, unjudged, 성공률(분모 전체), 성공률(판정된 단위만). anchor, free, strict의 값은 각 합친 폴더의 도구 `aggregate.json`과 대조한다.
- **표 5. 방식별 골격 단위 결과.** 4절의 단위 결과(success, partial, failure, unjudged, 성공률 둘). 세 표: 전체, `n_parts` 1과 2 이상으로 나눔, stratum(conditional, invariant, timed, scoped)별(칸마다 항목 수 n). 부분이 여러 개인 항목에서 "어느 한 문장이라도 일치"는 모든 부분을 만족한다는 뜻이 아님을 주석에 쓴다.
- **표 6. 골격 NEITHER 쌍의 trigger 대 holding 패턴.** 020 `rq_aggregate.py`의 RQ1c와 같은 규칙을 쌍에 적용한다(020의 코드는 단위 단위라 쌍 단위로 구현한다): 문장의 `scope`, `condition`, `timing`은 `fret_ltl_gen.jsonl`에서, 기준은 도구 기준 파일의 `gt_parts` 모든 부분의 모든 버전의 `fields`에서 읽고(`null`과 빈 값은 없음, `timing`이 없으면 `eventually`), 문장 x 기준 버전마다 어긋남 목록을 만든다(scope는 유무가 다르거나 값이 다르면 `scope`, condition은 유무가 다르면 `cond`, timing은 값이 다르면 `timing`). 어긋남이 가장 적은 기준 버전(같으면 먼저 본 것)을 고르고, 그 어긋남에 `cond`가 있고 기준 timing이 `always`이며 생성 timing이 `always`가 아니면 패턴이다. 분모 = 골격 NEITHER 쌍(조건 1: stratum이 conditional인 항목의 쌍, 조건 2: 모든 stratum). 방식별 행과 합계 행.
- **표 7. 교차표.** 행: 골격 역할(SAME, PROOF, REFUTE, NEITHER, UND쪽 미판정, N/M쪽 미판정), 열: anchor 역할(6개 라벨), 3999쌍 전부.
- **표 8. 방식 쌍 비교(골격 단위 성공률).** 020과 같은 항목 단위 부트스트랩: 항목이 재표집 단위, 항목 안에서 반복을 평균(항목별 성공률 = 그 방식의 그 항목 단위 중 골격 success의 비율, 분모 전체), 5000회 복원 재표집, 난수는 `random.Random("20261112:A:B:구분")`(구분 `all` 또는 `judged`), 95% 구간 = 정렬한 통계량의 125번째와 4875번째 값, 점 추정 = 원래 항목에서의 평균 차이. 020의 `rq_aggregate.py`의 `boot`와 `comparisons`를 import해서 쓴다. 비교 목록은 020의 RQ2c와 같다(각 방식 대 DIRECT, 자유 템플릿 방식 대 PARA, +R2 대 같은 템플릿의 자유 방식, +V 대 기본 방식, +D 대 기본 방식(51항목)). 모든 방식이 판정된(unjudged가 아닌) 항목만 쓰는 짝 비교는 별도 표로 하고 남은 항목 수를 적는다.

## 6. 점검의 정의 (`scripts/checks_021.py`, `scripts/judge_checks.py`)

1. 헤더: 새 헤더 모두 `frozen: true`, `code_tree_sha256` = `1fda2c19...`, `mode`가 태그와 같음(free, strict, ctrl_anchor는 anchor, ctrl_free는 free). 입력 해시가 고정한 값과 같음.
2. 쌍 수: 실행마다 기대 쌍 수(2절 표)와 같음, 중복 `pair_id` 0(합치기에서 확인), 빠진 쌍과 더 있는 쌍의 목록.
3. 결정성: 같은 (항목, 문장)의 판정 불일치 수(실행마다, 020의 `judge_checks.py` 규칙: `role`, `nm`, `nm_reason`, `und_reason`, `sound`, `compl`)와 골격의 같은 점검.
4. 항등 대응 시험: free, strict 실행과 020 anchor 실행에서 같은 (쌍, 기준 부분)이 시도되었고 생성과 기준의 변수 이름과 타입 집합이 같아(`align.candidates`의 첫 분기, 대응이 모든 모드에서 항등 하나) 후보가 항등 하나뿐인 시도의 역할(`role`, `nm`, `nm_reason`, `und_reason`)이 020과 같은지 전부 센다(표본이 아니라 전수). 다르면 목록.
5. 실행 전후 `make freeze-check`와 판정 매니페스트 OK(`logs/step0_4_manifests.log`, `logs/step9_manifests_after.log`).
6. 소요 시간(분할별, 실행별), 쌍당 시간, NuSMV timeout 쌍 수와 목록.

## 7. 한계 (표 주석과 보고서에 반드시 적는다)

- free는 상한이며 가짜 일치 가능성이 있다(표 3으로 정량화). 모드 free에서 UND가 사라지는 것은 비교가 가능해진 것이지 의미가 같다는 보증이 아니다.
- 골격 결과는 짝지어진 불투명 원자가 같은 상태 술어를 뜻한다는 검증되지 않은 전제 위에 있다.
- 골격 비교는 유한 구간 z3(호라이즌 기본 8, 시간 제한 있음)이며 도구의 NuSMV 판정과 엔진이 다르다.
- 61개 LM 항목은 v4 이후 사전 관찰된 자료다. 기준은 NASA FRETish 하나다.
- 여러 부분 항목에서 단위 결과는 "어느 한 문장이라도"의 관대한 규칙이며 모든 부분을 만족한다는 뜻이 아니다.
- 이 실행은 020의 결과를 본 뒤에 설계된 탐색적 보조 실행이다.

## 8. 시작 시점에 알고 있는 확인하지 못할 것

- free 모드의 소요 시간(후보 대응이 anchor보다 많아 질의 수가 늘 수 있음). 시작 뒤 진행률로 보고하며 설정은 바꾸지 않는다. 3시간 뒤 전체의 25% 미만이면 사용자에게 알린다.
- 골격 비교의 z3 시간 제한은 시계 기준이라 부하에 따라 `unknown`이 달라질 수 있다(결정성 점검으로 본다).
- 같은 (항목, 문장)이 여러 단위에 나올 때 도구는 단위마다 다시 판정한다(캐시 없음, 020과 같음).

## 9. 시작 시점의 기대값과 고정

- 입력(`bench/nl2fret_tool/inputs/`): `units.json` 2a130c99e1fb8606f258a48ccc7d1d3819d7c92d971974cbef92a7c74aa5b474, `fret_ltl_gen.jsonl` 52df67407b39a10934c59d39af7dd74c81f6dd78474361a9043fe11ea21bfea0, `fret_realizability_gen.jsonl` 5602692bcf13b33aa0cfa420a9e951ebef8ef3988911303e3d440158e3d3de58. 도구 zip 430ff36588f1559180a75472f7a08b15061c330e67a84f5fa250324bbabb367e. 기준 파일 `data/reference/lm_reference_with_ltl.jsonl`의 해시는 헤더 `inputs.reference`(020은 1f7c9a75...)에 기록되며 020과 같아야 한다.
- 단위 3387, 판정 쌍 3999(자유, strict), 대조 단위 300과 판정 쌍 339.
- 020 기준선: `judge_records.jsonl` 221e79ed4357eb64d6c105eb58c47ad92457d37ac0b661dd3c2433dab20a71f9, `aggregate.json` ead190224a3aea9ea7a479d744ee3ebca1a6541870b0eb27cafd06a5a35b3770 (실행 전 확인함, `logs/step0_1_hashes.log`).
- 고정 1(`notes/PIN_pin1.sha256`): 이 문서, 지시문 사본, 스크립트(판정 실행, 입력 준비, 골격 비교, 상태, 복사한 020 스크립트), 입력과 분할과 대조 파일, 두 동결 매니페스트. 고정 2(`notes/PIN_pin2.sha256`): 집계와 점검 스크립트와 합성 시험.
