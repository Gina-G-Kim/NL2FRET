#!/usr/bin/env python3
"""Small parser for the response and condition expressions that FRET prints in `semantics.post_condition` / `regular_condition`.

It is used only to decide, per FRETish sentence, which identifiers are
  * in the consequent of the response (candidates for system OUTPUT variables),
  * used as numbers (real) or as booleans,
  * compared with another bare identifier (symbolic state value, candidate constant),
  * applied as a function (user defined predicate, not supported by the variable mapping used in this bench).
Nothing here calls a model. The rules are the bench author's assumptions ("추측입니다") and are documented in FRET_NOTES.md.
"""
import re

TOKEN = re.compile(r"\s*(<=>|=>|<=|>=|!=|==|=|<|>|&|\||!|\+|-|\*|/|\(|\)|,|\d+(?:\.\d+)?|[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)")
BUILTIN_FUNCS = {"absReal", "preReal", "preInt", "preBool", "persisted", "abs", "sign"}
NUMERIC_FUNCS = {"absReal", "preReal", "preInt", "abs", "sign"}
BOOL_CONSTS = {"true", "false", "TRUE", "FALSE"}


def tokenize(s):
    pos, out = 0, []
    s = s.strip()
    while pos < len(s):
        m = TOKEN.match(s, pos)
        if not m:
            raise ValueError(f"cannot tokenize at {s[pos:pos + 20]!r}")
        out.append(m.group(1))
        pos = m.end()
        while pos < len(s) and s[pos].isspace():
            pos += 1
    return out


class Parser:
    def __init__(self, toks):
        self.t, self.i = toks, 0

    def peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def eat(self, x=None):
        v = self.peek()
        if v is None or (x is not None and v != x):
            raise ValueError(f"expected {x!r} got {v!r}")
        self.i += 1
        return v

    def parse(self):
        e = self.imp()
        if self.peek() is not None:
            raise ValueError(f"trailing {self.peek()!r}")
        return e

    def imp(self):
        l = self.orr()
        if self.peek() in ("=>", "<=>"):
            op = self.eat()
            r = self.imp()
            return (op, l, r)
        return l

    def orr(self):
        l = self.andd()
        while self.peek() == "|":
            self.eat()
            l = ("|", l, self.andd())
        return l

    def andd(self):
        l = self.nott()
        while self.peek() == "&":
            self.eat()
            l = ("&", l, self.nott())
        return l

    def nott(self):
        if self.peek() == "!":
            self.eat()
            return ("!", self.nott())
        return self.rel()

    def rel(self):
        l = self.add()
        if self.peek() in ("=", "==", "!=", "<", "<=", ">", ">="):
            op = self.eat()
            r = self.add()
            return ("rel", "=" if op == "==" else op, l, r)
        return l

    def add(self):
        l = self.mul()
        while self.peek() in ("+", "-"):
            op = self.eat()
            l = ("arith", op, l, self.mul())
        return l

    def mul(self):
        l = self.unary()
        while self.peek() in ("*", "/"):
            op = self.eat()
            l = ("arith", op, l, self.unary())
        return l

    def unary(self):
        if self.peek() == "-":
            self.eat()
            return ("neg", self.unary())
        return self.prim()

    def prim(self):
        v = self.peek()
        if v is None:
            raise ValueError("unexpected end")
        if v == "(":
            self.eat("(")
            e = self.imp()
            self.eat(")")
            return e
        if re.fullmatch(r"\d+(?:\.\d+)?", v):
            self.eat()
            return ("num", v)
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*", v):
            self.eat()
            if self.peek() == "(":
                self.eat("(")
                args = []
                if self.peek() != ")":
                    args.append(self.imp())
                    while self.peek() == ",":
                        self.eat(",")
                        args.append(self.imp())
                self.eat(")")
                return ("call", v, args)
            if v in BOOL_CONSTS:
                return ("boolconst", v.lower())
            return ("id", v)
        raise ValueError(f"unexpected {v!r}")


def parse(expr):
    return Parser(tokenize(expr)).parse()


def consequent(ast):
    """The part of a response that the component has to make true: the right side of the outermost implication chain."""
    while ast[0] in ("=>",):
        ast = ast[2]
    return ast


def ids_of(ast, funcs=None):
    out = set()
    if ast[0] == "id":
        out.add(ast[1])
    elif ast[0] == "call":
        if ast[1] not in BUILTIN_FUNCS and funcs is not None:
            funcs.add(ast[1])
        for a in ast[2]:
            out |= ids_of(a, funcs)
    elif ast[0] in ("!", "neg"):
        out |= ids_of(ast[1], funcs)
    elif ast[0] in ("&", "|", "=>", "<=>"):
        out |= ids_of(ast[1], funcs) | ids_of(ast[2], funcs)
    elif ast[0] in ("rel", "arith"):
        out |= ids_of(ast[2], funcs) | ids_of(ast[3], funcs)
    return out


def literals_of(ast):
    """Numeric literals (as strings) and whether a real-only builtin occurs in the subtree."""
    lits, real_fn = [], False
    stack = [ast]
    while stack:
        n = stack.pop()
        k = n[0]
        if k == "num":
            lits.append(n[1])
        elif k == "call":
            if n[1] in ("absReal", "preReal"):
                real_fn = True
            stack.extend(n[2])
        elif k in ("!", "neg"):
            stack.append(n[1])
        elif k in ("&", "|", "=>", "<=>"):
            stack.extend([n[1], n[2]])
        elif k in ("rel", "arith"):
            stack.extend([n[2], n[3]])
    return lits, real_fn


def classify(ast, info, numeric=False, boolean=True):
    """Fill info['num'], info['bool'], info['sym_eq'], info['funcs'] by walking the tree."""
    k = ast[0]
    if k == "id":
        (info["num"] if numeric else info["bool"]).add(ast[1])
    elif k == "call":
        name, args = ast[1], ast[2]
        if name not in BUILTIN_FUNCS:
            info["funcs"].add(name)
        # arguments of numeric builtins are numbers, arguments of other calls are left unclassified here
        for a in args:
            classify(a, info, numeric=(name in NUMERIC_FUNCS) or (name == "persisted" and False))
    elif k in ("!",):
        classify(ast[1], info, numeric=False)
    elif k in ("&", "|", "=>", "<=>"):
        classify(ast[1], info, numeric=False)
        classify(ast[2], info, numeric=False)
    elif k == "neg":
        classify(ast[1], info, numeric=True)
    elif k == "arith":
        classify(ast[2], info, numeric=True)
        classify(ast[3], info, numeric=True)
    elif k == "rel":
        op, l, r = ast[1], ast[2], ast[3]
        bare = lambda n: n[0] == "id"
        if op in ("=", "!=") and bare(l) and bare(r):
            info["sym_eq"].append((l[1], r[1]))
        elif op in ("=", "!=") and (bare(l) or bare(r)) and not any(x[0] in ("num", "arith", "neg", "call") for x in (l, r)):
            classify(l, info, numeric=False)
            classify(r, info, numeric=False)
        else:
            lits_l, rf_l = literals_of(l)
            lits_r, rf_r = literals_of(r)
            lits = lits_l + lits_r
            kind = "real" if (any("." in x for x in lits) or rf_l or rf_r) else "int" if lits else "unk"
            for v in ids_of(l, set()) | ids_of(r, set()):
                info["numkind"].setdefault(v, []).append(kind)
            classify(l, info, numeric=True)
            classify(r, info, numeric=True)


def analyze(post, cond=None):
    """post / cond: FRET printed expressions (strings). Returns dict with sets, or {'parse_ok': False, ...} when the text is not an expression."""
    info = {"cons": set(), "ante": set(), "num": set(), "bool": set(), "sym_eq": [], "funcs": set(), "numkind": {}, "parse_ok": True, "errors": []}
    for name, text, is_post in (("post", post, True), ("cond", cond, False)):
        if not text or not text.strip():
            continue
        try:
            ast = parse(text)
        except ValueError as e:
            info["parse_ok"] = False
            info["errors"].append(f"{name}: {e}")
            continue
        classify(ast, info)
        if is_post:
            c = consequent(ast)
            f = set()
            info["cons"] = ids_of(c, f)
            info["ante"] |= ids_of(ast, set()) - info["cons"]
        else:
            info["ante"] |= ids_of(ast, set())
    return info


if __name__ == "__main__":
    for s in ["(! liquid_level_1 => valve_0)", "(( standby & state = ap_transition_state ) => STATE = ap_standby_state)",
              "(absReal ( zt - z ) <= 0.01)", "(( airspeed >= 100 ))", "(! obstacle ( currentPosition ))",
              "(( MMoSt & AuAuMoR & ! PLC_END ) => at the next occurrence of PLC_END , AuMoSt)"]:
        print(s, "->", analyze(s))
