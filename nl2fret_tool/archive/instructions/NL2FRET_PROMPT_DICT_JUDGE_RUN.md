# 프롬프트: 사전과 별칭 적용 입력 판정 실행, 자산 버전업, 프로세스 문서 작성 (동결 도구 v1.2.0)

아래 전체를 Mac의 LLM 에이전트에게 전달한다. 입력은 `dict_inputs.zip`, 도구는 `nl2fret_tool_v1.2.zip`이다. 금지 사항, 분할 실행, 점검 절차는 `NL2FRET_PROMPT_LM61_JUDGE_RUN.md`를 따른다. 아래에 적힌 것이 우선한다.

보고서 첫 줄에 "사전과 별칭 적용 입력(이번 실험 한정 전처리)에 대한 동결 도구 판정 실행"이라고 적는다. 확인하지 못한 것은 "확인하지 못함"으로 적고 추측으로 채우지 마라. 이모지와 em dash를 쓰지 마라. 한계와 주의 문장은 문서와 코드에 쓰지 말고 최종 보고에만 쓴다.

## 금지 사항
- 판정 도구 v1.2.0의 모든 파일을 수정하지 마라. `make freeze-check`와 매니페스트 대조가 실행 전후 모두 OK여야 한다. `--allow-unfrozen` 금지.
- 입력 파일을 수정하거나 일부 단위, 문장을 제외하지 마라.
- 결과를 보고 설정(모드 anchor, cap 128, timeout 120, NuSMV)과 사전, 별칭 규칙을 바꾸지 마라.
- git 명령 금지.

## 1. 입력 대조와 재현
1. `dict_inputs/SHA256SUMS`로 전체 파일을 대조한다. 기대값: units `2a130c99e1fb8606f258a48ccc7d1d3819d7c92d971974cbef92a7c74aa5b474`, 본 판정 ltl(`fret_ltl_gen.jsonl`) `609f06a645a4018114eba826e0ddda4cc35e697cce67129e63c67b112f3167a3`, 사전만 적용한 ltl(`intermediate/fret_ltl_gen_dict_only.jsonl`) `e6a2dfde3f8d1d2322cd36c3bea71e7c760bf03f2e5896defd257d9339bd93c8`, rlz `5602692bcf13b33aa0cfa420a9e951ebef8ef3988911303e3d440158e3d3de58`, 별칭 증명서 `bf2a06ebc2758bffe5e8244751e382c9a421c5af176239d6b3ac5e15db5cc82f`, 사전 `50f6dd05341275c57e0bf80dccb5f48be99c1b341345a2d02dbcd3daf10ccbed`.
2. `NL2FRET_DICT_PRE_REGISTRATION.md`를 읽고 해시를 보고서에 적는다. 판정 기록을 열기 전에 해시를 고정한다.
3. 재현: `pip install z3-solver` 후 `scripts/apply_dict.py`와 `scripts/alias_apply.py`를 원본 입력에 실행해 위 ltl 해시와 증명서 해시가 같은지 대조한다(명령은 각 스크립트 첫 줄 usage. `alias_apply.py`와 `cert_check.py`는 환경변수 `NL2FRET_TOOL`에 도구 메인 디렉터리 경로를 주고, `alias_apply.py`의 세 번째 인자는 `data/reference/lm_reference_with_ltl.jsonl`이다. 입력은 원본 입력 폴더이고 `apply_dict.py`의 사전은 `map/mapping_final.json`이다). `scripts/cert_check.py`를 증명서에 실행해 불일치 0건을 확인한다.

## 2. 판정 실행 (설정 고정, 부분 실행과 병합은 LM61 프롬프트 1절 방식)
1. 본 실행: `dict_inputs/units.json` + `dict_inputs/fret_ltl_gen.jsonl` + `dict_inputs/fret_realizability_gen.jsonl`.
2. 음성 대조: `control/units_control.json` + 같은 `fret_ltl_gen.jsonl`. 기대 쌍 339, SAME 0.
3. 이름 교환 대조: 본 실행 종료 후 `python3 -I -B scripts/swap_control.py <본 실행 judge_records.jsonl> dict_inputs swap_in`을 실행하고 `swap_in/units_swap.json` + `swap_in/fret_ltl_swap.jsonl`로 판정한다.
4. 별칭 대조: `control/units_alias_subset.json` + `intermediate/fret_ltl_gen_dict_only.jsonl`로 판정하고, 같은 pair_id의 본 실행 기록과 역할 이동표(사전만 적용 행, 별칭 적용 열)를 만든다.
5. 본 실행의 이동표를 이전 사전 없는 앵커 실행(`strict_merged`)과도 만든다(이전 역할 행, 본 실행 열).

## 3. 점검과 집계
LM61 프롬프트의 2절(점검)과 3절(사전 정의 집계)을 본 실행에 적용한다. 대조 결과로 음성 대조 SAME 수(하나라도 있으면 쌍 전부 나열), 이름 교환 대조 SAME 수와 쌍 목록, 교환한 변수 두 개를 보고한다.

## 4. 도구 메인 디렉터리 버전업
실험에서 쓰거나 만든 자산은 `experiments/` 폴더에만 두지 말고 도구 메인 디렉터리에 둔다. 아래 자산이 대상이다.
- 신호 이름 사전, 사전 구성 규칙(rules_*.txt), 제거 목록
- 사전등록 문서 전부(T2, v4, 사전, 별칭)
- 사전 적용, 별칭 증명, 증명서 검사, 이름 교환 스크립트와 별칭 증명서
- LLM에게 주는 템플릿 가이드(MASTeR, EARS, Adv-EARS, SPIDER, Boilerplate, PARA 및 +R2, +V, +D 변형)
- LLM이 참고하는 모든 자료(시스템 프롬프트, 사용자 프롬프트, 키워드 가이드, 예시, 사전 문서)
- 기준 데이터와 입력 데이터

규칙:
1. 자산마다 메인 디렉터리 안의 지정 위치에 `vN` 형식 버전으로 둔다. 이번 실행에서 수정된 자산은 버전을 올리고, 이전 버전은 `archive/<자산>/vK/`로 옮긴다.
2. `VERSIONS.md` 색인을 만든다. 열: 자산, 현재 버전, 경로, sha256, 변경 사유, 변경을 일으킨 실험.
3. 이후 실험에서 수정사항이 생길 때마다 같은 규칙으로 버전을 올린다. 이 규칙을 `VERSIONS.md` 첫머리에 한 줄로 적는다.
4. 검토: 위 자산 중 메인 디렉터리에 아직 없는 것, 메인 디렉터리 버전과 `experiments/` 또는 입력 zip의 해시가 다른 것, 공개 대상 저장소에 반영되지 않은 것을 찾아 목록으로 만든다. 목록은 최종 보고에 싣고, 공개 반영(push)은 하지 않는다.

## 5. 프로세스 전 주기 문서
`docs/PROCESS_LIFECYCLE.md`를 만든다. 도구를 처음 보는 사람이 입력, 출력, 각 단의 처리를 파악하는 문서이다. 저장소의 실제 파일을 읽고 확인한 내용만 쓴다.

구성:
1. 첫머리에 전 주기를 한 표로 둔다. 열: 단계, 입력, 처리, 출력.
2. 단계마다 블록을 둔다. 항목: 입력(파일 경로), 처리(평서문 1 내지 3문장), 출력(파일 경로), 근거(스크립트와 문서의 저장소 경로).
3. 후보 단계(저장소 기준으로 확정하고 다르면 저장소를 따른다): 요구사항 입력과 기준 데이터, 템플릿 가이드와 프롬프트 구성, LLM 생성, FRETish 파싱과 LTL 컴파일, 실현가능성 검사, 사전 구성, 사전 적용, 별칭 증명, 판정(앵커, NuSMV), 집계, T2와 skeleton 분석, 대조 실험, RQ 분석, 버전 관리.

문체 규칙:
- 긍정 평서문만 쓴다. "않는다", "없다", "못한다", "아니다" 같은 부정형 문장을 쓰지 않는다.
- 주석성 문장, 주의, 참고, 단서, 한계 서술을 쓰지 않는다. 설명이 더 필요한 곳에는 해당 파일의 저장소 경로를 적는다.
- 이모지와 em dash를 쓰지 않는다.
- 확인하지 못한 단계는 문서에 쓰지 말고 최종 보고에 목록으로 적는다.

유지: 도구, 실험, 자산이 바뀔 때마다 이 문서를 같은 규칙으로 버전업하고 `VERSIONS.md`에 올린다.

## 최종 보고
1. 첫 줄 명시, 환경과 NuSMV 버전, 시계 차이
2. 입력과 도구 해시 대조, 재현 결과, `frozen: true`와 `code_tree_sha256` 확인
3. 본 실행: 기록 쌍 수(기대 2855), 역할 분포, UND 사유별, N/M 사유별, timeout 수, 쌍당 시간
4. 이동표 두 가지, 대조 세 가지 결과
5. 도구 `aggregate` 결과와 사전 정의 집계 표
6. 버전업 결과(`VERSIONS.md`), 검토 목록(없는 것, 해시가 다른 것, 공개 미반영)
7. `docs/PROCESS_LIFECYCLE.md`의 경로와 sha256, 확인하지 못한 단계 목록
8. 이상 징후, 확인하지 못한 항목
9. 산출물 경로와 sha256
