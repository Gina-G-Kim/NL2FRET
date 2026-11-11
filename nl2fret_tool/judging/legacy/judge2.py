#!/usr/bin/env python3
"""judge2: extension of judge_pt (bounded-trace z3 check of past-time LTL). Adds: unary minus, scientific numbers, pi, html tag stripping, uninterpreted functions
(Real args; Real result in numeric position, Bool otherwise), empty timed windows, and relation classes under injective renaming.
Classes: equivalent_bounded (same names), equivalent_under_renaming, stronger_under_renaming, weaker_under_renaming, incomparable_under_renaming,
atomization_mismatch (more generated variables than reference variables, or too many renamings), unsupported."""
import re, itertools, sys, json
import z3
N = 8
TOK = re.compile(r"\s*(H\[[^\]]*\]|O\[[^\]]*\]|<->|->|<=|>=|!=|[A-Za-z_][A-Za-z0-9_]*|\d+\.?\d*[eE][+-]?\d+|\d+\.\d+|\d+|[()!&|<>=+\-*/,])")
def lex(s):
    s = re.sub(r"</?[bi]>", "", s).strip()
    out, p = [], 0
    while p < len(s):
        m = TOK.match(s, p)
        if not m: raise ValueError("lex " + s[p:p+20])
        out.append(m.group(1)); p = m.end()
    return out
UN = {"!", "H", "O", "Y", "Z"}
CMP = {"<", "<=", ">", ">=", "=", "!="}
ARI = {"+", "-", "*", "/"}
BIN = {"S": (0, "l"), "<->": (1, "l"), "->": (2, "r"), "|": (3, "l"), "&": (4, "l"),
       "<": (5, "l"), "<=": (5, "l"), ">": (5, "l"), ">=": (5, "l"), "=": (5, "l"), "!=": (5, "l"),
       "+": (6, "l"), "-": (6, "l"), "*": (7, "l"), "/": (7, "l")}
def parse(toks):
    """precedence-climbing parser (S < <-> < -> < | < & < comparison < +,- < *,/); prefix: ! H O Y Z H[..] O[..] and unary minus"""
    pos = [0]
    def peek(): return toks[pos[0]] if pos[0] < len(toks) else None
    def nxt():
        t = toks[pos[0]]; pos[0] += 1; return t
    def unary():
        t = peek()
        if t is None: raise AssertionError("eof")
        if t in UN or t.startswith(("H[", "O[")):
            nxt(); return (t, unary())
        if t == "-":
            nxt(); return ("neg", unary())
        return primary()
    def primary():
        t = nxt()
        if t == "(":
            e = expr(0)
            assert nxt() == ")", "expected )"
            return e
        if t in ("TRUE", "FALSE"): return (t,)
        if re.match(r"\d", t): return ("num", t)
        if t == "pi": return ("num", "3.14159265358979")
        if peek() == "(":
            nxt(); args = [expr(0)]
            while peek() == ",": nxt(); args.append(expr(0))
            assert nxt() == ")", "expected ) after args"; return ("fn", t, *args)
        return ("var", t)
    def expr(minp):
        left = unary()
        while True:
            op = peek()
            if op not in BIN or BIN[op][0] < minp: break
            p, assoc = BIN[op]; nxt()
            right = expr(p + 1 if assoc == "l" else p)
            left = (op, left, right)
        return left
    r = expr(0)
    assert pos[0] == len(toks), "trailing"
    return r
def annot(a, numeric=False):
    k = a[0]
    if k == "fn":
        return ("fn", a[1] + ("#R" if numeric else "#B"), *[annot(x, True) for x in a[2:]])
    if k in ("var", "num", "TRUE", "FALSE"): return a
    c = k in CMP or k in ARI or k == "neg"
    return (k, *[annot(x, c) for x in a[1:]])
def vars_of(a, acc=None, ctx=False):
    acc = acc if acc is not None else {}
    k = a[0]
    if k == "var":
        if a[1] != "FTP": acc.setdefault(a[1], set()).add("real" if ctx else "bool")
    elif k in ("num", "TRUE", "FALSE"): pass
    elif k == "fn": [vars_of(x, acc, True) for x in a[2:]]
    else:
        c = ctx or k in CMP or k in ARI or k == "neg"
        for x in a[1:]: vars_of(x, acc, c)
    return acc
class Unsupported(Exception): pass
_WMAP = {}
TIMED = re.compile(r"^([HO])\[(?:(<=|<)\s*(-?\d+)|(-?\d+)\s*,\s*(-?\d+))\]$")
def window_of(op):
    m = TIMED.match(op)
    if not m: raise Unsupported(op)
    if m.group(2): return (0, int(m.group(3)) - (0 if m.group(2) == "<=" else 1))
    return (int(m.group(4)), int(m.group(5)))
def timed_ops(a, acc=None):
    acc = acc if acc is not None else set()
    if isinstance(a, tuple):
        if isinstance(a[0], str) and a[0].startswith(("H[", "O[")):
            l, r = window_of(a[0]); acc.update(x for x in (l, r) if x >= 0)
        for x in a[1:]:
            if isinstance(x, tuple): timed_ops(x, acc)
    return acc
_FN = {}
def fdecl(name, n):
    base, t = name.split("#")
    key = (name, n)
    if key not in _FN:
        _FN[key] = z3.Function(f"fn_{base}", *([z3.RealSort()] * n), z3.RealSort() if t == "R" else z3.BoolSort())
    return _FN[key]
def ev(a, i, V, memo):
    key = (id(a), i)
    if key in memo: return memo[key]
    k = a[0]
    if k == "TRUE": r = z3.BoolVal(True)
    elif k == "FALSE": r = z3.BoolVal(False)
    elif k == "num": r = z3.RealVal(a[1])
    elif k == "neg": r = -ev(a[1], i, V, memo)
    elif k == "var": r = z3.BoolVal(i == 0) if a[1] == "FTP" else V[a[1]][i]
    elif k == "fn":
        args = [ev(x, i, V, memo) for x in a[2:]]
        if a[1].startswith("absReal#"):
            x = args[0]; r = z3.If(x >= 0, x, -x)
        else: r = fdecl(a[1], len(args))(*args)
    elif k.startswith(("H[", "O[")):
        l, rr = window_of(k)
        l, rr = _WMAP.get(l, l), _WMAP.get(rr, rr)
        js = list(range(max(0, i - rr), i - l + 1)) if (i - l >= 0 and rr >= l) else []
        vals = [ev(a[1], j, V, memo) for j in js]
        r = (z3.And(vals) if vals else z3.BoolVal(True)) if k[0] == "H" else (z3.Or(vals) if vals else z3.BoolVal(False))
    elif k == "!": r = z3.Not(ev(a[1], i, V, memo))
    elif k == "H": r = z3.And([ev(a[1], j, V, memo) for j in range(i + 1)])
    elif k == "O": r = z3.Or([ev(a[1], j, V, memo) for j in range(i + 1)])
    elif k == "Y": r = z3.BoolVal(False) if i == 0 else ev(a[1], i - 1, V, memo)
    elif k == "Z": r = z3.BoolVal(True) if i == 0 else ev(a[1], i - 1, V, memo)
    elif k == "S":
        r = ev(a[2], i, V, memo)
        if i > 0: r = z3.Or(r, z3.And(ev(a[1], i, V, memo), ev(a, i - 1, V, memo)))
    elif k == "&": r = z3.And(ev(a[1], i, V, memo), ev(a[2], i, V, memo))
    elif k == "|": r = z3.Or(ev(a[1], i, V, memo), ev(a[2], i, V, memo))
    elif k == "->": r = z3.Implies(ev(a[1], i, V, memo), ev(a[2], i, V, memo))
    elif k == "<->": r = ev(a[1], i, V, memo) == ev(a[2], i, V, memo)
    elif k in CMP or k in ARI:
        x, y = ev(a[1], i, V, memo), ev(a[2], i, V, memo)
        r = {"<": lambda: x < y, "<=": lambda: x <= y, ">": lambda: x > y, ">=": lambda: x >= y, "=": lambda: x == y, "!=": lambda: x != y,
             "+": lambda: x + y, "-": lambda: x - y, "*": lambda: x * y, "/": lambda: x / y}[k]()
    else: raise Unsupported(k)
    memo[key] = r
    return r
def prep(s):
    return annot(parse(lex(s)))
def ren(a, m):
    if a[0] == "var": return ("var", m.get(a[1], a[1]))
    if a[0] in ("num", "TRUE", "FALSE"): return a
    return (a[0],) + tuple(ren(x, m) if isinstance(x, tuple) else x for x in a[1:]) if a[0] != "fn" else ("fn", a[1]) + tuple(ren(x, m) for x in a[2:])
def relation(g, r, vtypes, horizon, wmap, tmo=4000):
    global _WMAP
    _WMAP = wmap
    V = {v: [(z3.Real if t == "real" else z3.Bool)(f"{v}@{i}") for i in range(horizon)] for v, t in vtypes.items()}
    fg, fr = ev(g, horizon - 1, V, {}), ev(r, horizon - 1, V, {})
    def sat(f):
        s = z3.Solver(); s.set("timeout", tmo); s.add(f); return s.check()
    a = sat(z3.And(fg, z3.Not(fr))); b = sat(z3.And(fr, z3.Not(fg)))
    if a == z3.unknown or b == z3.unknown: return "unknown"
    A, B = a == z3.sat, b == z3.sat
    if not A and not B: return "eq"
    if A and not B: return "weaker"     # gen holds where ref fails
    if B and not A: return "stronger"
    return "incomparable"
def uses_temporal(a):
    if not isinstance(a, tuple): return False
    if a[0] in ("Y", "Z", "S") : return True
    return any(uses_temporal(x) for x in a[1:] if isinstance(x, tuple))
def setup(g, r):
    ws = sorted(timed_ops(g) | timed_ops(r))
    wmap = {}
    if ws and max(ws) > 6: wmap = {w: (0 if w == 0 else k + 3) for k, w in enumerate(ws)}
    horizon = max(N, max([wmap.get(w, w) for w in ws] or [0]) + 3)
    if not ws and not (uses_temporal(g) or uses_temporal(r)): horizon = 4
    return wmap, horizon
RANK = {"eq": 0, "stronger": 1, "weaker": 1, "incomparable": 2}
MAXPERM = 120
def judge(gen_pt, ref_pt):
    """-> (class, detail)"""
    try:
        g, r = prep(gen_pt), prep(ref_pt)
        wmap, horizon = setup(g, r)
    except Unsupported as e: return "unsupported", "operator " + str(e)
    except Exception as e: return "unsupported", "parse: " + str(e)[:60]
    vg, vr = vars_of(g), vars_of(r)
    for d in (vg, vr):
        for v in d:
            if len(d[v]) > 1: d[v] = {"real"}
    tg = {v: next(iter(t)) for v, t in vg.items()}; tr = {v: next(iter(t)) for v, t in vr.items()}
    try:
        if set(tg) == set(tr) and all(tg[v] == tr[v] for v in tg):
            rel = relation(g, r, tg, horizon, wmap)
            if rel == "eq": return "equivalent_bounded", f"N={horizon}"
            if rel == "unknown": return "unsupported", "solver unknown"
            # same names: report relation (names agree, so this is a real semantic relation)
            return {"stronger": "generated_stronger", "weaker": "generated_weaker", "incomparable": "incomparable"}[rel], "same names"
        gv, rv = sorted(tg), sorted(tr)
        if len(gv) > len(rv): return "atomization_mismatch", f"gen vars {len(gv)} > ref vars {len(rv)}"
        # type-respecting injective maps
        if len(rv) - len(gv) >= 3: return "atomization_mismatch", f"reference has {len(rv)} variables, generated {len(gv)}"
        cands = {v: [x for x in rv if tr[x] == tg[v]] for v in gv}
        if any(not c for c in cands.values()): return "atomization_mismatch", "type"
        maps = []
        def rec(i, used, cur):
            if len(maps) > MAXPERM: return
            if i == len(gv): maps.append(dict(cur)); return
            for c in cands[gv[i]]:
                if c not in used:
                    cur[gv[i]] = c; used.add(c); rec(i + 1, used, cur); used.discard(c); del cur[gv[i]]
        rec(0, set(), {})
        if len(maps) > MAXPERM: return "atomization_mismatch", "too many renamings"
        best = ("incomparable", None); anyknown = False
        for m in maps:
            g2 = ren(g, {k: "@" + v for k, v in m.items()})
            g2 = ren(g2, {"@" + v: v for v in rv})
            vt = dict(tr)
            rel = relation(g2, r, vt, horizon, wmap, tmo=800)
            if rel == "unknown": continue
            anyknown = True
            if RANK[rel] < RANK[best[0]] or best[1] is None and RANK[rel] <= RANK[best[0]]:
                best = (rel, m)
            if rel == "eq": break
        if not anyknown: return "unsupported", "solver unknown"
        rel, m = best
        swap = any(k != v and k in rv for k, v in (m or {}).items())
        name = {"eq": "equivalent_under_swap_renaming" if swap else "equivalent_under_renaming", "stronger": "stronger_under_renaming",
                "weaker": "weaker_under_renaming", "incomparable": "incomparable_under_renaming"}[rel]
        return name, str(m)[:200]
    except Unsupported as e: return "unsupported", "operator " + str(e)
if __name__ == "__main__":
    print(judge("(H (z >= -0.2))", "(H (z >= -0.2))"))
    print(judge("(H (absReal(x) <= 50))", "(H (y <= 50.0))"))
    print(judge("(H (maximum_roll_angle <= 33))", "(H ((-33.0 < roll_angle) & (roll_angle < 33.0)))"))
    print(judge("(H (a -> b))", "(H (c -> d))"), judge("(H b)", "(H (c -> d))"))
    print(judge("(H (sqrt(x) > 1))", "(H (sqrt(x) > 1))"))
