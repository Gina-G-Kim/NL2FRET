"""Name alignment by the dictionary (v9). The signal dictionary of the challenge is the vocabulary of the reference. Before a generated formula is judged, every identifier of it is
checked against the dictionary of its challenge:
  exact    the identifier is a dictionary name                                        -> kept
  aliased  not a dictionary name, but exactly ONE dictionary name has the same spelling
           ignoring case and underscores (Pull_Up -> pullup)                           -> renamed to the dictionary name
  oov      no dictionary name or several candidates                                    -> kept, listed (out of vocabulary)
Nothing else is renamed here. The judge's own alignment (align.py) runs afterwards on the result. The record keeps the original formula, the renaming and the oov list."""
import csv
import re

from . import abstraction as A
from . import align
from .judge import clean_markup


def load_dictionary(path):
    """-> {challenge: set(names)} ; function entries are listed by their name without the argument list"""
    out = {}
    for r in csv.DictReader(open(path, encoding="utf-8-sig")):
        out.setdefault(r["challenge"], set()).add(re.sub(r"\(.*", "", r["name"]))
    return out


def _norm(n):
    return n.replace("_", "").lower()


def formula_names(ltl):
    tree = align.J2.prep(ltl)
    return sorted(align.J2.vars_of(tree))


def align_formula(ltl, names):
    """-> (new_ltl, {"exact": [...], "aliased": {old: new}, "oov": [...]})"""
    ltl = clean_markup(ltl)          # FRET emphasis tags and operator precedence printing, as the judge does
    used = formula_names(ltl)
    norm = {}
    for n in names:
        norm.setdefault(_norm(n), []).append(n)
    exact, aliased, oov = [], {}, []
    for v in used:
        if v in names:
            exact.append(v)
            continue
        c = norm.get(_norm(v), [])
        if len(c) == 1:
            aliased[v] = c[0]
        else:
            oov.append(v)
    new = A.rename_identifiers(ltl, aliased) if aliased else ltl
    return new, {"exact": exact, "aliased": aliased, "oov": oov}
