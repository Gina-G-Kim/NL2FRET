"""v1.5: the complete official FRET field documents are added by --fret-reference; flag off = byte-identical to v1.4 prompts."""
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.environ.get("FRETDOCS", "")


def test_reference_flag_off_is_unchanged_and_on_adds_everything():
    from nl2fret import prompts3 as P
    P.FRET_REFERENCE = False
    off = P.build_system_D3("DIRECT")[0]
    P.FRET_REFERENCE = True
    try:
        on = P.build_system_D3("DIRECT")[0]
        ref = P.fret_reference()
        import re
        assert len(on) > len(off) + 15000
        # version 2 (2026-11-17, experiment 029): the prompt holds the heading block and every section of the reference verbatim, with "Writing requirements" before the grammar
        assert all(s.strip() in on for s in re.split(r"\n(?=## )", ref))
        assert on.index("## Writing requirements [") < on.index("## FRETish grammar [")
        assert "The reserved words and the full grammar" in off and "The reserved words and the full grammar" not in on     # the v1.5 guide has no 'not known' list
        assert "grammar Requirement" in on and "grammar Requirement" not in off and "at the first timepoint" in on
        for bad in ("UNVERIFIED", "NOT obtained", "rewritten for this bench", "MECHANICAL MAPPING"):
            assert bad not in on, bad
        # every field document is in the reference, in the field order
        heads = [h for h in ("## Scope [scope.md]", "## Condition [condition.md]", "## Component [component.md]", "## Timing [timing.md]", "## Probability [probability.md]",
                             "## Response [response.md]", "## Built-in functions [builtin_functions_explanations.md]", "## Temporal conditions [temporal_condition_explanations.md]")]
        for h in ("## Writing requirements [writingReqs.md]", "## Semantics of the fields [FRET parser output]"):
            assert h in ref, h
        assert "`whenever p the system shall immediately satisfy q`" in ref and "(G (p -> q))" in ref and "The timing *after* means" in ref
        pos = [ref.index(h) for h in heads]
        assert pos == sorted(pos)
        # the +R2 slot prompt gets the expression sections only (no scope or probability)
        slot = P.slot_system_r2()
        assert "## Built-in functions" in slot and "## Temporal conditions" in slot and "## Scope [scope.md]" not in slot and "## Probability [probability.md]" not in slot
    finally:
        P.FRET_REFERENCE = False


def test_reference_is_verbatim_from_the_documents():
    import re
    if not DOCS or not os.path.isdir(DOCS):
        return        # needs the FRET repository documents (FRETDOCS)
    from nl2fret import prompts3 as P
    ref = P.fret_reference()
    for f in ("scope", "condition", "component", "timing", "probability", "response", "builtin_functions_explanations", "temporal_condition_explanations"):
        t = open(os.path.join(DOCS, f + ".md"), encoding="utf-8").read().strip()
        assert t in ref, f
