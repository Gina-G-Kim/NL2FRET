#!/usr/bin/env python3
"""judge5: structure-level PROOF/REFUTE that does not depend on vocabulary.
Each maximal temporal-free subformula (a 'state predicate': boolean/arithmetic over signals) is replaced by one opaque boolean atom.
What remains is the temporal skeleton (scope, trigger vs holding, timing, response form).
Then judge4.compare is run on the two skeletons (injective renaming of the opaque atoms, the most favorable correspondence).
Reading: skeleton verdict holds PROVIDED each paired opaque atom denotes the same state predicate. Verdict NEITHER is vocabulary independent
under the assumption that distinct opaque atoms are independent propositions."""
import sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import judge2 as J
from judge2 import prep, Unsupported
import judge4

TEMPORAL = {"H", "O", "Y", "Z", "S"}

def is_temporal_node(a):
    k = a[0]
    return k in TEMPORAL or (isinstance(k, str) and k.startswith(("H[", "O[")))

def has_temporal(a):
    if not isinstance(a, tuple): return False
    if is_temporal_node(a): return True
    return any(has_temporal(x) for x in a[1:] if isinstance(x, tuple))

def abstract(a, table):
    """replace maximal temporal-free subtrees by opaque atoms; FTP, TRUE, FALSE are kept"""
    k = a[0]
    if k in ("TRUE", "FALSE"): return a
    if k == "var" and a[1] == "FTP": return a
    if not has_temporal(a):
        def atom(x):
            if x[0] == "!": return ("!", atom(x[1]))      # negation stays outside the opaque atom (polarity kept)
            if x[0] in ("TRUE", "FALSE") or (x[0] == "var" and x[1] == "FTP"): return x
            key = repr(x)
            if key not in table: table[key] = f"s{len(table)}"
            return ("var", table[key])
        if k == "->":          # FRETish holding idiom (condition => response): keep the two sides separate
            return ("->", atom(a[1]), atom(a[2]))
        return atom(a)
    if k == "fn":    # temporal inside function args: unsupported
        raise Unsupported("temporal in fn")
    return (k,) + tuple(abstract(x, table) if isinstance(x, tuple) else x for x in a[1:])

def to_str(a):
    k = a[0]
    if k == "var": return a[1]
    if k in ("TRUE", "FALSE"): return k
    if k == "num": return a[1]
    if k == "!": return f"(! {to_str(a[1])})"
    if k in ("H", "O", "Y", "Z") or k.startswith(("H[", "O[")): return f"({k} {to_str(a[1])})"
    if len(a) == 3: return f"({to_str(a[1])} {k} {to_str(a[2])})"
    raise Unsupported("to_str " + k)

def normalize(a):
    """canonical merging so equivalent skeletons get equal atom grouping: (H x) & (H y) -> H (x & y); (O x) | (O y) -> O (x | y); same for equal timed windows"""
    if not isinstance(a, tuple): return a
    a = (a[0],) + tuple(normalize(x) if isinstance(x, tuple) else x for x in a[1:])
    if a[0] == "&" and len(a) == 3 and a[1][0] == a[2][0] and (a[1][0] == "H" or (isinstance(a[1][0], str) and a[1][0].startswith("H["))):
        return (a[1][0], ("&", a[1][1], a[2][1]))
    if a[0] == "|" and len(a) == 3 and a[1][0] == a[2][0] and (a[1][0] == "O" or (isinstance(a[1][0], str) and a[1][0].startswith("O["))):
        return (a[1][0], ("|", a[1][1], a[2][1]))
    return a

def skeleton(pt):
    a = normalize(prep(pt))
    table = {}
    s = abstract(a, table)
    return to_str(s), len(table)

def skeleton_compare(gen_pt, ref_pt):
    """-> dict(cls, ngen, nref, miss, alarm, detail)"""
    try:
        gs, ng = skeleton(gen_pt); rs, nr = skeleton(ref_pt)
    except Unsupported as e:
        return dict(cls="unsupported", detail=str(e), ngen=None, nref=None)
    except Exception as e:
        return dict(cls="unsupported", detail="parse " + str(e)[:50], ngen=None, nref=None)
    import re as _re
    gs = _re.sub(r"\bs(\d+)\b", r"g\1", gs)   # disjoint atom names force the injective-renaming search (same names would force identity mapping)
    c = judge4.compare(gs, rs)
    c.update(ngen=ng, nref=nr, gen_skel=gs, ref_skel=rs)
    return c

if __name__ == "__main__":
    nasa = "(H (landing_request -> gear_extended))"
    trig = "(H ((landing_request & ((Y (! landing_request)) | FTP)) -> gear_extended))"
    for name, g in (("same", nasa), ("trigger", trig), ("strong", "(H (landing_request & gear_extended))"), ("other vocabulary", "(H (a -> (b & c)))")):
        r = skeleton_compare(g, nasa)
        print(name, r["cls"], r.get("ngen"), r.get("nref"), r.get("detail"))
