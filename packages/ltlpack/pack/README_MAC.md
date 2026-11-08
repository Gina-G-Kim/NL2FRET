# NuSMV와 Spot 비교 시험 (Mac)

목적: FRET 과거시제 식(ltl_pt)을 NuSMV로, 미래시제 식(ltl_ft)을 Spot으로 읽혀서 두 도구가 (1) 식을 받아들이는지, (2) 기존 통제 실험의 기대 역할과 맞는지, (3) 기존 z3 판정(judge4)과 맞는지 본다. 생성 모델 호출은 없다. 관측만 하고 해석하지 않는다.

## 구성
- tools/ltl_engines.py : 변환기와 실행기 (표준 라이브러리만 사용, z3는 있으면 사용)
- data/pairs.jsonl : 610쌍 (통제 실험 512, 생성 문장 98). 생성 식은 이름 고정 모드의 대응으로 정답 식 이름에 이미 맞춰져 있음
- data/formulas.jsonl : 식 478개 (받아들이는지 시험용)
- sandbox_reference_z3b.txt : 이 환경에서 z3로 같은 불리언 추상화를 판정한 참고 결과

## 1. 도구 준비
- Spot: `brew install spot` 후 `ltlfilt --version`
- NuSMV: 설치 방법은 알 수 없습니다. NuSMV 또는 nuXmv 실행 파일이 있으면 됩니다. 없으면 설치 시도 내용을 `INSTALL_NOTES.md`에 적고 이 시험에서 NuSMV는 제외합니다 (Spot만 진행).
- 선택: `pip3 install z3-solver` (있으면 세 번째 엔진 z3b도 같이 돌아감)

## 2. 실행 (이 폴더에서)
```bash
python3 -I tools/ltl_engines.py selftest      # SELFTEST_OK 이어야 함
python3 -I tools/ltl_engines.py parse   --nusmv <NuSMV 경로, 없으면 생략>
python3 -I tools/ltl_engines.py run     --nusmv <경로> --timeout 120
python3 -I tools/ltl_engines.py report > REPORT.txt
```
- 도구 이름이 PATH에 있으면 `--nusmv`, `--spot` 생략 가능 (NuSMV, nuXmv, ltlfilt를 찾음).
- `run`은 중간에 끊겨도 같은 명령을 다시 실행하면 이어서 진행.
- 시간은 알 수 없습니다. 창(window) 경계가 큰 식은 NuSMV가 오래 걸릴 수 있어 `--timeout`으로 자르고 오류로 기록됨.

## 3. 지켜야 할 것
1. data/와 tools/의 파일을 수정하지 않는다.
2. 오류가 나도 고치거나 다시 돌리지 않는다. 오류 원문을 그대로 `NOTES.md`에 적는다.
3. 결과 해석 문장을 쓰지 않는다.

## 4. 전달
`results/`, `REPORT.txt`, `NOTES.md`(있으면), `INSTALL_NOTES.md`(있으면)를 zip으로 묶어 보낸다.
```bash
zip -r ltl_engines_out.zip results REPORT.txt NOTES.md INSTALL_NOTES.md 2>/dev/null
```
그리고 `ltlfilt --version`, NuSMV 또는 nuXmv의 버전 출력을 `NOTES.md`에 적는다.

## 알려진 한계 (변환 방식)
- 산술 비교는 식마다 하나의 불리언 원자로 바뀐다. x<3과 x<5의 관계처럼 서로 다른 원자 사이의 산술 관계는 도구가 모른다. 이는 FRET 리팩터링 논문(arXiv 2202.05816 4.4절)이 쓴 불리언 치환과 같은 종류의 근사다. 정규화는 부등호 방향, 교환 가능 연산자 순서, != 와 =만 처리한다.
- Spot 시험은 미래시제 식 기준이다. FRET의 LAST는 Spot에서 일반 명제로 취급되어 유한 trace 의미와 다르다. 따라서 Spot 결과는 NuSMV 결과와 의미가 완전히 같지 않을 수 있다 (추측입니다).
- NuSMV는 `G (생성 -> 정답)` 과 `G (정답 -> 생성)` 를 검사한다. 과거시제 식이 모든 시점에서 성립하는지를 보는 것이며, FRET 의미론이 trace의 끝 시점에서 평가한다는 점에 근거한 추론이다 (문헌에 같은 수식이 공개된 것은 아님).
