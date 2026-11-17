"""Keyword check step KC (2026-11-17, experiment 030; specification KC_STAGE_SPEC.md of the project owner).

Position: v0 (first answer) -> feedback (FRET parser failure log, MAX_ROUNDS rounds) -> vf -> KC -> kc -> RT1 -> rt. KC is a check step, not feedback. The agent reads its current answer next to the
official reference text of the FRETish keywords of every keyword group that its sentences use and returns the answer again in the schema of its first answer. The agent scope is the one of
RT1: calls are grouped by (system prompt, challenge, repetition, stage) and information passes only inside the group. No reference sentence, no score and no realizability result is part of the message.

Which groups a sentence belongs to is decided mechanically from the fields of the official FRET parser output (no model judgement):
  scope.type          != "null"                       -> SCOPE            (the written keyword is read from scopeTextRange)
  condition           != "null" and qualifier_word    -> COND             (upon, when, where, if, whenever, unless)
  timing              "null" (omitted) or a point     -> TIMING_POINT     (immediately, initially, at the first / same / next timepoint, finally, at the last timepoint, eventually, always, never)
                      within, for, after              -> TIMING_DURATION
                      until, before                   -> TIMING_STOP      (the written keyword is read from timingTextRange)
Only when the fields are not available (the parser rejected the sentence) the groups are taken from the tokens of the sentence (lexical fallback) and `via` records it.
The answer of the step is adopted as RT1 does: only when the official parser accepts every sentence of it; otherwise vf stays and the variant kc equals vf (kc_adopted = false).
"""
import hashlib
import json
import os
import re

from nl2fret import rt_stage as RT
from nl2fret import units3 as U

HERE = os.path.dirname(os.path.abspath(__file__))
KC_STAGE = "KC1"
KC_DIR = os.path.join(HERE, "prompts", "kc")

# GROUPS: order of the table of the specification, used for the reference documents of a batch. SENTENCE_ORDER: order of the groups inside one sentence (scope, condition, timing: the order
# of the expected values of the specification, which is also the order of the words in the sentence)
GROUPS = ["COND", "TIMING_POINT", "TIMING_DURATION", "TIMING_STOP", "SCOPE"]
SENTENCE_ORDER = ["SCOPE", "COND", "TIMING_POINT", "TIMING_DURATION", "TIMING_STOP"]
GROUP_FILES = {"COND": "KC_COND.md", "TIMING_POINT": "KC_TIMING_POINT.md", "TIMING_DURATION": "KC_TIMING_DURATION.md", "TIMING_STOP": "KC_TIMING_STOP.md", "SCOPE": "KC_SCOPE.md"}

KC_HEAD = """CHECK OF KEYWORDS
Below is your current answer. For each sentence, the keyword groups of its keywords are listed, followed by the reference text of the FRETish guide for each listed group. Compare the keyword that the sentence uses with every other keyword of its group."""
KC_TAIL = """Return the complete answer again in exactly the JSON schema of the first answer. A sentence stays unchanged when the comparison confirms its keywords."""

COND_WORDS = ("upon", "when", "where", "if", "whenever", "unless")
POINT_WORDS = ("immediately", "initially", "at the first timepoint", "at the same timepoint", "at the next timepoint", "finally", "at the last timepoint", "eventually", "always", "never")
DURATION_WORDS = ("within", "for", "after")
STOP_WORDS = ("until", "before")
SCOPE_NAME = {"in": "in", "after": "after", "before": "before", "notin": "when/if not in", "onlyIn": "only in", "onlyAfter": "only after", "onlyBefore": "only before"}
TIMING_NAME = {"next": "at the next timepoint"}
OMITTED = "(timing omitted)"

_TIMING_ALT = "|".join(sorted((re.escape(w) for w in POINT_WORDS + DURATION_WORDS + STOP_WORDS), key=len, reverse=True))
_TIMING_RE = re.compile(r"^\s*,?\s*(" + _TIMING_ALT + r")\b", re.I)
_SCOPE_RE = re.compile(r"^\s*(only\s+(?:in|before|after)|(?:when|if)\s+not\s+in|in|during|while|before|after)\b", re.I)
_COND_RE = re.compile(r"\b(" + "|".join(COND_WORDS) + r")\b", re.I)


# ------------------------------------------------------------------ parser fields
def sem_fields(sem):
    """the fields of the parser output that decide the groups; None when the parser gave no output"""
    if not sem:
        return None
    sc = sem.get("scope")
    return {"scope": (sc.get("type") if isinstance(sc, dict) else sc), "scope_range": sem.get("scopeTextRange"), "condition": sem.get("condition"),
            "qualifier": sem.get("qualifier_word"), "timing": sem.get("timing"), "timing_range": sem.get("timingTextRange")}


def fields(texts, backend, cache_path):
    """-> {text: fields or None}; the official parser through fret_compile, cached in cache_path (jsonl). Not available for the mock parser."""
    if backend == "mock":
        raise SystemExit("the keyword check step needs the official parser (docker or node); the mock parser has no parser fields")
    cache = {}
    if os.path.exists(cache_path):
        for line in open(cache_path, encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                cache[r["t"]] = r["fields"]
    todo = [t for t in dict.fromkeys(texts) if t not in cache]
    if todo:
        from nl2fret.fret_check.tools import fret_compile
        res = fret_compile.compile_list(todo, backend=backend)
        with open(cache_path, "a", encoding="utf-8") as f:
            for r in res:
                fl = sem_fields(r.get("sem")) if r.get("ok") else None
                cache[r["fretish"]] = fl
                f.write(json.dumps({"t": r["fretish"], "fields": fl}, ensure_ascii=False) + "\n")
    return {t: cache.get(t) for t in texts}


def _slice(text, rng):
    if isinstance(rng, (list, tuple)) and len(rng) == 2 and all(isinstance(x, int) for x in rng):
        return text[rng[0]:rng[1] + 1]
    return None


def lexical_fields(text):
    """fields read from the tokens of the sentence (fallback when the parser output is not available): the part before `shall` holds scope and condition, the part after it the timing"""
    m = re.search(r"\bshall\b", text, re.I)
    pre, post = (text[:m.start()], text[m.end():]) if m else (text, "")
    sc = _SCOPE_RE.match(pre)
    scope = None
    if sc:
        w = re.sub(r"\s+", " ", sc.group(1).lower())
        scope = {"in": "in", "during": "in", "while": "in", "before": "before", "after": "after", "only in": "onlyIn", "only before": "onlyBefore", "only after": "onlyAfter"}.get(w, "notin" if "not in" in w else None)
    pre_c = re.sub(r"\b(?:when|if)\s+not\s+in\b", " ", pre, flags=re.I)
    c = _COND_RE.search(pre_c)
    seg = re.split(r"\bsatisfy\b", post, maxsplit=1, flags=re.I)[0]
    t = re.search(r"(?:^|[\s,])(" + _TIMING_ALT + r")\b", seg, re.I)
    tw = re.sub(r"\s+", " ", t.group(1).lower()) if t else None
    return {"scope": scope or "null", "scope_range": None, "condition": ("regular" if c else "null"), "qualifier": (c.group(1).lower() if c else None),
            "timing": tw or "null", "timing_range": None, "_scope_word": (re.sub(r"\s+", " ", sc.group(1).lower()) if sc else None)}


# ------------------------------------------------------------------ groups
def groups_for(text, fl=None):
    """-> list of {"group", "keyword", "via"} of one sentence, in the order of GROUPS. fl = fields of the parser output (None: lexical fallback)."""
    via = "fields"
    if not fl:
        fl, via = lexical_fields(text), "lexical"
    out = {}
    q = (fl.get("qualifier") or "").lower()
    if fl.get("condition") not in (None, "null") and q in COND_WORDS:
        out["COND"] = q
    tw = fl.get("timing")
    written = None
    seg = _slice(text, fl.get("timing_range"))
    if seg:
        m = _TIMING_RE.match(seg)
        written = re.sub(r"\s+", " ", m.group(1).lower()) if m else None
    if tw in (None, "null"):
        out["TIMING_POINT"] = OMITTED
    else:
        kw = written or TIMING_NAME.get(tw, tw)
        base = TIMING_NAME.get(tw, tw)
        g = "TIMING_DURATION" if base in DURATION_WORDS else "TIMING_STOP" if base in STOP_WORDS else "TIMING_POINT"
        out[g] = kw
    st = fl.get("scope")
    if st not in (None, "null"):
        seg = _slice(text, fl.get("scope_range"))
        m = _SCOPE_RE.match(seg) if seg else None
        out["SCOPE"] = re.sub(r"\s+", " ", m.group(1).lower()) if m else (fl.get("_scope_word") or SCOPE_NAME.get(st, st))
    return [{"group": g, "keyword": out[g], "via": via} for g in SENTENCE_ORDER if g in out]


def group_line(gs):
    return ", ".join(g["group"] + " " + (g["keyword"] if g["keyword"].startswith("(") else "(" + g["keyword"] + ")") for g in gs)


def plan(item_id, original_body, sentences, fields_of_text):
    """-> (body, groups per sentence) or None when no sentence has a group. Sentences without a group are not listed."""
    groups = [groups_for(t, fields_of_text.get(t)) for t in sentences]
    if not any(groups):
        return None
    lines = [f"ITEM {item_id}", "input: " + original_body.strip()]
    for n, (t, gs) in enumerate(zip(sentences, groups), 1):
        if gs:
            lines += [f"sentence {n}: {t}", f"groups: {group_line(gs)}"]
    return "\n".join(lines) + "\n", groups


# ------------------------------------------------------------------ documents and message
def doc_text(group):
    return open(os.path.join(KC_DIR, GROUP_FILES[group]), encoding="utf-8").read()


def doc_sha():
    """sha256 of the reference document of every group (recorded in run_info.json as kc_doc_sha)"""
    return {g: hashlib.sha256(open(os.path.join(KC_DIR, GROUP_FILES[g]), "rb").read()).hexdigest() for g in GROUPS}


def block_text(tasks, sigtext, sigdict_block):
    """user message of one KC call: ITEMS line, KC_HEAD, one block per item, the reference document of every group that the batch uses (once), KC_TAIL, the signal dictionary last"""
    fired = [g for g in GROUPS if any(g in t["extra"]["kc_group_names"] for t in tasks)]
    out = [f"ITEMS: {len(tasks)}", "", KC_HEAD, ""]
    for t in tasks:
        out += [f"### id: {t['it']['id']}", t["body"].rstrip(), ""]
    for g in fired:
        out += [f"== {g} ==", doc_text(g).rstrip(), ""]
    out.append(KC_TAIL)
    text = "\n".join(out).rstrip() + "\n"
    if sigtext:
        text += sigdict_block(sigtext).strip("\n") + "\n"
    return text


# ------------------------------------------------------------------ unit state
def with_kc(rec, rows, item, arm, rep, comp, groups_of=None):
    """-> (rec2, adopted). rec2 has the KC round appended when its row exists and the unit is applicable (every sentence of the last answer accepted by the parser); adopted is True
    when the sentences of that round are all accepted. kc_changed lists, per sentence of the KC answer, whether the text differs from the sentence at the same place before KC.
    kc_skipped is True for an applicable unit without a KC row and without a group in any sentence (groups_of: text list -> groups per sentence, optional)."""
    rec2 = dict(rec)
    rec2["kc_adopted"] = False
    rec2["kc_skipped"] = False
    row = rows.get(U.skey(item["id"], arm, rep, KC_STAGE))
    if not RT.applicable(rec):
        return rec2, False
    if row is None:
        if groups_of is not None and not any(groups_of(RT.last_texts(rec))):
            rec2["kc_skipped"] = True
        return rec2, False
    rule = U.is_rule(arm)
    free = (not rule) or bool(rec.get("fallback"))
    n = len(rec["rounds"])
    rr = U._free_round(n, KC_STAGE, row, comp) if free else U._slot_round(n, KC_STAGE, row, rec["parses"], rec["reqs"], comp, U.is_r2(arm))
    rec2["rounds"] = rec["rounds"] + [rr]
    adopted = bool(rr["sentences"]) and not rr.get("pending") and not U.round_failed(rr) and all(s.get("text") for s in rr["sentences"])
    before = RT.last_texts(rec)
    rec2["kc_changed"] = [(i >= len(before) or s.get("text") != before[i]) for i, s in enumerate(rr["sentences"])]
    rec2["kc_adopted"] = adopted
    return rec2, adopted


def chain(rows, items, arms, reps, parser, cache, groups_of_factory=None):
    """-> {(item, arm, rep): {"base": vf unit, "kc": unit with the KC round (adopted or not), "in": the unit that RT1 starts from (kc answer when adopted, else vf), "rt": unit with the RT round}}.
    The parser verdicts of the sentences of the KC and RT rounds are compiled (cache) until nothing is pending."""
    from nl2fret import fretparse
    by_id = {it["id"]: it for it in items}
    comp = fretparse._load_cache(cache)
    out = {}
    for _ in range(4):
        base = {(it["id"], a, r): U.derive(rows, it, a, r, comp) for it in items for a in arms for r in reps}
        groups_of = groups_of_factory() if groups_of_factory else None
        kc = {k: with_kc(rec, rows, by_id[k[0]], k[1], k[2], comp, groups_of)[0] for k, rec in base.items()}
        inn = {k: (kc[k] if kc[k].get("kc_adopted") else base[k]) for k in base}
        rt = {k: RT.with_rt(inn[k], rows, by_id[k[0]], k[1], k[2], comp)[0] for k in base}
        need = []
        for d in (base, kc, rt):
            for rec in d.values():
                need += U.pending_compile(rec)
        need = list(dict.fromkeys(need))
        out = {k: {"base": base[k], "kc": kc[k], "in": inn[k], "rt": rt[k]} for k in base}
        if not need:
            break
        fretparse.compile_texts(need, parser, cache)
        comp = fretparse._load_cache(cache)
    return out


def cached_groups_of(cache_path):
    """-> function (list of texts) -> groups per sentence, read from the field cache of the run only (no parser call); a text that is not in the cache counts as having a group (not skipped)"""
    cache = {}
    if os.path.exists(cache_path):
        for line in open(cache_path, encoding="utf-8"):
            if line.strip():
                r = json.loads(line)
                cache[r["t"]] = r["fields"]
    return lambda texts: [groups_for(t, cache[t]) if t in cache else [{"group": "unknown", "keyword": "", "via": "unknown"}] for t in texts]


def keywords_of(text, fl):
    """the keywords that one sentence uses, for the distribution table: {"condition", "timing", "scope"} (None when the sentence has none)"""
    d = {g["group"]: g["keyword"] for g in groups_for(text, fl)}
    t = d.get("TIMING_POINT") or d.get("TIMING_DURATION") or d.get("TIMING_STOP")
    return {"condition": d.get("COND"), "timing": t, "scope": d.get("SCOPE")}
