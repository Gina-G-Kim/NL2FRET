# 데이터셋과 사전 버전업 (Mac 메인 디렉터리)

자산별로 버전을 올린다. 자산: `dataset`(lm_dataset_final.jsonl, lm_dataset_table.xlsx), `dictionary`(lm_dictionary.csv), `reference`(lm_reference_with_ltl.jsonl, sigdict.json).
- 메인 디렉터리의 현재 파일을 `archive/<자산>/v<K>/`로 옮긴다(K는 현재 버전).
- 이 패키지의 `data/dataset`, `data/dictionary`, `data/reference` 파일을 메인 디렉터리 같은 위치에 v<K+1>로 둔다.
- `VERSIONS.md`에 자산, 버전, 경로, sha256, 사유, 사용 실험을 한 줄씩 추가한다.
- 이번 버전의 사유: 데이터셋 고정(61 항목, 기준 112행, EB-N2 제외, EB-N4 추가, AP-1.2와 AP-1.8 복원, EUL-N1 7부, EUL-N4, EUL-N8에 NASA-lus 판 추가), 사전 564 항목.
