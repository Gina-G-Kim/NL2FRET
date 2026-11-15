#!/usr/bin/env python3
"""Render the system prompts of the final tool (nl2fret_tool/bench) into prompts/current/system_prompts/.

The prompts of the generation pipeline are assembled by code (prompts3.py, common.py) from fretish_guide.md, the intent declaration, the five template
documents and string constants, so no single file holds them. This script sets the module switches the way run_pipeline.main() sets them from its command
line, calls the same function that the pipeline calls at the start of a run (run_pipeline.build_prompts, which also feeds <run>/gen/snapshot/system_prompt_*.txt)
and writes one file per system prompt, named like the snapshot files. It also writes MANIFEST.csv (file, stage, key, arms that use it, bytes, sha256).
Default = release 1.4 of the tool: the 11 approaches of the FSM test (DIRECT, five templates +G, five templates +R2) with the options
--dict-all --intent-decl --g-parity --tm-source-only --sourced-rules-only (--guide-sup off).
No model call, no Docker, no network, no bytecode files.

usage (from the repository root):
  python3 -I -B tools/render_prompts.py                          write the files and MANIFEST.csv
  python3 -I -B tools/render_prompts.py --check                  compare with the files on disk, write nothing, exit 1 on a difference
  python3 -I -B tools/render_prompts.py --arms DIRECT MASTeR+V   render another arm set (default: the 11 approaches of the FSM test)
  python3 -I -B tools/render_prompts.py --run-info <run>/gen/snapshot/run_info.json   take the switches from a run instead of the defaults and compare the
                                                                 prompt hashes of the run with the rendered prompts (exit 1 on a difference)
"""
import argparse
import csv
import hashlib
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BENCH = ROOT / "nl2fret_tool" / "bench"
OUT = ROOT / "prompts" / "current" / "system_prompts"

# switches of release 1.4 (run_pipeline.py options of the FSM test)
DEFAULT_SWITCHES = {"dict_all": True, "guide_sup": False, "g_parity": True, "intent_decl": True, "tm_source_only": True, "sourced_rules_only": True}


def render(arms, switches):
    """-> ({file name: (stage, key, system prompt text, [arms that use it])}, {"stage:key": sha prefix of the pipeline})"""
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(BENCH))
    import prompts3 as P          # noqa: E402  (the bench modules, imported from the project copy)
    import tpl_rules as T         # noqa: E402
    import run_pipeline as RP     # noqa: E402
    P.DICT_ALL = bool(switches["dict_all"])                         # the same assignments as run_pipeline.main()
    P.GUIDE_SUP = bool(switches["guide_sup"])
    P.G_PARITY = bool(switches["g_parity"])
    P.INTENT_DECL = bool(switches["intent_decl"])
    P.TM_SOURCE_ONLY = bool(switches["tm_source_only"])
    P.SOURCED_ONLY = T.SOURCED_ONLY = bool(switches["sourced_rules_only"])
    T.INTENT_COND = bool(switches["intent_decl"])
    ctx = types.SimpleNamespace(args=types.SimpleNamespace(arms=list(arms)))
    built = RP.build_prompts(ctx)                      # {(stage, key): (system prompt, sha, status)}
    used = {}
    for a in arms:                                     # the same key rules as run_pipeline.build_prompts
        if P.is_direct(a):
            keys = [("D", P.dkey(a))]
        elif P.is_rule(a):
            keys = [("A", P.akey(a)), ("S2" if P.is_r2(a) else "S", None), ("BF", P.base_of(a))]
        else:
            keys = [("A", P.akey(a)), ("B", a)]
        for k in keys:
            used.setdefault(k, []).append(a)
    if set(used) != set(built):
        raise SystemExit(f"internal check failed: keys used by the arms {sorted(map(str, used))} differ from the built prompts {sorted(map(str, built))}")
    out, hashes = {}, {}
    for (stage, key), (text, sha, _status) in built.items():
        out[f"system_prompt_{stage}_{key or 'none'}.txt"] = (stage, key, text, used[(stage, key)])
        hashes[f"{stage}:{key}"] = sha
    return out, hashes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arms", nargs="+", default=None)
    ap.add_argument("--run-info", default=None)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    sw, ref = dict(DEFAULT_SWITCHES), None
    if a.run_info:
        info = json.load(open(a.run_info, encoding="utf-8"))
        sw = {k: bool(info[k]) for k in DEFAULT_SWITCHES}
        ref = info["prompt_hashes"]
    sys.path.insert(0, str(BENCH))
    import prompts3 as P0          # noqa: E402
    arms = a.arms or list(P0.ARMS_FSM)
    files, hashes = render(arms, sw)
    if ref is not None:
        bad = [f"{k}: run {ref.get(k)} rendered {v}" for k, v in sorted(hashes.items()) if ref.get(k) != v]
        bad += [f"{k}: only in the run" for k in sorted(set(ref) - set(hashes))]
        print("\n".join(bad) if bad else f"run hashes ok: {len(hashes)} prompts equal the hashes of {a.run_info}")
        if bad:
            sys.exit(1)
    if a.check:
        bad = []
        for name, (_s, _k, text, _u) in sorted(files.items()):
            p = OUT / name
            if not p.exists():
                bad.append(f"missing: {name}")
            elif p.read_bytes() != text.encode("utf-8"):
                bad.append(f"differs: {name}")
        if OUT.exists():
            bad += [f"unexpected file: {p.name}" for p in sorted(OUT.glob("system_prompt_*.txt")) if p.name not in files]
        print("\n".join(bad) if bad else f"check ok: {len(files)} system prompts identical to the files on disk")
        sys.exit(1 if bad else 0)
    OUT.mkdir(parents=True, exist_ok=True)
    for p in OUT.glob("system_prompt_*.txt"):
        if p.name not in files:
            p.unlink()                                  # files of an earlier configuration (older ones are kept in assets/llm_system_prompts/v1/)
    rows = []
    for name, (stage, key, text, used) in sorted(files.items()):
        data = text.encode("utf-8")
        (OUT / name).write_bytes(data)
        rows.append([name, stage, key or "", "; ".join(used), len(data), hashlib.sha256(data).hexdigest()])
    with open(OUT / "MANIFEST.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["file", "stage", "key", "used_by_arms", "bytes", "sha256"])
        w.writerows(rows)
    print(f"wrote {len(rows)} system prompts and MANIFEST.csv to {OUT.relative_to(ROOT)}")
    for r in rows:
        print(f"{r[0]:48s} {r[4]:6d} {r[5][:12]}  {r[3]}")


if __name__ == "__main__":
    main()
