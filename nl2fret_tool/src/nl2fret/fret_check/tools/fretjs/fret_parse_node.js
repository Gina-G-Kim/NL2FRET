// Local (non-docker) twin of fret_parse_full.js. Reads a JSON array of FRETish strings (argv[2]) and prints [{fretish, ok, error, ltl_ft, ltl_pt, sem}] with the collectedSemantics of the official parser.
// env FRET_PARSER_JS = path of fret-electron/app/parser/FretSemantics.js (commit cf0f913cc15c41705e803593297e89cd6056b839); NODE_PATH must reach the modules of fret-electron/app and the stub of fretjs/stub.
const fs = require("fs");
const sem = require(process.env.FRET_PARSER_JS);
const inp = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
const out = inp.map((text) => {
  const r = sem.compile(text);
  if (r.parseErrors) return { fretish: text, ok: false, error: String(r.parseErrors) };
  const c = r.collectedSemantics;
  return { fretish: text, ok: !!c.ftExpanded, ltl_ft: c.ftExpanded, ltl_pt: c.ptExpanded, sem: c };
});
console.log(JSON.stringify(out));
