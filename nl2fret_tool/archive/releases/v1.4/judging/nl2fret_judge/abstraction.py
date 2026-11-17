"""Boolean abstraction of FRET past-time formulas (thin layer over the vendored ltl_engines module).

The vendored module (ltl_engines.py) parses a FRET ltl_pt string, replaces every comparison and function application by a boolean atom and
prints the result in NuSMV syntax. This layer adds what a recorded judgement needs: atom lists with types and the mapping from the original
atom text to the boolean variable name.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ltl_engines as LE  # noqa: E402  (vendored)

Unsupported = LE.Unsupported


def abstract(s):
    """FRET ltl_pt string -> boolean AST (raises ValueError on a syntax error, Unsupported on an unknown operator)."""
    return LE.abstract(s)


def atoms(b):
    return sorted(LE.aps(b))


def to_smv(b, cap=128):
    return LE.to_smv(b, cap)


def atom_map(s):
    """Mapping original atom text -> boolean variable, for the record (so the abstraction can be reproduced by hand)."""
    out = {}
    tree = LE.parse(LE.lex(s))

    def walk(a):
        if not isinstance(a, tuple):
            return
        k = a[0]
        if k == "var" and a[1] != "FTP":
            out[a[1]] = "b_" + a[1]
            return
        if k in LE.CMP:
            x, y = LE.canon(a[1]), LE.canon(a[2])
            if k in ("<", ">"):
                p, q = (x, y) if k == "<" else (y, x)
                name = LE.cat("lt", p + "<" + q)
            elif k in ("<=", ">="):
                p, q = (y, x) if k == "<=" else (x, y)
                name = LE.cat("lt", p + "<" + q)
            else:
                p, q = sorted([x, y])
                name = LE.cat("eq", p + "=" + q)
            out[f"{x} {k} {y}"] = name
            return
        if k == "fn":
            out[LE.canon(a)] = LE.cat("fn", LE.canon(a))
            return
        for x in a[1:]:
            walk(x)

    walk(tree)
    return out


def rename_identifiers(text, mapping):
    """Simultaneous renaming of identifiers in a formula string (one pass, so swaps are safe)."""
    if not mapping:
        return text
    return re.sub(r"[A-Za-z_][A-Za-z0-9_]*", lambda m: mapping.get(m.group(0), m.group(0)), text)
