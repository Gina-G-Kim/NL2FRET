"""Vocabulary alignment between a generated and a reference formula (the 'name-anchored' main layer and the auxiliary layers).

This is a port of the candidate construction in legacy/judge4.py (compare): the search over renamings is the same, but the verdict for each
candidate comes from the query engine instead of the bounded z3 solver. Modes:
  anchor : a generated variable whose name and type occur in the reference keeps its name (identity); only the remaining generated variables may be
           renamed, injectively, onto unused reference variables of the same type.                                       [main layer]
  lex    : as anchor, but constant-like unmatched names may only map onto lexically compatible reference constants.     [auxiliary]
  strict : as lex, and no renaming for non-constant unmatched variables.                                                [auxiliary]
  free   : injective renaming of all generated variables (no anchoring).                                               [auxiliary, upper bound]
Result: dict(maps=[...], anchored=int) or dict(und=reason, detail=text). 'und' means no alignment exists (role UND).
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
LEGACY = os.path.join(os.path.dirname(HERE), "legacy")
sys.path.insert(0, LEGACY)
import judge2 as J2  # noqa: E402
import judge4 as J4  # noqa: E402

MODES = ("anchor", "lex", "strict", "free")


def _types(tree):
    vt = J2.vars_of(tree)
    for v in vt:
        if len(vt[v]) > 1:
            vt[v] = {"real"}
    return {v: next(iter(t)) for v, t in vt.items()}


def candidates(gen_pt, ref_pt, mode="anchor"):
    if mode not in MODES:
        raise ValueError(mode)
    try:
        g, r = J2.prep(gen_pt), J2.prep(ref_pt)
        tg, tr = _types(g), _types(r)
    except Exception as e:  # noqa: BLE001
        return {"und": "unsupported", "detail": "parse " + str(e)[:80]}
    gv, rv = sorted(tg), sorted(tr)
    if set(tg) == set(tr) and all(tg[v] == tr[v] for v in tg):
        return {"maps": [{v: v for v in gv}], "anchored": len(gv)}
    MAXPERM = J2.MAXPERM
    maps = []
    if mode != "free":
        fixed = {v: v for v in gv if v in tr and tr[v] == tg[v]}
        fg = [v for v in gv if v not in fixed]
        fr = [x for x in rv if x not in set(fixed.values())]
        if len(fg) > len(fr):
            return {"und": "atomization_mismatch", "detail": f"unmatched gen vars {len(fg)} > unmatched ref vars {len(fr)}"}
        if mode in ("lex", "strict"):
            cg, cr = J4.const_vars(g), J4.const_vars(r)
            cands = {}
            for v in fg:
                if v in cg:
                    cands[v] = [x for x in fr if x in cr and tr[x] == tg[v] and J4.lex_compatible(v, x)]
                elif mode == "strict":
                    cands[v] = []
                else:
                    cands[v] = [x for x in fr if x not in cr and tr[x] == tg[v]]
            if any(not c for c in cands.values()):
                return {"und": "atomization_mismatch", "detail": "no lexically supported counterpart"}
        else:
            cands = {v: [x for x in fr if tr[x] == tg[v]] for v in fg}
            if any(not c for c in cands.values()):
                return {"und": "atomization_mismatch", "detail": "type"}

        def rec(i, used, cur):
            if len(maps) > MAXPERM:
                return
            if i == len(fg):
                maps.append({**fixed, **cur})
                return
            for c in cands[fg[i]]:
                if c not in used:
                    cur[fg[i]] = c
                    used.add(c)
                    rec(i + 1, used, cur)
                    used.discard(c)
                    del cur[fg[i]]
        rec(0, set(), {})
        anchored = len(fixed)
    else:
        if len(gv) > len(rv):
            return {"und": "atomization_mismatch", "detail": f"gen vars {len(gv)} > ref vars {len(rv)}"}
        if len(rv) - len(gv) >= 3:
            return {"und": "atomization_mismatch", "detail": f"reference has {len(rv)} variables, generated {len(gv)}"}
        cands = {v: [x for x in rv if tr[x] == tg[v]] for v in gv}
        if any(not c for c in cands.values()):
            return {"und": "atomization_mismatch", "detail": "type"}

        def rec2(i, used, cur):
            if len(maps) > MAXPERM:
                return
            if i == len(gv):
                maps.append(dict(cur))
                return
            for c in cands[gv[i]]:
                if c not in used:
                    cur[gv[i]] = c
                    used.add(c)
                    rec2(i + 1, used, cur)
                    used.discard(c)
                    del cur[gv[i]]
        rec2(0, set(), {})
        anchored = 0
    if len(maps) > MAXPERM:
        return {"und": "atomization_mismatch", "detail": "too many renamings"}
    return {"maps": maps, "anchored": anchored}
