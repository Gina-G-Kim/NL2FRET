"""Five-pair self check (NUSMV prompt 4.C). Run before every judge run; a failing engine must not be used.
Each case: (name, generated pt, reference pt, expected sound, expected compl)."""
from .judge import judge_pair

CASES = [
    ("identical", "(H (a -> b))", "(H (a -> b))", True, True),
    ("contrapositive", "(H ((! b) -> (! a)))", "(H (a -> b))", True, True),
    ("stronger_pred", "(H b)", "(H (a -> b))", False, True),
    ("weaker_pred", "((H (a -> b)) | (O (! a)))", "(H (a -> b))", True, False),
    ("converse", "(H (b -> a))", "(H (a -> b))", False, False),
]


def run(engine):
    rows, ok = [], True
    for name, g, r, es, ec in CASES:
        rec = judge_pair(g, r, engine, pair_id="selfcheck:" + name, meta={"group": "selfcheck"})
        good = rec["sound"] == es and rec["compl"] == ec
        ok = ok and good
        rows.append({"case": name, "expected": (es, ec), "got": (rec["sound"], rec["compl"]), "role": rec["role"], "ok": good})
    return ok, rows
