#!/usr/bin/env python3
"""Rule N-LIT of docs/V20_BATCH_DESIGN.md section 7 that works on the TEXT of a FRETish sentence (no model call, no reference information).

regions(text, sem)               character ranges (start, end exclusive) of the condition and the response expression, from the parser's conditionTextRange and responseTextRange
normalize_sentence(text, sem, dvars)   N-LIT (7.1): integer literals that share an arithmetic expression or comparison with a double variable or a real literal become real literals
                                  -> (new text, number of converted literals)
The J+def functions (substitute_defined, classify_terms, rename_aliases) were moved to archive/removed_features/ on 2026-11-17 (docs section 9).
"""
import re

TOKEN = re.compile(r"(<=>|=>|<=|>=|!=|==|=|<|>|&|\||!|\+|-|\*|/|\(|\)|,|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*)")
BOOL_OPS = {"&", "|", "=>", "<=>"}
CMP_OPS = {"<", "<=", ">", ">=", "=", "!=", "=="}
ARITH_OPS = {"+", "-", "*", "/"}


def regions(text, sem):
    out = []
    for k in ("conditionTextRange", "responseTextRange"):
        r = sem.get(k)
        if isinstance(r, list) and len(r) == 2 and 0 <= r[0] <= r[1] < len(text):
            out.append((r[0], r[1] + 1))
    return sorted(out)


def tokenize(s):
    toks = []
    for m in TOKEN.finditer(s):
        toks.append((m.group(1), m.start(1), m.end(1)))
    return toks


def _is_int(t):
    return re.fullmatch(r"\d+", t) is not None


def _is_real(t):
    return re.fullmatch(r"\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", t) is not None and not _is_int(t)


def _split(toks, i, j, ops):
    """indices (absolute) of depth-0 tokens in ops inside [i, j)"""
    depth, out = 0, []
    for k in range(i, j):
        t = toks[k][0]
        if t == "(":
            depth += 1
        elif t == ")":
            depth -= 1
        elif depth == 0 and t in ops:
            out.append(k)
    return out


def _match(toks, i, j):
    """if toks[i] is '(' and its partner is toks[j-1], True"""
    if toks[i][0] != "(":
        return False
    depth = 0
    for k in range(i, j):
        if toks[k][0] == "(":
            depth += 1
        elif toks[k][0] == ")":
            depth -= 1
            if depth == 0:
                return k == j - 1
    return False


def _walk(toks, i, j, dvars, conv):
    if i >= j:
        return
    cuts = _split(toks, i, j, BOOL_OPS)
    if cuts:
        a = i
        for c in cuts + [j]:
            _walk(toks, a, c, dvars, conv)
            a = c + 1
        return
    while i < j and toks[i][0] == "!":
        i += 1
    if i < j and _match(toks, i, j) and (_split(toks, i + 1, j - 1, BOOL_OPS | CMP_OPS)):
        _walk(toks, i + 1, j - 1, dvars, conv)
        return
    cmp_at = _split(toks, i, j, CMP_OPS)
    bounds, a = [], i
    for c in cmp_at + [j]:
        bounds.append((a, c))
        a = c + 1
    dbl = [any(toks[k][0] in dvars or _is_real(toks[k][0]) for k in range(x, y)) for x, y in bounds]
    for n, (x, y) in enumerate(bounds):
        pure = [toks[k][0] for k in range(x, y) if toks[k][0] not in ("(", ")", "-")]
        pure_literal = len(pure) == 1 and (_is_int(pure[0]) or _is_real(pure[0]))
        other_dbl = any(d for m, d in enumerate(dbl) if m != n) if len(bounds) > 1 else False
        if not (dbl[n] or (pure_literal and other_dbl)):
            continue
        for k in range(x, y):
            if _is_int(toks[k][0]):
                prev_t = toks[k - 1][0] if k - 1 >= 0 else None
                next_t = toks[k + 1][0] if k + 1 < len(toks) else None
                if prev_t in ARITH_OPS | CMP_OPS or next_t in ARITH_OPS | CMP_OPS:
                    conv.append(k)


def normalize_sentence(text, sem, dvars):
    dvars = set(dvars)
    edits = []
    for a, b in regions(text, sem):
        sub = text[a:b]
        toks = tokenize(sub)
        conv = []
        _walk(toks, 0, len(toks), dvars, conv)
        edits += [(a + toks[k][1], a + toks[k][2]) for k in conv]
    new = text
    for s, e in sorted(edits, reverse=True):
        new = new[:s] + new[s:e] + ".0" + new[e:]
    return new, len(edits)
