// Runs the official FRET parser (FretSemantics.compile, fret-electron/app/parser) on probe sentences and prints, per sentence, FRET's own natural-language
// description and its future-time formula. usage: node fret_semantics_probe.js <path to FretSemantics.js> <probes.json>   (NODE_PATH must reach the FRET dependencies)
const fs = require("fs");
const sem = require(process.argv[2]);
const probes = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const clean = (s) => String(s || "").replace(/<br\s*\/?>/g, " | ").replace(/<[^>]+>/g, "").replace(/\s+/g, " ").trim();
const out = probes.map((t) => {
  const r = sem.compile(t);
  if (r.parseErrors) return { sentence: t, ok: false, error: String(r.parseErrors) };
  const c = r.collectedSemantics;
  return { sentence: t, ok: true, description: clean(c.description), ft_inf: c.ftInfAUExpanded, ft_finite: c.ftExpanded, pt: c.ptExpanded };
});
console.log(JSON.stringify(out));
