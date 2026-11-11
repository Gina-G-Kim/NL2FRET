#!/usr/bin/env python3
"""Render the system prompts of the final tool (nl2fret_tool/bench) into prompts/current/system_prompts/.

The prompts of the generation pipeline are assembled by code (prompts3.py, common.py) from fretish_guide.md, the five template
documents and string constants, so no single file holds them. This script calls the same function that the pipeline calls at
the start of a run (run_pipeline.build_prompts, which also feeds results/snapshot/system_prompt_*.txt) and writes one file per
system prompt, named like the snapshot files. It also writes MANIFEST.csv (file, stage, key, arms that use it, bytes, sha256).
No model call, no Docker, no network, no bytecode files.

usage (from the repository root):
  python3 -I -B tools/render_prompts.py                          write the files and MANIFEST.csv
  python3 -I -B tools/render_prompts.py --check                  compare with the files on disk, write nothing, exit 1 on a difference
  python3 -I -B tools/render_prompts.py --arms DIRECT MASTeR+V   render another arm set (default: the 19 arms of the 61-item main run)
"""
import argparse
import csv
import hashlib
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BENCH = ROOT / "nl2fret_tool" / "bench"
OUT = ROOT / "prompts" / "current" / "system_prompts"

# run A (61 items, 16 arms) and run B (signal-dictionary arms) of the 61-item main generation run
MAIN_RUN_ARMS = ["DIRECT", "PARA", "MASTeR", "EARS", "Adv-EARS", "SPIDER", "Boilerplate",
                 "MASTeR+R2", "EARS+R2", "Adv-EARS+R2", "SPIDER+R2", "Boilerplate+R2",
                 "DIRECT+V", "MASTeR+V", "EARS+V", "Boilerplate+V",
                 "DIRECT+D", "MASTeR+D", "EARS+D"]


def render(arms):
    """-> {file name: (stage, key, system prompt text, [arms that use it])}"""
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(BENCH))
    import prompts3 as P          # noqa: E402  (the frozen bench modules, imported from the project copy)
    import run_pipeline as RP     # noqa: E402
    ctx = types.SimpleNamespace(args=types.SimpleNamespace(arms=list(arms)))
    built = RP.build_prompts(ctx)                      # {(stage, key): (system prompt, sha, status)}
    used = {}
    for a in arms:                                     # the same key rules as run_pipeline.build_prompts
        if P.is_direct(a):
            keys = [("D", P.dkey(a))]
        else:
            keys = [("A", P.akey(a)), ((("S2" if P.is_r2(a) else "S"), None) if P.is_rule(a) else ("B", a))]
        for k in keys:
            used.setdefault(k, []).append(a)
    if set(used) != set(built):
        raise SystemExit(f"internal check failed: keys used by the arms {sorted(map(str, used))} differ from the built prompts {sorted(map(str, built))}")
    out = {}
    for (stage, key), (text, _sha, _status) in built.items():
        out[f"system_prompt_{stage}_{key or 'none'}.txt"] = (stage, key, text, used[(stage, key)])
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arms", nargs="+", default=MAIN_RUN_ARMS)
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    files = render(a.arms)
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
