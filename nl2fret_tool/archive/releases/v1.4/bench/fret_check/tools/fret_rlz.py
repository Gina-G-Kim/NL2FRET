#!/usr/bin/env python3
"""FRET realizability checks for the NL2FRET bench (section 4.7 of the prompt document). Records only; nothing is fed back to the conversion.

Pieces
  compile_cached(texts)         official FRET parser (FretSemantics.compile in docker image fret-lab), cached on disk
  build_table(item, sentences)  per item ONE variable table (role, type, constant) shared by every arm and repetition (rules in FRET_NOTES.md)
  docs_for(...)                 FRET project documents (requirements with semantics, variable mapping) as the FRET GUI would store them
  run_batch(...)                realizability with `fretCLI realizability <project> <component> --solver kind2` inside the image, many projects per container

Roles, types and constants are the bench author's assumptions ("추측입니다"), except where the NASA report prints them (Liquid Mixer: CR21 p.15).
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
FC = os.path.dirname(HERE)
WORK = os.path.join(FC, "work")
sys.path.insert(0, HERE)
import fret_compile  # noqa: E402
import fretexpr  # noqa: E402

IMG = "fret-lab:latest"
CACHE = os.path.join(WORK, "compile_cache.json")
FUNC_WORDS = {"at", "the", "next", "occurrence", "of", "TRUE", "FALSE", "true", "false"}


def sha(s):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]


def compile_cached(texts):
    cache = json.load(open(CACHE, encoding="utf-8")) if os.path.exists(CACHE) else {}
    todo = [t for t in dict.fromkeys(texts) if t not in cache]
    if todo:
        for r in fret_compile.compile_list(todo):
            cache[r["fretish"]] = r
        json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False)
    return {t: cache[t] for t in texts}


def sentence_info(res):
    """res = compile result (ok, sem). Returns analysis dict or None when the parser rejected the sentence."""
    if not res["ok"]:
        return None
    sem = res["sem"]
    post = sem.get("post_condition") or ""
    cond = sem.get("regular_condition") or ""
    info = fretexpr.analyze(post, cond)
    names = list(sem.get("variables") or [])
    mode = sem.get("scope_mode")
    if not info["parse_ok"]:
        # fallback: identifiers after the first '=>' of the response text are consequent, all variables boolean
        tail = post.split("=>", 1)[1] if "=>" in post else post
        toks = {w for w in re.findall(r"[A-Za-z_][A-Za-z0-9_\.]*", tail) if w in names and w not in FUNC_WORDS}
        info["cons"] = toks
        info["ante"] = set(names) - toks
        info["bool"] = set(names)
    info["names"] = names
    info["mode"] = mode
    return info


def _stats(sentences):
    """Usage statistics of identifiers over a list of sentence dicts (text, res, kind)."""
    st = {"occ": {}, "cons": {}, "num": {}, "bool": {}, "symL": {}, "symR": {}, "funcs": set(), "real": {}, "int": {}, "n": 0}
    for s in sentences:
        info = sentence_info(s["res"])
        if info is None:
            continue
        st["n"] += 1
        st["funcs"] |= info["funcs"]
        seen = set(info["names"])
        for v in seen:
            st["occ"][v] = st["occ"].get(v, 0) + 1
        for v in info["cons"] & seen:
            st["cons"][v] = st["cons"].get(v, 0) + 1
        for v in info["num"]:
            st["num"][v] = st["num"].get(v, 0) + 1
        for v, kinds in info.get("numkind", {}).items():
            for kd in kinds:
                if kd == "real":
                    st["real"][v] = st["real"].get(v, 0) + 1
                elif kd == "int":
                    st["int"][v] = st["int"].get(v, 0) + 1
        for v in info["bool"]:
            st["bool"][v] = st["bool"].get(v, 0) + 1
        for l, r in info["sym_eq"]:
            st["symL"][l] = st["symL"].get(l, 0) + 1
            st["symR"][r] = st["symR"].get(r, 0) + 1
    st["funcs"] = {f for f in st["funcs"] if f not in st["bool"] and f not in st["num"]}   # also used as a plain variable: not a function
    return st


TYPE_POLICY = "literal"   # "literal" (v3: double only when a decimal literal is present) or "double" (probe: every numeric variable is double)


def build_table(item_id, sentences):
    """sentences: list of dict(text, res, kind) with kind 'gt', 'gt_alt' or 'gen'. One table per group (item, or the LM / FSM set).

    GT first: an identifier that occurs in a NASA sentence of the group takes its role, type and constant status from the NASA sentences only,
    so generated sentences can never redefine the reference interface. Identifiers that occur only in generated sentences are defined from
    the generated sentences by the same rules (majority usage). Rules (assumptions, 추측입니다):
      role   = Output when the identifier is in the consequent of the response in at least half of the sentences where it occurs, else Input
      type   = double when it is used as a number most often, integer when it is compared with another bare identifier most often, else boolean
      const  = compared only as the right side of '=' with another bare identifier and nowhere else: Internal integer with a distinct value
    """
    gt = _stats([s for s in sentences if s.get("kind") in ("gt", "gt_alt")])
    gen = _stats([s for s in sentences if s.get("kind") == "gen"])
    names = sorted(set(gt["occ"]) | set(gen["occ"]))
    table, consts_order = {}, []
    for v in names:
        src, origin = (gt, "NASA sentence") if v in gt["occ"] else (gen, "generated sentences")
        n = src["occ"][v]
        if v in src["funcs"]:
            table[v] = {"role": "Function", "dataType": None, "origin": origin, "n_sentences": n, "note": "used as a function application; not modelled"}
            continue
        isconst = src["symR"].get(v, 0) > 0 and not src["symL"].get(v) and not src["num"].get(v) and not src["bool"].get(v)
        if isconst:
            consts_order.append(v)
            table[v] = {"role": "Internal", "dataType": "integer", "origin": origin, "n_sentences": n,
                        "note": "symbolic value compared with another identifier (e.g. state = ap_standby_state); distinct integer constant"}
            continue
        share = src["cons"].get(v, 0) / n
        nb, nn, ns = src["bool"].get(v, 0), src["num"].get(v, 0), src["symL"].get(v, 0) + src["symR"].get(v, 0)
        if nn > max(nb, ns):
            # numeric: the Lustre type must agree with the literals of the sentence (FRET does not convert 0 to 0.0), so follow the literals
            dt = "double" if src["real"].get(v, 0) >= src["int"].get(v, 0) and src["real"].get(v, 0) > 0 else "integer"
            if TYPE_POLICY == "double":
                dt = "double"
        else:
            dt = "integer" if ns > max(nb, nn) else "boolean"
        table[v] = {"role": "Output" if share >= 0.5 else "Input", "dataType": dt, "origin": origin, "n_sentences": n,
                    "share_in_consequent": round(share, 3), "uses": {"boolean": nb, "numeric": nn, "symbolic": ns}}
    for k, v in enumerate(sorted(consts_order), 1):
        table[v]["constant"] = k
    return {"item": item_id, "n_parseable_nasa_sentences": gt["n"], "n_parseable_generated_sentences": gen["n"], "variables": table,
            "constants": sorted(consts_order), "status": "추측입니다 (rule based, see FRET_NOTES.md); the Liquid Mixer roles and types equal the CR21 p.15 table"}


def docs_for(project, comp, items, table, home_comp=None):
    """items: list of (reqid, fretish, sem). Returns (req docs, variable docs)."""
    reqs, vdocs, uses = [], {}, {}
    for reqid, text, sem in items:
        rid = f"req_{project}_{reqid}"
        reqs.append({"_id": rid, "reqid": reqid, "parent_reqid": "", "project": project, "rationale": "", "fulltext": text, "status": "completed",
                     "input": text, "semantics": sem})
        for v in sem.get("variables", []):
            uses.setdefault(v, []).append(rid)
    for v, rids in uses.items():
        t = table["variables"][v]
        if t["role"] == "Function":
            continue
        d = {"_id": f"{project}{comp}{v}", "project": project, "component_name": comp, "variable_name": v, "reqs": sorted(set(rids)),
             "dataType": t["dataType"], "idType": t["role"], "moduleName": "", "description": "", "assignment": "", "copilotAssignment": "",
             "smvAssignment": "", "modeRequirement": "", "modeldoc": False, "modelComponent": "", "modeldoc_id": "", "completed": True,
             "r2u2Completed": False, "smvCompleted": False, "file_path": "preloaded"}
        if t["role"] == "Internal":
            d["assignment"] = str(t["constant"])
        vdocs[v] = d
    return reqs, list(vdocs.values())


def run_batch(batch, jobs, timeout_each=300, solver="kind2", kind2_timeout=120):
    """jobs: list of dict(project, comp, reqs, vdocs). Runs them in ONE container; returns {project: dict(result, ...)}."""
    home = os.path.join(WORK, f"home_{batch}")
    if os.path.exists(home):
        subprocess.run(["rm", "-rf", home])
    os.makedirs(os.path.join(home, "Documents"), exist_ok=True)
    allreq = [r for j in jobs for r in j["reqs"]]
    allvar = [v for j in jobs for v in j["vdocs"]]
    json.dump(allreq, open(os.path.join(WORK, f"{batch}_reqs.json"), "w", encoding="utf-8"), ensure_ascii=False)
    json.dump(allvar, open(os.path.join(WORK, f"{batch}_vars.json"), "w", encoding="utf-8"), ensure_ascii=False)
    with open(os.path.join(WORK, f"{batch}_jobs.txt"), "w", encoding="utf-8") as f:
        for j in jobs:
            f.write(f"{j['project']} {j['comp']}\n")
    script = (f"node /tools/fret_import.js /work/{batch}_reqs.json /work/{batch}_vars.json 2>&1 | tail -2; cd /opt/fret/fret-electron/app; "
              f"while read p c; do echo \"@@@START $p\"; S=$(date +%s); timeout {timeout_each} node cli/fretCLI.main.js realizability \"$p\" \"$c\" "
              f"--solver {solver} --timeout {kind2_timeout} --json 2>&1; echo \"@@@END $p rc=$? wall=$(( $(date +%s) - S ))\"; done < /work/{batch}_jobs.txt")
    cmd = ["docker", "run", "--rm", "--cpus", "1", "--entrypoint", "sh", "-e", "NODE_PATH=/opt/fret/fret-electron/app/node_modules",
           "-v", HERE + ":/tools:ro", "-v", WORK + ":/work", "-v", os.path.join(home, "Documents") + ":/root/Documents", IMG, "-c", script]
    t0 = time.time()
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=max(3600, timeout_each * len(jobs) + 600))
    out = r.stdout + r.stderr
    open(os.path.join(WORK, f"{batch}_container.log"), "w", encoding="utf-8").write(out)
    res = {}
    for m in re.finditer(r"@@@START (\S+)\n(.*?)@@@END \S+ rc=(\d+) wall=(\d+)", out, re.S):
        p, body, rc, wall = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
        res[p] = summarize(body, rc, wall)
    res["_batch_wall_s"] = round(time.time() - t0, 1)
    return res


def summarize(body, rc, wall):
    i = body.find("{")
    out = {"rc": rc, "wall_s": wall}
    if i < 0:
        out.update(result="unknown", detail="no JSON in CLI output", tail=body.strip()[-400:])
        return out
    try:
        j = json.loads(body[i:body.rfind("}") + 1])
    except Exception:
        out.update(result="unknown", detail="unparseable CLI JSON", tail=body.strip()[-400:])
        return out
    sc = j["systemComponents"][0]
    comp, mono = sc.get("compositional"), sc.get("monolithic")
    if comp and comp.get("result") not in (None, "UNCHECKED"):
        out["mode"] = "compositional"
        out["raw_result"] = comp.get("result")
        out["n_cc"] = len(comp.get("connectedComponents", []))
        out["cc_results"] = [x.get("result") for x in comp.get("connectedComponents", [])]
        out["cc_sizes"] = [len(x.get("requirements", [])) for x in comp.get("connectedComponents", [])]
        out["time_s"] = comp.get("time")
        out["error"] = [x.get("error") for x in comp.get("connectedComponents", []) if x.get("error")] or None
    elif mono and mono.get("result") not in (None, "UNCHECKED"):
        out["mode"] = "monolithic"
        out["raw_result"] = mono.get("result")
        out["time_s"] = mono.get("time")
        out["error"] = mono.get("error")
    else:
        out["raw_result"] = None
        out["error"] = (comp or {}).get("error") or (mono or {}).get("error")
    rr = (out.get("raw_result") or "").upper()
    out["result"] = {"REALIZABLE": "realizable", "UNREALIZABLE": "unrealizable"}.get(rr, "unknown")
    return out
