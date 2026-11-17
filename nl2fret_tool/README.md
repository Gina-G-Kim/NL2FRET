# NL2FRET (release 2.0)

자연어 요구사항을 반정형 템플릿을 거쳐 FRETish로 바꾸고, 공식 FRET이 컴파일한 LTL이 NASA 전문가 FRETish의 LTL과 같은 뜻(SAME)인지, 또는 그것을 함의(PROOF)하는지 NuSMV 질의로 판정하는 도구이다.

연구 질문, 정답과 딕셔너리의 역할, 결정 사항은 [docs/V20_BATCH_DESIGN.md](docs/V20_BATCH_DESIGN.md) 맨 위에 있다. 단계별 설명과 실제 실행 예제는 프로젝트 루트의 `docs/TOOL_PROCESS_GUIDE.md`이다.

## 설치와 점검
PyPA 구조이다: `pyproject.toml`, `src/` 레이아웃, 패키지 밖 `tests/`. 이 폴더(`nl2fret_tool/`)가 프로젝트 루트이다.

```
python3 -m venv .venv && . .venv/bin/activate
pip install -e ".[test]"       # 패키지 nl2fret, nl2fret_judge (+ legacy), 의존성 z3-solver
make test                      # pytest (z3 엔진, NuSMV 불필요)
make build                     # sdist와 wheel (dist/)
```

콘솔 진입점: `nl2fret-batch`(배치 생성), `nl2fret-run`(문장 단위 생성), `nl2fret-judge`(판정). 나머지 도구는 `python -m nl2fret.tools.<이름>` 또는 `python -m nl2fret.fret_check.<이름>`으로 실행한다.

## 구성
| 위치 | 내용 |
|---|---|
| `pyproject.toml` | 메타데이터, 의존성, 진입점, 패키지 데이터 선언. 버전의 원천은 `VERSION` |
| `src/nl2fret/` | 생성 파이프라인 (`batch_pipeline.py`, `run_pipeline.py`, `prompts3.py`, `tpl_rules.py`, `common.py`, ...), `tools/`, `fret_check/` (FRET 파서와 Realizable 호출), `ext/` (확장 모듈), 패키지 데이터 `data/`, `prompts/`, `templates*/` |
| `src/nl2fret_judge/` | 판정 모듈 (이름 정렬, 불리언 추상화, NuSMV 질의, 역할 판정, 기록, 집계). 코드는 옮기기만 했고 바꾸지 않았다 |
| `src/legacy/` | 정렬 후보 생성에 쓰는 judge2, judge4, judge5, judge_pt (`nl2fret_judge/align.py`가 패키지 옆 `legacy` 폴더를 찾는다) |
| `tests/` | 시험 (설치된 패키지를 import한다) |
| `scripts/` | 실행 스크립트 `run_batch.sh`(2.0 배치), `run_fsm.sh`, `run_intent.sh`(1.3, 1.4 계열)와 유지보수 스크립트 `render_prompts.py`(프롬프트 파일을 코드에서 다시 만들고 대조), `build_cases.py`, `verify_lm_docx.py`, `run_selftests.sh` |
| `prompts/` | 현재 프롬프트 파일(`prompts/current/`)과 색인 `prompts/INDEX.md` |
| `assets/`, `VERSIONS.md` | 입력과 실험 자산의 버전별 사본과 버전 색인 |
| `archive/` | 이전 릴리스(`releases/`), 철회한 기능(`removed_features/`), 이전 판 문서(`nl2fret_tool_docs/`), 용도를 모르는 파일(`unsorted/`) |
| `external/docker/` | 외부 프로그램(FRET, NuSMV)의 Docker 이미지 레시피. 엔진 자체는 저장소에 없다 |
| `data/` | 연구 데이터 (데이터셋, 딕셔너리, 정답 키, 감사 표, 입력 케이스 `cases/`, 색인 `INDEX.md`). 휠에 넣지 않고 저장소에 둔다. 설치된 패키지에서 쓰려면 환경 변수 `NL2FRET_HOME`에 이 폴더의 상위(프로젝트 루트)를 준다 |
| `docs/` | 현행 문서 ([docs/RUNBOOK.md](docs/RUNBOOK.md) 실행 절차, [docs/DESIGN.md](docs/DESIGN.md) 설계, [docs/V20_BATCH_DESIGN.md](docs/V20_BATCH_DESIGN.md) 사전 등록, [docs/TOOL_PROCESS_GUIDE.md](docs/TOOL_PROCESS_GUIDE.md) 프로세스별 설명) |
| `runs/` | 실행 결과 (git 추적 제외) |

## 실행 (요약)
```
ONLY=06_EB REPS=1 NUSMV=/path/to/NuSMV bash scripts/run_batch.sh all runs/batch_06EB
```
`EXT=dictionary`(기본)이면 딕셔너리 확장이 켜진다. `EXT=`이면 꺼진다. 자세한 절차는 [docs/RUNBOOK.md](docs/RUNBOOK.md).

## 코드 고정
도구 코드의 고정은 릴리스 태그(`v2.0`, git)로 한다. 해시 목록(`FROZEN_MANIFEST.sha256`)과 `make freeze-check`는 2026-11-17에 없앴다 (`archive/removed_features/`). 실행은 `gen/snapshot/`에 코드 사본과 프롬프트 해시를 남긴다.

## 이전 문서
릴리스 1.4까지의 README, 설계, 실행 절차, FSM 시험 문서는 `archive/nl2fret_tool_docs/v1.4/`에 있다. 프로젝트 전체(논문, 실험 기록)는 이 폴더의 상위 `nl2semiformal/`에 있다 (`experiments/`, `docs/`).
