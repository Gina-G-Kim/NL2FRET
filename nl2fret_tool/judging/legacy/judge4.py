#!/usr/bin/env python3
"""judge4: judge2 + (a) reference-free sanity (satisfiable / valid) and (b) separating witness traces for the relation to a reference.

Definitions (Cavezza, Alrajeh, Gyorgy 2018, arXiv 1805.03151): phi2 is weaker than phi1 iff phi1 -> phi2 is valid.
Two existence flags, both bounded (horizon h, past-time semantics evaluated at the last step):
  MISS  = exists trace with generated true and reference false  (generated lets a reference violation pass)
  ALARM = exists trace with reference true and generated false  (generated rejects behavior the reference accepts)
Witnesses are validated by an independent concrete evaluator (not z3)."""
import sys, itertools
from fractions import Fraction
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import z3
import judge2 as J
from judge2 import prep, ren, vars_of, setup, timed_ops, window_of, Unsupported, CMP, ARI, MAXPERM


# ---------- constant-like identifiers and lexical support (anchor modes 'lex' and 'strict') ----------
import re as _re
def const_vars(a, acc=None, ok=None):
    """identifiers that occur ONLY as the right operand of '=' or '!=' (enumeration-like constants, as in variable_policy.md). -> set"""
    top = acc is None
    if top: acc, ok = {}, {}
    if not isinstance(a, tuple): return set()
    if a[0] == "var":
        acc[a[1]] = False          # an occurrence outside the right-operand position (marked True by the parent below when it is one)
        return set()
    if a[0] in ("=", "!=") and len(a) == 3:
        const_vars(a[1], acc, ok)
        if isinstance(a[2], tuple) and a[2][0] == "var":
            ok.setdefault(a[2][1], True)
        else:
            const_vars(a[2], acc, ok)
    else:
        for x in a[1:]:
            if isinstance(x, tuple): const_vars(x, acc, ok)
            elif isinstance(x, list):
                for y in x:
                    if isinstance(y, tuple): const_vars(y, acc, ok)
    if top:
        return {v for v in ok if v not in acc}
    return set()

def _tokens(name):
    n = _re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return {t for t in _re.split(r"[_\W]+", n.lower()) if t}

def lex_compatible(gname, rname):
    """both names are enumeration constants; they correspond only if the word tokens of one are contained in the tokens of the other (string evidence, no model)"""
    tg, tr = _tokens(gname), _tokens(rname)
    return bool(tg) and bool(tr) and (tg <= tr or tr <= tg)

# ---------- independent concrete evaluator ----------
def evc(a, i, T, wmap, memo):
    key = (id(a), i)
    if key in memo: return memo[key]
    k = a[0]
    if k == "TRUE": r = True
    elif k == "FALSE": r = False
    elif k == "num": r = Fraction(a[1])
    elif k == "neg": r = -evc(a[1], i, T, wmap, memo)
    elif k == "var": r = (i == 0) if a[1] == "FTP" else T[a[1]][i]
    elif k == "fn":
        if a[1].startswith("absReal#"):
            x = evc(a[2], i, T, wmap, memo); r = abs(x)
        else: raise Unsupported("fn " + a[1])
    elif k.startswith(("H[", "O[")):
        l, rr = window_of(k); l, rr = wmap.get(l, l), wmap.get(rr, rr)
        js = list(range(max(0, i - rr), i - l + 1)) if (i - l >= 0 and rr >= l) else []
        vals = [evc(a[1], j, T, wmap, memo) for j in js]
        r = all(vals) if k[0] == "H" else any(vals)
    elif k == "!": r = not evc(a[1], i, T, wmap, memo)
    elif k == "H": r = all(evc(a[1], j, T, wmap, memo) for j in range(i + 1))
    elif k == "O": r = any(evc(a[1], j, T, wmap, memo) for j in range(i + 1))
    elif k == "Y": r = False if i == 0 else evc(a[1], i - 1, T, wmap, memo)
    elif k == "Z": r = True if i == 0 else evc(a[1], i - 1, T, wmap, memo)
    elif k == "S":
        r = evc(a[2], i, T, wmap, memo)
        if i > 0: r = r or (evc(a[1], i, T, wmap, memo) and evc(a, i - 1, T, wmap, memo))
    elif k == "&": r = bool(evc(a[1], i, T, wmap, memo)) and bool(evc(a[2], i, T, wmap, memo))
    elif k == "|": r = bool(evc(a[1], i, T, wmap, memo)) or bool(evc(a[2], i, T, wmap, memo))
    elif k == "->": r = (not evc(a[1], i, T, wmap, memo)) or bool(evc(a[2], i, T, wmap, memo))
    elif k == "<->": r = bool(evc(a[1], i, T, wmap, memo)) == bool(evc(a[2], i, T, wmap, memo))
    elif k in CMP or k in ARI:
        x, y = evc(a[1], i, T, wmap, memo), evc(a[2], i, T, wmap, memo)
        if k == "/" and y == 0: raise Unsupported("div0")
        r = {"<": lambda: x < y, "<=": lambda: x <= y, ">": lambda: x > y, ">=": lambda: x >= y, "=": lambda: x == y, "!=": lambda: x != y,
             "+": lambda: x + y, "-": lambda: x - y, "*": lambda: x * y, "/": lambda: x / y}[k]()
    else: raise Unsupported(k)
    memo[key] = r
    return r

def holds(a, T, h, wmap):
    return bool(evc(a, h - 1, T, wmap, {}))

def has_uf(a):
    if not isinstance(a, tuple): return False
    if a[0] == "fn" and not a[1].startswith("absReal#"): return True
    return any(has_uf(x) for x in a[1:] if isinstance(x, tuple))

# ---------- z3 side ----------
def _V(vtypes, h):
    return {v: [(z3.Real if t == "real" else z3.Bool)(f"{v}@{i}") for i in range(h)] for v, t in vtypes.items()}

def _val(m, x):
    v = m.eval(x, model_completion=True)
    if z3.is_true(v): return True
    if z3.is_false(v): return False
    if z3.is_rational_value(v): return Fraction(v.numerator_as_long(), v.denominator_as_long())
    return None

TMO_SCALE = 1
def _solve(f, tmo):
    s = z3.Solver(); s.set("timeout", int(tmo * TMO_SCALE)); s.add(f)
    r = s.check()
    return r, (s.model() if r == z3.sat else None)

def find_witness(fa, fb, vtypes, h, wmap, tmo=4000):
    """trace where fa true and fb false; returns ('sat', T) | ('unsat', None) | ('unknown', None). Tries shortest horizon first when no timed ops."""
    J._WMAP = wmap
    V = _V(vtypes, h)
    ea, eb = J.ev(fa, h - 1, V, {}), J.ev(fb, h - 1, V, {})
    r, m = _solve(z3.And(ea, z3.Not(eb)), tmo)
    if r != z3.sat: return ("unsat" if r == z3.unsat else "unknown"), None, h
    best = (h, m)
    if not wmap:
        for hh in range(2, h):
            Vh = _V(vtypes, hh)
            e1, e2 = J.ev(fa, hh - 1, Vh, {}), J.ev(fb, hh - 1, Vh, {})
            r2, m2 = _solve(z3.And(e1, z3.Not(e2)), 1500)
            if r2 == z3.sat: best = (hh, m2); V = Vh; break
    hh, m = best
    Vh = _V(vtypes, hh)
    T = {v: [_val(m, Vh[v][i]) for i in range(hh)] for v in vtypes}
    return "sat", T, hh

def fmt_trace(T, h):
    lines = []
    for i in range(h):
        parts = []
        for v, seq in sorted(T.items()):
            x = seq[i]
            parts.append(f"{v}={'1' if x is True else '0' if x is False else (str(float(x)) if x is not None else '?')}")
        lines.append(f"t{i}: " + ", ".join(parts))
    return " | ".join(lines)

# ---------- sanity (reference free) ----------
def sanity(pt):
    """-> (cls, detail). cls in ok / contradictory / tautological / unsupported"""
    try:
        g = prep(pt)
        ws = sorted(timed_ops(g)); wmap = {}
        if ws and max(ws) > 6: wmap = {w: (0 if w == 0 else k + 3) for k, w in enumerate(ws)}
        h = max(J.N, max([wmap.get(w, w) for w in ws] or [0]) + 3)
        vt = {v: ("real" if "real" in t else "bool") for v, t in vars_of(g).items()}
        J._WMAP = wmap
        V = _V(vt, h)
        f = J.ev(g, h - 1, V, {})
        r1, _ = _solve(f, 4000); r2, _ = _solve(z3.Not(f), 4000)
        if r1 == z3.unknown or r2 == z3.unknown: return "unsupported", "solver unknown"
        if r1 == z3.unsat: return "contradictory", f"h={h}"
        if r2 == z3.unsat: return "tautological", f"h={h}"
        return "ok", f"h={h}"
    except Unsupported as e: return "unsupported", "operator " + str(e)
    except Exception as e: return "unsupported", "parse " + str(e)[:60]

# ---------- relation with witnesses ----------
def compare(gen_pt, ref_pt, anchor=False):
    """-> dict(cls, miss, alarm, miss_witness, alarm_witness, mapping, verified). cls from judge2 naming; miss/alarm are bool or None"""
    out = dict(cls=None, miss=None, alarm=None, miss_witness=None, alarm_witness=None, mapping=None, verified=None, detail="")
    try:
        g, r = prep(gen_pt), prep(ref_pt)
        wmap, h = setup(g, r)
    except Unsupported as e:
        out.update(cls="unsupported", detail="operator " + str(e)); return out
    except Exception as e:
        out.update(cls="unsupported", detail="parse " + str(e)[:60]); return out
    vg, vr = vars_of(g), vars_of(r)
    for d in (vg, vr):
        for v in d:
            if len(d[v]) > 1: d[v] = {"real"}
    tg = {v: next(iter(t)) for v, t in vg.items()}; tr = {v: next(iter(t)) for v, t in vr.items()}
    gv, rv = sorted(tg), sorted(tr)
    if set(tg) == set(tr) and all(tg[v] == tr[v] for v in tg):
        maps = [{v: v for v in gv}]
    elif anchor:
        # name-anchored: a generated variable whose name AND type occur in the reference is fixed by identity.
        # Only the remaining generated names may be renamed, onto reference variables not already used.
        # Reference variables the generated formula never mentions stay unconstrained (padding).
        fixed = {v: v for v in gv if v in tr and tr[v] == tg[v]}
        fg = [v for v in gv if v not in fixed]
        fr = [x for x in rv if x not in set(fixed.values())]
        if len(fg) > len(fr): out.update(cls="atomization_mismatch", detail=f"unmatched gen vars {len(fg)} > unmatched ref vars {len(fr)}"); return out
        if anchor in ("lex", "strict"):
            cg, cr = const_vars(g), const_vars(r)
            cands = {}
            for v in fg:
                if v in cg:      # constant without a dictionary entry: only lexically supported, constant-like reference identifiers
                    cands[v] = [x for x in fr if x in cr and tr[x] == tg[v] and lex_compatible(v, x)]
                elif anchor == "strict":
                    cands[v] = []
                else:            # other unmatched variable: as in plain anchor mode, but never onto a reference constant
                    cands[v] = [x for x in fr if x not in cr and tr[x] == tg[v]]
            if any(not c for c in cands.values()): out.update(cls="atomization_mismatch", detail="no lexically supported counterpart"); return out
        else:
            cands = {v: [x for x in fr if tr[x] == tg[v]] for v in fg}
            if any(not c for c in cands.values()): out.update(cls="atomization_mismatch", detail="type"); return out
        maps = []
        def rec2(i, used, cur):
            if len(maps) > MAXPERM: return
            if i == len(fg): maps.append({**fixed, **cur}); return
            for c in cands[fg[i]]:
                if c not in used:
                    cur[fg[i]] = c; used.add(c); rec2(i + 1, used, cur); used.discard(c); del cur[fg[i]]
        rec2(0, set(), {})
        if len(maps) > MAXPERM: out.update(cls="atomization_mismatch", detail="too many renamings"); return out
        out["anchored"] = len(fixed)
    else:
        if len(gv) > len(rv): out.update(cls="atomization_mismatch", detail=f"gen vars {len(gv)} > ref vars {len(rv)}"); return out
        if len(rv) - len(gv) >= 3: out.update(cls="atomization_mismatch", detail=f"reference has {len(rv)} variables, generated {len(gv)}"); return out
        cands = {v: [x for x in rv if tr[x] == tg[v]] for v in gv}
        if any(not c for c in cands.values()): out.update(cls="atomization_mismatch", detail="type"); return out
        maps = []
        def rec(i, used, cur):
            if len(maps) > MAXPERM: return
            if i == len(gv): maps.append(dict(cur)); return
            for c in cands[gv[i]]:
                if c not in used:
                    cur[gv[i]] = c; used.add(c); rec(i + 1, used, cur); used.discard(c); del cur[gv[i]]
        rec(0, set(), {})
        if len(maps) > MAXPERM: out.update(cls="atomization_mismatch", detail="too many renamings"); return out
    best = None
    for m in maps:
        g2 = ren(ren(g, {k: "@" + v for k, v in m.items()}), {"@" + v: v for v in rv})
        try:
            w1 = find_witness(g2, r, tr, h, wmap, 800 if len(maps) > 1 else 4000)   # gen true, ref false  (MISS)
            w2 = find_witness(r, g2, tr, h, wmap, 800 if len(maps) > 1 else 4000)   # ref true, gen false  (ALARM)
        except Unsupported as e:
            out.update(cls="unsupported", detail="operator " + str(e)); return out
        if w1[0] == "unknown" or w2[0] == "unknown": continue
        miss, alarm = w1[0] == "sat", w2[0] == "sat"
        score = (2 if (miss and alarm) else 1 if (miss or alarm) else 0)
        if best is None or score < best[0]:
            best = (score, m, g2, miss, alarm, w1, w2)
        if score == 0: break
    if best is None: out.update(cls="unsupported", detail="solver unknown"); return out
    _, m, g2, miss, alarm, w1, w2 = best
    out.update(miss=miss, alarm=alarm, mapping=m)
    renamed = any(k != v for k, v in m.items())
    if not miss and not alarm: out["cls"] = "equivalent_under_renaming" if renamed else "equivalent_bounded"
    elif miss and not alarm: out["cls"] = "weaker_under_renaming" if renamed else "generated_weaker"
    elif alarm and not miss: out["cls"] = "stronger_under_renaming" if renamed else "generated_stronger"
    else: out["cls"] = "incomparable_under_renaming" if renamed else "incomparable"
    ver = []
    uf = has_uf(g2) or has_uf(r)
    for tag, w, (fa, fb) in (("miss", w1, (g2, r)), ("alarm", w2, (r, g2))):
        if w[0] != "sat": continue
        out[tag + "_witness"] = fmt_trace(w[1], w[2])
        if uf: ver.append(None); continue
        try:
            T = {v: [(x if x is not None else False) for x in seq] for v, seq in w[1].items()}
            ok = holds(fa, T, w[2], wmap) and not holds(fb, T, w[2], wmap)
            ver.append(ok)
        except Unsupported:
            ver.append(None)
    out["verified"] = ver
    return out

if __name__ == "__main__":
    nasa = "(H (landing_request -> gear_extended))"
    trig = "((landing_request & ((! (Y landing_request)) | FTP)) -> gear_extended)"  # toy trigger on rising edge, evaluated per step
    print(sanity(nasa), sanity("(H (p & (! p)))"), sanity("(H (p | (! p)))"))
    for name, g in (("same", nasa), ("renamed", "(H (cmd -> down))"), ("strong", "(H (landing_request & gear_extended))"),
                    ("trigger", "(H ((landing_request & ((Y (! landing_request)) | FTP)) -> gear_extended))")):
        print(name, compare(g, nasa))
