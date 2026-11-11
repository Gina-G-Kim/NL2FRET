#!/usr/bin/env python3
"""Smoke 3 check table (stdlib only). Checks that the devices of v6 worked (+V, no leak, shared stage A, files),
and prints observations. It never judges meaning (no equivalence, no better or worse)."""
import argparse, csv, json, re, sys
from collections import Counter, defaultdict
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument("--results", default="results_smoke3")
ap.add_argument("--data", default="data/lm_smoke.jsonl")
ap.add_argument("--all-items", default="data/lm_items.jsonl")
ap.add_argument("--reps", type=int, default=2)
a = ap.parse_args()
R = Path(a.results); M = R / "metrics"; SNAP = R / "snapshot"
jl = lambda p: [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
rd = lambda p: list(csv.DictReader(open(p, encoding="utf-8")))
norm = lambda s: re.sub(r"\s+", "", s).lower()
data = jl(a.data); calls = jl(R / "calls.jsonl")
arms = json.loads((SNAP / "run_info.json").read_text(encoding="utf-8"))["arms"]
rows = []
def rec(i, title, ok, ev):
    rows.append((i, title, "통과" if ok is True else ("실패" if ok is False else "정보"), ev))
def run(i, title, fn):
    try:
        fn()
    except Exception as e:
        rec(i, title, False, "check crashed: %s: %s" % (type(e).__name__, e))
VMARK = "TIMING INFERENCE PRINCIPLES"
varms = [x for x in arms if x.endswith("+V")]

def s1():
    u = jl(R / "units_scored.jsonl")
    keys = {(x["item_id"], x["arm"], x["rep"]) for x in u}
    vs = Counter(",".join(sorted(x["variants"])) for x in u)
    exp = len(data) * len(arms) * a.reps
    rec("S1", "단위가 모두 기록됨, 단위마다 변형 v0 vn vf", len(keys) == exp and set(vs) == {"v0,vf,vn"}, "단위 %d (기대 %d), 변형 조합 %s" % (len(keys), exp, dict(vs)))
def s2():
    um = [r for r in rd(M / "lm_unit_metrics.csv") if r["variant"] == "vf"]
    c = Counter(r["arm"] for r in um if r["no_output"] in ("0", "0.0"))
    rec("S2", "모든 방식이 출력함", all(c[x] >= 1 for x in arms), "방식별 출력이 있는 단위 수 %s" % dict(c))
def s3():
    refs = {norm(v["fretish"]) for d in data for part in d["gt_parts"] for v in part if len(norm(v["fretish"])) >= 25}
    hits = []
    for p in list(SNAP.glob("system_prompt_*.txt")) + list((SNAP / "prompts").glob("*.md")) + list((SNAP / "templates").glob("*.md")):
        t = norm(p.read_text(encoding="utf-8"))
        hits += [(p.name, r[:40]) for r in refs if r in t]
    for c in calls:
        if c["stage"] in ("B", "D", "F1", "F2"):
            t = norm(c.get("user_prompt") or "")
            hits += [(c["stage_key"], r[:40]) for r in refs if r in t]
    rec("S3", "프롬프트 어디에도 기준 FRETish가 없음", not hits, "검색한 기준 문장 %d개, 일치 %s" % (len(refs), hits[:5] or "0건"))
def s4():
    ev = []; ok = bool(varms)
    for arm in varms:
        base = arm[:-2]; st = "D" if base == "DIRECT" else "B"
        pv = SNAP / ("system_prompt_%s_%s.txt" % (st, arm if st == "B" else "DIRECT+V"))
        pb = SNAP / ("system_prompt_%s_%s.txt" % (st, base if st == "B" else "none"))
        hv = pv.exists() and VMARK in pv.read_text(encoding="utf-8")
        hb = pb.exists() and VMARK in pb.read_text(encoding="utf-8")
        ev.append("%s: 자기 프롬프트에 있음 %s, 기본 프롬프트에 있음 %s" % (arm, hv, hb)); ok = ok and hv and not hb
    for p in SNAP.glob("system_prompt_A_*.txt"):
        if VMARK in p.read_text(encoding="utf-8"):
            ok = False; ev.append("단계 A 프롬프트에 V 문구: " + p.name)
    for p in SNAP.glob("templates/*.md"):
        if VMARK in p.read_text(encoding="utf-8"):
            ok = False; ev.append("템플릿 명세에 V 문구: " + p.name)
    rec("S4", "+V 원칙은 +V 방식의 단계 B 또는 D 프롬프트에만 있음 (단계 A와 템플릿 명세에는 없음)", ok, "; ".join(ev))
def s5():
    ev = []; ok = True
    for arm in varms:
        if arm == "DIRECT+V":
            continue
        own = [c for c in calls if c["stage"] == "A" and c["arm"] == arm]
        sb = sorted((c["item_id"], c["rep"]) for c in calls if c["stage"] == "B" and c["arm"] == arm)
        bb = sorted((c["item_id"], c["rep"]) for c in calls if c["stage"] == "B" and c["arm"] == arm[:-2])
        ev.append("%s: 자기 단계 A 행 %d, 단계 B 행 %d (기본 방식 %d)" % (arm, len(own), len(sb), len(bb))); ok = ok and not own and sb == bb
    rec("S5", "+V 템플릿 방식은 기본 방식의 단계 A 행을 공유함 (같은 템플릿 문장 위의 비교)", ok, "; ".join(ev) or "해당 없음")
def s6():
    ev = []; ok = True
    for arm in arms:
        rr = [c for c in calls if c["stage"] in ("B", "D") and c["arm"] == arm]
        tb = [((c.get("parsed") or {}).get("timing_basis") or {}) for c in rr]
        filled = sum(1 for t in tb if t.get("rule"))
        rules = Counter(t.get("rule") for t in tb if t.get("rule"))
        ev.append("%s: timing_basis 채움 %d/%d %s" % (arm, filled, len(rr), dict(rules)))
        ok = ok and ((filled > 0) if arm in varms else filled == 0)
    rec("S6", "timing_basis는 +V 방식에만 기록됨 (기록만 하고 채점에 쓰지 않음)", ok, "; ".join(ev))
def s7():
    ev = []
    for arm in arms:
        rr = [c for c in calls if c["stage"] in ("B", "D") and c["arm"] == arm]
        t = Counter()
        for c in rr:
            for f in ((c.get("parsed") or {}).get("fields") or []):
                tm = (f.get("timing") or "").strip().lower()
                t[tm.split()[0] if tm else "(없음)"] += 1
        ev.append("%s: %s" % (arm, dict(t)))
    rec("S7", "생성 필드의 타이밍 분포 (관측만, 우열 결론 없음)", None, "; ".join(ev))
def s8():
    pr = rd(M / "lm_paired_vs_direct.csv"); pc = Counter((r["arm"], r["versus"]) for r in pr)
    want = [(x, x[:-2]) for x in varms] + [(b, "DIRECT") for b in arms if b not in varms and b != "DIRECT"]
    miss = [w for w in want if pc[w] == 0]
    rec("S8", "비교 구도가 갖춰짐 (+V 대 같은 방식, 템플릿 대 DIRECT)", not miss, "빠진 쌍 %s" % (miss or "없음"))
def s9():
    need = "lm_unit_metrics.csv lm_summary.csv lm_paired_vs_direct.csv lm_consistency.csv lm_item_features.csv lm_failures.csv lm_judgment_queue.jsonl lm_pairs.jsonl METRICS_GLOSSARY.md".split()
    miss = [n for n in need if not (M / n).exists()]
    hdr = open(M / "lm_unit_metrics.csv", encoding="utf-8").readline().strip().split(",")
    bad = [h for h in hdr if re.search(r"equiv|stronger|weaker|implies|entail", h, re.I)]
    rec("S9", "지표 파일 9개가 있고 열 이름에 판정어(equiv, stronger, weaker, implies, entail)가 없음", not miss and not bad, "빠진 파일 %s, 판정어가 든 열 %s, 열 수 %d" % (miss or "없음", bad or "없음", len(hdr)))
def s10():
    um = [r for r in rd(M / "lm_unit_metrics.csv") if r["variant"] == "vf"]
    ev = []
    for arm in arms:
        rr = [r for r in um if r["arm"] == arm]
        f = lambda k: sum(float(r[k]) for r in rr if r.get(k) not in (None, "")) / max(1, len([r for r in rr if r.get(k) not in (None, "")]))
        ev.append("%s: aud_fill_rate %.3f, aud_drop_rate %.3f, ip_num_invented 합 %d" % (arm, f("aud_fill_rate"), f("aud_drop_rate"), sum(float(r["ip_num_invented"]) for r in rr if r.get("ip_num_invented") not in (None, ""))))
    rec("S10", "감사 지표 (슬롯 주석 1명 초안 기준, 관측만, 우열 결론 없음)", None, "; ".join(ev))
def s11():
    srcs = list((SNAP / "templates").glob("*.md")); cur = Path("templates")
    diff = [p.name for p in srcs if not (cur / p.name).exists() or (cur / p.name).read_bytes() != p.read_bytes()]
    rec("S11", "템플릿 명세가 작업 폴더의 원본과 같음 (수정 없음)", not diff, "스냅샷 템플릿 %d개, 다른 것 %s" % (len(srcs), diff or "없음"))
def s12():
    byk = {}
    for c in calls:
        if c["stage"] in ("B", "D"):
            byk.setdefault((c["item_id"], c["rep"], c["arm"]), c.get("parsed") or {})
    ev = []
    for arm in varms:
        base = arm[:-2]; ch = tot = 0
        for (i, r, ar), p in byk.items():
            if ar != arm: continue
            q = byk.get((i, r, base))
            if q is None: continue
            tot += 1; ch += int([f.get("timing") for f in p.get("fields", [])] != [f.get("timing") for f in q.get("fields", [])])
        ev.append("%s: 기본 방식과 타이밍 목록이 다른 단위 %d/%d" % (arm, ch, tot))
    rec("S12", "+V가 타이밍 필드를 바꾼 단위 수 (관측만, 맞고 틀림은 판정하지 않음)", None, "; ".join(ev))

for i, (t, f) in enumerate([("", s1), ("", s2), ("", s3), ("", s4), ("", s5), ("", s6), ("", s7), ("", s8), ("", s9), ("", s10), ("", s11), ("", s12)], 1):
    run("S%d" % i, "", f)
out = ["# SMOKE_CHECK (smoke 3)", "", "| # | 확인 | 결과 | 근거 |", "|---|---|---|---|"] + ["| %s | %s | %s | %s |" % r for r in rows]
(R / "SMOKE_CHECK.md").write_text("\n".join(out) + "\n", encoding="utf-8")
print("\n".join(out))
fails = [r for r in rows if r[2] == "실패"]
print("\nfailed checks: %d" % len(fails)); sys.exit(1 if fails else 0)
