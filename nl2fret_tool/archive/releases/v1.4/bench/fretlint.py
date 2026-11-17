"""Mechanical checks and repairs for FRETish pieces (v3). No model call here.

Everything in this file is derived from what the official FRET parser (FretSemantics.compile, FRET 3.0) was OBSERVED to accept or reject in the
previous two runs (about 1,500 distinct sentences, parse error texts in results of run 2). Each rule carries an id, an evidence note and a status:
  OBSERVED  seen as accepted / rejected by the official parser in the previous runs
  DEFAULT   a choice of the test bench author where the sources and the observations leave the choice open ("추측입니다")
Rules that are only syntax (units, symbols, reserved function names) are applied by the script. Nothing here reads the reference FRETish.
"""
import re

# ------------------------------------------------------------------ time units
# OBSERVED accepted after within / for / after: milliseconds, seconds, minutes, hours, ticks. Rejected: ms (15 of 15).
UNIT_MAP = {
    "tick": "ticks", "ticks": "ticks", "cycle": "ticks", "cycles": "ticks", "time unit": "ticks", "time units": "ticks", "time step": "ticks",
    "time steps": "ticks", "step": "ticks", "steps": "ticks",
    "ms": "milliseconds", "msec": "milliseconds", "msecs": "milliseconds", "millisecond": "milliseconds", "milliseconds": "milliseconds",
    "s": "seconds", "sec": "seconds", "secs": "seconds", "second": "seconds", "seconds": "seconds",
    "min": "minutes", "mins": "minutes", "minute": "minutes", "minutes": "minutes",
    "h": "hours", "hr": "hours", "hrs": "hours", "hour": "hours", "hours": "hours",
}
UNIT_RULE_ID = "L-UNIT"
UNSUPPORTED_UNITS = {"day", "days", "week", "weeks", "month", "months", "year", "years", "microsecond", "microseconds", "us"}  # not observed, not used


def norm_unit(u):
    """-> (frettish unit word or None, rule note)."""
    k = re.sub(r"\s+", " ", (u or "").strip().lower())
    if k in UNIT_MAP:
        return UNIT_MAP[k], None
    if k in UNSUPPORTED_UNITS:
        return None, "unit_unsupported"
    return None, "unit_unknown"


# ------------------------------------------------------------------ expressions
UNI = {"≤": "<=", "≥": ">=", "⇒": "=>", "−": "-", "≠": "!=", "→": "=>", "×": "*", "÷": "/", "’": "'",
       "“": '"', "”": '"', "°": ""}
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
NUMBER = re.compile(r"\d+(?:\.\d+)?")
OPS = ["<=>", "=>", "<=", ">=", "!=", "=", "<", ">", "&", "|", "!", "+", "-", "*", "/", "(", ")"]
WORDLIKE = {"and", "or", "not", "is", "the", "of", "than", "to", "then", "if", "when", "while", "true_if", "equals", "less", "greater", "more"}
FRET_CONST = {"true", "false", "TRUE", "FALSE"}


def tokenize_expr(e):
    """-> list of (kind, text). kind in id|num|op|bad. Whitespace dropped."""
    out, i = [], 0
    while i < len(e):
        ch = e[i]
        if ch.isspace():
            i += 1
            continue
        m = NUMBER.match(e, i)
        if m:
            out.append(("num", m.group()))
            i = m.end()
            continue
        m = IDENT.match(e, i)
        if m:
            out.append(("id", m.group()))
            i = m.end()
            continue
        for op in OPS:
            if e.startswith(op, i):
                out.append(("op", op))
                i += len(op)
                break
        else:
            out.append(("bad", ch))
            i += 1
    return out


def fix_expr(e):
    """Mechanical repairs of one boolean expression. -> (fixed, [rule ids applied], [violations])."""
    applied, viol = [], []
    s = e or ""
    for a, b in UNI.items():
        if a in s:
            s = s.replace(a, b)
            applied.append("L-SYM")
    for a, b in (("&&", "&"), ("||", "|"), ("==", "="), ("<->", "<=>"), ("~", "!")):
        if a in s:
            s = s.replace(a, b)
            applied.append("L-SYM")
    s2 = re.sub(r"\babs\s*\(", "absReal(", s)  # OBSERVED: abs( rejected (reserved), absReal( accepted
    if s2 != s:
        applied.append("L-ABS")
        s = s2
    s = re.sub(r"(?<=[\d)])\s*(?:%|percent)\b", "", s)  # OBSERVED: units and percent inside expressions rejected; the number is kept
    s = re.sub(r"\s+", " ", s).strip()
    toks = tokenize_expr(s)
    for k, t in toks:
        if k == "bad":
            viol.append(f"E-BADCHAR:{t}")
    for i, (k, t) in enumerate(toks):
        if k == "id" and t in ("max", "min") and i + 1 < len(toks) and toks[i + 1] == ("op", "("):
            viol.append(f"E-FUNC:{t}")  # OBSERVED: max( rejected as reserved
        if k == "id" and t in ("previous", "prev") and i + 1 < len(toks) and toks[i + 1] == ("op", "("):
            viol.append("E-FUNC:previous")  # OBSERVED: previous( rejected
        if k == "id" and t.lower() in WORDLIKE:
            viol.append(f"E-WORD:{t}")
        if k == "id" and t == "mode":
            viol.append("E-RESERVED:mode")  # OBSERVED: a variable named mode is rejected
    # number directly followed by identifier (a unit or a name starting with a digit)
    for i in range(len(toks) - 1):
        if toks[i][0] == "num" and toks[i + 1][0] == "id":
            viol.append(f"E-UNITINEXPR:{toks[i][1]} {toks[i + 1][1]}")
    # balanced parentheses
    depth = 0
    for k, t in toks:
        if t == "(":
            depth += 1
        elif t == ")":
            depth -= 1
        if depth < 0:
            break
    if depth != 0:
        viol.append("E-PAREN")
    if not toks:
        viol.append("E-EMPTY")
    return s, sorted(set(applied)), sorted(set(viol))


def valid_ident(x):
    """FRETish component or variable name: starts with a letter or underscore, letters digits underscore. OBSERVED: names starting with a digit or * rejected."""
    return bool(x) and bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", x)) and x.lower() not in {"mode", "shall", "satisfy", "the", "in", "before", "after", "when", "if",
                                                                                              "while", "until", "within", "always", "never", "eventually", "immediately",
                                                                                              "next", "for", "upon", "whenever", "unless", "where", "and", "or", "not"}


def snake_ident(s, maxw=6):
    """Mechanical identifier from words (used only for the DEFAULT component of SPIDER and for repair of invalid names)."""
    w = re.findall(r"[A-Za-z0-9]+", s or "")
    w = [x for x in w if x.lower() not in {"the", "a", "an", "of"}]
    t = "_".join(w[:maxw])
    if t and t[0].isdigit():
        t = "x_" + t
    return t


# ------------------------------------------------------------------ parser error classification
# The class names are the ones of the run 2 analysis. They decide only (a) which hint is sent back and (b) the failure code recorded.
# structural: the sentence shape is not accepted; expression: a symbol, a reserved word or a unit inside an expression; unknown: not matched.
ERR_CLASSES = [
    ("expr_reserved_abs_max", r"reserved letter combinations", "expression",
     "The function names abs and max (and min) are reserved. Use absReal(x) for the absolute value; max and min cannot be used, express the condition with comparisons and | instead."),
    ("expr_symbol", r"token recognition error", "expression",
     "A character that FRETish does not know was found in an expression (for example a unit, a degree sign, a percent sign, an asterisk or a bar |x|). Use only identifiers, numbers, ! & | => = != < <= > >= + - * / and parentheses; remove units and symbols."),
    ("struct_mode_word", r"mismatched input 'mode'", "structural",
     "The word mode is only allowed directly after the identifier of a scope, as in: in roll_hold mode. A scope takes ONE identifier. Do not use mode as a variable and do not put words between in and mode."),
    ("struct_expecting_shall", r"expecting SHALL|missing SHALL", "structural",
     "A component is a single identifier (letters, digits, underscore) optionally preceded by the. After scope and condition the next token must be the component followed by the word shall. Spaces, hyphens or extra words in the component name are not accepted."),
    ("struct_trailing", r"Trailing unparsed input", "structural",
     "Text remained after the response. A FRETish requirement is: [scope] [condition] component shall [timing] satisfy response, with nothing after the response expression. Do not append explanations, lists or a second sentence."),
    ("struct_number", r"expecting NUMBER", "structural",
     "A number is required here (after within, for, after, or in probability <= p). Write a numeric literal followed by one of: ticks, milliseconds, seconds, minutes, hours."),
    ("struct_relational", r"expecting RELATIONAL_OP", "structural",
     "After the word probability a relational operator and a number are required: with probability <= 0.01."),
    ("struct_timing_word", r"mismatched input 'every'|mismatched input 'ms'|mismatched input 's'", "structural",
     "The words every, ms, s and sec are not accepted. Use: within N seconds, for N seconds, after N seconds with the words ticks, milliseconds, seconds, minutes, hours."),
    ("struct_no_viable", r"no viable alternative", "structural",
     "The text could not be read as a FRETish requirement or expression at the position quoted in the message. Check the order scope, condition, component, shall, timing, satisfy, response and that the response is a Boolean expression."),
    ("struct_mismatched", r"mismatched input|extraneous input", "structural",
     "A token was found where the grammar does not allow it (see the quoted token). Check keywords and punctuation: scope keywords in, before, after, notin, onlyIn, onlyBefore, onlyAfter; condition keywords when, whenever, if, upon, unless; one component identifier; the word shall; optional timing; the word satisfy; a Boolean expression."),
]


def classify_error(msg):
    """-> (class, group, hint) for the first matching class; (unmatched, unknown, generic hint) otherwise."""
    m = msg or ""
    for cid, pat, grp, hint in ERR_CLASSES:
        if re.search(pat, m):
            return cid, grp, hint
    return "unmatched", "unknown", "The official FRET parser rejected the sentence; re-read the FRETish shape: [scope] [condition] component shall [timing] satisfy response."


def hints_for(msg):
    """All distinct hints for the classes present in an error message (messages often contain several errors)."""
    out, seen = [], set()
    for cid, pat, grp, hint in ERR_CLASSES:
        if re.search(pat, msg or "") and cid not in seen:
            seen.add(cid)
            out.append((cid, grp, hint))
    if not out:
        c = classify_error(msg)
        out.append(c)
    return out


# ------------------------------------------------------------------ whole-sentence normalizer (variant VN, applied to ANY arm's output; syntax only)
def normalize_fretish(s):
    """Mechanical syntax repairs on a finished FRETish sentence: unicode and C-style operators, abs( -> absReal(, unit words after within/for/after.
    Structure (scope, condition, component, trailing text) is NOT touched. -> (new sentence, [rule ids])"""
    applied = []
    t = s or ""
    for a, b in UNI.items():
        if a in t:
            t = t.replace(a, b)
            applied.append("L-SYM")
    for a, b in (("&&", "&"), ("||", "|"), ("==", "=")):
        if a in t:
            t = t.replace(a, b)
            applied.append("L-SYM")
    t2 = re.sub(r"\babs\s*\(", "absReal(", t)
    if t2 != t:
        applied.append("L-ABS")
        t = t2

    def unit_fix(m):
        u, _ = norm_unit(m.group(3))
        if u is None or u == m.group(3):
            return m.group(0)
        applied.append("L-UNIT")
        return f"{m.group(1)} {m.group(2)} {u}"
    t = re.sub(r"\b(within|for|after)\s+(\d+(?:\.\d+)?)\s*([A-Za-z]+(?:\s+units?)?)\b", unit_fix, t)
    t = re.sub(r"\s+", " ", t).strip()
    return t, sorted(set(applied))
