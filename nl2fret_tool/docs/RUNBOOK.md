# 실행 절차

## 0. 준비
- Python 3.10 이상, `pip install -r requirements.txt` (z3는 교차검증과 샌드박스 테스트용)
- NuSMV 2.6.0 실행 명령 확인 (직접 설치 또는 docker 래퍼 스크립트; 마지막 인자로 .smv 경로를 받는 실행 파일이면 된다)
- `make freeze-check` 로 bench 동결 해시 확인

## 1. 생성 단계 (bench, 기존 절차 그대로)
`bench/run_pipeline.py`와 `bench/score3.py`의 사용법은 각 파일 머리말과 `bench/NL2FRET_PROMPT_v8_DICT_SMOKE.md`를 따른다. 이 패키지는 bench를 수정하지 않는다.
판정 입력으로 필요한 세 파일을 `inputs/`에 둔다.
- `units.json` : {"units":[{"item","arm","rep","status","texts":[...]}]}
- `fret_ltl_gen.jsonl` : 문장별 FRET 컴파일 결과 (sentence, parser_ok, ltl_pt, ltl_ft)
- `fret_realizability_gen.jsonl` : 문장별 Kind2 결과 (item_id, arm, rep, sentence, result)
형식 예시는 `data/example_*` 파일.

## 2. 판정
1. `make selfcheck NUSMV="NuSMV" OUT=runs/r1` : 5쌍 점검. 실패하면 엔진을 쓰지 않는다 (판정 명령도 자동으로 거부한다).
2. `make judge OUT=runs/r1 NUSMV="NuSMV"` : 쌍마다 `judge_records.jsonl`에 추가 기록, `smv/`에 질의 파일 저장. 중단 후 같은 명령으로 재개된다.
3. `make aggregate OUT=runs/r1` : `aggregate.json` 생성 (arm별, stratum별, 쌍 결과 분포).

옵션: `--mode anchor|lex|strict|free` (정렬 층, 기본 anchor), `--cap 128` (구간 확장 상한), `--aux` (보조 sat/valid 질의), `--timeout 120`.

## 3. 샌드박스 교차검증 (NuSMV 없이)
`python -m nl2fret_judge judge --engine z3 ...` : 구간 길이가 horizon(기본 8) 이하인 쌍만 판정되고 나머지는 N/M(converter_limit)이 된다. NuSMV 결과와 판정된 쌍에서 비교한다.

## 4. 기록물
`run_header.json`(엔진 버전, 입력 해시, 설정), `judge_records.jsonl`(쌍별 전체 기록: 원 식, 원자, 질의 원문 출력, 정렬 사상, AP 불일치 기록), `smv/*.smv`.
