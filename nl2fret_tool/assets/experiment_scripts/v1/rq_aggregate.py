#!/usr/bin/env python3
"""RQ aggregation of the 020 run (instruction section 3 and 5). Reads the converted inputs, the bench outputs and the merged judge records; writes rq_tables.md and
rq_tables.json. No model call, no solver, no judgement of meaning. Definitions: notes/PRE_RUN_DEFINITIONS.md (pinned before the judge ran).

usage:
  python3 -I -B rq_aggregate.py --units units.json --ltl fret_ltl_gen.jsonl --rlz fret_realizability_gen.jsonl --records judge_records.jsonl \
      --items lm_items_combined_v6.jsonl --units-scored units_scored.jsonl --calls calls.jsonl --bench-dir <bench folder of the tool> --tool-dir <tool package root> \
      --out-md rq_tables.md --out-json rq_tables.json [--seed 20261112] [--boot 5000]
The judge records are only read. The per-sentence and per-unit classes come from the code of the frozen tool (nl2fret_judge.aggregate), imported read-only.
"""
import argparse
import collections
import json
import os
import random
import re
import sys

sys.dont_write_bytecode = True

ARM_ORDER = ["DIRECT", "PARA", "MASTeR", "EARS", "Adv-EARS", "SPIDER", "Boilerplate", "MASTeR+R2", "EARS+R2", "Adv-EARS+R2", "SPIDER+R2", "Boilerplate+R2",
             "DIRECT+V", "MASTeR+V", "EARS+V", "Boilerplate+V", "DIRECT+D", "MASTeR+D", "EARS+D"]
BASE_GROUP = ["DIRECT", "MASTeR", "EARS"]                 # the base arms that have a +D arm
D_GROUP = ["DIRECT+D", "MASTeR+D", "EARS+D"]
FREE_TEMPLATES = ["MASTeR", "EARS", "Adv-EARS", "SPIDER", "Boilerplate"]
STRATA = ["conditional", "invariant", "timed", "scoped"]
SENT_LABELS = ["SAME", "PROOF", "REFUTE", "NEITHER", "UND", "N/M", "PARSE_FAIL", "NO_RECORD"]
BAD_RANK = {"success": 0, "partial": 1, "unjudged": 2, "failure": 3}      # worst-sentence rule of the unit outcome (definition 4 of PRE_RUN_DEFINITIONS)
REFUSAL_ITEM = "LM-04_NLG-N2p3"


def jl(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]


def pct(a, b):
    return "-" if not b else f"{100.0 * a / b:.1f}%"


def frac(a, b):
    return None if not b else a / b


def order_arms(arms):
    return [a for a in ARM_ORDER if a in arms] + sorted(a for a in arms if a not in ARM_ORDER)


# ------------------------------------------------------------------------------------------------------------------------------------------------------------
class Data:
    def __init__(self, a):
        sys.path.insert(0, os.path.join(a.tool_dir, "judging"))
        sys.path.insert(0, a.bench_dir)
        from nl2fret_judge import aggregate as AG          # noqa: E402  (frozen tool code, read-only import)
        import common as C                                  # noqa: E402  (bench code of the tool)
        self.AG, self.C = AG, C
        self.units = json.load(open(a.units, encoding="utf-8"))["units"]
        self.ltl = {r["sentence"]: r for r in jl(a.ltl)}
        self.rlz = {(r["item_id"], r["arm"], int(r["rep"]), r["sentence"]): r["result"] for r in jl(a.rlz)}
        self.records = {r["pair_id"]: r for r in jl(a.records)}
        self.items = {r["id"]: r for r in jl(a.items)}
        self.scored = {(r["item_id"], r["arm"], r["rep"]): r for r in jl(a.units_scored)}
        self.calls = {r["stage_key"]: r for r in jl(a.calls)} if a.calls and os.path.exists(a.calls) else {}
        self.arms = order_arms({u["arm"] for u in self.units})
        self.by_arm = collections.defaultdict(list)
        for u in self.units:
            self.by_arm[u["arm"]].append(u)
        self.d_items = sorted({u["item"] for u in self.units if u["arm"].endswith("+D")})
        self._prep()

    # per-sentence label, per-sentence class (tool code), per-unit outcomes
    def _prep(self):
        AG = self.AG
        for u in self.units:
            labels, classes = [], []
            for i, t in enumerate(u["texts"]):
                L = self.ltl.get(t) or {}
                if not L.get("parser_ok") or not L.get("ltl_pt"):
                    labels.append("PARSE_FAIL")
                    classes.append("failure")                       # as aggregate.aggregate: parser-rejected / no formula = failure
                    continue
                rec = self.records.get(f"{u['item']}|{u['arm']}|{u['rep']}|{i}")
                if rec is None:
                    labels.append("NO_RECORD")
                    classes.append("unjudged")
                    continue
                realizable = self.rlz.get((u["item"], u["arm"], int(u["rep"]), t), "not_run") == "realizable"
                classes.append(AG.sentence_class(rec, realizable))
                role = rec.get("role")
                labels.append("N/M" if rec.get("nm") else (role if role in ("SAME", "PROOF", "REFUTE", "NEITHER", "UND") else "N/M"))
            u["_labels"], u["_classes"] = labels, classes
            u["_best"] = AG.unit_outcome(classes)                  # the tool's rule: best sentence (lenient)
            u["_worst"] = max(classes, key=lambda c: BAD_RANK[c]) if classes else "failure"
            u["_same"] = any(l == "SAME" for l in labels)
            it = self.items[u["item"]]
            u["_stratum"] = it["stratum"]
            u["_nparts_grp"] = "n_parts=1" if it["n_parts"] == 1 else "n_parts>=2"


# ------------------------------------------------------------------------------------------------------------------------------------------------------------
def md_table(headers, rows):
    out = ["| " + " | ".join(str(h) for h in headers) + " |", "|" + "---|" * len(headers)]
    for r in rows:
        out.append("| " + " | ".join("" if c is None else str(c) for c in r) + " |")
    return "\n".join(out)


class Report:
    def __init__(self):
        self.md, self.js = [], {}

    def section(self, title, note=None):
        self.md.append(f"\n## {title}\n")
        if note:
            self.md.append(note + "\n")

    def table(self, key, headers, rows, note=None, title=None):
        if title:
            self.md.append(f"\n### {title}\n")
        self.md.append(md_table(headers, rows) + "\n")
        if note:
            self.md.append(note + "\n")
        self.js[key] = {"headers": headers, "rows": rows}


# ------------------------------------------------------------------------------------------------------------------------------------------------------------
def t_denominators(D, R):
    rows = []
    for a in D.arms:
        us = D.by_arm[a]
        st = collections.Counter(u["status"] for u in us)
        rows.append([a, len(us), len({u["item"] for u in us}), sum(len(u["texts"]) for u in us), sum(1 for u in us if not u["texts"]),
                     st.get("parsed", 0), st.get("parse_error", 0), st.get("pipeline", 0)])
    R.table("denominators", ["방식", "단위 수(분모)", "항목 수", "문장 수(최종 문장, 사용 횟수)", "문장이 없는 단위", "status parsed", "parse_error", "pipeline"], rows,
            note="분모는 방식별 전체 단위다(실행 A 방식 183, `+D` 방식 153). 파서 거부, 문장 없음, 모델 거부, UND, N/M은 모두 분모에 남는다.", title="0. 분모와 단위 구성")


def t_rq1a(D, R):
    rows = []
    for a in D.arms:
        us = D.by_arm[a]
        v0 = collections.Counter()
        vf = collections.Counter()
        c0, cf = collections.Counter(), collections.Counter()
        for u in us:
            sc = D.scored[(u["item"], a, u["rep"])]["variants"]
            for v, cnt, cc in (("v0", v0, c0), ("vf", vf, cf)):
                d = sc.get(v)
                if d is None:
                    continue
                cnt[d["pre"]] += 1
                if d["pre"] != "parsed":
                    cc[f"{d['pre']}:{d['code'] or '-'}"] += 1
        n = len(us)
        rows.append([a, n, n - v0["parsed"], pct(n - v0["parsed"], n), n - vf["parsed"], pct(n - vf["parsed"], n),
                     "; ".join(f"{k} {v}" for k, v in sorted(c0.items())) or "-", "; ".join(f"{k} {v}" for k, v in sorted(cf.items())) or "-"])
    R.table("rq1a", ["방식", "단위", "v0 미통과", "비율", "vf 미통과", "비율", "v0 실패 코드 분포", "vf 실패 코드 분포"], rows,
            note="미통과 = 단위 상태가 `parsed`가 아님(`parse_error` 또는 `pipeline`). v0 = 되먹임 전 첫 답, vf = 되먹임 뒤 최종 답. 코드는 `상태:코드`.", title="RQ1a. 구문 오류")


def nz(v):
    return None if v in (None, "null", "") else v


def refs_of(D, item):
    out = []
    for part in D.items[item]["gt_parts"]:
        for v in part:
            f = v["fields"]
            out.append({"scope": nz(f.get("scope")), "condition": nz(f.get("condition")), "timing": nz(f.get("timing")) or "eventually"})
    return out


def classify(D, u, refs_cache):
    """NL2FRET_ref_rq_v8.py classify, unchanged: parser-accepted unit, the sentence/reference pair with the fewest field mismatches (first one wins ties)."""
    if u["status"] != "parsed" or not u["texts"]:
        return None
    refs = refs_cache.setdefault(u["item"], refs_of(D, u["item"]))
    best = None
    for t in u["texts"]:
        c = D.ltl.get(t)
        if not c or not c.get("parser_ok"):
            continue
        g = {"scope": nz(c.get("scope")), "condition": nz(c.get("condition")), "timing": nz(c.get("timing")) or "eventually"}
        for r in refs:
            e = []
            if bool(g["scope"]) != bool(r["scope"]):
                e.append("scope")
            elif g["scope"] != r["scope"]:
                e.append("scope")
            if bool(g["condition"]) != bool(r["condition"]):
                e.append("cond")
            if g["timing"] != r["timing"]:
                e.append("timing")
            if best is None or len(e) < len(best[0]):
                best = (e, g, r)
    return best


def field_row(label, cl):
    n = len(cl)
    return [label, n, sum(1 for e, _, _ in cl if not e), pct(sum(1 for e, _, _ in cl if not e), n), pct(sum(1 for e, _, _ in cl if "timing" in e), n),
            pct(sum(1 for e, _, _ in cl if "cond" in e), n), pct(sum(1 for e, _, _ in cl if "scope" in e), n)]


def t_rq1bc(D, R):
    cache = {}
    for u in D.units:
        u["_cls"] = classify(D, u, cache)
    hd = ["대상", "분류된 단위", "전 필드 일치(수)", "전 필드 일치", "timing 불일치", "condition 유무 불일치", "scope 불일치"]
    R.table("rq1b_arm", hd, [field_row(a, [u["_cls"] for u in D.by_arm[a] if u["_cls"]]) for a in D.arms],
            note="분류된 단위 = 상태 `parsed`이고 문장이 있는 단위. 문장과 기준 부분(모든 부분의 모든 버전) 중 필드 어긋남이 가장 적은 쌍을 택한다(`NL2FRET_ref_rq_v8.py`의 `classify`와 같은 규칙). 비율의 분모는 분류된 단위다.",
            title="RQ1b. 필드 수준 (방식별)")
    rows = []
    for a in D.arms:
        for s in STRATA:
            cl = [u["_cls"] for u in D.by_arm[a] if u["_cls"] and u["_stratum"] == s]
            if cl:
                rows.append(field_row(f"{a} / {s}", cl))
    R.table("rq1b_arm_stratum", hd, rows, title="RQ1b. 필드 수준 (방식 x stratum)", note="n이 작은 칸(scoped 항목 2개 등)은 분류된 단위 열의 수를 같이 본다.")
    rows = []
    for name, grp in (("기본(DIRECT, MASTeR, EARS) 합산, 같은 51항목", BASE_GROUP), ("+D(DIRECT+D, MASTeR+D, EARS+D) 합산, 51항목", D_GROUP)):
        for s in STRATA:
            cl = [u["_cls"] for a in grp for u in D.by_arm.get(a, []) if u["_cls"] and u["_stratum"] == s and u["item"] in D.d_items]
            if cl:
                rows.append(field_row(f"{name} / {s}", cl))
    R.table("rq1b_pooled", hd, rows, title="RQ1b. 필드 수준 (기본 합산과 +D 합산, stratum별, 같은 51항목)")
    rows = []
    for a in D.arms:
        us = [u for u in D.by_arm[a] if u["_stratum"] == "conditional" and u["_cls"]]
        pat = sum(1 for u in us if "cond" in u["_cls"][0] and u["_cls"][2]["timing"] == "always" and u["_cls"][1]["timing"] != "always")
        rows.append([a, len(us), pat, pct(pat, len(us))])
    for name, grp in (("기본(DIRECT, MASTeR, EARS) 합산, 51항목", BASE_GROUP), ("+D 합산, 51항목", D_GROUP)):
        us = [u for a in grp for u in D.by_arm.get(a, []) if u["_stratum"] == "conditional" and u["_cls"] and u["item"] in D.d_items]
        pat = sum(1 for u in us if "cond" in u["_cls"][0] and u["_cls"][2]["timing"] == "always" and u["_cls"][1]["timing"] != "always")
        rows.append([name, len(us), pat, pct(pat, len(us))])
    R.table("rq1c", ["대상", "conditional 분류된 단위", "trigger 대 holding 패턴 단위", "비율"], rows,
            note="패턴 = condition 유무가 불일치이면서 기준의 timing이 `always`이고 생성의 timing이 `always`가 아닌 단위(가장 적게 어긋나는 문장과 기준 부분의 쌍 기준).",
            title="RQ1c. trigger 대 holding 패턴")


def t_outcomes(D, R):
    AG = D.AG
    rows, rows_w, rows_role = [], [], []
    for a in D.arms:
        us = D.by_arm[a]
        n = len(us)
        best = collections.Counter(u["_best"] for u in us)
        worst = collections.Counter(u["_worst"] for u in us)
        judged = n - best["unjudged"]
        diff = sum(1 for u in us if u["_best"] != u["_worst"])
        rows.append([a, n, best["success"], best["partial"], best["failure"], best["unjudged"], pct(best["success"], n), pct(best["success"], judged), sum(1 for u in us if u["_same"]),
                     pct(sum(1 for u in us if u["_same"]), n)])
        rows_w.append([a, n, worst["success"], worst["partial"], worst["failure"], worst["unjudged"], pct(worst["success"], n), diff])
        lab = collections.Counter(l for u in us for l in u["_labels"])
        tot = sum(lab.values())
        rows_role.append([a, tot] + [f"{lab.get(k, 0)} ({pct(lab.get(k, 0), tot)})" for k in SENT_LABELS])
    R.table("outcome_best", ["방식", "단위(분모)", "success", "partial", "failure", "unjudged", "성공률(분모 전체)", "성공률(판정된 단위만)", "단위 SAME 수", "단위 SAME 비율(분모 전체)"], rows,
            note="단위 결과는 도구의 `aggregate.unit_outcome`(단위 안 가장 좋은 문장, 관대한 규칙). success = SAME 또는 PROOF이면서 같은 문장이 realizable. 판정된 단위 = unjudged가 아닌 단위(문헌 비교용으로만 병기). 단위 SAME = 단위 안 어느 문장이 SAME.",
            title="RQ1d, RQ2a. 단위 결과 (도구의 관대한 규칙)")
    R.table("outcome_worst", ["방식", "단위(분모)", "success", "partial", "failure", "unjudged", "성공률(분모 전체)", "관대한 규칙과 결과가 다른 단위 수"], rows_w,
            note="추가 지표: 단위 안 가장 나쁜 문장 기준(나쁨 순서 failure > unjudged > partial > success, 문장이 없으면 failure). 같은 문장 클래스에서 도구의 `sentence_class`를 그대로 쓴다.",
            title="RQ1d. 단위 결과 (가장 나쁜 문장 기준)")
    R.table("role_sentence", ["방식", "문장(사용 횟수)"] + SENT_LABELS, rows_role,
            note="문장 수준 도구 역할 분포(같은 문장이 여러 단위에 나오면 나온 횟수만큼 셈). PARSE_FAIL = 공식 파서가 거부했거나 LTL이 없는 문장(분모에 실패로 남음), NO_RECORD = 판정 기록이 없는 문장(0이어야 함).",
            title="RQ1d. 문장 수준 역할 분포")
    rows = []
    for a in D.arms:
        for g in ("n_parts=1", "n_parts>=2"):
            us = [u for u in D.by_arm[a] if u["_nparts_grp"] == g]
            n = len(us)
            rows.append([a, g, len({u["item"] for u in us}), n, sum(1 for u in us if u["_best"] == "success"), pct(sum(1 for u in us if u["_best"] == "success"), n),
                         sum(1 for u in us if u["_same"]), pct(sum(1 for u in us if u["_same"]), n)])
    R.table("by_nparts", ["방식", "항목 구분", "항목 수", "단위", "success", "성공률", "단위 SAME", "SAME 비율"], rows,
            note="항목 구분은 기준 부분 수 `n_parts`가 1인 항목과 2 이상인 항목이다. 부분이 여러 개인 항목에서 '어느 한 문장이라도 일치'(관대한 규칙)는 모든 부분을 만족한다는 뜻이 아니다.",
            title="항목 구분별 단위 결과 (n_parts)")


def norm_text(t):
    return re.sub(r"\s+", "", t.lower())


def t_consistency(D, R):
    C = D.C
    def skey(t):
        try:
            return C.struct_key(C.fretish_parse(t))
        except Exception:                                      # noqa: BLE001  (as NL2FRET_ref_rq_v8.py)
            return "ERR"
    rows = []
    for a in D.arms:
        by_item = collections.defaultdict(dict)
        for u in D.by_arm[a]:
            by_item[u["item"]][u["rep"]] = u
        s1 = s2 = n = 0
        for it, reps in by_item.items():
            rs = sorted(reps)
            for i in range(len(rs)):
                for j in range(i + 1, len(rs)):
                    a_, b_ = reps[rs[i]], reps[rs[j]]
                    n += 1
                    s1 += bool(a_["texts"]) and sorted(norm_text(t) for t in a_["texts"]) == sorted(norm_text(t) for t in b_["texts"])
                    s2 += bool(a_["texts"]) and sorted(skey(t) for t in a_["texts"]) == sorted(skey(t) for t in b_["texts"])
        rows.append([a, len(by_item), n, s1, pct(s1, n), s2, pct(s2, n)])
    R.table("consistency", ["방식", "항목 수", "항목별 반복 쌍 수", "같은 문장 쌍", "같은 문장 비율", "같은 구조 쌍", "같은 구조 비율"], rows,
            note="항목마다 반복 쌍(3반복이면 3쌍)에서, 앞 반복의 최종 문장 목록이 비어 있지 않고 두 반복의 목록이 같으면 같음(문장: 공백 제거 소문자 정규화 후 정렬한 목록, 구조: `common.struct_key(common.fretish_parse(문장))`의 정렬한 목록, 파싱 예외는 `ERR`). 비율 = 같은 쌍 / 전체 쌍(항목별 쌍 수가 같으므로 항목 평균과 같음).",
            title="RQ2b. 반복 간 일관성")


def item_success(D, arm, items, rule="best"):
    """item -> (mean success over reps (all units in the denominator), all units judged?)"""
    out = {}
    for it in items:
        us = [u for u in D.by_arm[arm] if u["item"] == it]
        if not us:
            continue
        out[it] = (sum(1 for u in us if u["_best"] == "success") / len(us), all(u["_best"] != "unjudged" for u in us))
    return out


def boot(d, seed_key, B):
    vals = list(d.values())
    n = len(vals)
    rng = random.Random(seed_key)
    stats = sorted(sum(vals[rng.randrange(n)] for _ in range(n)) / n for _ in range(B))
    return sum(vals) / n, stats[int(0.025 * B)], stats[min(int(0.975 * B), B - 1)]      # positions 125 and 4875 of 5000, as NL2FRET_ref_rq_v8.py


def comparisons(arms):
    pairs = []
    def add(a, b):
        if a in arms and b in arms and (a, b) not in pairs:
            pairs.append((a, b))
    for a in ARM_ORDER:
        if a != "DIRECT":
            add(a, "DIRECT")
    for t in FREE_TEMPLATES:
        add(t, "PARA")
    for t in FREE_TEMPLATES:
        add(t + "+R2", t)
    for t in ["DIRECT", "MASTeR", "EARS", "Boilerplate"]:
        add(t + "+V", t)
    for t in ["DIRECT", "MASTeR", "EARS"]:
        add(t + "+D", t)
    return pairs


def t_bootstrap(D, R, seed, B):
    rows, rows_j = [], []
    for a, b in comparisons(D.arms):
        items = sorted(set(u["item"] for u in D.by_arm[a]) & set(u["item"] for u in D.by_arm[b]))
        sa, sb = item_success(D, a, items), item_success(D, b, items)
        d = {i: sa[i][0] - sb[i][0] for i in items if i in sa and i in sb}
        pt, lo, hi = boot(d, f"{seed}:{a}:{b}:all", B)
        better = sum(1 for x in d.values() if x > 0)
        worse = sum(1 for x in d.values() if x < 0)
        rows.append([f"{a} - {b}", len(d), f"{100 * pt:+.1f}", f"[{100 * lo:+.1f}, {100 * hi:+.1f}]", better, len(d) - better - worse, worse])
        dj = {i: sa[i][0] - sb[i][0] for i in items if sa[i][1] and sb[i][1]}
        if dj:
            ptj, loj, hij = boot(dj, f"{seed}:{a}:{b}:judged", B)
            rows_j.append([f"{a} - {b}", len(dj), len(d), f"{100 * ptj:+.1f}", f"[{100 * loj:+.1f}, {100 * hij:+.1f}]"])
        else:
            rows_j.append([f"{a} - {b}", 0, len(d), "-", "-"])
    R.table("bootstrap_all", ["비교 (A - B)", "항목 수", "성공률 차이(%p)", "95% 구간", "A가 나은 항목", "같은 항목", "A가 나쁜 항목"], rows,
            note=f"항목 단위 부트스트랩: 항목이 재표집 단위, 항목 안에서는 반복을 평균(항목별 성공률 = 그 항목의 단위 성공 수 / 단위 수, 분모 전체), 5000회 복원 재표집(요청 횟수 {B}), 시드 `{seed}`와 비교 이름으로 고정, 구간 = 정렬한 통계량의 2.5%와 97.5% 위치. `+D` 비교는 51항목, 그 밖은 61항목.",
            title="RQ2c. 방식 쌍 비교 (항목 단위 부트스트랩, 모든 항목)")
    R.table("bootstrap_judged", ["비교 (A - B)", "남은 항목 수", "모든 항목 수", "성공률 차이(%p)", "95% 구간"], rows_j,
            note="별도 표: 두 방식의 모든 단위(반복 포함)가 판정된(unjudged가 아닌) 항목만 쓴 짝 비교. 남은 항목 수를 적었다. 같은 부트스트랩 규칙.",
            title="RQ2c. 방식 쌍 비교 (모든 방식이 판정된 항목만)")


def t_rq3(D, R):
    rows = []
    for a in D.arms:
        for s in STRATA:
            us = [u for u in D.by_arm[a] if u["_stratum"] == s]
            if not us:
                continue
            n = len(us)
            rows.append([a, s, len({u["item"] for u in us}), n, sum(1 for u in us if u["_best"] == "success"), pct(sum(1 for u in us if u["_best"] == "success"), n),
                         sum(1 for u in us if u["_same"]), pct(sum(1 for u in us if u["_same"]), n)])
    R.table("rq3", ["방식", "stratum", "항목 수 n", "단위(분모)", "success", "성공률", "단위 SAME", "SAME 비율"], rows,
            note="분모는 그 칸의 전체 단위다. stratum `scoped`는 항목이 2개뿐이므로 n을 반드시 함께 본다.", title="RQ3. 방식 x stratum")


def t_realizability(D, R):
    rows, rows_s = [], []
    for a in D.arms:
        us = D.by_arm[a]
        st = collections.Counter(D.scored[(u["item"], a, u["rep"])]["variants"]["vf"]["status"] for u in us)
        rows.append([a, len(us)] + [st.get(k, 0) for k in ("realizable", "unrealizable", "unknown", "not_run", "parse_error", "pipeline")])
        sc = collections.Counter(D.rlz.get((u["item"], a, int(u["rep"]), t), "NO_ROW") for u in us for t in u["texts"])
        rows_s.append([a, sum(sc.values())] + [sc.get(k, 0) for k in ("realizable", "unrealizable", "unknown", "not_run", "parse_error", "NO_ROW")])
    R.table("rlz_unit", ["방식", "단위", "realizable", "unrealizable", "unknown", "not_run", "parse_error", "pipeline"], rows,
            note="단위 수준 = bench `score3.py final`의 상태(최종 답 vf, 단위 안 문장 결과 중 가장 나쁜 것: pipeline > parse_error > not_run > unknown > unrealizable > realizable).", title="실현가능성. 단위 수준")
    R.table("rlz_sentence", ["방식", "문장(사용 횟수)", "realizable", "unrealizable", "unknown", "not_run", "parse_error", "행 없음"], rows_s,
            note="문장 수준 = `fret_realizability_gen.jsonl`의 결과(Kind2). 행 없음 = 공식 파서가 거부한 문장이거나 파이프라인 실패 단위의 문장처럼 realizability 행이 없는 것(도구는 `not_run`으로 읽음).", title="실현가능성. 문장 수준")


def t_sensitivity(D, R):
    rows = []
    for a in D.arms:
        if not a.endswith("+R2"):
            continue
        us = D.by_arm[a]
        us2 = [u for u in us if u["item"] != REFUSAL_ITEM]
        rows.append([a, len(us), sum(1 for u in us if u["_best"] == "success"), pct(sum(1 for u in us if u["_best"] == "success"), len(us)),
                     len(us2), len({u["item"] for u in us2}), sum(1 for u in us2 if u["_best"] == "success"), pct(sum(1 for u in us2 if u["_best"] == "success"), len(us2))])
    R.table("sensitivity", ["방식", "단위(주 표)", "success", "성공률(주 표, 전체 단위)", "단위(뺀 값)", "항목 수(뺀 값)", "success(뺀 값)", "성공률(뺀 값)"], rows,
            note=f"민감도(보조, 주 결과를 바꾸지 않음): `{REFUSAL_ITEM}`의 `+R2` 단위(모델 거부)를 뺀 값. 뺀 항목 수는 1(61 대 60). 주 표는 뺀 값이 아니라 전체 단위 기준이다.", title="민감도 표")


def t_rq4(D, R):
    rows = []
    for a in D.arms:
        if a.startswith("DIRECT"):
            rows.append([a, "해당 없음(단계 A 없음)", "", "", "", ""])
            continue
        base = a.split("+")[0]
        un = ch = nun = nch = n = 0
        for u in D.by_arm[a]:
            r = D.calls.get(f"{u['item']}|{base}|{u['rep']}|A")
            if not r or r.get("status") != "ok" or not r.get("parsed"):
                continue
            n += 1
            m, c = r["parsed"].get("unmapped_content") or [], r["parsed"].get("choices") or []
            un += len(m)
            ch += len(c)
            nun += 1 if m else 0
            nch += 1 if c else 0
        rows.append([a, n, un, nun, ch, nch])
    R.table("rq4_stageA", ["방식", "단계 A 출력이 있는 단위", "`unmapped_content` 항목 합", "그것이 있는 단위", "`choices` 항목 합", "그것이 있는 단위"], rows,
            note="RQ4는 이 실행에서 분석하지 않고 기록만 보존한다. 단계 A 행은 템플릿 이름으로 `+R2`, `+V`, `+D` 방식과 공유되므로 같은 템플릿의 방식들은 같은 단계 A 출력을 센다.", title="RQ4 기록. 단계 A 출력")
    rows = []
    for a in D.arms:
        c = collections.Counter()
        for u in D.by_arm[a]:
            for i, t in enumerate(u["texts"]):
                r = D.records.get(f"{u['item']}|{a}|{u['rep']}|{i}")
                if not r:
                    continue
                ap = r.get("ap_check") or {}
                if ap.get("equal") is None:
                    c["ap_check 없음(UND 등)"] += 1
                    continue
                c["equal"] += 1 if ap["equal"] else 0
                c["gt_subset_pred"] += 1 if ap["gt_subset_pred"] else 0
                c["pred_subset_gt"] += 1 if ap["pred_subset_gt"] else 0
                c["nm_pair_any"] += 1 if ap["nm_pair_any"] else 0
                c["nm_pair_all"] += 1 if ap["nm_pair_all"] else 0
                c["기록 수"] += 1
        rows.append([a, c["기록 수"], c["equal"], c["gt_subset_pred"], c["pred_subset_gt"], c["nm_pair_any"], c["nm_pair_all"], c["ap_check 없음(UND 등)"]])
    R.table("rq4_ap", ["방식", "ap_check가 있는 기록", "atom 집합이 같음", "gt가 pred의 부분집합", "pred가 gt의 부분집합", "저자 규칙 N/M(어느 질의라도)", "저자 규칙 N/M(모든 질의)", "ap_check 없음"], rows,
            note="`ap_check`(규칙 `author_subset_v1`)는 기록만 하며 판정 값을 바꾸지 않는다. 판정 기록 한 줄(문장 하나)이 한 건이다.", title="RQ4 기록. AP 불일치 기록")


# ------------------------------------------------------------------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for k in ("units", "ltl", "rlz", "records", "items", "units-scored", "bench-dir", "tool-dir", "out-md", "out-json"):
        ap.add_argument("--" + k, required=True)
    ap.add_argument("--calls")
    ap.add_argument("--seed", default="20261112")
    ap.add_argument("--boot", type=int, default=5000)
    a = ap.parse_args()
    a.units_scored, a.bench_dir, a.tool_dir, a.out_md, a.out_json = a.units_scored, a.bench_dir, a.tool_dir, a.out_md, a.out_json
    D = Data(argparse.Namespace(**{k.replace("-", "_"): v for k, v in vars(a).items()}))
    R = Report()
    R.md.append("# RQ 집계 표 (020, 본 실험 019의 판정 단계)\n\n정의는 `notes/PRE_RUN_DEFINITIONS.md`(판정 전에 고정). 해석 문장은 쓰지 않았다. 판정 기록은 읽기만 했다.")
    R.section("A. 분모와 구성")
    t_denominators(D, R)
    R.section("B. RQ1 (오류와 의미 손실)")
    t_rq1a(D, R)
    t_rq1bc(D, R)
    R.section("C. 도구 역할과 단위 결과 (RQ1d, RQ2a)")
    t_outcomes(D, R)
    R.section("D. RQ2 (템플릿 중간 표현)")
    t_consistency(D, R)
    t_bootstrap(D, R, a.seed, a.boot)
    R.section("E. RQ3 (요구사항 유형별)")
    t_rq3(D, R)
    R.section("F. 실현가능성")
    t_realizability(D, R)
    R.section("G. 민감도와 RQ4 기록")
    t_sensitivity(D, R)
    t_rq4(D, R)
    open(a.out_md, "w", encoding="utf-8").write("\n".join(R.md) + "\n")
    json.dump(R.js, open(a.out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote", a.out_md, a.out_json, "| tables:", len(R.js), "| units:", len(D.units), "| records:", len(D.records))


if __name__ == "__main__":
    main()
