// Runs inside fret-lab image. Reads JSON array of FRETish strings (argv[2]); prints [{fretish, ok, error, sem, ltl_ft}] with the compile() collectedSemantics.
const fs = require("fs");
const sem = require("/opt/fret/fret-electron/app/parser/FretSemantics.js");
const inp = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const out = inp.map((text) => {
  const r = sem.compile(text);
  if (r.parseErrors) return { fretish: text, ok: false, error: String(r.parseErrors) };
  const c = r.collectedSemantics;
  return { fretish: text, ok: !!c.ftExpanded, ltl_ft: c.ftExpanded, ltl_pt: c.ptExpanded, sem: c };
});
console.log(JSON.stringify(out));
