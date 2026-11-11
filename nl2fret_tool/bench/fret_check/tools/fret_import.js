// Runs inside fret-lab. usage: node fret_import.js <reqs.json> <vars.json>
// Writes FRET project docs into ~/Documents/fret-db and ~/Documents/model-db (PouchDB/leveldb), as FRET's own import does.
const fs = require("fs");
const os = require("os");
const path = require("path");
const PouchDB = require("pouchdb");
PouchDB.plugin(require("pouchdb-find"));
(async () => {
  const docsDir = path.join(os.homedir(), "Documents");
  const reqs = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
  const vars = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
  const fretdb = new PouchDB(path.join(docsDir, "fret-db"));
  const modeldb = new PouchDB(path.join(docsDir, "model-db"));
  const r1 = await fretdb.bulkDocs(reqs.map((d) => { const x = Object.assign({}, d); delete x._rev; return x; }));
  const r2 = await modeldb.bulkDocs(vars.map((d) => { const x = Object.assign({}, d); delete x._rev; return x; }));
  const bad = (a) => a.filter((x) => x.error).length;
  console.log("imported reqs", r1.length, "errors", bad(r1), "vars", r2.length, "errors", bad(r2));
  await fretdb.close(); await modeldb.close();
})().catch((e) => { console.error("ERR", e); process.exit(1); });
