"""Shared code of the NL2FRET bench: paths, prompts, output parsers, a tolerant FRETish parser,
template keyword classifiers (ambiguity observables) and deterministic similarity metrics.

Nothing in this file calls a model. The FRETish parser is a HEURISTIC reader written by the bench author; it is not
the official FRET parser (the full FRETish grammar was not obtained). It is used only to classify outputs and to
compare field by field, and every number that depends on it is labelled "parser based" in the report.
"""
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATES = {
    "MASTeR": "templates/masteR.md",
    "EARS": "templates/ears.md",
    "Adv-EARS": "templates/adv_ears.md",
    "SPIDER": "templates/spider.md",
    "Boilerplate": "templates/boilerplate.md",
}
ARMS_E1 = list(TEMPLATES)          # experiment 1: raw -> template -> FRETish
ARM_E2 = "DIRECT"                  # experiment 2: raw -> FRETish
ALL_ARMS = ARMS_E1 + [ARM_E2]

# ------------------------------------------------------------------ small io helpers


def load_jsonl(path):
    p = Path(path)
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def sha(text, n=16):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:n]


def read_rel(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def spec_status(text):
    m = re.search(r"^SPEC_STATUS:\s*(\S+)", text, re.M)
    return m.group(1) if m else "unknown"


# ------------------------------------------------------------------ prompts

RULES_COMMON = """GENERAL RULES (apply to every task)
- Keep every piece of information of the input: component and variable names, numbers and units, parenthetical hints such as "(not standby)", conditions, order of events, negations, modal strength.
- Never invent identifiers, numbers, thresholds or default behaviour. If something cannot be expressed, list it in "unmapped_content" and do not drop it silently.
- Where the specification below leaves a choice open (for example two keywords could both describe the situation), decide yourself, do NOT ask for clarification, and report the choice in "choices" (at most 3 entries, each entry only the point and your choice, a few words each). No extra tie-breaking rule is provided by the test bench on purpose.
- Output exactly one JSON object and nothing else (no markdown fence, no text before or after). Keep it compact: one line of JSON, short strings, no explanations, no restating of the input, no reasoning text outside the fields.
- Do not use tools, do not ask questions, and do not write anything for the reader of the conversation; the program reads only the JSON."""

SCHEMA_A = """OUTPUT SCHEMA (stage A: natural language -> template)
{"sentences": ["<one or more sentences that follow the template specification>"],
 "requirement_type": "<name of the template form or type you used>",
 "split_reason": "<empty if one sentence, otherwise why the input needed several sentences>",
 "choices": [{"point": "<what had to be decided, e.g. condition keyword>", "chosen": "<your choice>"}],
 "unmapped_content": ["<content of the input that the template cannot carry>"]}
Use several sentences only if one template sentence cannot carry the input. Do NOT write FRETish."""

SCHEMA_B = """OUTPUT SCHEMA (FRETish)
{"fretish": ["<one FRETish requirement per string>"],
 "fields": [{"scope": "", "condition": "", "component": "", "timing": "", "response": ""}],
 "choices": [{"point": "<what had to be decided, e.g. scope or condition, default timing, identifier name>", "chosen": "<your choice>"}],
 "unmapped_content": ["<content of the input that FRETish cannot carry>"]}
"fields" has one object per FRETish string, in the same order, with the text you put into each field (empty string if the field is not used)."""

TASK_A = """TASK: Rewrite the natural language requirement given by the user into the requirement template described below. Input: one natural language requirement (the user message). Output: sentence(s) in that template."""
TASK_B = """TASK: The user message contains one or more sentences written in the requirement template named below (the original natural language is NOT given). Convert them into FRETish. Use the template specification only to read the input correctly."""
TASK_D = """TASK: Translate the natural language requirement given by the user directly into FRETish (NASA FRET structured English)."""

# control arm PARA: the same two-step flow as the template arms, but stage A uses no template (plain English rewrite)
ARM_PARA = "PARA"
TASK_A_PARA = """TASK: PLAIN ENGLISH REWRITE. Rewrite the natural language requirement given by the user into plain English sentence(s). Input: one natural language requirement (the user message). Output: one or more plain English sentences. Do not use a requirement template, do not use template keywords on purpose, and do not write FRETish."""
SCHEMA_A_PARA = """OUTPUT SCHEMA (stage A: natural language -> plain English rewrite)
{"sentences": ["<one or more plain English sentences>"],
 "requirement_type": "<a short free label of the kind of requirement>",
 "split_reason": "<empty if one sentence, otherwise why the input needed several sentences>",
 "choices": [{"point": "<what had to be decided>", "chosen": "<your choice>"}],
 "unmapped_content": ["<content of the input that the rewrite does not carry>"]}
Use several sentences only if one sentence cannot carry the input. Do NOT write FRETish."""
TASK_B_PARA = """TASK: The user message contains one or more plain English sentences that are a rewrite of a requirement (the original natural language is NOT given). Convert them into FRETish."""


def build_system(stage, tpl=None):
    """stage: 'A' (raw -> template), 'B' (template -> FRETish), 'D' (raw -> FRETish). Returns (system_prompt, spec_status_map)."""
    st = {}
    parts = []
    if stage == "A" and tpl == ARM_PARA:
        st[tpl] = "plain"
        parts = [TASK_A_PARA, RULES_COMMON, SCHEMA_A_PARA]
    elif stage == "B" and tpl == ARM_PARA:
        guide = read_rel("prompts/fretish_guide.md")
        st[tpl] = "plain"
        st["FRETish"] = spec_status(guide)
        parts = [TASK_B_PARA, RULES_COMMON, SCHEMA_B, "FRETISH GUIDE\n" + guide]
    elif stage == "A":
        spec = read_rel(TEMPLATES[tpl])
        st[tpl] = spec_status(spec)
        parts = [TASK_A, RULES_COMMON, SCHEMA_A, "TEMPLATE SPECIFICATION\n" + spec]
    elif stage == "B":
        spec = read_rel(TEMPLATES[tpl])
        guide = read_rel("prompts/fretish_guide.md")
        st[tpl] = spec_status(spec)
        st["FRETish"] = spec_status(guide)
        parts = [TASK_B, RULES_COMMON, SCHEMA_B, "FRETISH GUIDE\n" + guide, "TEMPLATE SPECIFICATION (for reading the input only)\n" + spec]
    elif stage == "D":
        guide = read_rel("prompts/fretish_guide.md")
        st["FRETish"] = spec_status(guide)
        parts = [TASK_D, RULES_COMMON, SCHEMA_B, "FRETISH GUIDE\n" + guide]
    else:
        raise ValueError(stage)
    return "\n\n".join(parts).strip() + "\n", st


def user_prompt_A(raw):
    return "NATURAL LANGUAGE REQUIREMENT:\n" + raw.strip() + "\n"


def sigdict_block(sigdict):
    if not sigdict:
        return ""
    return "\nSIGNAL DICTIONARY (copied without selection from the requirement document of this requirement; columns: scope | name | # | type | description):\n" + sigdict.strip() + "\n"


def user_prompt_B(tpl, sentences, raw=None, sigdict=None):
    if tpl == ARM_PARA:
        body = "REWRITTEN SENTENCES:\n" + "\n".join(f"{i + 1}. {x}" for i, x in enumerate(sentences)) + "\n"
        if raw is not None:
            body += "ORIGINAL NATURAL LANGUAGE (ablation):\n" + raw.strip() + "\n"
        return body
    body = "TEMPLATE: " + tpl + "\nTEMPLATE SENTENCES:\n" + "\n".join(f"{i + 1}. {s}" for i, s in enumerate(sentences)) + "\n"
    if raw is not None:  # ablation only (--stageb-sees-raw); off by default
        body += "ORIGINAL NATURAL LANGUAGE (ablation):\n" + raw.strip() + "\n"
    return body + sigdict_block(sigdict)


def user_prompt_D(raw, sigdict=None):
    return "NATURAL LANGUAGE REQUIREMENT:\n" + raw.strip() + "\n" + sigdict_block(sigdict)


# ------------------------------------------------------------------ output parsing


def extract_json(text):
    if text is None:
        return None
    t = str(text).strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S).strip()
    try:
        o = json.loads(t)
        return o if isinstance(o, dict) else None
    except Exception:
        pass
    i, j = t.find("{"), t.rfind("}")
    if i >= 0 and j > i:
        try:
            o = json.loads(t[i:j + 1])
            return o if isinstance(o, dict) else None
        except Exception:
            return None
    return None


def _strlist(v):
    if isinstance(v, str):
        v = [v]
    if not isinstance(v, list):
        return None
    out = [str(x).strip() for x in v if isinstance(x, (str, int, float)) and str(x).strip()]
    return out


def parse_output(text, stage):
    """Return (obj, errors). obj has normalised keys; errors lists schema problems (an empty list means usable)."""
    o = extract_json(text)
    if o is None:
        return None, ["no_json"]
    errs = []
    key = "sentences" if stage == "A" else "fretish"
    sents = _strlist(o.get(key))
    if not sents:
        errs.append(f"schema_{key}")
    norm = {key: sents or []}
    norm["choices"] = [c for c in (o.get("choices") or []) if isinstance(c, dict)] if isinstance(o.get("choices"), list) else []
    norm["unmapped_content"] = _strlist(o.get("unmapped_content")) or []
    if stage == "A":
        norm["requirement_type"] = str(o.get("requirement_type") or "")[:120]
        norm["split_reason"] = str(o.get("split_reason") or "")[:300]
        norm["spec_confidence"] = str(o.get("spec_confidence") or "")[:40]
    else:
        flds = o.get("fields")
        norm["fields"] = [f for f in flds if isinstance(f, dict)] if isinstance(flds, list) else []
        norm["confidence"] = str(o.get("confidence") or "")[:40]
        tb = o.get("timing_basis")
        if isinstance(tb, dict):                                     # only the +V arms are asked for it; kept as a record, never used for scoring
            norm["timing_basis"] = {k: str(tb.get(k) or "")[:300] for k in ("rule", "words", "forbidden_situation")}
    return norm, errs


# ------------------------------------------------------------------ text normalisation and tokens

UNI = {"≤": "<=", "≥": ">=", "⇒": "=>", "−": "-", "→": "->", "≠": "!=", "’": "'", "“": '"', "”": '"', "­": ""}


def uni(s):
    for a, b in UNI.items():
        s = s.replace(a, b)
    return s


def collapse(s):
    return re.sub(r"\s+", " ", uni(s)).strip()


def words(s):
    """word tokens: identifiers split on underscore and camelCase, numbers kept, operators kept as tokens."""
    s = uni(s)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", s)
    s = s.replace("_", " ")
    return [t.lower() for t in re.findall(r"[A-Za-z]+|\d+(?:\.\d+)?|=>|<=|>=|!=|[<>=!&|+*/-]", s)]


def tok_f1(a, b):
    ta, tb = Counter(words(a)), Counter(words(b))
    ov = sum((ta & tb).values())
    if not ov:
        return 0.0
    p, r = ov / sum(tb.values()), ov / sum(ta.values())
    return 2 * p * r / (p + r)


def char_cos(a, b, n=3):
    def v(s):
        s = " " + re.sub(r"\s+", " ", uni(s).lower()) + " "
        return Counter(s[i:i + n] for i in range(max(1, len(s) - n + 1)))
    va, vb = v(a), v(b)
    dot = sum(va[k] * vb[k] for k in va if k in vb)
    na = math.sqrt(sum(x * x for x in va.values()))
    nb = math.sqrt(sum(x * x for x in vb.values()))
    return dot / (na * nb) if na and nb else 0.0


def lev_sim(a, b):
    a, b = collapse(a).lower(), collapse(b).lower()
    if not a and not b:
        return 1.0
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return 1.0 - prev[-1] / max(len(a), len(b))


IDENT = re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+\b|\b[A-Za-z]+[A-Z][A-Za-z0-9]*\b|\b[A-Z]{2,}[A-Za-z0-9]*\b")
FRET_WORDS = {"shall", "satisfy", "always", "never", "eventually", "immediately", "within", "until", "before", "after", "when", "whenever",
              "if", "then", "upon", "in", "mode", "the", "for", "next", "every", "with", "probability", "ticks", "seconds", "sec", "not", "and", "or"}


def identifiers(s):
    s = uni(s)
    ids = {m.group(0).lower() for m in IDENT.finditer(s)}
    return {i for i in ids if i not in FRET_WORDS}


def numbers(s):
    return Counter(re.findall(r"(?<![A-Za-z_])\d+(?:\.\d+)?", uni(s)))


def set_f1(a, b):
    if not a and not b:
        return 1.0
    ov = len(a & b)
    if not ov:
        return 0.0
    p, r = ov / len(b), ov / len(a)
    return 2 * p * r / (p + r)


# ------------------------------------------------------------------ expression canonical form


def _strip_outer(s):
    s = s.strip()
    while s.startswith("(") and s.endswith(")"):
        d = 0
        ok = True
        for i, ch in enumerate(s):
            d += ch == "("
            d -= ch == ")"
            if d == 0 and i < len(s) - 1:
                ok = False
                break
        if not ok:
            break
        s = s[1:-1].strip()
    return s


def _split_top(s, op):
    parts, d, cur, i = [], 0, "", 0
    while i < len(s):
        ch = s[i]
        if ch == "(":
            d += 1
        elif ch == ")":
            d -= 1
        if d == 0 and s.startswith(op, i):
            if op in ("&", "|") and ((i > 0 and s[i - 1] in "&|") or (i + 1 < len(s) and s[i + 1] in "&|")):
                cur += ch
                i += 1
                continue
            parts.append(cur)
            cur = ""
            i += len(op)
            continue
        cur += ch
        i += 1
    parts.append(cur)
    return parts


def canon_expr(s):
    """Commutative canonical form: lower case, ASCII operators, if A then B == A => B, sorted operands of & and |."""
    s = uni(s).lower().strip().rstrip(".;")
    s = re.sub(r"\s+", " ", s)
    m = re.match(r"^if (.+?) then (.+)$", s)
    if m:
        s = f"({m.group(1)}) => ({m.group(2)})"
    s = s.replace(" ", "")
    return _canon(s)


def _canon(s):
    s = _strip_outer(s)
    p = _split_top(s, "=>")
    if len(p) > 1:
        return "=>".join([_canon(p[0]), _canon("=>".join(p[1:]))]).join(["(", ")"])
    for op in ("|", "&"):
        p = _split_top(s, op)
        if len(p) > 1:
            return "(" + op.join(sorted(_canon(x) for x in p)) + ")"
    m = re.match(r"^!(.+)$", s)
    if m and not m.group(1).startswith("!"):
        return "!" + _canon(m.group(1))
    return s


# ------------------------------------------------------------------ tolerant FRETish parser

SCOPE_KW = ("onlyin", "onlybefore", "onlyafter", "notin", "in", "before", "after", "while")
COND_KW = ("whenever", "when", "upon", "if", "unless", "where")
TIMING_KW = ["always", "never", "eventually", "immediately", "next", "within", "for", "after", "until", "before", "every"]


def fretish_parse(s):
    """Heuristic reader of one FRETish sentence. Returns a dict, never raises."""
    raw = collapse(s)
    out = {"raw": raw, "ok": False, "scope_kw": "", "scope": "", "cond_kw": "", "condition": "", "component": "", "timing_kws": [],
           "timing": "", "response": "", "resp_form": "", "prob": False, "legacy_when_in_mode": False}
    m = re.search(r"\bshall\b", raw, re.I)
    if not m:
        out["response"] = raw
        return out
    left, right = raw[:m.start()].strip(), raw[m.end():].strip()
    # right side: timing then 'satisfy' then response
    ms = re.search(r"\bsatisfy\b", right, re.I)
    if ms:
        timing, resp = right[:ms.start()].strip(), right[ms.end():].strip()
    else:
        mt = re.match(r"^((?:with (?:a )?probability\s*[<>=!]+\s*[\d.]+\s*)?(?:always|never|eventually|immediately|next|(?:within|for|after|until|before|every)\s+\S+(?:\s+\S+)?)?)\s*(.*)$", right, re.I)
        timing, resp = (mt.group(1).strip(), mt.group(2).strip()) if mt else ("", right)
    out["timing"], out["response"] = timing, resp
    tl = timing.lower()
    out["prob"] = "probab" in tl
    kws = []
    for t in re.finditer(r"\b(always|never|eventually|immediately|next|within|for|after|until|before|every)\b", tl):
        if t.group(1) not in kws:
            kws.append(t.group(1))
    out["timing_kws"] = kws
    r = resp.strip()
    if re.match(r"^if\b.+\bthen\b", r, re.I):
        out["resp_form"] = "if_then"
    elif "=>" in uni(r):
        out["resp_form"] = "implication"
    elif r.startswith("!"):
        out["resp_form"] = "negation"
    else:
        out["resp_form"] = "plain"
    # left side: [scope] [condition kw + expr] component   (rewritten for v2: camel-case mode names without the word "mode" are allowed)
    l = left
    mt = list(re.finditer(r"\bthe\b", l, re.I))
    if mt:
        comp_start = mt[-1].start()
    else:
        toks = l.rsplit(None, 1)
        comp_start = len(l) - len(toks[-1]) if toks else 0
    comp = l[comp_start:].strip()
    pre = l[:comp_start].strip()
    lm = re.match(r"^when\s+(?=(?:onlyin|onlybefore|onlyafter|notin|in|before|after|while)\b)", pre, re.I)
    if lm:
        out["legacy_when_in_mode"] = True
        pre = pre[lm.end():]

    def _kw_at_depth0(text, start=0):
        depth = 0
        for mm in re.finditer(r"[()]|\b(?:whenever|when|upon|if|unless|where)\b", text[start:], re.I):
            g = mm.group(0)
            if g == "(":
                depth += 1
            elif g == ")":
                depth = max(0, depth - 1)
            elif depth == 0:
                return start + mm.start()
        return None

    sm = re.match(r"^(onlyin|onlybefore|onlyafter|notin|in|before|after|while)\b", pre, re.I)
    rest = pre
    if sm:
        out["scope_kw"] = sm.group(1).lower()
        cut = _kw_at_depth0(pre, sm.end())
        cut = len(pre) if cut is None else cut
        out["scope"] = pre[:cut].strip()
        rest = pre[cut:].strip()
    cm = re.match(r"^(whenever|when|upon|if|unless|where)\b\s*(.*)$", rest, re.I | re.S)
    if cm:
        out["cond_kw"] = cm.group(1).lower()
        out["condition"] = cm.group(2).strip()
    out["component"] = comp
    out["ok"] = bool(comp) and bool(out["response"])
    return out


def comp_canon(c):
    c = re.sub(r"^the\s+", "", uni(c).strip(), flags=re.I)
    return re.sub(r"[^a-z0-9]", "", c.lower())


def scope_class(p):
    return p["scope_kw"] if p["scope_kw"] else "none"


def cond_class(p):
    if not p["cond_kw"]:
        return "none"
    return "trigger_kw:" + p["cond_kw"]


def timing_class(p):
    k = [x for x in p["timing_kws"]]
    return "+".join(k) if k else "none"


def struct_key(p):
    """Structure of a FRETish sentence without identifiers: used for cross-item consistency."""
    sc = "scope" if p["scope_kw"] else "noscope"
    cd = "cond" if p["cond_kw"] else "nocond"
    tm = timing_class(p)
    return f"{sc}|{cd}|{tm}|{p['resp_form']}"


def neg_state_form(p, raw_hint=False):
    """How a negated state is expressed: notin scope, negation in the condition, if-then in the response, negation in the response, none."""
    cond = p["condition"].replace(" ", "")
    if p["scope_kw"] == "notin":
        return "scope_notin"
    if "!" in cond or re.search(r"\bnot\b", p["condition"], re.I):
        return "condition_negation"
    if p["resp_form"] == "if_then" and re.search(r"^if\s*!", p["response"].replace("  ", " "), re.I):
        return "response_if_not_then"
    if "!" in p["response"] or re.search(r"\bnot\b", p["response"], re.I):
        return "response_negation"
    return "none"


def field_matches(out, gt):
    """Field-wise comparison of two parsed FRETish sentences (parser based)."""
    return {
        "scope_class": scope_class(out) == scope_class(gt),
        "cond_present": bool(out["cond_kw"]) == bool(gt["cond_kw"]),
        "cond_expr": canon_expr(out["condition"]) == canon_expr(gt["condition"]) if (out["condition"] or gt["condition"]) else True,
        "component": comp_canon(out["component"]) == comp_canon(gt["component"]),
        "timing": timing_class(out) == timing_class(gt),
        "response": canon_expr(out["response"]) == canon_expr(gt["response"]),
        "struct": struct_key(out) == struct_key(gt),
        "parse_ok": out["ok"],
    }


def best_alignment(out_list, gt_list):
    """Greedy one-to-one alignment of output sentences to gt sentences by token F1. Returns list of (out_idx or None, gt_idx)."""
    pairs = []
    used = set()
    for gi, g in enumerate(gt_list):
        best, bj = -1, None
        for oi, o in enumerate(out_list):
            if oi in used:
                continue
            f = tok_f1(g, o)
            if f > best:
                best, bj = f, oi
        if bj is not None:
            used.add(bj)
        pairs.append((bj, gi))
    return pairs


# ------------------------------------------------------------------ template keyword classifiers (ambiguity observables)


def _caps(s, phrase):
    return len(re.findall(r"(?<![A-Za-z])" + phrase + r"(?![A-Za-z])", s))


def tpl_features(tpl, sentences):
    """Observable choices in a stage A output. Returns dict with 'sig' (choice signature string) and fields. Keyword spotting only."""
    text = " ".join(sentences)
    f = {"n_sentences": len(sentences)}
    if tpl == "MASTeR":
        kws = []
        for m in re.finditer(r"(?i)\bas soon as\b|\bas long as\b|(?<![A-Za-z])(?:IF|If)(?![A-Za-z])", text):
            g = m.group(0).lower()
            kws.append("AS SOON AS" if "soon" in g else "AS LONG AS" if "long" in g else "IF")
        liab = re.findall(r"\b(SHALL|SHOULD|WILL)\b", text)
        f.update({"cond_kws": kws, "kw_first": kws[0] if kws else "none", "kw_set": "+".join(sorted(set(kws))) or "none", "n_cond": len(kws),
                  "liability": liab[0] if liab else "none",
                  "perfect_tense_after_asap": bool(re.search(r"(?i)as soon as[^,]*\b(has|have|had)\b", text)),
                  "sig": ("+".join(kws) if kws else "none") + "|" + (liab[0] if liab else "none")})
    elif tpl in ("EARS", "Adv-EARS"):
        seq = re.findall(r"(?<![A-Za-z])(WHEN|WHILE|WHERE|IF|THEN|When|While|Where|If)(?![A-Za-z])", text)
        seq = [s.upper() for s in seq if s.upper() != "THEN"]
        hyb = bool(re.search(r"(?i)\bwhile\b[^,]*\bif\b", text)) or bool(re.search(r"(?i)if necessary", text))
        f.update({"cond_kws": seq, "kw_first": seq[0] if seq else "none", "kw_set": "+".join(sorted(set(seq))) or "none", "order": ">".join(seq) or "none",
                  "n_cond": len(seq), "hybrid_pattern": hyb, "sig": (">".join(seq) or "none")})
    elif tpl == "SPIDER":
        s0 = text.strip()
        sc = ("between" if re.match(r"(?i)between\b", s0) else "after_until" if re.match(r"(?i)after\b.*\buntil\b", s0) else "after" if re.match(r"(?i)after\b", s0)
              else "before" if re.match(r"(?i)before\b", s0) else "globally" if re.match(r"(?i)globally\b", s0) else "other")
        pats = []
        for name, rx in (("response_within", r"\bthen\b.*\bwithin\b"), ("response_eventually", r"\bthen\b.*\beventually\b"), ("response", r"\bif\b.*\bthen\b"),
                         ("until", r"\buntil\b"), ("absence", r"\bnever\b"), ("existence", r"\beventually\b"), ("periodic", r"\bat least every\b"),
                         ("duration", r"\bfor\b.*\btime units?|\bheld for\b"), ("universality", r"\balways the case that\b")):
            if re.search(rx, text, re.I):
                pats.append(name)
        f.update({"scope_class": sc, "pattern": pats[0] if pats else "other", "pattern_set": "+".join(pats) or "other", "sig": sc + "|" + (pats[0] if pats else "other")})
    else:  # Boilerplate
        s0 = text.strip()
        pre = re.match(r"(?i)^(while|if|unless|after|when|before|during|upon)\b", s0)
        main = ("be_able_to" if re.search(r"(?i)\bshall (not )?be able to\b", text) else "have_parameter" if re.search(r"(?i)\bshall have\b", text) else
                "shall_function" if re.search(r"(?i)\bshall\b", text) else "other")
        suf = re.findall(r"(?i)\b(after|before|using)\b", text)
        f.update({"prefix": pre.group(1).lower() if pre else "none", "main": main, "suffix_kws": "+".join(sorted(set(x.lower() for x in suf))) or "none",
                  "sig": (pre.group(1).lower() if pre else "none") + "|" + main})
    return f


# ------------------------------------------------------------------ raw natural language cues (input side ambiguity)

RAW_CUES = [("when", r"\bwhen\b"), ("whenever", r"\bwhenever\b"), ("while", r"\bwhile\b"), ("if", r"\bif\b"), ("upon", r"\bupon\b"),
            ("as_long_as", r"\bas long as\b"), ("as_soon_as", r"\bas soon as\b"), ("until", r"\buntil\b"), ("before", r"\bbefore\b"),
            ("after", r"\bafter\b"), ("not", r"\bnot\b"), ("or", r"\bor\b"), ("and", r"\band\b"), ("within", r"\bwithin\b"),
            ("extended_vague", r"\b(extremely|high probability|extended time|near)\b")]


def raw_cues(raw):
    t = uni(raw).lower()
    return {k: len(re.findall(rx, t)) for k, rx in RAW_CUES}


def cue_diversity(raw):
    c = raw_cues(raw)
    return sum(1 for k in ("when", "whenever", "while", "if", "upon", "as_long_as", "as_soon_as", "until", "before", "after") if c[k])


# ------------------------------------------------------------------ rule based loss of content (raw -> template)

STOP = set("the a an of to in on at by for with and or is are be been shall should will may can it its this that these those as from into than then".split())


def stem(w):
    for suf in ("ing", "ed", "es", "s"):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[:-len(suf)]
    return w


def content_words(s):
    return {stem(w) for w in re.findall(r"[a-z]+", uni(s).lower()) if w not in STOP and len(w) > 1}


def raw_loss(raw, out_text):
    """Recall of content words, numbers and parenthetical hints of the raw text in the output. Rule based, no model."""
    cw_r, cw_o = content_words(raw), content_words(out_text)
    cw = len(cw_r & cw_o) / len(cw_r) if cw_r else 1.0
    nr, no = numbers(raw), numbers(out_text)
    num = sum((nr & no).values()) / sum(nr.values()) if nr else 1.0
    hints = re.findall(r"\(([^)]+)\)", raw)
    hw = set()
    for h in hints:
        hw |= content_words(h)
    hint = len(hw & cw_o) / len(hw) if hw else 1.0
    return {"content_recall": round(cw, 4), "number_recall": round(num, 4), "hint_recall": round(hint, 4)}
