"""Template -> FRETish by mechanical rules (v3). No model call in this file.

Pipeline of one template sentence:
  parse_template(tpl, sentence)  -> TplParse (clauses, subject, modal, response phrase, extracted timing) or a recorded failure code
  slot_requests(parse)           -> the named phrases a model must turn into Boolean expressions (the ONLY step left to the model)
  assemble(parse, slot_values)   -> FRETish string (or a recorded failure code), by the rule table RULES
Every decision the script takes is a rule with an id (RULES). A rule is OBSERVED when the official parser behaviour behind it was seen in the
previous runs, SOURCE when the template source defines the construct, DEFAULT when the bench author chose (the sources leave it open; 추측입니다).
The script never reads the reference FRETish.
"""
import re

import fretlint as L

# ------------------------------------------------------------------ rule table (documentation + coverage counting)
RULES = {
    # template syntax -> field mapping
    "R-EARS-WHEN": ("EARS", "WHEN <trigger> -> condition `when <expr>`", "DEFAULT", "FRETish keyword when exists in all NASA examples read"),
    "R-EARS-IF": ("EARS", "IF <trigger> THEN -> condition `if <expr>`", "DEFAULT", "keyword if exists in the NASA examples read"),
    "R-EARS-WHILE": ("EARS", "WHILE <state> -> scope `in <id> mode` when the state is a single named mode, else scope `while <expr>`", "DEFAULT",
                     "`while <expr>` accepted by the official parser (run 2 GT rows); `in <id> mode` is the documented scope form"),
    "R-EARS-WHERE": ("EARS", "WHERE <feature> -> scope `while <expr>` (a feature flag is a state, not an event)", "DEFAULT", "semantic reading by the bench author"),
    "R-EARS-UB": ("EARS", "no keyword -> no scope, no condition", "SOURCE", "EARS ubiquitous type"),
    "R-MAS-IF": ("MASTeR", "IF <logic> -> condition `if <expr>`", "DEFAULT", "keyword preserved"),
    "R-MAS-SOON": ("MASTeR", "AS SOON AS <event> -> condition `when <expr>`", "DEFAULT", "event = trigger"),
    "R-MAS-LONG": ("MASTeR", "AS LONG AS <state> -> scope (as WHILE)", "DEFAULT", "time period / state"),
    "R-MAS-ABLE": ("MASTeR", "SHALL BE ABLE TO <verb object> -> response phrase `<verb object>` (the ability wrapper is dropped, recorded)", "DEFAULT", "no FRETish slot for ability"),
    "R-MAS-PROVIDE": ("MASTeR", "SHALL PROVIDE <whom> WITH THE ABILITY TO <v o> -> response phrase `<whom> can <v o>`", "DEFAULT", "no FRETish slot"),
    "R-ADV-WHEN": ("Adv-EARS", "When <pre> -> condition `when <expr>`", "DEFAULT", "as EARS"),
    "R-ADV-IF": ("Adv-EARS", "IF <pre> THEN -> condition `if <expr>`", "DEFAULT", "as EARS"),
    "R-ADV-WHILE": ("Adv-EARS", "WHILE <state> -> scope (as EARS)", "DEFAULT", "as EARS"),
    "R-ADV-WHERE": ("Adv-EARS", "WHERE <feature> -> scope `while <expr>`", "DEFAULT", "as EARS"),
    "R-ADV-HY": ("Adv-EARS", "WHILE <state> if <pre> / if necessary -> scope + condition `if <expr>`; `if necessary` adds nothing", "DEFAULT", "Adv-EARS hybrid type"),
    "R-ADV-PERFORM": ("Adv-EARS", "shall perform <functionality> -> response phrase `<functionality>`", "DEFAULT", "the word perform carries no content"),
    "R-BP-WHILE": ("Boilerplate", "While <state>, -> scope (as EARS)", "DEFAULT", "operational condition = state"),
    "R-BP-IF": ("Boilerplate", "If <event or state>, -> condition `if <expr>`", "DEFAULT", "keyword preserved"),
    "R-BP-UNLESS": ("Boilerplate", "Unless <x>, -> condition `if !(<expr>)`", "DEFAULT", "unless is not used (parser acceptance not observed)"),
    "R-BP-SUFFIX": ("Boilerplate", "suffix after/before/using/within..of -> see R-TIME-*", "DEFAULT", "suffix clauses are timing or condition"),
    "R-SP-GLOBAL": ("SPIDER", "Globally -> no scope", "SOURCE", "ICSE 2005 rule 2"),
    "R-SP-BEFORE": ("SPIDER", "Before R -> scope `before <expr>`", "DEFAULT", "FRETish scope keyword before"),
    "R-SP-AFTER": ("SPIDER", "After Q -> scope `after <expr>`", "DEFAULT", "FRETish scope keyword after"),
    "R-SP-AFTERUNTIL": ("SPIDER", "After Q until R / Between Q and R -> scope `after <expr>` and timing `until <expr>`", "DEFAULT", "no between scope in FRETish (not observed)"),
    "R-SP-UNIV": ("SPIDER", "it is always the case that P holds -> timing always, response P", "DEFAULT", ""),
    "R-SP-ABS": ("SPIDER", "it is never the case that P holds -> timing never, response P", "DEFAULT", ""),
    "R-SP-EXIST": ("SPIDER", "P eventually holds -> timing eventually, response P", "DEFAULT", ""),
    "R-SP-RESP": ("SPIDER", "if P holds, then S eventually holds -> condition `when P`, timing eventually, response S", "DEFAULT", "trigger semantics (RE 2020 paper) is not state semantics"),
    "R-SP-PREC": ("SPIDER", "if P holds, then S previously held -> timing `before P`, response S (semantics NOT verified)", "DEFAULT", "past operators do not exist in FRETish timing"),
    "R-SP-BRESP": ("SPIDER", "if P holds, then S holds after at most c units -> condition `when P`, timing `within c units`", "DEFAULT", ""),
    "R-SP-BINV": ("SPIDER", "if P holds, then S holds for at least c units -> condition `when P`, timing `for c units`", "DEFAULT", ""),
    "R-SP-MINDUR": ("SPIDER", "once P becomes satisfied, it holds for at least c units -> condition `when P`, timing `for c units`, response P", "DEFAULT", ""),
    "R-SP-COMP": ("SPIDER", "SPIDER has no component slot -> component identifier `system`", "DEFAULT", "grammar has no component"),
    "R-SP-NOMAP": ("SPIDER", "chains, bounded existence, max duration, periodic recurrence -> NO mapping, failure code recorded", "DEFAULT", "every is rejected by the parser (observed)"),
    # shared
    "R-COMP": ("*", "component = subject phrase without article, as snake_case identifier (mechanical, no model)", "DEFAULT", "identifier shape OBSERVED: spaces and hyphens rejected"),
    "R-TIME-WITHIN": ("*", "within N <unit> -> timing `within N <unit word>`", "OBSERVED", "accepted: within N milliseconds/seconds/minutes/hours/ticks"),
    "R-TIME-FOR": ("*", "for [at least] N <unit> -> timing `for N <unit word>`", "OBSERVED", "accepted for hours (3 of 3)"),
    "R-TIME-AFTER": ("*", "after N <unit> -> timing `after N <unit word>`", "OBSERVED", "accepted after minutes/seconds"),
    "R-TIME-UNTIL": ("*", "until <phrase> -> timing `until <expr>`", "DEFAULT", "timing keyword listed in the NASA guide"),
    "R-TIME-BEFORE": ("*", "before <phrase> -> timing `before <expr>`", "DEFAULT", "timing keyword listed in the NASA guide"),
    "R-TIME-ADV": ("*", "immediately/always/never/eventually -> timing keyword", "SOURCE", "NASA guide"),
    "R-TIME-NEXT": ("*", "at the next time step -> timing `next`", "DEFAULT", "timing keyword next exists in NASA reports"),
    "R-TIME-PROB": ("*", "with probability <= p -> `with probability <= p`", "OBSERVED", "accepted in GT rows (NASA/TM-20240006865)"),
    "R-TIME-EVERY": ("*", "every N <unit> -> NO mapping (parser rejects every), failure code recorded", "OBSERVED", "every rejected 18 of 18"),
    "R-DEFTIME": ("*", "no timing given: `always` when there is no condition, no timing word when there is a condition", "DEFAULT", "GT timing by condition in the residual pool"),
    "R2-TIME": ("*", "v7 (+R2 arms only): no timing given and not a negation: the timing is a slot answered by the model (always, immediately, eventually); never left out", "FRET", "Adam et al. 2023: omitted timing is read as eventually; compiled output (!LAST) U response"),
    "R-NEG": ("*", "shall not X -> timing `never` + X when no other timing, else `satisfy !(X)`", "DEFAULT", ""),
    "R-MULTI": ("*", "several triggers -> `(e1) & (e2)`; several states -> `while (e1) & (e2)`", "DEFAULT", ""),
    "L-UNIT": ("*", "unit words ms/s/sec/step... -> milliseconds/seconds/ticks (script)", "OBSERVED", "ms rejected 15 of 15"),
    "L-ABS": ("*", "abs( -> absReal( (script)", "OBSERVED", "abs rejected 41 times, absReal accepted"),
    "L-SYM": ("*", "unicode and C-style operators -> FRETish operators (script)", "OBSERVED", "token recognition errors"),
}

# ------------------------------------------------------------------ generic sentence engine
MODAL_RE = re.compile(r"\b(shall|should|will|must)\b(\s+not)?", re.I)
ABLE_RE = re.compile(r"^\s*be\s+able\s+to\s+", re.I)
PROVIDE_RE = re.compile(r"^\s*provide\s+(?P<whom>.+?)\s+with\s+the\s+ability\s+to\s+(?P<rest>.+)$", re.I)
PERFORM_RE = re.compile(r"^\s*perform\s+", re.I)
NUM = r"(?P<n>\d+(?:\.\d+)?)"
UNITW = r"(?P<u>ticks?|time\s+units?|time\s+steps?|cycles?|steps?|milliseconds?|msecs?|ms|seconds?|secs?|s|minutes?|mins?|hours?|hrs?|h|days?|weeks?|microseconds?)"

KWS = {
    "EARS": [("WHEN", "trigger", "R-EARS-WHEN"), ("IF", "trigger_if", "R-EARS-IF"), ("WHILE", "state", "R-EARS-WHILE"), ("WHERE", "state_feature", "R-EARS-WHERE")],
    "Adv-EARS": [("WHEN", "trigger", "R-ADV-WHEN"), ("IF", "trigger_if", "R-ADV-IF"), ("WHILE", "state", "R-ADV-WHILE"), ("WHERE", "state_feature", "R-ADV-WHERE")],
    "MASTeR": [("AS SOON AS", "trigger", "R-MAS-SOON"), ("AS LONG AS", "state", "R-MAS-LONG"), ("IF", "trigger_if", "R-MAS-IF")],
    "Boilerplate": [("WHILE", "state", "R-BP-WHILE"), ("IF", "trigger_if", "R-BP-IF"), ("UNLESS", "unless", "R-BP-UNLESS")],
}


def _clean(s):
    s = re.sub(r"\s+", " ", (s or "").replace("’", "'").replace("“", '"').replace("”", '"')).strip()
    s = re.sub(r"[.;]+$", "", s).strip()
    return s


def _kw_alt(tpl):
    return "|".join(re.escape(k).replace(r"\ ", r"\s+") for k, _, _ in sorted(KWS[tpl], key=lambda x: -len(x[0])))


def _split_subject(pre, tpl):
    """pre = text before the modal. Returns (clause_text, subject, how)."""
    if not re.match(r"^\s*(?:" + _kw_alt(tpl) + r")\b", pre, re.I):
        return "", pre, "none"          # no keyword clause: the whole text is the subject (it may contain commas: "The NN output, z,")
    m = list(re.finditer(r"\s+then\s+", pre, re.I))
    if m:
        return pre[:m[-1].start()], pre[m[-1].end():], "then"
    if "," in pre:
        i = pre.rfind(",")
        return pre[:i], pre[i + 1:].strip(), "comma"
    lead = re.match(r"^\s*(?:" + _kw_alt(tpl) + r")\b", pre, re.I)
    if not lead:
        return "", pre, "none"
    arts = [mm.start() for mm in re.finditer(r"\b(?:the|a|an)\s", pre, re.I)]
    arts = [i for i in arts if i > lead.end()]
    if arts:
        return pre[:arts[-1]], pre[arts[-1]:], "heuristic_the"
    w = pre.rsplit(" ", 1)
    return (w[0], w[1], "heuristic_lastword") if len(w) == 2 else ("", pre, "none")


def _split_clauses(text, tpl):
    """text = clause string(s) before the subject: 'WHILE a, WHEN b'. -> list of dicts, or None when the text does not start with a keyword."""
    alt = _kw_alt(tpl)
    out, rest = [], text.strip()
    pat = re.compile(r"(?:^|,\s*)(" + alt + r")\b\s*", re.I)
    ms = list(pat.finditer(rest))
    if not ms or ms[0].start() != 0:
        return None
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(rest)
        out.append({"kw": re.sub(r"\s+", " ", m.group(1).upper()), "text": rest[m.end():end].strip(" ,")})
    return out


def _kw_info(tpl, kw):
    for k, kind, rid in KWS[tpl]:
        if k == kw:
            return kind, rid
    return None, None


def _extract_timing(post):
    """Remove timing and suffix phrases from the predicate. -> (response_phrase, timings list, suffixes list, rule ids, no_mapping list, unit problems)"""
    rules, nomap, unitprob = [], [], []
    timings, suff = [], []
    p = " " + post + " "

    def take(rx, fn):
        nonlocal p
        m = re.search(rx, p, re.I)
        if m:
            fn(m)
            p = p[:m.start()] + " " + p[m.end():]
            return True
        return False

    def unit_of(m):
        u, note = L.norm_unit(m.group("u"))
        if u is None:
            unitprob.append(note + ":" + m.group("u"))
        return u

    # probability first (it contains numbers)
    def f_prob(m):
        timings.append({"kind": "prob", "op": m.group("op"), "n": m.group("n")})
        rules.append("R-TIME-PROB")
    take(r"\bwith\s+probability\s+(?P<op><=|>=|<|>)\s*" + NUM, f_prob)
    # every: not mappable
    EVERY_RX = r"\b(?:at\s+least\s+)?every\s+(?:(?:" + NUM + r"\s*" + UNITW + r")|(?:second|minute|hour|millisecond|tick)s?\b)"
    if re.search(EVERY_RX, p, re.I):
        nomap.append("every")
        rules.append("R-TIME-EVERY")
        take(EVERY_RX, lambda m: None)
    # within N unit [of|from|after EVENT]
    def f_within(m):
        u = unit_of(m)
        timings.append({"kind": "within", "n": m.group("n"), "unit": u})
        rules.append("R-TIME-WITHIN")
        if m.groupdict().get("ev"):
            suff.append({"kind": "event", "text": m.group("ev").strip(" ,")})
    take(r"\bwithin\s+(?:at\s+most\s+)?" + NUM + r"\s*" + UNITW + r"(?:\s+(?:of|from|after|following)\s+(?P<ev>.+?))?(?=\s+(?:while|until|before|and)\b|\s*$)", f_within)
    def f_for(m):
        u = unit_of(m)
        timings.append({"kind": "for", "n": m.group("n"), "unit": u})
        rules.append("R-TIME-FOR")
    take(r"\bfor\s+(?:at\s+least\s+)?" + NUM + r"\s*" + UNITW + r"\b", f_for)
    def f_after(m):
        u = unit_of(m)
        timings.append({"kind": "after", "n": m.group("n"), "unit": u})
        rules.append("R-TIME-AFTER")
    take(r"\bafter\s+" + NUM + r"\s*" + UNITW + r"\b", f_after)
    # operational condition suffix: while <cond> (to the end)
    def f_while(m):
        suff.append({"kind": "state", "text": m.group("t").strip(" ,")})
        rules.append("R-BP-SUFFIX")
    take(r"\bwhile\s+(?P<t>.+?)(?=\s+(?:until|before)\b|\s*$)", f_while)
    def f_until(m):
        timings.append({"kind": "until", "text": m.group("t").strip(" ,")})
        rules.append("R-TIME-UNTIL")
    take(r"\buntil\s+(?P<t>.+?)\s*$", f_until)
    def f_before(m):
        timings.append({"kind": "before", "text": m.group("t").strip(" ,")})
        rules.append("R-TIME-BEFORE")
    if re.search(r"\bbefore\s+\w+(?:\s+\w+){0,7}\s*$", p, re.I):
        take(r"\bbefore\s+(?P<t>[^,]+?)\s*$", f_before)
    take(r"\bat\s+the\s+next\s+(?:time\s*step|timepoint|time\s+point|tick)\b", lambda m: (timings.append({"kind": "next"}), rules.append("R-TIME-NEXT")))
    for adv in ("immediately", "always", "never", "eventually"):
        take(r"\b" + adv + r"\b", lambda m, a=adv: (timings.append({"kind": a}), rules.append("R-TIME-ADV")))
    return re.sub(r"\s+", " ", p).strip(" ,"), timings, suff, rules, nomap, unitprob


def parse_generic(tpl, sentence):
    """Parser for MASTeR, EARS, Adv-EARS, Boilerplate. -> dict (ok True) or dict(ok False, code, detail)."""
    s = _clean(sentence)
    out = {"ok": False, "template": tpl, "sentence": sentence, "rules": [], "notes": []}
    m = MODAL_RE.search(s)
    if not m:
        out.update(code="tpl_no_modal", detail="no shall/should/will/must found")
        return out
    pre, post = s[:m.start()].strip(), s[m.end():].strip()
    neg = bool(m.group(2))
    clause_text, subject, how = _split_subject(pre, tpl)
    out["notes"].append("split:" + how)
    clauses = []
    hy_necessary = False
    if clause_text:
        cl = _split_clauses(clause_text, tpl)
        if cl is None:
            # Adv-EARS hybrid / keyword not at the start, or a subject that starts with the leftover text
            out.update(code="tpl_unknown_prefix", detail="text before the subject does not start with a keyword of the template: " + clause_text[:80])
            return out
        clauses = cl
    elif how == "none" and re.match(r"^\s*(?:" + _kw_alt(tpl) + r")\b", subject, re.I):
        out.update(code="tpl_no_subject", detail="keyword clause without a subject before the modal")
        return out
    # Adv-EARS hybrid: WHILE <state> if <pre> / if necessary
    if tpl == "Adv-EARS" and len(clauses) == 1 and clauses[0]["kw"] == "WHILE":
        hm = re.match(r"^(?P<st>.+?)\s+if\s+(?P<pre>.+)$", clauses[0]["text"], re.I)
        if hm:
            clauses[0]["text"] = hm.group("st").strip()
            if hm.group("pre").strip().lower() == "necessary":
                hy_necessary = True
            else:
                clauses.append({"kw": "IF", "text": hm.group("pre").strip()})
            out["rules"].append("R-ADV-HY")
    subj = re.sub(r"^\s*(?:the|a|an)\s+", "", subject.strip(), flags=re.I).strip()
    if not subj:
        out.update(code="tpl_no_subject", detail="empty subject")
        return out
    # modal tail forms
    rules = out["rules"]
    able = ABLE_RE.match(post)
    prov = PROVIDE_RE.match(post)
    if prov:
        post = f"{prov.group('whom')} can {prov.group('rest')}"
        rules.append("R-MAS-PROVIDE")
    elif able:
        post = post[able.end():]
        rules.append("R-MAS-ABLE")
        out["notes"].append("ability_wrapper_dropped")
    pm = PERFORM_RE.match(post)
    if pm and tpl == "Adv-EARS":
        post = post[pm.end():]
        rules.append("R-ADV-PERFORM")
    resp, timings, suff, trules, nomap, unitprob = _extract_timing(post)
    rules += trules
    cl_out = []
    for c in clauses:
        kind, rid = _kw_info(tpl, c["kw"])
        if kind is None:
            out.update(code="tpl_unknown_prefix", detail="keyword " + c["kw"])
            return out
        rules.append(rid)
        cl_out.append({"kw": c["kw"], "kind": kind, "text": c["text"]})
    for sf in suff:
        if sf["kind"] == "state":
            cl_out.append({"kw": "(suffix) WHILE", "kind": "state", "text": sf["text"]})
        else:
            cl_out.append({"kw": "(suffix) OF/FROM", "kind": "trigger", "text": sf["text"]})
    if not resp:
        out.update(code="tpl_no_response", detail="nothing left after the modal verb and timing phrases")
        return out
    out.update(ok=True, clauses=cl_out, subject=subj, modal=m.group(1).lower(), neg=neg, resp=resp, timings=timings, nomap=nomap, unitprob=unitprob,
               hy_necessary=hy_necessary)
    if not clauses and not suff:
        rules.append("R-EARS-UB")
    return out


# ------------------------------------------------------------------ SPIDER
PC = r"(?P<{}>.+?)"
SP_PATTERNS = [
    ("bresp", r"^it is always the case that if (?P<p>.+?)(?: holds)?,? then (?P<s>.+?)(?: holds)? after at most " + NUM + r"(?:\s*" + UNITW + r")?$"),
    ("binv", r"^it is always the case that if (?P<p>.+?)(?: holds)?,? then (?P<s>.+?)(?: holds)? for at least " + NUM + r"(?:\s*" + UNITW + r")?$"),
    ("mindur", r"^it is always the case that once (?P<p>.+?)(?: becomes satisfied)?,? it holds for at least " + NUM + r"(?:\s*" + UNITW + r")?$"),
    ("maxdur", r"^it is always the case that once (?P<p>.+?)(?: becomes satisfied)?,? it holds for less than " + NUM + r"(?:\s*" + UNITW + r")?$"),
    ("periodic", r"^it is always the case that (?P<p>.+?)(?: holds)? at least every " + NUM + r"(?:\s*" + UNITW + r")?$"),
    ("chain", r"^it is always the case that if (?P<p>.+?)(?: holds)?.*(?:succeeded by|preceded by|previously held and|where .* does not hold).*$"),
    ("resp", r"^it is always the case that if (?P<p>.+?)(?: holds)?,? then (?P<s>.+?) eventually(?: holds)?$"),
    ("prec", r"^it is always the case that if (?P<p>.+?)(?: holds)?,? then (?P<s>.+?) previously held$"),
    ("boundex", r"^transitions to states in which (?P<p>.+?)(?: holds)? occur at most twice$"),
    ("abs", r"^it is never the case that (?P<p>.+?)(?: holds)?$"),
    ("univ", r"^it is always the case that (?P<p>.+?)(?: holds)?(?: until (?P<r2>.+?)(?: holds)?)?$"),
    ("exist", r"^(?P<p>.+?) eventually(?: holds)?$"),
]


def _unparen(x):
    x = x.strip()
    while x.startswith("(") and x.endswith(")") and _balanced(x[1:-1]):
        x = x[1:-1].strip()
    return x


def _balanced(x):
    d = 0
    for ch in x:
        d += (ch == "(") - (ch == ")")
        if d < 0:
            return False
    return d == 0


def _top_index(text, token, start=0):
    """index of token (case-insensitive) outside parentheses, or -1"""
    d, low, t = 0, text.lower(), token.lower()
    for k in range(start, len(text)):
        ch = text[k]
        d += (ch == "(") - (ch == ")")
        if d == 0 and low.startswith(t, k):
            return k
    return -1


def _spider_scope(s):
    """-> (scope dict, body) or (None, None). The scope phrase ends at the first comma outside parentheses."""
    m = re.match(r"^(globally|before|after|between)\b\s*", s, re.I)
    if not m:
        return None, None
    kw = m.group(1).lower()
    ci = _top_index(s, ",", m.end())
    if ci < 0:
        return None, None
    phrase, body = s[m.end():ci].strip(), s[ci + 1:].strip()
    if not body:
        return None, None
    if kw == "globally":
        return {"kind": "global", "q": "", "r": ""}, body
    if kw == "before":
        return {"kind": "before", "q": "", "r": _unparen(phrase)}, body
    if kw == "between":
        k = _top_index(phrase, " and ")
        return ({"kind": "between", "q": _unparen(phrase[:k]), "r": _unparen(phrase[k + 5:])}, body) if k > 0 else (None, None)
    k = _top_index(phrase, " until ")
    if k > 0:
        return {"kind": "afteruntil", "q": _unparen(phrase[:k]), "r": _unparen(phrase[k + 7:])}, body
    return {"kind": "after", "q": _unparen(phrase), "r": ""}, body


def parse_spider(sentence):
    s = _clean(sentence)
    out = {"ok": False, "template": "SPIDER", "sentence": sentence, "rules": [], "notes": []}
    scope, body = _spider_scope(s)
    if scope is None:
        out.update(code="tpl_no_scope", detail="SPIDER property must start with Globally/Before/After/Between ... followed by a comma")
        return out
    kind = scope["kind"]
    out["rules"].append({"global": "R-SP-GLOBAL", "before": "R-SP-BEFORE", "after": "R-SP-AFTER", "afteruntil": "R-SP-AFTERUNTIL", "between": "R-SP-AFTERUNTIL"}[kind])
    for name, pat in SP_PATTERNS:
        m = re.match(pat, body, re.I)
        if m:
            gd = m.groupdict()
            pat_out = {"pattern": name, "p": _unparen(gd.get("p") or ""), "s": _unparen(gd.get("s") or ""), "n": gd.get("n"), "u": gd.get("u"),
                       "r2": _unparen(gd.get("r2") or "")}
            break
    else:
        out.update(code="tpl_no_pattern", detail="no SPIDER pattern of ICSE 2005 Figure 3 matches: " + body[:100])
        return out
    nm = {"chain": "chain", "boundex": "bounded existence", "maxdur": "max duration", "periodic": "periodic recurrence"}
    if name in nm:
        out["rules"].append("R-SP-NOMAP")
        out.update(ok=True, scope=scope, pat=pat_out, nomap=[nm[name]], unitprob=[], timings=[], clauses=[])
        return out
    unitprob = []
    if pat_out["u"]:
        u, note = L.norm_unit(pat_out["u"])
        if u is None:
            unitprob.append(note + ":" + pat_out["u"])
        pat_out["unit"] = u
    elif pat_out["n"]:
        unitprob.append("unit_missing:" + pat_out["n"])
    out["rules"].append({"bresp": "R-SP-BRESP", "binv": "R-SP-BINV", "mindur": "R-SP-MINDUR", "resp": "R-SP-RESP", "prec": "R-SP-PREC", "abs": "R-SP-ABS",
                         "univ": "R-SP-UNIV", "exist": "R-SP-EXIST"}[name])
    out["rules"].append("R-SP-COMP")
    out.update(ok=True, scope=scope, pat=pat_out, nomap=[], unitprob=unitprob, timings=[], clauses=[], subject="system")
    return out


def parse_template(tpl, sentence):
    return parse_spider(sentence) if tpl == "SPIDER" else parse_generic(tpl, sentence)


# ------------------------------------------------------------------ slots
def slot_requests(p, r2=False):
    """Named phrases the model has to turn into expressions. -> ordered dict name -> {"phrase":..., "kind": expr|state}"""
    req = {}
    if p["template"] == "SPIDER":
        sc, pt = p["scope"], p["pat"]
        if sc["q"]:
            req["q"] = {"phrase": sc["q"], "kind": "expr"}
        if sc["r"]:
            req["r"] = {"phrase": sc["r"], "kind": "expr"}
        if pt["p"]:
            req["p"] = {"phrase": pt["p"], "kind": "expr"}
        if pt["s"]:
            req["s"] = {"phrase": pt["s"], "kind": "expr"}
        if pt.get("r2"):
            req["r2"] = {"phrase": pt["r2"], "kind": "expr"}
        return req
    ci = si = 0
    for c in p["clauses"]:
        if c["kind"].startswith("state"):
            si += 1
            c["slot"] = f"s{si}"
            req[c["slot"]] = {"phrase": c["text"], "kind": "state"}
        else:
            ci += 1
            c["slot"] = f"c{ci}"
            req[c["slot"]] = {"phrase": c["text"], "kind": "expr"}
    req["r"] = {"phrase": p["resp"], "kind": "expr"}
    if r2 and not [x for x in p["timings"] if x["kind"] != "prob"] and not p["neg"]:
        req["tm"] = {"phrase": "(choose always, immediately or eventually)", "kind": "timing"}
    for k, t in enumerate(p["timings"]):
        if t["kind"] in ("until", "before"):
            t["slot"] = f"t{k + 1}"
            req[t["slot"]] = {"phrase": t["text"], "kind": "expr"}
    return req


# ------------------------------------------------------------------ assembly
def _paren(e):
    e = e.strip()
    return e if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*|\d+(?:\.\d+)?", e) or (e.startswith("(") and e.endswith(")") and _balanced(e[1:-1])) else f"({e})"


def _join(exprs, op="&"):
    return exprs[0] if len(exprs) == 1 else f" {op} ".join(_paren(x) for x in exprs)


def _timing_str(t, slots):
    k = t["kind"]
    if k in ("within", "for", "after"):
        return f"{k} {t['n']} {t['unit']}"
    if k in ("until", "before"):
        return f"{k} {slots[t['slot']]['expr']}"
    if k == "prob":
        return f"with probability {t['op']} {t['n']}"
    return k


def assemble(p, slots, r2=False):
    """p = parse (ok True); slots = {name: {"expr": str, "mode": str|None, "violations": [..], "fixes": [..]}} (already linted).
    -> dict(ok, fretish, code, detail, rules) ; codes are recorded failures of the rule layer."""
    rules = list(p["rules"])
    if p["nomap"]:
        return {"ok": False, "code": "rule_no_mapping", "detail": ",".join(p["nomap"]), "rules": rules}
    if p["unitprob"]:
        return {"ok": False, "code": "rule_unit_unsupported", "detail": ",".join(p["unitprob"]), "rules": rules}
    viol = [f"{n}:{v}" for n, s in slots.items() for v in s.get("violations", [])]
    if viol:
        return {"ok": False, "code": "slot_lint", "detail": "; ".join(viol), "rules": rules, "fretish": None}
    if p["template"] == "SPIDER":
        return _assemble_spider(p, slots, rules)
    scope_parts, trig = [], []
    states = []
    for c in p["clauses"]:
        v = slots[c["slot"]]
        kind = c["kind"]
        if kind.startswith("state"):
            states.append(v)
        elif kind == "trigger":
            trig.append(("when", v["expr"]))
        elif kind == "trigger_if":
            trig.append(("if", v["expr"]))
        elif kind == "unless":
            trig.append(("if", "!" + _paren(v["expr"])))
    scope = ""
    if states:
        if len(states) == 1 and states[0].get("mode"):
            scope = f"in {states[0]['mode']} mode"
        else:
            scope = "while " + _join([s["expr"] for s in states])
        if len(states) > 1:
            rules.append("R-MULTI")
    cond = ""
    if trig:
        kws = {k for k, _ in trig}
        kw = "when" if "when" in kws else "if"
        cond = kw + " " + _join([e for _, e in trig])
        if len(trig) > 1:
            rules.append("R-MULTI")
    timings = [t for t in p["timings"] if t["kind"] != "prob"]
    prob = [t for t in p["timings"] if t["kind"] == "prob"]
    if len(timings) > 1:
        ks = {t["kind"] for t in timings}
        if not (ks <= {"always", "immediately"}):
            return {"ok": False, "code": "rule_no_mapping", "detail": "multi_timing:" + ",".join(sorted(ks)), "rules": rules}
        timings = timings[:1]
    resp = slots["r"]["expr"]
    tstr = ""
    if p["neg"]:
        rules.append("R-NEG")
        if not timings and not prob:
            tstr = "never"
        else:
            resp = "!" + _paren(resp)
    if timings:
        tstr = _timing_str(timings[0], slots)
    if prob:
        tstr = (_timing_str(prob[0], slots) + " " + tstr).strip()
    if not tstr and r2 and "tm" in slots:
        rules.append("R2-TIME")
        tstr = slots["tm"]["expr"]
    elif not tstr:
        rules.append("R-DEFTIME")
        if not cond:
            tstr = "always"
    comp = L.snake_ident(p["subject"])
    rules.append("R-COMP")
    if not L.valid_ident(comp):
        return {"ok": False, "code": "slot_lint", "detail": f"component:{comp!r}", "rules": rules}
    parts = [x for x in (scope, cond, comp, "shall", tstr, "satisfy", resp) if x]
    return {"ok": True, "fretish": " ".join(parts), "rules": rules, "code": None, "detail": ""}


def _assemble_spider(p, slots, rules):
    sc, pt = p["scope"], p["pat"]
    g = lambda k: slots[k]["expr"]
    name = pt["pattern"]
    scope, tstr, cond, resp = "", "", "", ""
    if sc["kind"] == "before":
        scope = "before " + g("r")
    elif sc["kind"] == "after":
        scope = "after " + g("q")
    elif sc["kind"] in ("afteruntil", "between"):
        scope = "after " + g("q")
        tstr = "until " + g("r")
    if name == "univ":
        tstr, resp = tstr or "always", g("p")
        if pt.get("r2"):
            tstr, resp = "until " + g("r2"), g("p")
    elif name == "abs":
        tstr, resp = "never", g("p")
    elif name == "exist":
        tstr, resp = "eventually", g("p")
    elif name == "resp":
        cond, tstr, resp = "when " + g("p"), "eventually", g("s")
    elif name == "prec":
        tstr, resp = "before " + g("p"), g("s")
    elif name == "bresp":
        cond, tstr, resp = "when " + g("p"), f"within {pt['n']} {pt['unit']}", g("s")
    elif name in ("binv",):
        cond, tstr, resp = "when " + g("p"), f"for {pt['n']} {pt['unit']}", g("s")
    elif name == "mindur":
        cond, tstr, resp = "when " + g("p"), f"for {pt['n']} {pt['unit']}", g("p")
    parts = [x for x in (scope, cond, "system", "shall", tstr, "satisfy", resp) if x]
    return {"ok": True, "fretish": " ".join(parts), "rules": rules, "code": None, "detail": ""}


# ------------------------------------------------------------------ slot value linting (applied to what the model returned)
def lint_slots(req, raw):
    """req = slot_requests(...); raw = model output for this sentence {slot: str | {"expr"|"mode": str}}.
    -> {slot: {"expr", "mode", "violations", "fixes"}}  (missing slots are violations)."""
    out = {}
    for name, rq in req.items():
        v = raw.get(name) if isinstance(raw, dict) else None
        if rq["kind"] == "timing":
            w = (v.get("expr") if isinstance(v, dict) else v)
            w = str(w).strip().lower() if w is not None else ""
            out[name] = {"expr": w, "mode": None, "violations": [] if w in ("always", "immediately", "eventually") else ["E-TIMING:" + w[:20]], "fixes": []}
            continue
        mode = None
        if isinstance(v, dict):
            mode = (v.get("mode") or "").strip() or None
            v = v.get("expr") if v.get("expr") is not None else (v.get("mode") or "")
        if v is None or not str(v).strip():
            out[name] = {"expr": "", "mode": None, "violations": ["E-MISSING"], "fixes": []}
            continue
        e, fixes, viol = L.fix_expr(str(v))
        if mode is not None and rq["kind"] == "state":
            if not L.valid_ident(mode):
                viol = viol + ["E-MODEID:" + mode]
            else:
                viol = [x for x in viol if not x.startswith("E-WORD")] if False else viol
        out[name] = {"expr": e, "mode": mode if (rq["kind"] == "state" and mode and L.valid_ident(mode)) else None, "violations": viol, "fixes": fixes}
    return out
