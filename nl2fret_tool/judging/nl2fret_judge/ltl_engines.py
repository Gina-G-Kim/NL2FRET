#!/usr/bin/env python3
"""LTL engine comparison: NuSMV (past-time) vs Spot (future-time) vs bounded z3 on boolean abstractions.

Subcommands
  selftest           no external engine needed: parser, atom abstraction and printers
  parse              can each engine read the formulas? (data/formulas.jsonl)
  run                role verdicts for data/pairs.jsonl with every available engine (resumable)
  report             tables from results/*.jsonl

All formulas are first abstracted to propositional atoms (arithmetic comparisons become one boolean atom each,
normalised only by: > and >= rewritten with < , != with = , commutative operands sorted). This is the same kind of abstraction
as the FRET refactoring paper (arXiv 2202.05816, section 4.4: terms replaced by boolean variables). Arithmetic relations between
different atoms (x<3 and x<5) are NOT known to the engines: this is a known loss.
"""
import re, sys, json, os, subprocess, shutil, argparse, hashlib, time, collections, itertools
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
TOK = re.compile(r"\s*([HOFG]\[[^\]]*\]|<->|->|<=|>=|!=|[A-Za-z_][A-Za-z0-9_]*|\d+\.?\d*[eE][+\-]?\d+|\d+\.\d+|\d+|[()!&|<>=+\-*/,])")
CMP = {"<", "<=", ">", ">=", "=", "!="}; ARI = {"+", "-", "*", "/"}
UN = {"!", "H", "O", "Y", "Z", "X", "F", "G"}
BIN = {"&", "|", "->", "<->", "S", "T", "U", "V", "W"} | CMP | ARI

class Unsupported(Exception): pass

def lex(s):
    out, p, s = [], 0, s.strip()
    while p < len(s):
        m = TOK.match(s, p)
        if not m: raise ValueError("lex " + s[p:p + 20])
        out.append(m.group(1)); p = m.end()
    return out

def parse(toks):
    pos = [0]
    def peek(): return toks[pos[0]] if pos[0] < len(toks) else None
    def nxt():
        t = toks[pos[0]]; pos[0] += 1; return t
    def is_un(t): return t in UN or bool(re.match(r"^[HOFG]\[", t or ""))
    def atom():
        t = nxt()
        if t == "(":
            if is_un(peek()):
                op = nxt(); a = atom(); assert nxt() == ")"; return (op, a)
            a = atom()
            if peek() == ")": nxt(); return a
            op = nxt(); b = atom(); assert nxt() == ")", "paren"
            return (op, a, b)
        if t in ("TRUE", "FALSE"): return (t,)
        if t == "-": return ("neg", atom())
        if re.match(r"\d", t): return ("num", t)
        if peek() == "(":
            nxt(); args = [atom()]
            while peek() == ",": nxt(); args.append(atom())
            assert nxt() == ")"; return ("fn", t, *args)
        return ("var", t)
    r = atom(); assert pos[0] == len(toks), "trailing"; return r

TIMED = re.compile(r"^([HOFG])\[(?:(<=|<)\s*(\d+)|(\d+)\s*,\s*(\d+))\]$")
def window_of(op):
    m = TIMED.match(op)
    if not m: raise Unsupported(op)
    if m.group(2): return (0, int(m.group(3)) - (0 if m.group(2) == "<=" else 1))
    return (int(m.group(4)), int(m.group(5)))

# ---------- abstraction to a boolean AST ----------
def ser(a):
    if a[0] == "num":
        f = Fraction(a[1]); return str(f.numerator) if f.denominator == 1 else f"{f.numerator}/{f.denominator}"
    return "(" + " ".join(str(x) if not isinstance(x, tuple) else ser(x) for x in a) + ")"

def canon(a):
    k = a[0]
    if k == "var": return a[1]
    if k == "neg": return "-" + canon(a[1])
    if k == "num":
        f = Fraction(a[1]); return str(f.numerator) if f.denominator == 1 else f"{f.numerator}/{f.denominator}"
    if k == "fn": return a[1] + "(" + ",".join(canon(x) for x in a[2:]) + ")"
    if k in ("TRUE", "FALSE"): return k
    if k in ARI:
        x, y = canon(a[1]), canon(a[2])
        if k in ("+", "*") and x > y: x, y = y, x
        return f"({x}{k}{y})"
    return ser(a)

def cat(name, key): return "c_" + hashlib.sha1((name + "|" + key).encode()).hexdigest()[:10]

def to_b(a):
    k = a[0]
    if k == "TRUE": return ("true",)
    if k == "FALSE": return ("false",)
    if k == "var": return ("FTP",) if a[1] == "FTP" else ("ap", "b_" + a[1])
    if k == "!": return ("not", to_b(a[1]))
    if k in ("&", "|", "->", "<->"): return (k, to_b(a[1]), to_b(a[2]))
    if k in ("H", "O", "Y", "Z", "X", "F", "G"): return (k, to_b(a[1]))
    if k in ("S", "T", "U", "V", "W"): return (k, to_b(a[1]), to_b(a[2]))
    if re.match(r"^[HOFG]\[", k): l, r = window_of(k); return ("win", k[0], l, r, to_b(a[1]))
    if k in CMP:
        x, y = canon(a[1]), canon(a[2])
        lt = lambda p, q: ("ap", cat("lt", p + "<" + q))
        if k == "<": return lt(x, y)
        if k == ">": return lt(y, x)
        if k == "<=": return ("not", lt(y, x))
        if k == ">=": return ("not", lt(x, y))
        p, q = sorted([x, y]); e = ("ap", cat("eq", p + "=" + q))
        return e if k == "=" else ("not", e)
    if k == "fn": return ("ap", cat("fn", canon(a)))
    raise Unsupported("to_b " + k)

def abstract(s): return to_b(parse(lex(s)))

def aps(b, acc=None):
    acc = acc if acc is not None else set()
    if b[0] == "ap": acc.add(b[1])
    for x in b[1:]:
        if isinstance(x, tuple): aps(x, acc)
    return acc

def has_op(b, ops):
    if b[0] in ops: return True
    return any(has_op(x, ops) for x in b[1:] if isinstance(x, tuple))

def max_window(b):
    m = 0
    if b[0] == "win": m = b[3]
    for x in b[1:]:
        if isinstance(x, tuple): m = max(m, max_window(x))
    return m

# ---------- printers ----------
def _rep(op, x, n):
    for _ in range(n): x = f"({op} {x})"
    return x
def to_smv(b, cap=128):
    k = b[0]
    if k == "true": return "TRUE"
    if k == "false": return "FALSE"
    if k == "ap": return b[1]
    if k == "FTP": return "(! (Y TRUE))"
    if k == "not": return f"(! {to_smv(b[1], cap)})"
    if k in ("&", "|", "->", "<->"): return f"({to_smv(b[1], cap)} {k} {to_smv(b[2], cap)})"
    if k in ("Y", "Z", "O", "H"): return f"({k} {to_smv(b[1], cap)})"
    if k == "S": return f"({to_smv(b[1], cap)} S {to_smv(b[2], cap)})"
    if k == "T": return f"({to_smv(b[1], cap)} T {to_smv(b[2], cap)})"
    if k == "win":
        _, o, l, r, x = b
        if r > cap: raise Unsupported("window>%d" % cap)
        inner = to_smv(x, cap)
        if o == "H":
            parts = [_rep("Z", inner, i) for i in range(l, r + 1)]
            return "TRUE" if not parts else "(" + " & ".join(parts) + ")"
        if o == "O":
            parts = [_rep("Y", inner, i) for i in range(l, r + 1)]
            return "FALSE" if not parts else "(" + " | ".join(parts) + ")"
    raise Unsupported("smv " + k)

def to_spot(b, past_literal=False):
    k = b[0]
    if k == "true": return "1"
    if k == "false": return "0"
    if k == "ap": return b[1]
    if k == "not": return f"(!{to_spot(b[1], past_literal)})"
    if k in ("&", "|", "->", "<->"): return f"({to_spot(b[1], past_literal)} {k} {to_spot(b[2], past_literal)})"
    if k in ("X", "F", "G"): return f"({k} {to_spot(b[1], past_literal)})"
    if k == "U": return f"({to_spot(b[1], past_literal)} U {to_spot(b[2], past_literal)})"
    if k == "V": return f"({to_spot(b[1], past_literal)} R {to_spot(b[2], past_literal)})"
    if k == "W": return f"({to_spot(b[1], past_literal)} W {to_spot(b[2], past_literal)})"
    if k == "win" and b[1] in ("F", "G"): return f"({b[1]}[{b[2]}..{b[3]}] {to_spot(b[4], past_literal)})"
    if past_literal:   # hand the past-time syntax to Spot's own parser and let it answer
        if k == "FTP": return "(!(Y 1))"
        if k in ("Y", "Z", "O", "H"): return f"({k} {to_spot(b[1], True)})"
        if k in ("S", "T"): return f"({to_spot(b[1], True)} {k} {to_spot(b[2], True)})"
    raise Unsupported("spot " + k)

# ---------- engines ----------
def find_bin(names):
    for n in names:
        p = shutil.which(n)
        if p: return p
    return None

def run_smv(binary, specs, atoms, timeout):
    """specs: list of formula strings; returns list of bool (True = holds) or raises"""
    body = "MODULE main\nVAR\n" + "".join(f"  {a} : boolean;\n" for a in sorted(atoms) or ["dummy"]).replace("dummy", "dummy_ap")
    body += "".join(f"LTLSPEC {s}\n" for s in specs)
    path = os.path.join(ROOT, "work"); os.makedirs(path, exist_ok=True)
    fn = os.path.join(path, "q_%s.smv" % hashlib.sha1(body.encode()).hexdigest()[:12])
    open(fn, "w").write(body)
    p = subprocess.run([binary, fn], capture_output=True, text=True, timeout=timeout)
    res = re.findall(r"-- specification .* is (true|false)", p.stdout)
    if len(res) != len(specs): raise RuntimeError("smv output: " + (p.stdout + p.stderr)[-300:].replace("\n", " | "))
    return [r == "true" for r in res]

def smv_roles(binary, gen_pt, ref_pt, timeout):
    g, r = abstract(gen_pt), abstract(ref_pt)
    gs, rs = to_smv(g), to_smv(r)
    ats = aps(g) | aps(r)
    gr, rg, gsat, gval = run_smv(binary, [f"G (({gs}) -> ({rs}))", f"G (({rs}) -> ({gs}))", f"G (! ({gs}))", f"G ({gs})"], ats, timeout)
    return dict(miss=not gr, alarm=not rg, gen_sat=not gsat, gen_valid=gval)

def spot_cmd(binary, f, opt, other, timeout):
    p = subprocess.run([binary, "-c", "-f", f, f"{opt}={other}"], capture_output=True, text=True, timeout=timeout)
    if p.returncode not in (0, 1) or p.stderr.strip(): raise RuntimeError(p.stderr.strip()[:200] or "rc%d" % p.returncode)
    return p.stdout.strip() == "1"

def spot_roles(binary, gen_ft, ref_ft, timeout):
    g, r = to_spot(abstract(gen_ft)), to_spot(abstract(ref_ft))
    gr = spot_cmd(binary, g, "--imply", r, timeout)       # gen implies ref : no MISS
    rg = spot_cmd(binary, r, "--imply", g, timeout)       # ref implies gen : no ALARM
    gtaut = spot_cmd(binary, g, "--equivalent-to", "1", timeout)
    gunsat = spot_cmd(binary, g, "--equivalent-to", "0", timeout)
    return dict(miss=not gr, alarm=not rg, gen_sat=not gunsat, gen_valid=gtaut)

def role_of(m, a): return "SAME" if (not m and not a) else "PROOF" if not m else "REFUTE" if not a else "NEITHER"

# bounded z3 evaluator on the same boolean abstraction (bridge engine: shows the effect of the abstraction without any external tool)
def z3_roles(gen_pt, ref_pt, H=8):
    import z3
    g, r = abstract(gen_pt), abstract(ref_pt)
    if max(max_window(g), max_window(r)) > H - 2: raise Unsupported("window>horizon")
    names = sorted(aps(g) | aps(r)); V = {n: [z3.Bool(f"{n}@{i}") for i in range(H)] for n in names}
    def ev(b, i, memo):
        key = (id(b), i)
        if key in memo: return memo[key]
        k = b[0]
        if k == "true": x = z3.BoolVal(True)
        elif k == "false": x = z3.BoolVal(False)
        elif k == "ap": x = V[b[1]][i]
        elif k == "FTP": x = z3.BoolVal(i == 0)
        elif k == "not": x = z3.Not(ev(b[1], i, memo))
        elif k == "&": x = z3.And(ev(b[1], i, memo), ev(b[2], i, memo))
        elif k == "|": x = z3.Or(ev(b[1], i, memo), ev(b[2], i, memo))
        elif k == "->": x = z3.Implies(ev(b[1], i, memo), ev(b[2], i, memo))
        elif k == "<->": x = ev(b[1], i, memo) == ev(b[2], i, memo)
        elif k == "Y": x = z3.BoolVal(False) if i == 0 else ev(b[1], i - 1, memo)
        elif k == "Z": x = z3.BoolVal(True) if i == 0 else ev(b[1], i - 1, memo)
        elif k == "H": x = z3.And([ev(b[1], j, memo) for j in range(i + 1)])
        elif k == "O": x = z3.Or([ev(b[1], j, memo) for j in range(i + 1)])
        elif k == "S":
            x = ev(b[2], i, memo)
            if i > 0: x = z3.Or(x, z3.And(ev(b[1], i, memo), ev(b, i - 1, memo)))
        elif k == "T":   # a T b = not(not a S not b)
            nb = ("S", ("not", b[1]), ("not", b[2])); x = z3.Not(ev(nb, i, memo))
        elif k == "win":
            _, o, l, rr, y = b
            js = list(range(max(0, i - rr), i - l + 1)) if i - l >= 0 else []
            vals = [ev(y, j, memo) for j in js]
            x = z3.And(vals) if o == "H" else z3.Or(vals)
        else: raise Unsupported(k)
        memo[key] = x; return x
    def sat(f):
        s = z3.Solver(); s.set("timeout", 20000); s.add(f); return s.check() == z3.sat
    m1, m2 = {}, {}
    gl, rl = ev(g, H - 1, m1), ev(r, H - 1, m2)
    miss, alarm = sat(z3.And(gl, z3.Not(rl))), sat(z3.And(rl, z3.Not(gl)))
    return dict(miss=miss, alarm=alarm, gen_sat=sat(gl), gen_valid=not sat(z3.Not(gl)))

def load(fn): return [json.loads(l) for l in open(fn)] if os.path.exists(fn) else []

def cmd_selftest(a):
    n = 0
    for r in load(os.path.join(ROOT, "data", "formulas.jsonl")):
        for k in ("pt", "ft"):
            if not r.get(k): continue
            try: b = abstract(r[k]); n += 1
            except Exception as e: print("unparsable:", r["id"], k, str(e)[:40]); continue
            if k == "pt":
                try: to_smv(b)
                except Unsupported as e: pass
    print("abstracted", n, "formulas"); 
    assert abstract("(H (a -> (x > 3)))") == abstract("(H (a -> (3 < x)))")
    assert abstract("(x >= 3)") == ("not", abstract("(x < 3)"))
    assert abstract("(x != y)") == ("not", abstract("(y = x)"))
    print(to_smv(abstract("(H ((a & (Y b)) -> (x <= 3)))")))
    print(to_smv(abstract("(H[0,2] a)")))
    print("SELFTEST_OK")

def cmd_parse(a):
    fs = load(os.path.join(ROOT, "data", "formulas.jsonl")); out = {}
    smv = a.nusmv or find_bin(["NuSMV", "nuXmv", "nusmv"]); spot = a.spot or find_bin(["ltlfilt"])
    print("NuSMV binary:", smv, "| ltlfilt:", spot)
    rows = []
    for f in fs:
        row = dict(id=f["id"], kind=f["kind"])
        try: b = abstract(f["pt"]) if f.get("pt") else None
        except Exception as e: b = None; row["abstract_pt"] = "ERR " + str(e)[:60]
        if b is not None:
            row["abstract_pt"] = "ok"
            try: s = to_smv(b)
            except Unsupported as e: row["smv_pt"] = "skip " + str(e); s = None
            if s and smv:
                try: run_smv(smv, [f"G ({s})"], aps(b), a.timeout); row["smv_pt"] = "ok"
                except Exception as e: row["smv_pt"] = "ERR " + str(e)[:150]
            if spot:
                try: sp = to_spot(b, past_literal=True)
                except Unsupported as e: sp = None; row["spot_pt_literal"] = "skip"
                if sp:
                    p = subprocess.run([spot, "-c", "-f", sp], capture_output=True, text=True, timeout=a.timeout)
                    row["spot_pt_literal"] = "ok" if (p.returncode in (0, 1) and not p.stderr.strip()) else "ERR " + p.stderr.strip()[:120]
        if f.get("ft"):
            try:
                bf = abstract(f["ft"]); row["abstract_ft"] = "ok"
                if spot:
                    sp = to_spot(bf); p = subprocess.run([spot, "-c", "-f", sp], capture_output=True, text=True, timeout=a.timeout)
                    row["spot_ft"] = "ok" if (p.returncode in (0, 1) and not p.stderr.strip()) else "ERR " + p.stderr.strip()[:120]
            except Exception as e: row["abstract_ft"] = "ERR " + str(e)[:80]
        rows.append(row)
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    with open(os.path.join(ROOT, "results", "parse.jsonl"), "w") as w:
        for r in rows: w.write(json.dumps(r, ensure_ascii=False) + "\n")
    for key in ("abstract_pt", "smv_pt", "spot_pt_literal", "abstract_ft", "spot_ft"):
        c = collections.Counter((r.get(key) or "-")[:60] for r in rows)
        print(key, dict(c.most_common(6)), "total", len(rows))

def cmd_run(a):
    ps = load(os.path.join(ROOT, "data", "pairs.jsonl"))
    smv = a.nusmv or find_bin(["NuSMV", "nuXmv", "nusmv"]); spot = a.spot or find_bin(["ltlfilt"])
    try: import z3; have_z3 = True
    except Exception: have_z3 = False
    print("engines: nusmv", smv, "| spot", spot, "| z3b", have_z3)
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    fn = os.path.join(ROOT, "results", "pairs_out.jsonl"); done = {(r["id"]) for r in load(fn)}
    with open(fn, "a") as w:
        for i, p in enumerate(ps):
            if p["id"] in done: continue
            row = dict(id=p["id"], source=p["source"], name=p["name"], expected=p["expected"], z3_role=p.get("z3_role"))
            for eng in ("nusmv", "spot_ft", "z3b"):
                try:
                    t = time.time()
                    if eng == "nusmv":
                        if not smv: continue
                        x = smv_roles(smv, p["gen_pt"], p["ref_pt"], a.timeout)
                    elif eng == "spot_ft":
                        if not spot or not p.get("gen_ft"): continue
                        x = spot_roles(spot, p["gen_ft"], p["ref_ft"], a.timeout)
                    else:
                        if not have_z3: continue
                        x = z3_roles(p["gen_pt"], p["ref_pt"])
                    x["role"] = role_of(x["miss"], x["alarm"]); x["sec"] = round(time.time() - t, 2); row[eng] = x
                except Exception as e: row[eng] = dict(error=str(e)[:200])
            w.write(json.dumps(row, ensure_ascii=False) + "\n"); w.flush()
            if (i + 1) % 25 == 0: print(i + 1, "/", len(ps), flush=True)

def degenerate(x): return "DEGEN" if (x.get("gen_valid") or not x.get("gen_sat")) else None

def cmd_report(a):
    rs = load(os.path.join(ROOT, "results", "pairs_out.jsonl"))
    engs = ["nusmv", "spot_ft", "z3b"]
    def get(r, e):
        x = r.get(e)
        if not x: return "n/a"
        if "error" in x: return "ERR"
        return degenerate(x) or x["role"]
    print("## controls (expected role defined by the mutation, independent of any engine): match / n")
    names = []; [names.append(r["name"]) for r in rs if r["source"] == "ctl" and r["name"] not in names]
    print("| mutation | n | z3 (judge4) | " + " | ".join(engs) + " |"); print("|---|---|---|" + "---|" * len(engs))
    for n in names:
        sub = [r for r in rs if r["source"] == "ctl" and r["name"] == n]
        cells = [f"{sum(r['z3_role']==r['expected'] for r in sub)}"]
        for e in engs:
            ok = sum(get(r, e) == r["expected"] for r in sub); er = sum(get(r, e) in ("ERR", "n/a") for r in sub)
            cells.append(f"{ok}" + (f" (err/na {er})" if er else ""))
        print(f"| {n} | {len(sub)} | " + " | ".join(cells) + " |")
    ctl = [r for r in rs if r["source"] == "ctl"]
    print("| total | %d | %d | " % (len(ctl), sum(r["z3_role"] == r["expected"] for r in ctl)) + " | ".join(str(sum(get(r, e) == r["expected"] for r in ctl)) for e in engs) + " |")
    print("\n## generated sentences (d8): engine role vs judge4 z3 role (anchor mode)")
    d8 = [r for r in rs if r["source"] == "d8"]
    for e in engs:
        c = collections.Counter((r["z3_role"], get(r, e)) for r in d8)
        agree = sum(v for (a_, b_), v in c.items() if a_ == b_)
        print(e, "agree", agree, "/", len(d8), dict(c))
    print("\n## engine vs engine (d8): nusmv vs spot_ft")
    c = collections.Counter((get(r, "nusmv"), get(r, "spot_ft")) for r in d8)
    print(dict(c))
    print("seconds per pair (median):", {e: sorted(r[e].get("sec", 0) for r in rs if e in r and "sec" in r[e])[len([1 for r in rs if e in r and "sec" in r[e]]) // 2] if any(e in r and "sec" in r[e] for r in rs) else None for e in engs})

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["selftest", "parse", "run", "report"])
    ap.add_argument("--nusmv"); ap.add_argument("--spot"); ap.add_argument("--timeout", type=int, default=120)
    a = ap.parse_args()
    {"selftest": cmd_selftest, "parse": cmd_parse, "run": cmd_run, "report": cmd_report}[a.cmd](a)
