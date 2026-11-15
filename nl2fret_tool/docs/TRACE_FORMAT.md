# 단계별 추적 형식

단위 = 항목 x arm x 반복. 단위마다 S0 내지 S6 블록을 기록하고, 각 블록 끝에 원본 로그 파일과 키를 적는다(경로는 RUN 기준).

| 단계 | 내용 | 원본 로그 |
|---|---|---|
| S0 input | 자연어, 챌린지 | `gen/snapshot/items_used.jsonl`, `data/dictionary/lm_dictionary.csv` |
| S1 template | 자연어 -> 템플릿 문장, 선택, 담지 못한 내용 | `gen/calls.jsonl` 키 `item|템플릿|rep|A` |
| S2 fretish | 규칙 층이 읽은 구절, 모델 슬롯 값, 조립 문장, 자유 생성 문장, fallback 사유 | `gen/calls.jsonl` 키 `item|arm|rep|S/B/D` |
| S3 fret_loop | 시도별 FRET 판정(accepted/REJECTED), FRET 원문 메시지, 거절 횟수, 되먹임 호출 수, cap_reached | `gen/parser_cache.jsonl`, `gen/calls.jsonl` 키 `...|F1..Fn` (누적 로그가 프롬프트에 들어간 호출) |
| S4 ltl | 최종 문장의 과거시제, 미래시제 LTL | `inputs/fret_ltl_gen.jsonl` |
| S5 dictionary_alignment | exact, aliased, oov | `judge/judge_records.jsonl`의 `dict_alignment` |
| S6 judge | 부분별 대표 쌍, 쌍마다 역할, equiv/sound/compl, 반례 상태 | `judge/judge_records.jsonl`(pair_id), `judge/smv/<sha>.smv`, `judge/counterexamples.jsonl`, `judge/part_results.jsonl` |

pair_id 형식: `item|arm|rep|s{문장}|p{부분}|v{버전}`.
산출: `trace/INDEX.md`(단위 목록), `trace/units/*.md`, `trace/unit_trace.jsonl`, `summary.md`, `summary.json`(arm별 성공률, 역할 수, 거절 수, 2회 이상 거절 수, cap_reached, fallback). summary는 관측값만 적는다.
