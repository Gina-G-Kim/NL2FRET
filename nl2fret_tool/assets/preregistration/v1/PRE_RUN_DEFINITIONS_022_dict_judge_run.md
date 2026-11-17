# PRE_RUN_DEFINITIONS_022: 사전과 별칭 적용 입력에 대한 동결 도구 판정 실행 (v1.2.0), 2026-11-13

사전과 별칭 적용 입력(이번 실험 한정 전처리)에 대한 동결 도구 판정 실행이다. 이 문서는 판정 기록을 열기 전에 쓰고 해시를 고정한다(`notes/PIN_pin1.sha256`). 집계와 점검 스크립트는 판정이 도는 동안 합성 예시로 시험해 만들고 새 기록의 값을 읽기 전에 두 번째로 고정한다(`notes/PIN_pin2.sha256`). 교환 대조의 입력과 분할은 본 실행이 끝난 뒤 만들고 세 번째로 고정한다(`notes/PIN_pin3.sha256`).

## 1. 범위와 원칙

- 지시문 `docs/NL2FRET_PROMPT_DICT_JUDGE_RUN.md`(sha256 a912e64c4d0752a2bed24a58b48277ab31ee30accd502cb2a8bc6a67886964ad)와 사전등록 `docs/NL2FRET_DICT_PRE_REGISTRATION.md`(sha256 aa351623fd208b33a8cdbab42184ff708fcd6268946cb2d0bd8293b426c44127)를 따른다. 사전과 별칭은 이번 실험의 입력 전처리이다.
- 판정 도구 v1.2.0(`nl2fret_tool_v1.2.zip` sha256 430ff36588f1559180a75472f7a08b15061c330e67a84f5fa250324bbabb367e)의 모든 파일을 고치지 않는다. `make freeze-check`(bench 38개 파일, 매니페스트 `176b144f...e571`)와 판정 매니페스트(18개 파일, `1fda2c19...a154b`)는 실행 전후 모두 OK여야 하고 `--allow-unfrozen`을 쓰지 않는다. 모든 새 기록 헤더가 `frozen: true`이다.
- 입력 파일을 고치지 않고 단위와 문장을 빼지 않는다. 결과를 보고 설정(모드 anchor, cap 128, timeout 120초, NuSMV 엔진)과 사전, 별칭 규칙을 바꾸지 않는다. 컨테이너 안 timeout 125초, 컨테이너 `--cpus=1`, `nice -n 10`, `caffeinate -i`, 4분할, 한 번에 컨테이너 4개 이하이다.
- 020, 021 폴더는 읽기만 한다. 지시문이 참조하는 `NL2FRET_PROMPT_LM61_JUDGE_RUN.md`는 입력 zip과 저장소에 없으므로, 같은 역할의 020 지시문 절차(분할 실행, 합치기, 점검, 사전 정의 집계)와 020, 021의 스크립트를 쓴다.
- git 명령을 쓰지 않는다. 계정 이메일은 어디에도 쓰지 않는다. 판정 결과의 해석 문장을 쓰지 않는다.

## 2. 입력과 재현 (판정 기록을 열기 전에 끝낸 단계)

- `inputs/dict_inputs/SHA256SUMS` 23개 파일이 모두 OK이고 지시문 1.1항의 값 여섯 개가 같다: units 2a130c99e1fb8606f258a48ccc7d1d3819d7c92d971974cbef92a7c74aa5b474, 본 판정 ltl 609f06a645a4018114eba826e0ddda4cc35e697cce67129e63c67b112f3167a3, 사전만 적용한 ltl e6a2dfde3f8d1d2322cd36c3bea71e7c760bf03f2e5896defd257d9339bd93c8, rlz 5602692bcf13b33aa0cfa420a9e951ebef8ef3988911303e3d440158e3d3de58, 별칭 증명서 bf2a06ebc2758bffe5e8244751e382c9a421c5af176239d6b3ac5e15db5cc82f, 사전 50f6dd05341275c57e0bf80dccb5f48be99c1b341345a2d02dbcd3daf10ccbed(`logs/step0_1_hashes.log`).
- 재현(`logs/repro_*.log`, `repro/`): 원본 입력(020의 `units.json`, `fret_ltl_gen.jsonl` 52df6740..., `fret_realizability_gen.jsonl`)에 `scripts/apply_dict.py`(사전 `map/mapping_final.json`)를 실행한 결과의 ltl 해시가 e6a2dfde...과 같고(바뀐 문장 1642, 같은 문장 1088, 충돌 규칙으로 버린 치환 38), 그 출력에 `scripts/alias_apply.py`(`NL2FRET_TOOL` = 도구 원본 사본, 기준 `data/reference/lm_reference_with_ltl.jsonl`, `--procs 3`)를 실행한 결과의 ltl 해시가 609f06a6...이고 증명서 해시가 bf2a06eb...이다(바뀐 문장 140, 증명서 302건). `scripts/cert_check.py`는 302건 중 불일치 0건, 건너뜀 0건이다.

## 3. 판정 실행의 정의

호출은 `scripts/run_judge_shard.sh`가 모듈을 직접 부른다: `cd judging && python -m nl2fret_judge judge --engine nusmv --nusmv <래퍼> --out ../runs/<태그>/shard<k> --units <분할 입력> --ltl <ltl 파일> --rlz ../inputs/dict/fret_realizability_gen.jsonl --mode anchor --cap 128`(timeout 120초는 기본값).

| 태그 | 분할 입력(작업 폴더 `bench/nl2fret_tool/` 기준) | ltl 파일 | 기대 판정 쌍 |
|---|---|---|---|
| main | `inputs/shards/units_shard<k>.json`(`units.json` 3387단위의 4분할, 020과 같은 파일) | `inputs/dict/fret_ltl_gen.jsonl`(사전과 별칭 적용) | 3999(분할 1031, 851, 1028, 1089) |
| ctrl | `inputs/control/units_control_shard<k>.json`(`control/units_control.json` 300단위의 4분할, 021과 같은 파일) | `inputs/dict/fret_ltl_gen.jsonl` | 339(분할 88, 89, 83, 79), 역할 SAME 기대 0 |
| alias_dictonly | `inputs/alias/units_alias_shard<k>.json`(`control/units_alias_subset.json` 120단위의 4분할) | `inputs/dict_only/fret_ltl_gen_dict_only.jsonl`(사전만 적용) | 266(분할 5, 245, 11, 5) |
| swap | `swap_in/units_swap.json`의 4분할(본 실행이 끝난 뒤 `scripts/swap_control.py`로 만듦) | `swap_in/fret_ltl_swap.jsonl` | 교환 단위 수(`swap_control.py`가 센 값) |

- 기대 쌍 수는 입력에서 센 값이다(해당 ltl 파일에서 `parser_ok`이고 `ltl_pt`가 있는 문장 수). 지시문의 본 실행 기대값 2855는 이 입력의 값 3999와 다르며, 이 실행의 기대는 3999이다.
- 분할은 `shard_units.py`(항목 id 정렬 후 라운드로빈, 항목 통째로)이다. 대기열은 `run_queue.sh`(`xargs -P 4`)이고 순서는 main 분할 1, 3, 2, 4, ctrl 분할 1부터 4, alias_dictonly 분할 2, 3, 1, 4이다. 중단되면 같은 명령으로 재개하고 헤더가 처음 값임을 적는다.
- 교환 단위 키 규칙: `units_swap.json`에서 (항목, 방식, 반복)이 같은 단위가 둘 이상이면 `rep`를 `원래 반복 + 1000 x 원래 문장 인덱스`로 바꿔 키를 유일하게 하고 `orig_pair_id`는 그대로 둔다. 겹침이 없으면 파일을 그대로 쓴다.
- 분할 기록은 020의 `merge_judge.py`로 합친다(원본 줄 그대로, 단위 순서와 문장 인덱스 순서). 중복 `pair_id`가 있거나 단위에 없는 기록이 있거나 헤더가 `frozen: true`가 아니거나 `code_tree_sha256`이 `1fda2c19...`가 아니면 합치지 않고 보고한다. 합친 폴더에서 도구의 `aggregate` 명령을 실행한다.

## 4. 점검의 정의 (`scripts/judge_checks.py`, `scripts/checks_022.py`)

1. 헤더: 분할 헤더 모두 `frozen: true`, `code_tree_sha256` = `1fda2c19...`, `mode` anchor, cap 128, timeout 120, 엔진 nusmv, `allow_unfrozen` false, `selfcheck_passed` true, 입력 해시(분할 단위 파일, ltl 파일, rlz 파일)가 실행 정의와 같음.
2. 쌍 수: 실행마다 기대 쌍 수와 같음, 분할별로도 같음, 중복 `pair_id` 0, 빠진 쌍과 더 있는 쌍의 목록.
3. 역할 분포, UND 사유별, N/M 사유별, 시간 초과 쌍 수와 목록, 쌍당 시간 평균과 최대와 합.
4. 결정성: 같은 (항목, 문장)의 판정 불일치 수(`role`, `nm`, `nm_reason`, `und_reason`, `sound`, `compl`).
5. 020 anchor 기록과 겹치는 쌍의 비교(`judge_checks.py --previous`): (생성 식, 기준 식)이 같은 쌍의 역할과 사유가 같은지 센다. 대상 실행은 main과 ctrl이다.
6. 소요 시간(분할별, 실행별)과 시작 횟수, 종료 코드.
7. 실행 전후 `make freeze-check`와 판정 매니페스트 OK.

## 5. 이동표와 대조의 정의 (`scripts/tables_022.py`)

공통: 쌍 라벨 = N/M(`nm` 참)이면 "N/M", 아니면 `role`(SAME, PROOF, REFUTE, NEITHER, UND). 쌍은 `pair_id`로 짝짓는다.

- **이동표 1(사전 없음에서 본 실행으로).** 행: 이전 실행의 쌍 라벨, 열: 본 실행(main)의 쌍 라벨, 3999쌍 전부. 이전 실행은 둘이다: (a) 020 anchor 합친 기록(`experiments/020_lm61_main_judge/bench/nl2fret_tool/runs/merged/judge_records.jsonl`, sha256 221e79ed4357eb64d6c105eb58c47ad92457d37ac0b661dd3c2433dab20a71f9, 모드 anchor, 사전 없음), (b) 021 strict 합친 기록(`experiments/021_comparability_test/bench/nl2fret_tool/runs/strict_merged/judge_records.jsonl`, sha256 28b645bb3a5b3f485f0d66b8a5a4b9b98b9654dc1755b40ab778741aa1a1a3f5, 지시문이 `strict_merged`라고 적은 실행, 모드 strict). 따로 적는 수: UND에서 비교 가능한 역할(SAME, PROOF, REFUTE, NEITHER)로 바뀐 쌍 수, NEITHER에서 SAME, PROOF, REFUTE로 바뀐 쌍 수, SAME, PROOF, REFUTE에서 다른 역할로 바뀐 쌍 수.
- **이동표 2(별칭).** 행: alias_dictonly 실행의 쌍 라벨(사전만 적용), 열: 같은 `pair_id`의 main 기록의 쌍 라벨(별칭 적용). 두 표: (a) alias_dictonly의 266쌍 전부, (b) 그 중 문장(항목, 문장)이 별칭 증명서(`alias/alias_certificates.jsonl`의 `item`, `sentence`)에 있는 쌍만.
- **음성 대조(ctrl).** 쌍 수, 역할 분포(사유 포함), SAME 수. SAME이 하나라도 있으면 쌍 전부를 나열한다(쌍 id, 생성 문장, 원래 항목, 바꾼 기준 항목, 기준 부분, 기준 문장, 대응). 같은 방식으로 SAME 또는 PROOF, SAME 또는 PROOF 또는 REFUTE의 비율도 적는다. 원래 항목은 021의 `control_sampling.json`(sha256 f50344d8599e78d04fe5b0cb1a27c87e200f8425c7753f19deec8cdff3595121)의 `drawn_units`에서 읽는다.
- **이름 교환 대조(swap).** 입력: main 기록의 SAME 쌍 중 생성 식(`ltl_pt`)의 변수가 둘 이상인 쌍(`swap_control.py`가 정한 대로, 정렬한 앞 두 변수를 맞바꿈). 보고: main의 SAME 쌍 수, 교환 단위 수, 변수 하나뿐이라 건너뛴 쌍 수, 교환 판정 쌍 수와 역할 분포, 교환 판정에서 SAME인 쌍의 수와 목록(`orig_pair_id`, 교환한 변수 두 개, 원 식과 교환 식). 대칭 판별: 원 식과 교환 식을 `judging/legacy/judge4.compare`(유한 구간 z3, 같은 변수 집합이므로 항등 대응)로 비교해 클래스가 `equivalent_*`이면 두 변수에 대해 대칭인 식으로 센다. SAME인 교환 쌍은 대칭인 쌍과 아닌 쌍으로 나누어 적고 대칭이 아닌 쌍은 목록으로 손으로 확인한다.

## 6. 집계의 정의

- 사전 정의 집계는 020의 `notes/PRE_RUN_DEFINITIONS.md`(sha256 bc66794850a2a63f14eb8f36c6468c1f1ffb117e4c8788c00ec9d6d9dff6e3a1)의 3절과 같다. 020의 `scripts/rq_aggregate.py`(sha256 b65d4b8b0bc00a22c77fbdd418fa6ac34aa3a40c6b971a25d383bbba34c91780)를 바꾸지 않고 main의 합친 기록, 이 실행의 ltl 파일, 020의 항목 파일(`inputs/lm_items_combined_v6.jsonl`)과 생성 후처리 산출물(`results_main_post/units_scored.jsonl`, `calls.jsonl`)로 돌린다. 분모 규칙은 020과 같고 파서 거부, 문장 없음, 모델 거부, UND, N/M은 분모에 남는다. 단위 수는 방식별 183 또는 153(+D), 합 3387이다.
- 도구의 `aggregate.json`(관대한 규칙)은 실행마다 그대로 보존한다.
- 나란히 표시: 3999쌍의 쌍 라벨 분포(사유 포함)를 020 anchor(사전 없음), main(사전과 별칭), 021 free, 021 strict, 021 골격(`skeleton_records.jsonl`의 역할)에 대해 한 표로 둔다. 방식별 단위 성공률(분모 전체와 판정된 단위만)은 020 anchor, main, 021 free, 021 strict의 도구 `aggregate.json` 값을 한 표로 둔다.

## 7. 산출물 규칙

- `assets/<자산>/vN/`에 자산을 두고 이전 버전은 `archive/<자산>/vK/`로 옮긴다. `VERSIONS.md`의 열은 자산, 현재 버전, 경로, sha256, 변경 사유, 변경을 일으킨 실험이다. 첫머리 한 줄에 버전업 규칙을 적는다.
- `docs/PROCESS_LIFECYCLE.md`는 긍정 평서문만 쓴다. 단계마다 입력, 처리, 출력, 근거를 적는다.
- 검토 목록: 메인 디렉터리에 없는 자산, 메인 디렉터리 버전과 `experiments/` 또는 입력 zip의 해시가 다른 자산, 공개 대상 저장소에 반영되지 않은 자산(`.gitignore` 패턴으로 제외되는 위치의 자산, git 명령은 쓰지 않으므로 추적 여부는 파일 경로와 패턴으로만 판단)을 찾는다. 공개 반영(push)은 하지 않는다.

## 8. 시작 시점의 기대값과 고정

- 입력(작업 폴더 `bench/nl2fret_tool/inputs/`): `dict/units.json` 2a130c99..., `dict/fret_ltl_gen.jsonl` 609f06a6..., `dict/fret_realizability_gen.jsonl` 5602692b..., `dict_only/fret_ltl_gen_dict_only.jsonl` e6a2dfde..., `control/units_control.json` 7c945ee1ca90afaf83955709dcd737532cba1b738ef3c0b5a9bb9dd6a209f791, `alias/units_alias_subset.json` 8faf935d4b7bb87e9762783a0322b4812a482c9159bdf1c8e44bad9816921ed0.
- 단위 3387, 본 실행 판정 쌍 3999, 음성 대조 339, 별칭 대조 266.
- 입력에서 센 값(판정 기록 아님): 정렬 후보가 하나도 없는 쌍은 020 입력 1557, 사전만 1545, 사전과 별칭 1545이고, 정렬 후보 수 합계는 36675, 16075, 16075이다.
- 고정 1(`notes/PIN_pin1.sha256`): 이 문서, 지시문 사본과 사전등록 사본, 판정 실행 스크립트(`run_judge_shard.sh`, `run_queue.sh`, `container.sh`, `launch.sh`, `cleanenv.sh`, `bin/NuSMV`, `shard_units.py`, `merge_judge.py`, `judge_checks.py`, `prepare_inputs.sh`, `step0_022.sh`, `status.py`, `pin.sh`), 대기열 파일, 입력과 분할과 기대 쌍 수, 두 동결 매니페스트, 입력 zip이 준 스크립트(`dict_inputs/scripts/*`). 고정 2(`notes/PIN_pin2.sha256`): 집계와 점검 스크립트와 합성 시험. 고정 3: 교환 대조의 입력과 분할.
