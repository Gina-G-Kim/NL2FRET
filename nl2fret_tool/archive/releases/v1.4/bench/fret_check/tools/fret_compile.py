#!/usr/bin/env python3
"""Compile FRETish sentences with the official FRET parser (FretSemantics.compile) inside the docker image fret-lab.

usage: fret_compile.py <in.json> <out.json>
  in.json  = JSON list of FRETish strings
  out.json = JSON list of {fretish, ok, error, ltl_ft, ltl_pt, sem}
The helper script fretjs/fret_parse_full.js and the stub for the missing module product-iterable were copied unchanged from
~/cst_test/round12_testnote12/E22_run/tools/fretjs (an earlier experiment of this user). Input files must sit under /Users (Colima mounts only /Users).
Importable: compile_list(list_of_str) -> list of dicts.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
JS = os.path.join(HERE, "fretjs")
WORK = os.path.join(os.path.dirname(HERE), "work")


def compile_list_node(texts, chunk=400):
    """Offline alternative to the docker image (sandbox tests): runs a local copy of the official FretSemantics.js with node.
    env NL2FRET_NODE_PARSER = path of a small node script that reads the JSON list (argv[2]) and prints [{fretish, ok, error, ltl_ft, ltl_pt}] (the script of fretjs/fret_parse_full.js with a local require path);
    env NODE_PATH must contain antlr4 and the other modules of fret-electron/app."""
    script = os.environ["NL2FRET_NODE_PARSER"]
    os.makedirs(WORK, exist_ok=True)
    out = []
    for i in range(0, len(texts), chunk):
        part = texts[i:i + chunk]
        tmp = os.path.join(WORK, f"fcn_in_{os.getpid()}_{i}.json")
        json.dump(part, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
        r = subprocess.run(["node", script, tmp], capture_output=True, text=True, timeout=1800)
        os.remove(tmp)
        try:
            res = json.loads(r.stdout)
        except json.JSONDecodeError:
            raise SystemExit(f"node compile failed: rc={r.returncode} stderr={r.stderr[-500:]!r}")
        out += [{"fretish": x["fretish"], "ok": bool(x.get("ok")), "error": x.get("error"), "ltl_ft": x.get("ltl_ft"), "ltl_pt": x.get("ltl_pt"), "sem": None} for x in res]
    return out


def compile_list(texts, chunk=400, backend="docker"):
    if backend == "node":
        return compile_list_node(texts, chunk)
    os.makedirs(WORK, exist_ok=True)
    out = []
    for i in range(0, len(texts), chunk):
        part = texts[i:i + chunk]
        tmp = os.path.join(WORK, f"fc_in_{os.getpid()}_{i}.json")
        json.dump(part, open(tmp, "w", encoding="utf-8"), ensure_ascii=False)
        cmd = ["docker", "run", "--rm", "--cpus", "1", "--entrypoint", "node", "-e", "NODE_PATH=/stub:/opt/fret/fret-electron/app/node_modules",
               "-v", JS + ":/tools:ro", "-v", os.path.join(JS, "stub") + ":/stub:ro", "-v", tmp + ":/in.json:ro", "fret-lab:latest",
               "/tools/fret_parse_full.js", "/in.json"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        os.remove(tmp)
        try:
            res = json.loads(r.stdout)
        except json.JSONDecodeError:
            raise SystemExit(f"compile failed: rc={r.returncode} stderr={r.stderr[-500:]!r} stdout={r.stdout[-300:]!r}")
        out += [{"fretish": x["fretish"], "ok": bool(x.get("ok")), "error": x.get("error"), "ltl_ft": x.get("ltl_ft"), "ltl_pt": x.get("ltl_pt"),
                 "sem": x.get("sem")} for x in res]
    return out


if __name__ == "__main__":
    res = compile_list(json.load(open(sys.argv[1], encoding="utf-8")))
    json.dump(res, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for i, x in enumerate(res):
        print(i, "OK" if x["ok"] else "ERROR " + str(x["error"])[:140], "|", x["fretish"][:100])
