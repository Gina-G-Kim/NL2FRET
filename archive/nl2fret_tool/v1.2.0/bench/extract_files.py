#!/usr/bin/env python3
"""Extract every <!-- FILE: path --> block of the prompt document and verify its sha256 against the manifest."""
import hashlib, json, pathlib, re, sys

doc = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else "NL2FRET_PROMPT_v6_LM.md")
md = doc.read_text(encoding="utf-8")
manifest = json.loads(re.search(r"<!-- MANIFEST (\{.*?\}) -->", md, re.S).group(1))
pat = re.compile(r"<!-- FILE: (\S+) -->\n````[a-z]*\n(.*?)\n````(?:\n|\Z)", re.S)
seen, bad = set(), 0
for m in pat.finditer(md):
    rel, body = m.group(1), m.group(2) + "\n"
    p = pathlib.Path(rel)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body, encoding="utf-8")
    ok = hashlib.sha256(body.encode("utf-8")).hexdigest() == manifest.get(rel)
    bad += 0 if ok else 1
    seen.add(rel)
    print(("OK       " if ok else "MISMATCH ") + rel)
missing = set(manifest) - seen
print("missing files:", sorted(missing) if missing else "none")
sys.exit(1 if (bad or missing) else 0)
