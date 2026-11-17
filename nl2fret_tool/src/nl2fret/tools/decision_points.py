"""Decision points of a FRETish sentence (scope, condition kind, timing), read from the sentence text by the FRETish field order
[scope] [condition] component shall [timing] satisfy response  (FRET documentation: scope.md, condition.md, timing.md).
Purely lexical; no reference statistic is used. Condition classes: none | trigger (upon, when, if, where) | whenever | unless.
Only for DIAGNOSIS (which decision differs); the success of a unit is always decided by the judge, never by this module.

Reading class (semantic, not lexical). Verified with the official FRET parser (fretrun/batch.js): `whenever c ... immediately r` has the LTL H(c -> r), the same as `always satisfy c => r`;
`when c ... immediately r` is rising-edge only. Therefore
  EDGE        condition upon/when/if/where (trigger)
  EVERY_TIME  condition whenever, or no condition keyword with an implication in the response (c => r, if c then r)
  UNCOND      no condition keyword and no implication in the response
  UNLESS      condition unless
`if` and `where` give the same LTL as `when` and `upon` (rule_semantics_check S1a to S1c, official parser, NuSMV).

ntiming is the SEMANTIC equivalence class of (condition form, timing), read from data/timing_semantics.json (tools/timing_semantics.py: official FRET parser + judge engine, every pair of forms compared).
Nothing is merged by hand. Facts in that table: `whenever c ... immediately r` is the same as `always satisfy c => r`; `whenever c ... always r` is NOT (it is stronger: r must hold from the trigger onwards);
an omitted timing means `eventually` (same LTL); `when` (edge) differs from `whenever` for every timing except always and finally.
A form that is not in the table (never, for, after, until, before, within N with other N, unless, scope-only forms) is its own class.
Condition forms in the table: whenever | when (upon, when, if, where) | none_impl (no condition keyword, implication in the response)."""
import json
import os
import re

_TS = None


def _classes():
    global _TS
    if _TS is None:
        p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "timing_semantics.json")
        d = json.load(open(p, encoding="utf-8"))
        _TS = {m: c[0] for c in d["equivalence_classes"] for m in c}
    return _TS


def ntiming_class(cond, timing, impl):
    form = {"whenever": "whenever", "trigger": "when"}.get(cond, "none_impl" if (cond == "none" and impl) else cond)
    timing_key = "within3" if timing == "within" else timing
    return _classes().get(f"{form}|{timing_key}", f"{form}|{timing}")

SCOPE_RE = re.compile(r"^\s*(?:(only\s+in|except\s+in|in|before|after|while|only\s+before|only\s+after|except\s+before|except\s+after)\b)", re.I)
COND_RE = re.compile(r"\b(whenever|unless|upon|when|if|where)\b", re.I)
TIMINGS = ["at the next timepoint", "at the next time point", "next", "immediately", "initially", "always", "never", "eventually", "finally", "within", "for", "after", "until", "before"]


def split_head(f):
    f = " ".join((f or "").split())
    m = re.search(r"\bshall\b", f, re.I)
    if not m:
        return f, ""
    return f[:m.start()], f[m.end():]


def decision_points(fretish):
    head, tail = split_head(fretish)
    h = head.strip()
    scope = "none"
    m = SCOPE_RE.match(h)
    if m:
        scope = m.group(1).lower()
        # a scope clause ends at the first comma or at a condition word that follows it
        rest = re.split(r",|\b(?:whenever|unless|upon|when|if)\b", h[m.end():], maxsplit=1, flags=re.I)
        h = h[m.end() + len(rest[0]):] if len(rest) > 1 else ""
    c = COND_RE.search(h)
    cond = "none"
    if c:
        w = c.group(1).lower()
        cond = "whenever" if w == "whenever" else "unless" if w == "unless" else "trigger"
    t = tail.strip().lstrip(",").strip().lower()
    timing = "omitted"
    for k in TIMINGS:
        if re.match(rf"{re.escape(k)}\b", t):
            timing = {"at the next timepoint": "next", "at the next time point": "next", "initially": "immediately"}.get(k, k)
            break
    resp = tail.lower().split("satisfy", 1)[1] if "satisfy" in tail.lower() else ""
    impl = bool(re.search(r"=>|->|\bif\b.+\bthen\b|\bimplies\b", resp))
    reading = "EDGE" if cond == "trigger" else "UNLESS" if cond == "unless" else "EVERY_TIME" if (cond == "whenever" or impl) else "UNCOND"
    ntiming = ntiming_class(cond, timing, impl)
    return {"scope": "none" if scope == "none" else "scoped", "cond": cond, "timing": timing, "reading": reading, "ntiming": ntiming}
