#!/usr/bin/env python3
"""LM bench scorer. Writes MANY metrics and the files a judge needs. It does NOT decide whether a generated FRETish means the same as the reference
(no equivalence or implication checking, no solver). Every number here is a deterministic count or string comparison.

usage (python3 -I score_lm.py ...):
  python3 -I score_lm.py all --results results_lm [--data data/lm_items.jsonl]
Needs: results_lm/units_scored.jsonl (score3.py final), results_lm/fret_realizability.jsonl and results_lm/fret_ltl.jsonl (fret_check/check.py single).
Writes into results_lm/metrics/ :
  lm_unit_metrics.csv          one row per unit and variant (v0, vn, vf), about 150 columns
  lm_summary.csv               long format: group_by, key, arm, variant, metric, mean, ci_lo, ci_hi, n_items, n_units (item level bootstrap, 2000 resamples)
  lm_paired_vs_direct.csv      per item paired differences of every arm against DIRECT (and +G, +R against the free arm of the same template)
  lm_consistency.csv           repetition consistency per item and arm
  lm_item_features.csv         objective input and reference features of every item (used for strata)
  lm_failures.csv              failure codes by arm and variant
  lm_judgment_queue.jsonl      every DISTINCT (item, generated sentence) once, with the best aligned reference part, both LTL strings and all string level flags
  lm_pairs.jsonl               unit level alignment records (variant vf and v0)
  METRICS_GLOSSARY.md          the definition of every column
"""
import argparse
import collections
import csv
import itertools
import json
import math
import os
import random
import re
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import _split_top, _strip_outer, char_cos, collapse, comp_canon, fretish_parse, lev_sim, numbers, tok_f1, uni, words  # noqa: E402

BOOT = 2000
SEED = 20261101
KEYWORDS = {"true", "false", "and", "or", "not", "mode"}


# ---------------------------------------------------------------- small helpers
def jl(path):
    return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()] if os.path.exists(path) else []


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def prf(tp, fp, fn):
    p = tp / (tp + fp) if (tp + fp) else None
    r = tp / (tp + fn) if (tp + fn) else None
    f = 2 * p * r / (p + r) if (p is not None and r is not None and (p + r) > 0) else (0.0 if (p is not None and r is not None) else None)
    return p, r, f


def group_of(arm):
    if arm == "DIRECT":
        return "D"
    if arm == "PARA":
        return "P"
    if arm.endswith("+G"):
        return "G"
    if arm.endswith("+U"):
        return "U"
    if arm.endswith("+V"):
        return "V"
    if arm.endswith("+R"):
        return "R"
    return "F"


def base_of(arm):
    return arm.split("+")[0]


# ---------------------------------------------------------------- expression forms (string level, no semantics)
_ID = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def _shape(s):
    """identifiers -> v, numbers kept, function names kept"""
    def rep(m):
        w = m.group(0)
        end = m.end()
        if w.lower() in KEYWORDS or (end < len(m.string) and m.string[end] == "("):
            return w
        return "v"
    return _ID.sub(rep, s)


def _canon_sorted(s):
    """like common.canon_expr but operands of & and | are sorted by their identifier-free shape first, so renamed variables do not change the order."""
    s = _strip_outer(s)
    p = _split_top(s, "=>")
    if len(p) > 1:
        return "(" + _canon_sorted(p[0]) + "=>" + _canon_sorted("=>".join(p[1:])) + ")"
    for op in ("|", "&"):
        p = _split_top(s, op)
        if len(p) > 1:
            return "(" + op.join(sorted((_canon_sorted(x) for x in p), key=lambda z: (_shape(z), z))) + ")"
    m = re.match(r"^!(.+)$", s)
    if m and not m.group(1).startswith("!"):
        return "!" + _canon_sorted(m.group(1))
    return s


def norm_expr(s):
    s = uni(s or "").lower().strip().rstrip(".;")
    s = re.sub(r"\s+", " ", s)
    m = re.match(r"^if (.+?) then (.+)$", s)
    if m:
        s = f"({m.group(1)}) => ({m.group(2)})"
    s = s.replace(" ", "")
    return _canon_sorted(s)


def alpha_form(parts):
    """joint first-occurrence renaming over a list of normalized expression strings"""
    names = {}

    def rep(m):
        w = m.group(0)
        end = m.end()
        if w in KEYWORDS or (end < len(m.string) and m.string[end] == "("):
            return w
        if w not in names:
            names[w] = f"x{len(names) + 1}"
        return names[w]
    return [_ID.sub(rep, p) for p in parts]


def ops_of(s):
    s = uni(s or "")
    return collections.Counter(re.findall(r"=>|<=>|<=|>=|!=|[<>=!&|+*/-]", s))


def consts_of(s):
    return numbers(s)


def ids_of(s):
    s = uni(s or "")
    out = set()
    for m in _ID.finditer(s):
        w = m.group(0)
        if w.lower() in KEYWORDS or re.match(r"^\d", w):
            continue
        if m.end() < len(s) and s[m.end()] == "(":
            continue
        out.add(w.lower())
    return out - {"shall", "satisfy", "always", "never", "eventually", "immediately", "within", "until", "before", "after", "when", "whenever", "if", "then", "upon", "in", "the", "for",
                  "next", "every", "while", "ticks", "seconds", "milliseconds", "minutes", "hours", "probability", "with", "abs", "absreal", "prebool", "prereal", "preint", "persisted"}


def parsed(s):
    p = fretish_parse(s)
    scope_n = norm_expr(p["scope"]) if p["scope"] else ""
    cond_n = norm_expr(p["condition"]) if p["condition"] else ""
    resp_n = norm_expr(p["response"]) if p["response"] else ""
    tim = " ".join(p["timing_kws"])
    tnum = tuple(sorted(numbers(p["timing"]).elements()))
    a_scope, a_cond, a_resp = alpha_form([scope_n, cond_n, resp_n])
    p.update({"scope_n": scope_n, "cond_n": cond_n, "resp_n": resp_n, "tim": tim, "tnum": tnum, "a_scope": a_scope, "a_cond": a_cond, "a_resp": a_resp,
              "shape_resp": _shape(resp_n), "shape_cond": _shape(cond_n)})
    return p


def l0_key(s):
    t = collapse(s).lower()
    t = re.sub(r"\bthe\s+", "", t)
    return re.sub(r"\s+", "", t.rstrip("."))


def sent_flags(g, t):
    """string level comparison of a generated parsed sentence g and a reference parsed sentence t. Booleans and similarities only."""
    f = {}
    f["l0_exact"] = l0_key(g["raw"]) == l0_key(t["raw"])
    f["scope_eq"] = g["scope_kw"] == t["scope_kw"]
    f["cond_present_eq"] = bool(g["cond_kw"]) == bool(t["cond_kw"])
    f["cond_kw_eq"] = g["cond_kw"] == t["cond_kw"]
    f["component_eq"] = comp_canon(g["component"]) == comp_canon(t["component"])
    f["timing_class_eq"] = g["tim"] == t["tim"]
    f["timing_num_eq"] = g["tnum"] == t["tnum"]
    f["timing_eq"] = f["timing_class_eq"] and f["timing_num_eq"]
    f["scope_expr_alpha_eq"] = g["a_scope"] == t["a_scope"]
    f["cond_expr_alpha_eq"] = g["a_cond"] == t["a_cond"]
    f["resp_exact_eq"] = g["resp_n"] == t["resp_n"]
    f["resp_alpha_eq"] = g["a_resp"] == t["a_resp"]
    f["resp_shape_eq"] = g["shape_resp"] == t["shape_resp"]
    f["resp_form_eq"] = g["resp_form"] == t["resp_form"]
    f["l1_alpha"] = (f["scope_eq"] and f["cond_kw_eq"] and f["timing_eq"] and f["scope_expr_alpha_eq"] and f["cond_expr_alpha_eq"] and f["resp_alpha_eq"])
    f["l2_shape"] = (f["scope_eq"] and f["cond_kw_eq"] and f["timing_eq"] and f["resp_shape_eq"] and g["shape_cond"] == t["shape_cond"])
    f["l2b_struct"] = (f["scope_eq"] and f["cond_present_eq"] and f["timing_class_eq"] and f["resp_form_eq"])
    f["n_fields_eq5"] = sum([f["scope_eq"], f["cond_present_eq"], f["component_eq"], f["timing_eq"], f["resp_alpha_eq"]])
    f["tok_f1"] = tok_f1(t["raw"], g["raw"])
    f["char_cos3"] = char_cos(t["raw"], g["raw"])
    f["lev_sim"] = lev_sim(t["raw"], g["raw"])
    f["resp_tok_f1"] = tok_f1(t["response"], g["response"])
    ot, og = ops_of(t["response"] + " " + t["condition"]), ops_of(g["response"] + " " + g["condition"])
    f["ops_f1"] = _bag_f1(ot, og)
    ct, cg = consts_of(t["response"] + " " + t["condition"] + " " + t["timing"]), consts_of(g["response"] + " " + g["condition"] + " " + g["timing"])
    f["consts_f1"] = _bag_f1(ct, cg)
    f["consts_eq"] = ct == cg
    it, ig = ids_of(t["response"] + " " + t["condition"] + " " + t["scope"]), ids_of(g["response"] + " " + g["condition"] + " " + g["scope"])
    f["ids_f1"] = (2 * len(it & ig) / (len(it) + len(ig))) if (it or ig) else 1.0
    f["ids_jaccard"] = (len(it & ig) / len(it | ig)) if (it or ig) else 1.0
    f["n_atoms_ratio"] = (min(len(it), len(ig)) / max(len(it), len(ig))) if (it or ig) else 1.0
    f["len_ratio"] = (min(len(t["raw"]), len(g["raw"])) / max(len(t["raw"]), len(g["raw"]))) if (t["raw"] and g["raw"]) else 0.0
    return f


def _bag_f1(a, b):
    if not a and not b:
        return 1.0
    ov = sum((a & b).values())
    if not ov:
        return 0.0
    p, r = ov / sum(b.values()), ov / sum(a.values())
    return 2 * p * r / (p + r)


LEVELS = {  # name -> predicate over flags
    "L0_exact": lambda f: f["l0_exact"],
    "L1_alpha": lambda f: f["l1_alpha"],
    "L2_shape": lambda f: f["l2_shape"],
    "L2b_struct": lambda f: f["l2b_struct"],
    "L3_fields4of5": lambda f: f["n_fields_eq5"] >= 4,
    "L4_tok80": lambda f: f["tok_f1"] >= 0.8,
    "L5_resp_alpha": lambda f: f["resp_alpha_eq"],
    "L6_consts_ops": lambda f: f["consts_eq"] and f["ops_f1"] >= 0.999,
}


def greedy_match(S):
    """S[i][j] = (key tuple) for pred i, gt part j (higher better) with a bool 'ok'. one-to-one greedy by key. returns dict j->i for ok pairs"""
    pairs = sorted(((S[i][j][1], i, j) for i in range(len(S)) for j in range(len(S[i])) if S[i][j][0]), reverse=True)
    ui, uj, out = set(), set(), {}
    for _, i, j in pairs:
        if i in ui or j in uj:
            continue
        ui.add(i)
        uj.add(j)
        out[j] = i
    return out


def best_alignment(preds, parts):
    """one-to-one alignment of predicted sentences to reference parts for slot metrics. parts: list of list of parsed versions. Uses the best version per pair.
    returns list of (pred_idx or None, part_idx, version_idx or None, flags or None)"""
    cand = []
    for i, g in enumerate(preds):
        for j, vs in enumerate(parts):
            best = None
            for k, t in enumerate(vs):
                f = sent_flags(g, t)
                key = (f["l0_exact"], f["l1_alpha"], f["n_fields_eq5"], f["tok_f1"])
                if best is None or key > best[0]:
                    best = (key, k, f)
            cand.append((best[0], i, j, best[1], best[2]))
    cand.sort(key=lambda x: x[0], reverse=True)
    ui, uj, got = set(), set(), {}
    for key, i, j, k, f in cand:
        if i in ui or j in uj:
            continue
        ui.add(i)
        uj.add(j)
        got[j] = (i, k, f)
    return [(got[j][0], j, got[j][1], got[j][2]) if j in got else (None, j, None, None) for j in range(len(parts))], sorted(set(range(len(preds))) - ui)


def level_counts(preds, parts):
    """tp, fp, fn for every level (version aware: a part counts as matched if ANY version matches at that level). one-to-one."""
    out = {}
    for name, pred in LEVELS.items():
        S = []
        for i, g in enumerate(preds):
            row = []
            for j, vs in enumerate(parts):
                best = None
                for t in vs:
                    f = sent_flags(g, t)
                    if pred(f):
                        key = (f["tok_f1"],)
                        if best is None or key > best:
                            best = key
                row.append((best is not None, best or (0.0,)))
            S.append(row)
        m = greedy_match(S)
        tp = len(m)
        out[name] = (tp, len(preds) - tp, len(parts) - tp)
    return out


FIELDS = ["scope", "cond", "component", "timing", "response"]


def slot_counts(preds, parts, align, extra_pred):
    """per field slot TP/FP/FN and accuracy counters, as in v3 (a field is present if the sentence has it). unmatched parts count as empty predictions; unmatched predictions as FP."""
    def present(p):
        return {"scope": bool(p["scope_kw"]), "cond": bool(p["cond_kw"]), "component": bool(p["component"]), "timing": bool(p["tim"]), "response": bool(p["response"])}

    def eq(g, t, f):
        return {"scope": f["scope_eq"], "cond": f["cond_kw_eq"] and f["cond_expr_alpha_eq"], "component": f["component_eq"], "timing": f["timing_eq"], "response": f["resp_alpha_eq"]}
    c = {k: {"tp": 0, "fp": 0, "fn": 0, "acc_ok": 0, "acc_n": 0} for k in FIELDS}
    for pi, j, k, f in align:
        t = parts[j][k if k is not None else 0]
        pt = present(t)
        if pi is None:
            for fld in FIELDS:
                if pt[fld]:
                    c[fld]["fn"] += 1
                c[fld]["acc_n"] += 1
            continue
        g = preds[pi]
        pg = present(g)
        e = eq(g, t, f)
        for fld in FIELDS:
            c[fld]["acc_n"] += 1
            if pg[fld] and pt[fld] and e[fld]:
                c[fld]["tp"] += 1
                c[fld]["acc_ok"] += 1
            else:
                if pg[fld]:
                    c[fld]["fp"] += 1
                if pt[fld]:
                    c[fld]["fn"] += 1
                if (not pg[fld]) and (not pt[fld]):
                    c[fld]["acc_ok"] += 1
    for i in extra_pred:
        pg = present(preds[i])
        for fld in FIELDS:
            if pg[fld]:
                c[fld]["fp"] += 1
    return c


# ---------------------------------------------------------------- information preservation (input side, no reference needed except the reference numbers)
NEG_NL = re.compile(r"\b(not|no|never|neither|nor|without|cannot|can't|isn't|aren't|won't|n't)\b", re.I)
NEG_OUT = re.compile(r"!|\bnever\b|\bnot\b|!=")
COND_NL = re.compile(r"\b(when|whenever|if|once|as soon as|as long as|while|unless|upon|in case|after|until)\b", re.I)
TIME_NL = re.compile(r"\b(within|for|every|after|until|before|seconds?|secs?|ms|milliseconds?|minutes?|hours?|frames?|hz|ticks?|durations?|persist\w*)\b", re.I)
MODAL_NL = re.compile(r"\b(shall|should|must|will|may|can)\b", re.I)
CMP_NL = {"<": r"less than|below|under|smaller than|<", "<=": r"at most|no more than|not exceed|not greater|less than or equal|up to|<=", ">": r"greater than|more than|above|exceed|>",
          ">=": r"at least|no less than|greater than or equal|>=", "=": r"equal|same as|is set to|=", "!=": r"differ|not equal|!="}
PAREN = re.compile(r"\(([A-Za-z_][A-Za-z0-9_]*)\)")


def nl_features(nl):
    n = uni(nl)
    nums = numbers(n)
    return {"nl_len_chars": len(nl), "nl_len_words": len(re.findall(r"\w+", nl)), "nl_n_sentences": max(1, len(re.findall(r"[.;]\s|[.;]$", nl))),
            "nl_has_condition_cue": bool(COND_NL.search(n)), "nl_has_time_cue": bool(TIME_NL.search(n)), "nl_has_negation": bool(NEG_NL.search(n)), "nl_n_numbers": sum(nums.values()),
            "nl_n_distinct_numbers": len(nums), "nl_has_equation": bool(re.search(r"[A-Za-z_)\]]\s*=\s*[A-Za-z0-9_(\-]", n)), "nl_has_paren_hint": bool(PAREN.search(n)),
            "nl_n_paren_hints": len(PAREN.findall(n)), "nl_modal": (MODAL_NL.findall(n) or [""])[0].lower(), "nl_n_modals": len(MODAL_NL.findall(n)),
            "nl_n_cmp_phrases": sum(1 for v in CMP_NL.values() if re.search(v, n, re.I)), "nl_has_formula_symbols": bool(re.search(r"[−±≤≥Δθφψ]|sqrt|sin|cos", n, re.I))}


def info_preservation(nl, texts, gt_texts):
    n_in = numbers(nl)
    out_t = " ".join(texts)
    n_out = numbers(out_t)
    n_gt = numbers(" ".join(gt_texts))
    din = set(n_in)
    dout = set(n_out)
    dgt = set(n_gt)
    r = {}
    r["num_nl_recall"] = (len(din & dout) / len(din)) if din else None            # numbers of the input found in the output
    r["num_out_in_nl_precision"] = (len(din & dout) / len(dout)) if dout else None  # numbers of the output found in the input
    r["num_invented"] = len(dout - din - dgt)                                       # in output, in neither input nor reference
    r["num_dropped"] = len(din - dout)
    r["num_gt_recall"] = (len(dgt & dout) / len(dgt)) if dgt else None
    r["num_gt_precision"] = (len(dgt & dout) / len(dout)) if dout else None
    r["num_gt_added_not_in_nl"] = len(dgt - din)                                    # numbers the reference carries that the input does not (reference side addition)
    hints = [h.lower() for h in PAREN.findall(uni(nl))]
    oi = ids_of(out_t)
    r["paren_hint_recall"] = (sum(1 for h in hints if h in oi or h in out_t.lower()) / len(hints)) if hints else None
    r["nl_negation_in"] = bool(NEG_NL.search(uni(nl)))
    r["out_negation_present"] = bool(NEG_OUT.search(uni(out_t)))
    r["negation_agree"] = (r["nl_negation_in"] == r["out_negation_present"])
    r["negation_dropped"] = r["nl_negation_in"] and not r["out_negation_present"]
    r["negation_added"] = (not r["nl_negation_in"]) and r["out_negation_present"]
    ops_o = ops_of(out_t)
    cmp_in = {k for k, v in CMP_NL.items() if re.search(v, uni(nl), re.I)}
    r["cmp_ops_in_nl_present_in_out"] = (sum(1 for k in cmp_in if ops_o.get(k)) / len(cmp_in)) if cmp_in else None
    nlw = set(re.findall(r"[a-z]{4,}", uni(nl).lower()))
    ow = set(w for t in texts for w in words(t) if re.match(r"[a-z]{4,}$", w))
    r["nl_content_word_recall"] = (len(nlw & ow) / len(nlw)) if nlw else None
    gw = set(w for t in gt_texts for w in words(t) if re.match(r"[a-z]{4,}$", w))
    r["out_words_not_in_nl_ratio"] = (len(ow - nlw) / len(ow)) if ow else None
    r["out_words_not_in_nl_or_gt_ratio"] = (len(ow - nlw - gw) / len(ow)) if ow else None
    return r


# ---------------------------------------------------------------- slot audit (annotation of the natural language, S/U/A)
AUDIT_FIELDS = ("scope", "condition", "timing")


AUDIT_KEYS = ([f"aud_{f}_{x}" for f in AUDIT_FIELDS for x in ("has", "fill", "drop")]
              + ["aud_fill_n", "aud_fill_den", "aud_fill_rate", "aud_drop_n", "aud_drop_den", "aud_drop_rate"]
              + [f"aud_timing_fill_{k}" for k in ("always", "immediately", "eventually", "bounded", "never")]
              + ["aud_timing_fill_nonalways", "aud_cond_fill_kw", "aud_cond_fill_impl", "aud_n_slots_present"])


def _implication_top(p):
    r = re.sub(r"\s+", "", uni(p.get("response") or ""))
    return len(_split_top(_strip_outer(r), "=>")) > 1


def has_slot(p, fld):
    """does one parsed generated sentence carry the slot? condition counts a condition keyword or a top level implication in the response."""
    if fld == "scope":
        return bool(p["scope_kw"])
    if fld == "condition":
        return bool(p["cond_kw"]) or _implication_top(p)
    return bool(p["tim"])


def timing_kind(tim):
    w = set((tim or "").split())
    if "always" in w:
        return "always"
    if "immediately" in w:
        return "immediately"
    if "eventually" in w or "next" in w:
        return "eventually"
    if "never" in w:
        return "never"
    return "bounded" if w else "none"


def slot_audit(preds, ann):
    """Compare what the output carries with what the natural language states (annotation S stated, U not stated, A ambiguous).
    fill = the output has a slot that the natural language does not state (U). drop = the output lacks a slot that the natural language states (S).
    Slots annotated A are not counted in any rate. Returns {} when there is no annotation or no accepted sentence."""
    if not ann:
        return {}
    if not preds:
        return {k: None for k in AUDIT_KEYS}
    r = {}
    fn = fd = dn = dd = 0
    for f in AUDIT_FIELDS:
        lab = ann.get(f)
        has = any(has_slot(p, f) for p in preds)
        r[f"aud_{f}_has"] = int(has)
        r[f"aud_{f}_fill"] = (int(has) if lab == "U" else None)
        r[f"aud_{f}_drop"] = (int(not has) if lab == "S" else None)
        if lab == "U":
            fd += 1
            fn += int(has)
        if lab == "S":
            dd += 1
            dn += int(not has)
    r.update({"aud_fill_n": fn, "aud_fill_den": fd, "aud_fill_rate": (fn / fd) if fd else None,
              "aud_drop_n": dn, "aud_drop_den": dd, "aud_drop_rate": (dn / dd) if dd else None})
    # what was filled in
    kinds = {timing_kind(p["tim"]) for p in preds}
    u_t = ann.get("timing") == "U"
    for k in ("always", "immediately", "eventually", "bounded", "never"):
        r[f"aud_timing_fill_{k}"] = (int(k in kinds) if u_t else None)
    r["aud_timing_fill_nonalways"] = (int(bool(kinds - {"always", "none"})) if u_t else None)
    u_c = ann.get("condition") == "U"
    r["aud_cond_fill_kw"] = (int(any(bool(p["cond_kw"]) for p in preds)) if u_c else None)
    r["aud_cond_fill_impl"] = (int(any(_implication_top(p) for p in preds)) if u_c else None)
    # the same sentence set seen from the other side: how many slots are present at all
    r["aud_n_slots_present"] = sum(r[f"aud_{f}_has"] for f in AUDIT_FIELDS)
    return r


# ---------------------------------------------------------------- main scoring
def load_annotation(path):
    ann = {d["id"]: d for d in jl(path)}
    return ann


def load_review(path):
    if not os.path.exists(path):
        return {}
    return {k: v["verdict"] for k, v in json.load(open(path, encoding="utf-8")).get("items", {}).items()}


def load_all(res, data):
    items = {d["id"]: d for d in jl(data)}
    units = jl(os.path.join(res, "units_scored.jsonl"))
    rlz = jl(os.path.join(res, "fret_realizability.jsonl"))
    ltl = {r["sentence"]: r for r in jl(os.path.join(res, "fret_ltl.jsonl"))}
    gt_rlz = collections.defaultdict(list)
    for r in rlz:
        if r.get("arm") == "GT":
            gt_rlz[r["item_id"]].append((r.get("gt_ref"), r.get("result")))
    return items, units, ltl, gt_rlz


def unit_rows(items, units, ltl, gt_rlz, ann=None, review=None):
    ann = ann or {}
    review = review or {}
    rows, pairs = [], []
    queue = {}
    for u in units:
        it = items[u["item_id"]]
        parts_raw = [[v["fretish"] for v in p] for p in it["gt_parts"]]
        parts = [[parsed(s) for s in p] for p in parts_raw]
        gt_prim = [p[0] for p in parts_raw]
        gt_all = [s for p in parts_raw for s in p]
        gstat = [r for _, r in gt_rlz.get(it["id"], [])]
        for var in ("v0", "vn", "vf"):
            d = u["variants"].get(var)
            if d is None:
                continue
            texts = list(d.get("accepted_texts") or [])
            alltexts = list(d.get("texts") or [])
            preds = [parsed(t) for t in texts]
            row = {"item_id": u["item_id"], "arm": u["arm"], "group": group_of(u["arm"]), "base": base_of(u["arm"]), "rep": u["rep"], "variant": var, "stratum": it.get("stratum"),
                   "challenge": it.get("challenge"), "n_parts": len(parts), "n_versions": sum(len(p) for p in parts), "has_versions": it.get("has_versions"),
                   "n_pred_all": len(alltexts), "n_pred_accepted": len(texts), "pre": d.get("pre"), "code": d.get("code"), "status": d.get("status"), "failed": int(bool(d.get("failed"))),
                   "fail_stage": d.get("fail_stage"), "parser_accepted_all": int(bool(alltexts) and len(texts) == len(alltexts)), "no_output": int(d.get("pre") == "pipeline"),
                   "parse_rejected": int(d.get("pre") == "parse_error"), "realizable": int(d.get("status") == "realizable"), "unrealizable": int(d.get("status") == "unrealizable"),
                   "unknown": int(d.get("status") == "unknown"), "not_run": int(d.get("status") == "not_run"), "n_rounds": u.get("n_rounds"), "tokens_total": u.get("tokens_total"),
                   "wall_s": u.get("wall_s"), "n_norm_rules": len(d.get("norm_rules") or []), "n_rules": len(d.get("rules") or []), "n_slot_fixes": len(d.get("slot_fixes") or []),
                   "n_rejections": len(d.get("rejections") or []), "gt_all_realizable": int(bool(gstat) and all(s == "realizable" for s in gstat)),
                   "gt_any_unknown": int(any(s == "unknown" for s in gstat)), "gt_status_set": "|".join(sorted(set(gstat))),
                   "map_review": review.get(u["item_id"], "not_id_order") if it.get("mapping_basis") == "id_order" else "not_id_order",
                   "ann_scope": (ann.get(u["item_id"]) or {}).get("scope", ""), "ann_condition": (ann.get(u["item_id"]) or {}).get("condition", ""),
                   "ann_timing": (ann.get(u["item_id"]) or {}).get("timing", "")}
            row["count_match"] = int(len(texts) == len(parts))
            row["count_diff"] = len(texts) - len(parts)
            row["split_ratio"] = (len(texts) / len(parts)) if parts else None
            lc = level_counts(preds, parts) if preds else {k: (0, 0, len(parts)) for k in LEVELS}
            for name, (tp, fp, fn) in lc.items():
                p, r, f = prf(tp, fp, fn)
                row.update({f"{name}_tp": tp, f"{name}_fp": fp, f"{name}_fn": fn, f"{name}_P": p, f"{name}_R": r, f"{name}_F1": f,
                            f"{name}_item_exact": int(tp == len(parts) and fp == 0), f"{name}_part_acc": tp / len(parts) if parts else None})
            align, extra = best_alignment(preds, parts) if preds else ([(None, j, None, None) for j in range(len(parts))], [])
            sc = slot_counts(preds, parts, align, extra)
            for fld, c in sc.items():
                p, r, f = prf(c["tp"], c["fp"], c["fn"])
                row.update({f"slot_{fld}_tp": c["tp"], f"slot_{fld}_fp": c["fp"], f"slot_{fld}_fn": c["fn"], f"slot_{fld}_P": p, f"slot_{fld}_R": r, f"slot_{fld}_F1": f,
                            f"slot_{fld}_acc": (c["acc_ok"] / c["acc_n"]) if c["acc_n"] else None})
            for tag, flds in (("5", FIELDS), ("3", ["scope", "cond", "timing"])):
                tp = sum(sc[x]["tp"] for x in flds)
                fp = sum(sc[x]["fp"] for x in flds)
                fn = sum(sc[x]["fn"] for x in flds)
                p, r, f = prf(tp, fp, fn)
                row.update({f"slot{tag}_micro_P": p, f"slot{tag}_micro_R": r, f"slot{tag}_micro_F1": f, f"slot{tag}_acc": (sum(sc[x]["acc_ok"] for x in flds) / sum(sc[x]["acc_n"] for x in flds))})
            # similarity of the aligned pairs
            ms = [a for a in align if a[0] is not None]
            for key in ("tok_f1", "char_cos3", "lev_sim", "resp_tok_f1", "ops_f1", "consts_f1", "ids_f1", "ids_jaccard", "n_atoms_ratio", "len_ratio"):
                row["aln_" + key] = mean([a[3][key] for a in ms]) if ms else (0.0 if parts else None)
            for key in ("consts_eq", "resp_shape_eq", "resp_form_eq", "timing_num_eq", "component_eq", "scope_eq", "cond_present_eq", "resp_exact_eq", "l2b_struct"):
                row["aln_" + key] = mean([float(a[3][key]) for a in ms]) if ms else (0.0 if parts else None)
            row["aligned_parts"] = len(ms)
            # information preservation
            ip = info_preservation(it["raw_nl"], texts, gt_all)
            row.update({"ip_" + k: (int(v) if isinstance(v, bool) else v) for k, v in ip.items()})
            # LTL strings: counts and plain string equality only
            gen_ltl = [ltl.get(t) or {} for t in texts]
            row["ltl_available"] = int(bool(texts) and all(g.get("ltl_ft") for g in gen_ltl))
            row["ltl_ft_chars"] = mean([len(g.get("ltl_ft") or "") for g in gen_ltl])
            gt_ft = {norm_ltl(v.get("future_time", "")) for p in it["gt_parts"] for v in p for v in [v["ltl"]]}
            gt_pt = {norm_ltl(v.get("past_time", "")) for p in it["gt_parts"] for v in p for v in [v["ltl"]]}
            row["ltl_ft_string_eq_any"] = int(any(norm_ltl(g.get("ltl_ft")) in gt_ft for g in gen_ltl)) if gen_ltl else 0
            row["ltl_pt_string_eq_any"] = int(any(norm_ltl(g.get("ltl_pt")) in gt_pt for g in gen_ltl)) if gen_ltl else 0
            row["ltl_ft_string_eq_parts"] = sum(1 for j, vs in enumerate(it["gt_parts"]) if any(norm_ltl(g.get("ltl_ft")) == norm_ltl(v["ltl"]["future_time"]) for g in gen_ltl for v in vs))
            row["ltl_ft_alpha_eq_parts"] = sum(1 for j, vs in enumerate(it["gt_parts"]) if any(alpha_ltl(g.get("ltl_ft")) == alpha_ltl(v["ltl"]["future_time"]) for g in gen_ltl for v in vs))
            row.update(slot_audit(preds, ann.get(u["item_id"])))
            row["gen_scope_types"] = "|".join(sorted({str(g.get("scope")) for g in gen_ltl}))
            row["gen_timing_types"] = "|".join(sorted({str(g.get("timing")) for g in gen_ltl}))
            rows.append(row)
            if var in ("vf", "v0"):
                pairs.append({"item_id": u["item_id"], "arm": u["arm"], "rep": u["rep"], "variant": var, "status": d.get("status"), "code": d.get("code"),
                              "predicted": texts, "rejected_or_unaccepted": [t for t in alltexts if t not in texts],
                              "alignment": [{"part": j, "pred_idx": pi, "version_idx": k, "pred": texts[pi] if pi is not None else None,
                                             "ref_version": it["gt_parts"][j][k if k is not None else 0]["reqid"],
                                             "flags": {a: (round(b, 4) if isinstance(b, float) else b) for a, b in (f or {}).items()}} for pi, j, k, f in align],
                              "unaligned_pred": [texts[i] for i in extra]})
            if var == "vf":
                for pi, j, k, f in align:
                    pass
                for i, t in enumerate(texts):
                    key = (u["item_id"], t)
                    q = queue.setdefault(key, {"item_id": u["item_id"], "sentence": t, "arms": collections.Counter(), "n_units": 0})
                    q["arms"][u["arm"]] += 1
                    q["n_units"] += 1
    return rows, pairs, queue


def norm_ltl(s):
    return re.sub(r"\s+", "", s or "")


def alpha_ltl(s):
    s = s or ""
    return " ".join(alpha_form([re.sub(r"\s+", " ", s)]))


def judgment_queue(items, queue, ltl):
    out = []
    for (iid, sent), q in sorted(queue.items()):
        it = items[iid]
        g = parsed(sent)
        parts = []
        for j, vs in enumerate(it["gt_parts"]):
            best = None
            for k, v in enumerate(vs):
                f = sent_flags(g, parsed(v["fretish"]))
                key = (f["l0_exact"], f["l1_alpha"], f["n_fields_eq5"], f["tok_f1"])
                if best is None or key > best[0]:
                    best = (key, k, f)
            parts.append((best[0], j, best[1], best[2]))
        parts.sort(key=lambda x: x[0], reverse=True)
        key, j, k, f = parts[0]
        v = it["gt_parts"][j][k]
        gl = ltl.get(sent) or {}
        out.append({"item_id": iid, "raw_nl": it["raw_nl"], "generated": sent, "used_by_arms": dict(q["arms"]), "n_units": q["n_units"],
                    "generated_ltl": {"parser_ok": gl.get("parser_ok"), "ft": gl.get("ltl_ft"), "pt": gl.get("ltl_pt"), "scope": gl.get("scope"), "condition": gl.get("condition"),
                                      "timing": gl.get("timing"), "response": gl.get("response"), "post_condition": gl.get("post_condition"), "variables": gl.get("variables")},
                    "best_ref_part": j, "n_parts": len(it["gt_parts"]), "best_ref_version": v["reqid"], "reference": v["fretish"], "reference_fields": v["fields"],
                    "reference_ltl": v["ltl"], "other_versions": [x["reqid"] for x in it["gt_parts"][j] if x["reqid"] != v["reqid"]],
                    "flags": {a: (round(b, 4) if isinstance(b, float) else b) for a, b in f.items()}})
    return out


# ---------------------------------------------------------------- aggregation
def num_cols(rows):
    cols = []
    for k in rows[0]:
        vals = [r[k] for r in rows if r[k] is not None]
        if vals and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in vals) and k not in ("rep",):
            cols.append(k)
    return cols


_BOOT_IDX = {}


def boot_ci(per_item, rng):
    ks = list(per_item)
    if not ks:
        return None, None, None
    pt = mean([per_item[k] for k in ks])
    if len(ks) < 2:
        return pt, pt, pt
    n = len(ks)
    ix = _BOOT_IDX.get(n)
    if ix is None:                                         # resample positions are cached per sample size (speed); seeded by SEED and n
        r2 = random.Random(SEED * 1000 + n)
        ix = _BOOT_IDX[n] = [[r2.randrange(n) for _ in range(n)] for _ in range(BOOT)]
    v = [per_item[k] for k in ks]
    g = v.__getitem__
    bs = sorted(sum(map(g, row)) / n for row in ix)
    return pt, bs[int(0.025 * BOOT)], bs[int(0.975 * BOOT) - 1]


def summarize(rows, cols, group_keys):
    rng = random.Random(SEED)
    out = []
    for gb in group_keys:
        buckets = collections.defaultdict(list)
        for r in rows:
            buckets[(gb, str(r[gb]) if gb != "ALL" else "all", r["arm"], r["variant"])].append(r)
        for (gname, key, arm, var), rs in sorted(buckets.items()):
            for m in cols:
                per_item = collections.defaultdict(list)
                for r in rs:
                    if r[m] is not None:
                        per_item[r["item_id"]].append(r[m])
                if not per_item:
                    continue
                pi = {k: sum(v) / len(v) for k, v in per_item.items()}
                pt, lo, hi = boot_ci(pi, rng)
                out.append({"group_by": gname, "key": key, "arm": arm, "variant": var, "metric": m, "mean": pt, "ci_lo": lo, "ci_hi": hi, "n_items": len(pi), "n_units": len(rs)})
    return out


def paired(rows, cols):
    rng = random.Random(SEED + 1)
    by = collections.defaultdict(dict)
    for r in rows:
        by[(r["arm"], r["variant"])].setdefault(r["item_id"], []).append(r)
    arms = sorted({r["arm"] for r in rows})
    pairs = []
    for a in arms:
        if a != "DIRECT":
            pairs.append((a, "DIRECT"))
        if (a.endswith("+G") or a.endswith("+R") or a.endswith("+U") or a.endswith("+V")) and (a, base_of(a)) not in pairs:
            pairs.append((a, base_of(a)))
        if "PARA" in arms and a not in ("DIRECT", "PARA") and "+" not in a:
            pairs.append((a, "PARA"))                      # free template arm minus the plain English control
    out = []
    for a, b in pairs:
        for var in ("v0", "vn", "vf"):
            A, B = by.get((a, var), {}), by.get((b, var), {})
            ids = sorted(set(A) & set(B))
            for m in cols:
                d = {}
                for i in ids:
                    xa = [r[m] for r in A[i] if r[m] is not None]
                    xb = [r[m] for r in B[i] if r[m] is not None]
                    if xa and xb:
                        d[i] = sum(xa) / len(xa) - sum(xb) / len(xb)
                if not d:
                    continue
                pt, lo, hi = boot_ci(d, rng)
                out.append({"arm": a, "versus": b, "variant": var, "metric": m, "mean_diff": pt, "ci_lo": lo, "ci_hi": hi, "n_items": len(d),
                            "items_arm_better": sum(1 for x in d.values() if x > 0), "items_equal": sum(1 for x in d.values() if x == 0), "items_arm_worse": sum(1 for x in d.values() if x < 0)})
    return out


def consistency(items, units, ann=None):
    ann = ann or {}
    out = []
    by = collections.defaultdict(list)
    for u in units:
        by[(u["item_id"], u["arm"])].append(u)
    for (iid, arm), us in sorted(by.items()):
        for var in ("v0", "vf"):
            ds = [u["variants"].get(var) for u in sorted(us, key=lambda x: x["rep"]) if u["variants"].get(var)]
            if len(ds) < 2:
                continue
            seqs = [[t for t in (d.get("accepted_texts") or [])] for d in ds]
            keys_l0 = [tuple(l0_key(t) for t in s) for s in seqs]
            ps = [[parsed(t) for t in s] for s in seqs]
            keys_a = [tuple(p["a_scope"] + "|" + p["scope_kw"] + "|" + p["cond_kw"] + "|" + p["a_cond"] + "|" + p["tim"] + str(p["tnum"]) + "|" + p["a_resp"] for p in pp) for pp in ps]
            keys_s = [tuple((p["scope_kw"], p["cond_kw"], p["tim"], p["resp_form"]) for p in pp) for pp in ps]
            keys_comp = [tuple(comp_canon(p["component"]) for p in pp) for pp in ps]
            ids = [frozenset(x for p in pp for x in ids_of(p["raw"])) for pp in ps]
            n = len(ds)
            pairs_ = list(itertools.combinations(range(n), 2))
            def frac(f):
                return sum(1 for i, j in pairs_ if f(i, j)) / len(pairs_)
            out.append({"item_id": iid, "arm": arm, "variant": var, "n_reps": n, "pair_identical_sentence": frac(lambda i, j: keys_l0[i] == keys_l0[j] and keys_l0[i] != ()),
                        "pair_identical_alpha": frac(lambda i, j: keys_a[i] == keys_a[j] and keys_a[i] != ()), "pair_identical_struct": frac(lambda i, j: keys_s[i] == keys_s[j] and keys_s[i] != ()),
                        "pair_same_component": frac(lambda i, j: keys_comp[i] == keys_comp[j] and keys_comp[i] != ()), "pair_same_identifier_set": frac(lambda i, j: ids[i] == ids[j] and ids[i]),
                        "pair_id_jaccard": mean([(len(ids[i] & ids[j]) / len(ids[i] | ids[j])) if (ids[i] | ids[j]) else 1.0 for i, j in pairs_]),
                        "pair_tok_f1": mean([tok_f1(" ".join(seqs[i]), " ".join(seqs[j])) for i, j in pairs_]), "pair_same_status": frac(lambda i, j: ds[i].get("status") == ds[j].get("status")),
                        "pair_same_n_sentences": frac(lambda i, j: len(seqs[i]) == len(seqs[j])), "n_distinct_sentence_sets": len(set(keys_l0)), "n_distinct_alpha_forms": len(set(keys_a)),
                        "n_distinct_struct": len(set(keys_s)), "all_reps_realizable": int(all(d.get("status") == "realizable" for d in ds))}
                       | _fill_consistency(ps, ann.get(iid)))
    return out


def _fill_consistency(ps, a):
    """for slots the natural language does not state (U): do the repetitions agree on filling it and on what they fill in? 1 = all repetitions the same, 0 = they differ."""
    if not a:
        return {}
    r = {}
    if a.get("timing") == "U":
        sets = [frozenset(timing_kind(p["tim"]) for p in pp) for pp in ps]
        r["u_timing_kinds_agree"] = int(len(set(sets)) == 1)
        r["u_timing_n_distinct"] = len(set(sets))
    if a.get("condition") == "U":
        sets = [any(has_slot(p, "condition") for p in pp) for pp in ps]
        r["u_cond_fill_agree"] = int(len(set(sets)) == 1)
    return r


def item_features(items, ann=None, review=None):
    ann = ann or {}
    review = review or {}
    out = []
    for it in items.values():
        f = {"item_id": it["id"], "challenge": it["challenge"], "stratum": it["stratum"], "n_parts": it["n_parts"], "n_versions": sum(len(p) for p in it["gt_parts"]), "has_versions": it["has_versions"],
             "mapping_basis": it["mapping_basis"], "gt_chars_primary": sum(len(p[0]["fretish"]) for p in it["gt_parts"]),
             "map_review": review.get(it["id"], "not_id_order") if it["mapping_basis"] == "id_order" else "not_id_order"}
        a = ann.get(it["id"]) or {}
        f.update({"ann_scope": a.get("scope", ""), "ann_condition": a.get("condition", ""), "ann_timing": a.get("timing", ""), "ann_status": a.get("status", "")})
        f.update(nl_features(it["raw_nl"]))
        f.update({"gt_" + k: v for k, v in it["gt_form"].items()})
        prim = [parsed(p[0]["fretish"]) for p in it["gt_parts"]]
        f["gt_scope_kws"] = "|".join(sorted({p["scope_kw"] or "none" for p in prim}))
        f["gt_timing_kws"] = "|".join(sorted({p["tim"] or "none" for p in prim}))
        f["gt_components"] = "|".join(sorted({p["component"] for p in prim}))
        f["gt_n_distinct_identifiers"] = len({x for p in prim for x in ids_of(p["raw"])})
        f["gt_n_numbers"] = sum(sum(numbers(p["raw"]).values()) for p in prim)
        f["gt_uses_function_calls"] = int(any(re.search(r"\b(sin|cos|sqrt|mag|dot|det_3x3|persisted|preBool|preReal|preInt)\s*\(", p["raw"]) for p in prim))
        out.append(f)
    return out


def failures(units):
    c = collections.Counter()
    for u in units:
        for var, d in u["variants"].items():
            c[(u["arm"], var, d.get("pre"), d.get("code") or "", d.get("status"), d.get("fail_stage") or "")] += 1
    return [{"arm": a, "variant": v, "pre": p, "code": cd, "status": s, "fail_stage": fs, "n_units": n} for (a, v, p, cd, s, fs), n in sorted(c.items())]


def write_csv(path, rows):
    if not rows:
        open(path, "w").write("")
        return
    keys = list(rows[0].keys())
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


GLOSSARY = """# Metric glossary (score_lm.py)

All values are string level counts or similarities. None of them says that a generated sentence means the same as the reference. A judge decides that from lm_judgment_queue.jsonl.

Unit = item x arm x repetition. Variant v0 = first answer, vn = first answer after the mechanical syntax normalizer, vf = final answer after up to 2 rounds of official parser feedback.
Part = one reference FRETish of an item that the natural language requires (an item can have several parts, for example nine matrix elements). Version = an alternative published formalization of the same part (v1, v2 ...).
A part is covered if any of its versions matches. Matching is one-to-one between predicted sentences and parts, greedy by token F1.

## Levels (name_tp, name_fp, name_fn, name_P, name_R, name_F1, name_item_exact, name_part_acc)
- L0_exact: same text after lower case, whitespace removal, dropping the word `the`.
- L1_alpha: same scope keyword, condition keyword, timing words and numbers, and scope, condition and response expressions equal after commutative sorting and joint renaming of identifiers in order of first occurrence (names ignored, structure and constants kept). Component name is ignored.
- L2_shape: as L1 but identifiers are all replaced by one symbol (loses the identity of variables, keeps operators, constants, nesting).
- L2b_struct: scope keyword, condition present, timing class, response form (if-then, implication, negation, plain). No constants.
- L3_fields4of5: at least 4 of the 5 fields (scope, condition presence, component, timing with numbers, response alpha form) equal.
- L4_tok80: token F1 of the whole sentence at least 0.8.
- L5_resp_alpha: response expression alpha-equal only.
- L6_consts_ops: all numeric constants and all operators of response and condition equal as multisets.
tp = parts covered; fp = predicted sentences not used; fn = parts not covered. P = tp/(tp+fp), R = tp/(tp+fn), F1 = harmonic mean. item_exact = all parts covered and no extra sentence (the Accuracy at item level). part_acc = tp/n_parts.
Units without any accepted sentence have tp = 0, fp = 0, fn = n_parts (P undefined, counted as missing in means, R = 0).

## Slot metrics (slot_<field>_*, slot5_*, slot3_*)
Fields: scope, cond, component, timing, response. A field is present if the sentence has it. TP = both present and equal; FP = predicted present and not TP; FN = reference present and not TP.
slot_<field>_acc = share of aligned slots that match, both-absent counts as a match; unmatched parts count as mismatches. slot5 = micro over five fields; slot3 = micro over scope, cond, timing.
In the Lockheed Martin reference 71 of 84 parts are `always` without scope and 80 of 84 have no condition field (the condition is inside the response by `=>`), so timing, scope and cond slots are dominated by both-absent matches. Read slot_response_* and the L levels first.

## Alignment similarity (aln_*)
Mean over aligned pairs: tok_f1, char_cos3 (character trigram cosine), lev_sim, resp_tok_f1, ops_f1 (operators multiset F1), consts_f1 (numeric constants multiset F1), ids_f1 and ids_jaccard (identifier sets), n_atoms_ratio, len_ratio, and shares of equal consts, response shape, response form, timing numbers, component, scope, condition presence, exact normalized response, structure.

## Validity and cost
pre: parsed, parse_error, pipeline (no output). status: realizable, unrealizable, unknown, not_run, parse_error, pipeline. failed = status is not realizable. gt_all_realizable and gt_any_unknown describe the reference parts of the item under the same realizability check.
no_output, parse_rejected, parser_accepted_all, realizable, unrealizable, unknown, not_run are 0/1 flags. n_rounds = feedback rounds used. tokens_total, wall_s as recorded. n_norm_rules, n_rules, n_slot_fixes, n_rejections count mechanical edits and parser rejections.
count_match = number of accepted sentences equals the number of parts; count_diff = accepted minus parts; split_ratio = accepted / parts.

## Information preservation (ip_*, input side)
num_nl_recall: share of distinct numbers of the natural language that appear in the output. num_out_in_nl_precision: share of output numbers that are in the natural language. num_invented: output numbers in neither the natural language nor any reference. num_dropped: natural language numbers missing from the output. num_gt_recall and num_gt_precision: same against the numbers of the references. num_gt_added_not_in_nl: reference numbers that the natural language does not contain (reference side addition, not an error of the tool).
paren_hint_recall: words in parentheses in the natural language (variable hints) found in the output. negation_*: natural language has a negation word, output has `!`, `never` or `not`; negation_dropped and negation_added are the disagreements. cmp_ops_in_nl_present_in_out: comparison phrases of the natural language and the matching operators in the output. nl_content_word_recall, out_words_not_in_nl_ratio, out_words_not_in_nl_or_gt_ratio: word overlap based invention indicators.

## LTL string level (ltl_*)
Taken from the official compile output (fret_ltl.jsonl) of each accepted sentence. ltl_available = every accepted sentence compiled. ltl_ft_string_eq_any / ltl_pt_string_eq_any = some generated formula string equals some reference formula string (whitespace removed). ltl_ft_string_eq_parts = number of parts with an equal future time string; ltl_ft_alpha_eq_parts = same after identifier renaming. ltl_ft_chars = length. gen_scope_types, gen_timing_types = FRET semantic scope and timing types of the generated sentences. String equality is NOT semantic equivalence.

## Consistency (lm_consistency.csv, per item, arm, variant over repetitions)
pair_identical_sentence (normalized text), pair_identical_alpha (names ignored), pair_identical_struct, pair_same_component, pair_same_identifier_set, pair_id_jaccard, pair_tok_f1, pair_same_status, pair_same_n_sentences, n_distinct_sentence_sets, n_distinct_alpha_forms, n_distinct_struct, all_reps_realizable.

## Item features (lm_item_features.csv)
nl_* are cues counted in the natural language (condition words, time words, negation, numbers, equation symbols, parenthesis hints, modal verb, comparison phrases). gt_* describe the reference (parts, versions, scope and timing keywords, components, identifiers, numbers, function calls).

## Aggregation
lm_summary.csv: mean per item first (over repetitions), then over items; ci_lo and ci_hi from an item level bootstrap (2000 resamples, seed 20261101; the resample positions are drawn once per sample size and shared by all metrics). group_by ALL, stratum, challenge, group (D free-text direct, P plain English rewrite control, F free template, G rule text, R rule assembly, U no-completion rules, V principled timing inference), base template, has_versions.
lm_paired_vs_direct.csv: per item mean differences arm minus DIRECT, +G, +R, +U, +V minus the free arm of the same template (DIRECT+V minus DIRECT), and free template arms minus PARA (the plain English control), with item level bootstrap intervals and win, tie, loss counts.

## Slot audit (aud_*; needs data/lm_slot_annotation.jsonl)
The annotation says, for the natural language only (the reference is not looked at), whether scope, condition and timing are stated (S), not stated (U) or ambiguous (A). It is a draft by one rater until a second rater has labelled the same items.
- aud_{scope,condition,timing}_has: 1 if any accepted sentence of the unit carries the slot. Condition counts a condition keyword (when, whenever, if, upon, unless, where) or a top level implication in the response. Timing counts any timing word.
- aud_{slot}_fill: for slots annotated U, 1 if the output carries the slot anyway (a completion). Rate over units = completion rate. None for slots annotated S or A.
- aud_{slot}_drop: for slots annotated S, 1 if the output lacks the slot (an omission). None for U and A.
- aud_fill_n, aud_fill_den, aud_fill_rate and aud_drop_n, aud_drop_den, aud_drop_rate: the same counted over the three slots of one unit (A slots excluded).
- aud_timing_fill_{always,immediately,eventually,bounded,never}: for timing annotated U, which kind of timing the output chose (bounded = within, for, after, until, before). aud_timing_fill_nonalways: a timing other than always.
- aud_cond_fill_kw, aud_cond_fill_impl: for condition annotated U, whether the completion is a condition keyword or an implication inside the response.
- aud_n_slots_present: number of the three slots present.
- lm_consistency.csv: u_timing_kinds_agree, u_timing_n_distinct, u_cond_fill_agree show whether the repetitions agree on what they fill into a slot that the natural language leaves open (arbitrariness).
- map_review: review verdict of the id_order mapping of the item (consistent, consistent_semantics_unverified, partial_gap, suspicious, or not_id_order). ann_scope, ann_condition, ann_timing: the annotation. Summaries are also grouped by map_review, ann_timing and ann_condition.
These columns count string level features of the output. They do not say whether the completion is wrong; the judge decides that.
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["all"])
    ap.add_argument("--results", default="results_lm")
    ap.add_argument("--data", default=os.path.join(HERE, "data/lm_items.jsonl"))
    ap.add_argument("--annotation", default=os.path.join(HERE, "data/lm_slot_annotation.jsonl"), help="slot annotation of the natural language (S/U/A); audit columns are skipped when the file is missing")
    ap.add_argument("--review", default=os.path.join(HERE, "data/lm_mapping_review.json"))
    a = ap.parse_args()
    items, units, ltl, gt_rlz = load_all(a.results, a.data)
    ann = load_annotation(a.annotation)
    review = load_review(a.review)
    if not units:
        raise SystemExit("no units_scored.jsonl rows")
    md = os.path.join(a.results, "metrics")
    os.makedirs(md, exist_ok=True)
    rows, pairs, queue = unit_rows(items, units, ltl, gt_rlz, ann, review)
    write_csv(os.path.join(md, "lm_unit_metrics.csv"), rows)
    cols = num_cols(rows)
    for r in rows:
        r["group_all"] = "all"
        r["ALL"] = "all"
        r["has_versions_s"] = str(r["has_versions"])
    rows_s = summarize(rows, cols, ["ALL", "stratum", "challenge", "group", "base", "has_versions_s", "map_review", "ann_timing", "ann_condition"])
    write_csv(os.path.join(md, "lm_summary.csv"), rows_s)
    write_csv(os.path.join(md, "lm_paired_vs_direct.csv"), paired(rows, cols))
    write_csv(os.path.join(md, "lm_consistency.csv"), consistency(items, units, ann))
    write_csv(os.path.join(md, "lm_item_features.csv"), item_features(items, ann, review))
    write_csv(os.path.join(md, "lm_failures.csv"), failures(units))
    with open(os.path.join(md, "lm_judgment_queue.jsonl"), "w", encoding="utf-8") as f:
        for q in judgment_queue(items, queue, ltl):
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    with open(os.path.join(md, "lm_pairs.jsonl"), "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    open(os.path.join(md, "METRICS_GLOSSARY.md"), "w", encoding="utf-8").write(GLOSSARY)
    print("unit rows", len(rows), "columns", len(rows[0]), "numeric metrics", len(cols), "summary rows", len(rows_s), "judgment queue", len(queue))


if __name__ == "__main__":
    main()
