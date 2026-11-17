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
and the timing of an EVERY_TIME sentence is normalised: immediately and always both mean "now" (ntiming).
Whether `if` and `where` behave as `when` was not verified (the class groups them as in the earlier profile): this is a diagnosis label only."""
import re

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
    ntiming = "now" if (reading == "EVERY_TIME" and timing in ("immediately", "always")) else timing
    return {"scope": "none" if scope == "none" else "scoped", "cond": cond, "timing": timing, "reading": reading, "ntiming": ntiming}
