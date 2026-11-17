#!/usr/bin/env python3
"""Apply the experiment-only signal dictionary to generated LTL (outside the frozen judge tool).
usage: python3 -I -B apply_dict.py MAPPING INPUTS_DIR OUT_DIR
Renames identifier tokens in ltl_pt / ltl_ft per item (whole-token, simultaneous, never a token followed by '(' = function name).
A sentence that occurs in several items must get an identical result in each item, else the script stops."""
import json, re, sys, os, shutil, hashlib, collections
mp, ind, out = sys.argv[1:4]
M = json.load(open(mp))
os.makedirs(out, exist_ok=True)
units = json.load(open(f"{ind}/units.json"))["units"]
rows = [json.loads(l) for l in open(f"{ind}/fret_ltl_gen.jsonl")]
by = {r["sentence"]: r for r in rows}
s2i = collections.defaultdict(set)
for u in units:
    for t in u["texts"]:
        s2i[t].add(u["item"])
TOK = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
def ren(s, m):
    if not s: return s, 0
    n = 0
    def f(mo):
        nonlocal n
        w = mo.group(0)
        if w in m and not s[mo.end():].lstrip().startswith("("):
            n += 1
            return m[w][0]
        return w
    return TOK.sub(f, s), n
res = {}
stat = collections.Counter(); coll = []
def sent_map(m, r):
    """collision rule: inside one sentence a rename is dropped when its target equals a different identifier of the sentence
    that stays unrenamed, or when two different source names would receive the same target"""
    src = set(TOK.findall((r.get("ltl_pt") or "") + " " + (r.get("ltl_ft") or "")))
    cand = {w: m[w] for w in src if w in m}
    untouched = {w for w in src if w not in m}
    tgt = collections.Counter(v[0] for v in cand.values())
    keep = {}
    for w, v in cand.items():
        if v[0] in untouched or tgt[v[0]] > 1 or (v[0] in src and v[0] != w and v[0] not in cand):
            coll.append((w, v[0])); continue
        keep[w] = v
    return keep
for sent, items in s2i.items():
    r = by.get(sent)
    if not r: continue
    outs = set()
    for it in items:
        m = sent_map(M.get(it, {}), r)
        pt, n1 = ren(r.get("ltl_pt"), m)
        ft, n2 = ren(r.get("ltl_ft"), m)
        outs.add((pt, ft))
    if len(outs) > 1:
        print("SHARED SENTENCE DIFFERS", sent[:100], items); sys.exit(2)
    pt, ft = outs.pop()
    nr = dict(r); nr["ltl_pt"], nr["ltl_ft"] = pt, ft
    res[sent] = nr
    stat["changed" if (pt, ft) != (r["ltl_pt"], r["ltl_ft"]) else "same"] += 1
with open(f"{out}/fret_ltl_gen.jsonl", "w") as f:
    for r in rows:
        f.write(json.dumps(res.get(r["sentence"], r), ensure_ascii=False) + "\n")
for fn in ("units.json", "fret_realizability_gen.jsonl"):
    if os.path.exists(f"{ind}/{fn}"): shutil.copy(f"{ind}/{fn}", f"{out}/{fn}")
print(dict(stat), "dropped renames (collision rule)", len(coll))
print(collections.Counter(coll).most_common(12))
for fn in ("units.json", "fret_ltl_gen.jsonl", "fret_realizability_gen.jsonl"):
    p = f"{out}/{fn}"
    if os.path.exists(p): print(hashlib.sha256(open(p, "rb").read()).hexdigest(), fn)
