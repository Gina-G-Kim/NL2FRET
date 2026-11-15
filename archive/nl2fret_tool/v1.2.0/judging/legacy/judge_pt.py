#!/usr/bin/env python3
"""Pilot judge: bounded-trace equivalence of two FRET past-time LTL strings with z3. Identical variable names are required (no alignment).
Classes: equivalent_bounded, generated_stronger, generated_weaker, incomparable, alignment_required, unsupported. Bounded horizon N: a counterexample is real, equivalence is only shown up to N steps.
Timed operators H[<=n], H[<n], O[<=n], O[<n] and H[l,r], O[l,r] are supported as windows: <=n looks 0..n steps back, <n looks 0..n-1 steps back, [l,r] looks l..r steps back. When a bound is larger than 6 the distinct
bounds of the two formulas are mapped order preserving onto small numbers (0 stays 0, the others 3, 4, 5, ...) so that equal bounds stay equal and different bounds stay different; magnitudes are lost,
so a timed equivalence is weaker evidence than an untimed one (detail says 'windows mapped').
Time units are steps only (no real-time scaling)."""
import re, sys, json
import z3
N = 8
TOK = re.compile(r"\s*(H\[[^\]]*\]|O\[[^\]]*\]|<->|->|<=|>=|!=|[A-Za-z_][A-Za-z0-9_]*|\d+\.\d+|\d+|[()!&|<>=+\-*/,])")
def lex(s):
    out, p = [], 0
    s = s.strip()
    while p < len(s):
        m = TOK.match(s, p)
        if not m: raise ValueError("lex " + s[p:p+20])
        out.append(m.group(1)); p = m.end()
    return out
UN = {"!", "H", "O", "Y", "Z"}
BIN = {"&", "|", "->", "<->", "S", "T", "<", "<=", ">", ">=", "=", "!=", "+", "-", "*", "/"}
def parse(toks):
    pos = [0]
    def peek(): return toks[pos[0]] if pos[0] < len(toks) else None
    def nxt():
        t = toks[pos[0]]; pos[0] += 1; return t
    def atom():
        t = nxt()
        if t == "(":
            if peek() in UN or (peek() or "").startswith(("H[", "O[")):
                op = nxt(); a = atom(); assert nxt() == ")"; return (op, a)
            a = atom()
            if peek() == ")": nxt(); return a
            op = nxt(); b = atom(); assert nxt() == ")", toks[pos[0]-3:pos[0]+3]
            return (op, a, b)
        if t in ("TRUE", "FALSE"): return (t,)
        if re.match(r"\d", t): return ("num", t)
        if peek() == "(":   # function call f(a,b)
            nxt(); args = [atom()]
            while peek() == ",": nxt(); args.append(atom())
            assert nxt() == ")"; return ("fn", t, *args)
        return ("var", t)
    r = atom()
    assert pos[0] == len(toks), "trailing"
    return r
def vars_of(a, acc=None, ctx=False):
    acc = acc if acc is not None else {}
    k = a[0]
    if k == "var":
        if a[1] != "FTP": acc.setdefault(a[1], set()).add("real" if ctx else "bool")   # FTP (first time point) is a macro, not a variable
    elif k in ("num", "TRUE", "FALSE"): pass
    elif k == "fn": [vars_of(x, acc, True) for x in a[2:]]
    else:
        c = ctx or k in ("<", "<=", ">", ">=", "=", "!=", "+", "-", "*", "/")
        for x in a[1:]: vars_of(x, acc, c)
    return acc
class Unsupported(Exception): pass
_WMAP = {}
TIMED = re.compile(r"^([HO])\[(?:(<=|<)\s*(\d+)|(\d+)\s*,\s*(\d+))\]$")
def window_of(op):
    """-> (l, r): the window looks l to r steps back (r inclusive). <=n is (0,n), <n is (0,n-1), [l,r] is (l,r)."""
    m = TIMED.match(op)
    if not m: raise Unsupported(op)
    if m.group(2): return (0, int(m.group(3)) - (0 if m.group(2) == "<=" else 1))
    return (int(m.group(4)), int(m.group(5)))
def timed_ops(a, acc=None):
    """set of all bound integers used by timed operators"""
    acc = acc if acc is not None else set()
    if isinstance(a, tuple):
        if isinstance(a[0], str) and a[0].startswith(("H[", "O[")): acc.update(window_of(a[0]))
        for x in a[1:]:
            if isinstance(x, tuple): timed_ops(x, acc)
    return acc
def ev(a, i, V, memo):
    key = (id(a), i)
    if key in memo: return memo[key]
    k = a[0]
    if k == "TRUE": r = z3.BoolVal(True)
    elif k == "FALSE": r = z3.BoolVal(False)
    elif k == "num": r = z3.RealVal(a[1])
    elif k == "var": r = z3.BoolVal(i == 0) if a[1] == "FTP" else V[a[1]][i]
    elif k == "fn":
        if a[1] == "absReal":
            x = ev(a[2], i, V, memo); r = z3.If(x >= 0, x, -x)
        else: raise Unsupported(a[1])
    elif k.startswith(("H[", "O[")):
        l, rr = window_of(k)
        l, rr = _WMAP.get(l, l), _WMAP.get(rr, rr)
        js = range(max(0, i - rr), i - l + 1) if i - l >= 0 else range(0)
        r = z3.And([ev(a[1], j, V, memo) for j in js]) if k[0] == "H" else z3.Or([ev(a[1], j, V, memo) for j in js])
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
    elif k in ("<", "<=", ">", ">=", "=", "!=", "+", "-", "*", "/"):
        x, y = ev(a[1], i, V, memo), ev(a[2], i, V, memo)
        r = {"<": lambda: x < y, "<=": lambda: x <= y, ">": lambda: x > y, ">=": lambda: x >= y, "=": lambda: x == y, "!=": lambda: x != y,
             "+": lambda: x + y, "-": lambda: x - y, "*": lambda: x * y, "/": lambda: x / y}[k]()
    else: raise Unsupported(k)
    memo[key] = r
    return r
def judge(gen_pt, ref_pt):
    global _WMAP
    try:
        g, r = parse(lex(gen_pt)), parse(lex(ref_pt))
    except Exception as e:
        return "unsupported", "parse: " + str(e)[:60]
    try:
        ws = sorted(timed_ops(g) | timed_ops(r))
    except Unsupported as e:
        return "unsupported", "operator " + str(e)
    note = ""
    _WMAP = {}
    n_h = N
    if ws:
        if max(ws) > 6:
            _WMAP = {w: (0 if w == 0 else k + 3) for k, w in enumerate(ws)}
            note = "; bounds mapped " + ",".join(f"{w}->{m}" for w, m in _WMAP.items())
        n_h = max(N, max(_WMAP.get(w, w) for w in ws) + 3)
    vg, vr = vars_of(g), vars_of(r)
    if set(vg) != set(vr):
        return "alignment_required", "only_gen=" + ",".join(sorted(set(vg) - set(vr))) + "; only_ref=" + ",".join(sorted(set(vr) - set(vg)))
    allv = {}
    for v in vg:
        t = vg[v] | vr[v]
        if len(t) > 1: return "alignment_required", "type_conflict " + v
        allv[v] = next(iter(t))
    V = {v: [(z3.Real if t == "real" else z3.Bool)(f"{v}@{i}") for i in range(n_h)] for v, t in allv.items()}
    try:
        fg, fr = ev(g, n_h - 1, V, {}), ev(r, n_h - 1, V, {})
    except Unsupported as e:
        return "unsupported", "operator " + str(e)
    def sat(f):
        s = z3.Solver(); s.set("timeout", 20000); s.add(f); return s.check()
    a = sat(z3.And(fg, z3.Not(fr)))   # gen holds, ref fails -> gen weaker
    b = sat(z3.And(fr, z3.Not(fg)))   # ref holds, gen fails -> gen stronger
    if a == z3.unknown or b == z3.unknown: return "unsupported", "solver unknown"
    A, B = a == z3.sat, b == z3.sat
    if not A and not B: return "equivalent_bounded", f"N={n_h}" + note
    if A and not B: return "generated_weaker", note.lstrip("; ")
    if B and not A: return "generated_stronger", note.lstrip("; ")
    return "incomparable", note.lstrip("; ")
if __name__ == "__main__":
    print(judge("(H ((a & b) -> c))", "(H ((b & a) -> c))"), judge("(H (x <= 3))", "(H (x < 3))"))
    print(judge("(H[<=100] (p))", "(H[<=100] (p))"), judge("(H[<=100] (p))", "(H[<100] (p))"), judge("(H[<=100] (p))", "(H (p))"))
    print(judge("(H[<=3] (p))", "(H[<=3] (p))"), judge("(H[<=3] (p))", "(H[<=2] (p))"), judge("(H[<=3] (p))", "(H[<4] (p))"))
    print(judge("(O[<=5] (p))", "(H[<=5] (p))"), judge("(O[<=200] (p))", "(O[<=100] (p))"), judge("(O[<=200] (p))", "(O[<=200] (p))"))
