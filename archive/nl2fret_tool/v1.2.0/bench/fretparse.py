"""Access to the OFFICIAL FRET parser (FretSemantics.compile, docker image fret-lab) with a disk cache, and a MOCK parser for offline tests.

compile_texts(texts, backend, cache_path) -> {text: {"ok": bool, "error": str|None}}
  backend "docker": fret_check/tools/fret_compile.compile_list (one container run per 400 sentences)
  backend "mock":   mock_parse() below. It is NOT FRET. It re-implements, roughly, the accept/reject facts observed in the previous runs, only to exercise
                    the code paths of the feedback loop without docker. Never use its numbers.
"""
import json
import os
import re
import sys

import fretlint as L

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "fret_check", "tools"))


def _load_cache(path):
    c = {}
    if os.path.exists(path):
        for line in open(path, encoding="utf-8"):
            line = line.strip()
            if line:
                try:
                    r = json.loads(line)
                    c[r["t"]] = {"ok": r["ok"], "error": r.get("error")}
                except Exception:
                    pass
    return c


def compile_texts(texts, backend="docker", cache_path=None):
    texts = list(dict.fromkeys(t for t in texts if isinstance(t, str)))
    cache = _load_cache(cache_path) if cache_path else {}
    todo = [t for t in texts if t not in cache]
    if todo:
        if backend == "mock":
            res = {t: mock_parse(t) for t in todo}
        elif backend == "docker":
            import fret_compile
            res = {r["fretish"]: {"ok": bool(r["ok"]), "error": (None if r["ok"] else str(r["error"])[:600])} for r in fret_compile.compile_list(todo)}
        else:
            raise SystemExit("unknown parser backend " + backend)
        if cache_path:
            with open(cache_path, "a", encoding="utf-8") as f:
                for t, r in res.items():
                    f.write(json.dumps({"t": t, "ok": r["ok"], "error": r["error"], "backend": backend}, ensure_ascii=False) + "\n")
        cache.update(res)
    return {t: cache[t] for t in texts if t in cache}


# ------------------------------------------------------------------ mock parser
TIME_UNITS = {"ticks", "milliseconds", "seconds", "minutes", "hours"}
COND_KW = {"when", "whenever", "if", "upon", "unless"}
SCOPE_KW = {"in", "before", "after", "while", "notin", "onlyin", "onlybefore", "onlyafter"}


def _tok(s):
    return re.findall(r"[A-Za-z_][A-Za-z0-9_\.]*|\d+(?:\.\d+)?|<=>|=>|<=|>=|!=|[=<>&|!+\-*/()]|\S", s)


def _expr_end(toks, i, stop_words=()):
    """Greedy expression read; returns index after the expression. Raises ValueError(msg)."""
    n = len(toks)
    expect_operand = True
    depth = 0
    start = i
    while i < n:
        t = toks[i]
        if t.lower() in stop_words and not expect_operand:
            break
        if expect_operand:
            if t in ("!", "-", "~"):
                i += 1
                continue
            if t == "(":
                depth += 1
                i += 1
                continue
            if re.fullmatch(r"\d+(?:\.\d+)?", t):
                expect_operand = False
                i += 1
                continue
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_\.]*", t):
                if t in ("abs", "max", "min") and i + 1 < n and toks[i + 1] == "(" and t != "absReal":
                    raise ValueError("These reserved letter combinations cannot be used: " + t + ".")
                if t in ("previous", "prev") and i + 1 < n and toks[i + 1] == "(":
                    raise ValueError("no viable alternative at input '" + t + "('")
                i += 1
                expect_operand = False
                if i < n and toks[i] == "(":  # function application like absReal(x)
                    depth += 1
                    i += 1
                    expect_operand = True
                continue
            raise ValueError(f"token recognition error at: '{t}'" if not re.fullmatch(r"[=<>&|!+\-*/()]|<=>|=>|<=|>=|!=", t) else f"no viable alternative at input '{t}'")
        else:
            if t == ")":
                depth -= 1
                if depth < 0:
                    break
                i += 1
                continue
            if t in ("&", "|", "=>", "<=>", "=", "!=", "<", "<=", ">", ">=", "+", "-", "*", "/"):
                expect_operand = True
                i += 1
                continue
            break
    if expect_operand and i > start:
        raise ValueError("no viable alternative at input '<end>'")
    if depth != 0 and i >= n:
        raise ValueError("no viable alternative at input '<end>'")
    return i


def mock_parse(text):
    try:
        s = re.sub(r"\s+", " ", text.strip())
        for ch in "≤≥≠°’":
            if ch in s:
                raise ValueError(f"token recognition error at: '{ch}'")
        m = re.search(r"\bshall\b", s, re.I)
        if not m:
            raise ValueError("missing SHALL at '<EOF>'")
        pre, post = s[:m.start()].strip(), s[m.end():].strip()
        # ----- post: [timing] satisfy EXPR
        toks = _tok(post)
        i = 0
        if toks[i:i + 2] == ["with", "probability"]:
            if i + 2 >= len(toks) or toks[i + 2] not in ("<=", "<", ">=", ">"):
                raise ValueError("mismatched input '" + (toks[i + 2] if i + 2 < len(toks) else "<EOF>") + "' expecting RELATIONAL_OP")
            if i + 3 >= len(toks) or not re.fullmatch(r"\d+(?:\.\d+)?", toks[i + 3]):
                raise ValueError("mismatched input '" + (toks[i + 3] if i + 3 < len(toks) else "<EOF>") + "' expecting NUMBER")
            i += 4
        w = toks[i].lower() if i < len(toks) else ""
        if w in ("always", "never", "eventually", "immediately", "next"):
            i += 1
        elif w in ("within", "for", "after"):
            if i + 1 >= len(toks) or not re.fullmatch(r"\d+(?:\.\d+)?", toks[i + 1]):
                raise ValueError("mismatched input '" + (toks[i + 1] if i + 1 < len(toks) else "<EOF>") + "' expecting NUMBER")
            if i + 2 >= len(toks) or toks[i + 2].lower() not in TIME_UNITS:
                raise ValueError("mismatched input '" + (toks[i + 2] if i + 2 < len(toks) else "<EOF>") + "' expecting {ticks, milliseconds, seconds, minutes, hours}")
            i += 3
        elif w in ("until", "before"):
            j = _expr_end(toks, i + 1, stop_words=("satisfy",))
            i = j
        elif w == "every":
            raise ValueError("mismatched input 'every' expecting {',', AFTER, ALWAYS, AT, BEFORE, EVENTUALLY, FINALLY, FOR, IMMEDIATELY, INITIALLY, NEVER, SATISFY, UNTIL, WITH, WITHIN}")
        if i >= len(toks) or toks[i].lower() != "satisfy":
            raise ValueError("mismatched input '" + (toks[i] if i < len(toks) else "<EOF>") + "' expecting SATISFY")
        j0 = i + 1
        if j0 < len(toks) and toks[j0].lower() == "if":  # response form: if A then B (liquid mixer pairs)
            j = _expr_end(toks, j0 + 1, stop_words=("then",))
            if j < len(toks) and toks[j].lower() == "then":
                j = _expr_end(toks, j + 1)
        else:
            j = _expr_end(toks, j0)
        if j < len(toks):
            raise ValueError("Trailing unparsed input: '" + " ".join(toks[j:]) + "'")
        # ----- pre: [scope] [condition] component
        toks = _tok(pre)
        i = 0
        if i < len(toks) and toks[i].lower() in SCOPE_KW:
            kw = toks[i].lower()
            if kw == "notin":
                raise ValueError("mismatched input 'notin' expecting {...}")
            if kw == "in":
                if i + 1 >= len(toks) or not re.fullmatch(r"[A-Za-z_]\w*", toks[i + 1]):
                    raise ValueError("no viable alternative at input 'in'")
                i += 2
                if i < len(toks) and toks[i].lower() == "mode":
                    i += 1
            else:
                i = _expr_end(toks, i + 1, stop_words=tuple(COND_KW))
        if i < len(toks) and toks[i].lower() in COND_KW:
            i = _expr_end(toks, i + 1)
        rest = [t for t in toks[i:]]
        if rest and rest[0].lower() == "the":
            rest = rest[1:]
        if not rest:
            raise ValueError("mismatched input 'shall' expecting ID")
        if len(rest) > 1 or not re.fullmatch(r"[A-Za-z_]\w*", rest[0]):
            raise ValueError(f"extraneous input '{rest[0]}' expecting {{AND, IF, SHALL, THE, UNLESS, UPON, WHEN, WHENEVER, WHERE, ID}}; mismatched input 'shall' expecting SHALL")
        if rest[0].lower() == "mode":
            raise ValueError("mismatched input 'mode' expecting {'!', '~', '(', 'true', 'false', '-', AT, IF, ID, NUMBER}")
        return {"ok": True, "error": None}
    except ValueError as e:
        return {"ok": False, "error": str(e)}
