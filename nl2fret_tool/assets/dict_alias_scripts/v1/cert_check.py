#!/usr/bin/env python3
"""usage: NL2FRET_TOOL=<tool main directory> python3 -I -B cert_check.py alias_certificates.jsonl
Independent numeric check of alias certificates: both sides evaluated on random rational points (no solver)."""
import sys, os, json, random
from fractions import Fraction
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import alias_apply as A
def ev(a, env):
    k = a[0]
    if k == "var": return env[a[1]]
    if k == "num": return Fraction(a[1])
    if k == "TRUE": return True
    if k == "FALSE": return False
    if k == "neg": return -ev(a[1], env)
    if k == "fn":
        if a[1].lower().startswith("abs"): return abs(ev(a[2], env))
        raise KeyError(a[1])
    x = [ev(y, env) for y in a[1:]]
    return {"!": lambda: not x[0], "&": lambda: x[0] and x[1], "|": lambda: x[0] or x[1], "->": lambda: (not x[0]) or x[1], "<->": lambda: x[0] == x[1],
            "<": lambda: x[0] < x[1], "<=": lambda: x[0] <= x[1], ">": lambda: x[0] > x[1], ">=": lambda: x[0] >= x[1], "=": lambda: x[0] == x[1],
            "!=": lambda: x[0] != x[1], "+": lambda: x[0] + x[1], "-": lambda: x[0] - x[1], "*": lambda: x[0] * x[1], "/": lambda: x[0] / x[1]}[a[0]]()
random.seed(7); ok = bad = skip = 0
pool = [Fraction(n, d) for n in range(-60, 61) for d in (1, 2, 4)]
for l in open(sys.argv[1]):
    c = json.loads(l); g, r = A.tparse(c["gen"]), A.tparse(c["ref"])
    types = {}; A.ctx_types(g, "bool", types); A.ctx_types(r, "bool", types)
    try:
        for _ in range(3000):
            env = {v: (random.random() < .5 if t == "bool" else random.choice(pool)) for v, t in types.items()}
            if ev(g, env) != ev(r, env): bad += 1; print("MISMATCH", c["gen"], c["ref"], env); break
        else: ok += 1
    except KeyError: skip += 1
print("ok", ok, "mismatch", bad, "skipped (unsupported function)", skip)
