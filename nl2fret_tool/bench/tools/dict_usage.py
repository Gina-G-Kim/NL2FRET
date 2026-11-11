"""Observation only. For every first-stage answer (stage D or B, not the feedback rounds) counts how many identifiers of the generated FRETish are names
of the signal dictionary of the item's challenge. No reference FRETish is used. Usage: python3 tools/dict_usage.py results_dir [data/dict8_items.jsonl]"""
import json, re, sys, collections
res = sys.argv[1]
items = {json.loads(l)["id"]: json.loads(l) for l in open(sys.argv[2] if len(sys.argv) > 2 else "data/dict8_items.jsonl")}
sd = json.load(open("data/sigdict.json"))
names = {}
for ch, txt in sd.items():
    s = set()
    for ln in txt.splitlines():
        c = [x.strip() for x in ln.split("|")]
        if len(c) >= 2 and c[1] and c[1] not in ("Name",):
            s.add(c[1])
        if len(c) == 3 and c[0] and c[1] not in ("Name", "Variable Name"):   # nlguide definition table: Name | Variable Name | Definition
            s.add(c[1])
    names[ch] = s
KW = {"when", "if", "upon", "while", "in", "mode", "the", "shall", "always", "never", "immediately", "eventually", "within", "for", "after", "until", "before", "at", "next", "timepoint",
      "satisfy", "it", "is", "not", "case", "unless", "only", "ticks", "milliseconds", "seconds", "minutes", "hours", "tick", "second", "minute", "hour", "millisecond", "true", "false",
      "absReal", "preReal", "preBool", "preInt", "persisted", "occurs", "of", "than", "global", "during", "startup", "null", "regular", "emptyscope", "then", "and", "or", "xor", "ltl", "mod", "pi"}
agg = collections.defaultdict(lambda: [0, 0, 0, 0])   # arm -> [identifiers, in dictionary, units, units with all identifiers in dictionary]
for l in open(f"{res}/calls.jsonl"):
    r = json.loads(l)
    if r["stage"] not in ("D", "B") or r["status"] != "ok" or not r.get("parsed"):
        continue
    ch = items[r["item_id"]]["challenge"].split("_")[0]
    ids = []
    for t in r["parsed"].get("fretish", []):
        for tok in re.findall(r"[A-Za-z_][A-Za-z_0-9]*", t):
            if tok.lower() not in KW and not re.fullmatch(r"[0-9.]+", tok):
                ids.append(tok)
    n_in = sum(1 for t in ids if t in names.get(ch, ()))
    a = agg[r["arm"]]; a[0] += len(ids); a[1] += n_in; a[2] += 1; a[3] += (1 if ids and n_in == len(ids) else 0)
print("| arm | first-stage units | identifier tokens | in dictionary | share | units with all identifiers in dictionary |")
print("|---|---|---|---|---|---|")
for arm, (n, k, u, all_) in sorted(agg.items()):
    print(f"| {arm} | {u} | {n} | {k} | {k / n * 100 if n else 0:.1f}% | {all_} |")
