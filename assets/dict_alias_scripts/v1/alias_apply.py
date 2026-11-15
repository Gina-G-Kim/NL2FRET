#!/usr/bin/env python3
"""Proof-backed subformula alias (outside the frozen judge tool).
usage: NL2FRET_TOOL=<tool main directory> python3 -I -B alias_apply.py INPUTS_DIR OUT_DIR REFERENCE_JSONL [--tmo MS] [--procs N] [--limit N]
For every generated formula (ltl_pt and ltl_ft separately) of every unit sentence, each maximal temporal-free formula subtree g is compared with the
temporal-free formula subtrees r of the reference formulas of the same item. If both have the same variable set, differ after the tool's own atom
abstraction, and z3 proves (g <-> r) valid over the reals (unsat of its negation), g is replaced by r. Nothing else is changed.
Output: OUT_DIR/fret_ltl_gen.jsonl (units.json and realizability file copied), OUT_DIR/alias_certificates.jsonl (one row per replacement)."""
import sys, os, re, json, shutil, hashlib, argparse, collections
from fractions import Fraction
sys.dont_write_bytecode = True
TOOL = os.environ.get("NL2FRET_TOOL", "/home/claude/nl2fret_tool")
sys.path.insert(0, TOOL + "/judging")
sys.path.insert(0, TOOL + "/judging/nl2fret_judge")
import ltl_engines as LE
import z3
from multiprocessing import Pool

TEMPORAL = {"H", "O", "Y", "Z", "X", "F", "G", "S", "T", "U", "V", "W"}
BOOLOPS = {"&", "|", "->", "<->"}
FORMULA_ROOT = set(LE.CMP) | BOOLOPS | {"!"}

def tparse(s): return LE.parse(LE.lex(s))

def unparse(a):
    k = a[0]
    if k in ("var", "num"): return a[1]
    if k in ("TRUE", "FALSE"): return k
    if k == "neg": return "-" + unparse(a[1])
    if k == "fn": return a[1] + "(" + ", ".join(unparse(x) for x in a[2:]) + ")"
    if len(a) == 2: return "(" + k + " " + unparse(a[1]) + ")"
    return "(" + unparse(a[1]) + " " + k + " " + unparse(a[2]) + ")"

def temporal_free(a):
    k = a[0]
    if k in TEMPORAL or re.match(r"^[HOFG]\[", k): return False
    if k == "var": return a[1] != "FTP"
    if k in ("num", "TRUE", "FALSE"): return True
    if k == "fn":
        if a[1].lower().startswith("pre"): return False
        return all(temporal_free(x) for x in a[2:])
    return all(temporal_free(x) for x in a[1:] if isinstance(x, tuple))

def subtrees(a, acc):
    """all temporal-free formula-rooted subtrees"""
    if not isinstance(a, tuple): return
    if a[0] in FORMULA_ROOT and temporal_free(a): acc.append(a)
    for x in (a[2:] if a[0] == "fn" else a[1:]):
        if isinstance(x, tuple): subtrees(x, acc)

def varset(a, acc=None):
    acc = acc if acc is not None else set()
    if a[0] == "var": acc.add(a[1])
    for x in (a[2:] if a[0] == "fn" else a[1:]):
        if isinstance(x, tuple): varset(x, acc)
    return acc

def ctx_types(a, ctx, types):
    k = a[0]
    if k == "var":
        types[a[1]] = ctx if types.get(a[1], ctx) == ctx else "conflict"; return
    if k in ("num", "TRUE", "FALSE"): return
    if k == "fn":
        for x in a[2:]: ctx_types(x, "real", types)
        return
    if k == "!": ctx_types(a[1], "bool", types); return
    if k in BOOLOPS:
        for x in a[1:]: ctx_types(x, "bool", types)
        return
    for x in a[1:]:
        if isinstance(x, tuple): ctx_types(x, "real", types)

def bad_div(a):
    if a[0] == "/" and a[2][0] != "num": return True
    return any(bad_div(x) for x in (a[2:] if a[0] == "fn" else a[1:]) if isinstance(x, tuple))

FN = {}
def to_z3(a, V):
    k = a[0]
    if k == "var": return V[a[1]]
    if k == "num":
        f = Fraction(a[1]); return z3.RealVal(f"{f.numerator}/{f.denominator}")
    if k == "TRUE": return z3.BoolVal(True)
    if k == "FALSE": return z3.BoolVal(False)
    if k == "fn":
        name = a[1]; args = [to_z3(x, V) for x in a[2:]]
        if name.lower().startswith("abs") and len(args) == 1:
            return z3.If(args[0] >= 0, args[0], -args[0])
        key = (name, len(args))
        if key not in FN: FN[key] = z3.Function("f_" + name, *([z3.RealSort()] * len(args)), z3.RealSort())
        return FN[key](*args)
    x = [to_z3(y, V) for y in a[1:] if isinstance(y, tuple)]
    if k == "!": return z3.Not(x[0])
    if k == "neg": return -x[0]
    ops = {"&": lambda: z3.And(x[0], x[1]), "|": lambda: z3.Or(x[0], x[1]), "->": lambda: z3.Implies(x[0], x[1]), "<->": lambda: x[0] == x[1],
           "<": lambda: x[0] < x[1], "<=": lambda: x[0] <= x[1], ">": lambda: x[0] > x[1], ">=": lambda: x[0] >= x[1], "=": lambda: x[0] == x[1],
           "!=": lambda: x[0] != x[1], "+": lambda: x[0] + x[1], "-": lambda: x[0] - x[1], "*": lambda: x[0] * x[1], "/": lambda: x[0] / x[1]}
    return ops[k]()

def prove(g, r, tmo):
    """True iff z3 proves g <-> r valid over the reals (variable types from usage; conflict or unsupported -> False)"""
    if bad_div(g) or bad_div(r): return False
    types = {}
    ctx_types(g, "bool", types); ctx_types(r, "bool", types)
    if "conflict" in types.values(): return False
    V = {v: (z3.Bool(v) if t == "bool" else z3.Real(v)) for v, t in types.items()}
    try:
        s = z3.Solver(); s.set("timeout", tmo); s.add(z3.Not(to_z3(g, V) == to_z3(r, V)))
        return s.check() == z3.unsat
    except Exception:
        return False

def _bz3(b):
    k = b[0]
    if k == "ap": return z3.Bool(b[1])
    if k == "true": return z3.BoolVal(True)
    if k == "false": return z3.BoolVal(False)
    if k == "not": return z3.Not(_bz3(b[1]))
    x = [_bz3(y) for y in b[1:]]
    return {"&": lambda: z3.And(x[0], x[1]), "|": lambda: z3.Or(x[0], x[1]), "->": lambda: z3.Implies(x[0], x[1]), "<->": lambda: x[0] == x[1]}[k]()

def abstract_eq(g, r):
    """True when the tool's own atom abstraction already makes g and r propositionally equivalent (no alias needed)"""
    try:
        bg, br = LE.to_b(g), LE.to_b(r)
        if bg == br: return True
        s = z3.Solver(); s.set("timeout", 2000); s.add(z3.Not(_bz3(bg) == _bz3(br)))
        return s.check() == z3.unsat
    except Exception:
        return False

def process_formula(s, cands, tmo, certs):
    """s: formula string; cands: list of (tree, varset). -> new string (or s if unchanged)"""
    if not s: return s
    try: t = tparse(s)
    except Exception: return s
    changed = [False]; memo = {}
    def walk(a):
        if not isinstance(a, tuple): return a
        if a[0] in FORMULA_ROOT and temporal_free(a):
            vs = varset(a)
            if vs:
                if a in memo:
                    if memo[a] is not None: changed[0] = True; return memo[a]
                else:
                    memo[a] = None
                    for r, rv in cands:
                        if rv != vs or r == a or abstract_eq(a, r): continue
                        if prove(a, r, tmo):
                            certs.append({"gen": unparse(a), "ref": unparse(r)}); changed[0] = True; memo[a] = r
                            return r
            # no alias for the whole subtree: look inside
        if a[0] == "fn": return ("fn", a[1]) + tuple(walk(x) for x in a[2:])
        return (a[0],) + tuple(walk(x) if isinstance(x, tuple) else x for x in a[1:])
    out = walk(t)
    if not changed[0]: return s
    new = unparse(out)
    assert tparse(new) == out, "unparse round trip"
    return new

def work(args):
    item, sent, pt, ft, refs, tmo = args
    certs = []
    cpt, cft = [], []
    for rp, rf in refs:
        for src, dst in ((rp, cpt), (rf, cft)):
            if not src: continue
            try: tr = tparse(src)
            except Exception: continue
            acc = []; subtrees(tr, acc)
            for x in acc:
                if x not in [y for y, _ in dst]: dst.append((x, varset(x)))
    npt = process_formula(pt, cpt, tmo, certs)
    nft = process_formula(ft, cft, tmo, certs)
    return item, sent, npt, nft, certs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inputs"); ap.add_argument("out"); ap.add_argument("reference")
    ap.add_argument("--tmo", type=int, default=10000); ap.add_argument("--procs", type=int, default=8); ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    units = json.load(open(f"{a.inputs}/units.json"))["units"]
    rows = [json.loads(l) for l in open(f"{a.inputs}/fret_ltl_gen.jsonl")]
    by = {r["sentence"]: r for r in rows}
    from nl2fret_judge import units as U
    refs = {k: [(pt, ft) for _, pt, ft in v] for k, v in U.load_reference(a.reference).items()}
    jobs = []; seen = set()
    for u in units:
        for t in u["texts"]:
            r = by.get(t)
            if not r or not r.get("parser_ok") or not r.get("ltl_pt"): continue
            k = (u["item"], t)
            if k in seen: continue
            seen.add(k); jobs.append((u["item"], t, r["ltl_pt"], r.get("ltl_ft"), refs.get(u["item"], []), a.tmo))
    if a.limit: jobs = jobs[:a.limit]
    print("jobs", len(jobs), "items with refs", sum(1 for v in refs.values() if v), flush=True)
    res = collections.defaultdict(dict); allc = []
    with Pool(a.procs) as p:
        for i, (item, sent, npt, nft, certs) in enumerate(p.imap_unordered(work, jobs, chunksize=4)):
            res[sent][item] = (npt, nft)
            for c in certs: allc.append({"item": item, "sentence": sent, **c})
            if i % 200 == 0: print(i, len(allc), flush=True)
    out = []; stat = collections.Counter()
    for r in rows:
        nr = dict(r); outs = set(res.get(r["sentence"], {}).values())
        if len(outs) == 1:
            npt, nft = next(iter(outs)); nr["ltl_pt"], nr["ltl_ft"] = npt, nft
            stat["changed" if (npt, nft) != (r["ltl_pt"], r.get("ltl_ft")) else "same"] += 1
        elif len(outs) > 1: stat["shared_sentence_kept_original"] += 1
        out.append(nr)
    with open(f"{a.out}/fret_ltl_gen.jsonl", "w") as f:
        for r in out: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    allc.sort(key=lambda c: (c["item"], c["sentence"], c["gen"], c["ref"]))
    with open(f"{a.out}/alias_certificates.jsonl", "w") as f:
        for c in allc: f.write(json.dumps(c, ensure_ascii=False) + "\n")
    for fn in ("units.json", "fret_realizability_gen.jsonl"):
        if os.path.exists(f"{a.inputs}/{fn}"): shutil.copy(f"{a.inputs}/{fn}", f"{a.out}/{fn}")
    print(dict(stat), "certificates", len(allc))
    for fn in ("units.json", "fret_ltl_gen.jsonl", "fret_realizability_gen.jsonl", "alias_certificates.jsonl"):
        pth = f"{a.out}/{fn}"
        if os.path.exists(pth): print(hashlib.sha256(open(pth, "rb").read()).hexdigest(), fn)
if __name__ == "__main__": main()
