"""Builds data/sigdict.json from the Lockheed Martin challenge requirement documents (.docx).
Rule: every table whose header row starts with 'Input Scope' or 'Output Scope' (the signal tables), plus the 4_nlguide definition table
('Name | Variable Name | Definition'), copied cell by cell without selection, rewriting or ordering by relevance. Tables that hold requirement text or
tuning parameters are not copied. Challenge 7_autopilot is left out (its signal tables are empty or hold requirement text).
Usage: python3 tools/make_sigdict.py <folder with the original_models/ challenge folders>   (not needed to run the bench; sigdict.json is shipped)"""
import docx, glob, json, os, sys
root = sys.argv[1]
OUT = {}
for f in sorted(glob.glob(os.path.join(root, "*/*.docx"))):
    ch = os.path.basename(os.path.dirname(f))
    num = ch.split("_")[0]
    if num == "7":
        continue
    d = docx.Document(f)
    blocks = []
    for t in d.tables:
        hdr = [c.text.strip() for c in t.rows[0].cells]
        if hdr[0] in ("Input Scope", "Output Scope") or hdr[:2] == ["Name", "Variable Name"]:
            rows = [" | ".join(c.text.strip().replace("\n", " ") for c in r.cells) for r in t.rows]
            blocks.append("\n".join(rows))
    OUT[num.zfill(2)] = "\n\n".join(blocks)
json.dump(OUT, open("data/sigdict.json", "w"), ensure_ascii=False, indent=1)
for k, v in OUT.items():
    print(k, len(v), "chars")
