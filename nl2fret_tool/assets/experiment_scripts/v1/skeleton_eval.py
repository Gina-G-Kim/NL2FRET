#!/usr/bin/env python3
"""Skeleton comparison of every judged pair (instruction section 4 of the 021 comparability test). Outside the judging tool, read-only use of the tool code.

For every generated sentence that has a parsed past-time formula (the same pair set and the same pair_id format as nl2fret_judge judge: item|arm|rep|sentence index),
the generated formula is compared with every reference part and version of the item (units.load_reference, same order as judge.best_over_references) with
legacy/judge5.skeleton_compare (each maximal temporal-free subformula becomes one opaque atom; the remaining skeleton is compared with judge4.compare, bounded z3).
The best result over the reference parts is kept with the rank order of the tool (judge.RANK): same < stronger or weaker < incomparable < not decided; the loop stops at
the first 'same', ties keep the first part (strict improvement only), exactly as best_over_references.

Class -> skeleton role (direction read from judging/legacy/judge4.py: MISS = a trace where the generated formula holds and the reference does not, i.e. the generated
formula is weaker; ALARM = a trace where the reference holds and the generated formula does not, i.e. the generated formula is stronger; the tool's PROOF = no MISS
(compl true) and REFUTE = no ALARM (sound true), see judging/nl2fret_judge/judge.py):
  equivalent_bounded, equivalent_under_renaming              -> SAME
  stronger_under_renaming, generated_stronger (ALARM only)   -> PROOF
  weaker_under_renaming, generated_weaker (MISS only)        -> REFUTE
  incomparable, incomparable_under_renaming (MISS and ALARM) -> NEITHER
  unsupported (operator, parse error, solver unknown)        -> N/M   (not decided, rank 3)
  atomization_mismatch                                       -> UND   (not decided, rank 4)

usage:
  python3 -I -B skeleton_eval.py run   --tool-dir T --units U --ltl L --out F [--shard K --nshards N] [--limit M]
  python3 -I -B skeleton_eval.py merge --tool-dir T --units U --ltl L --parts F1 F2 ... --out F
run writes one JSON object per pair (resume: pairs already in --out are skipped; a partial last line is cut). merge puts the parts together in unit order and sentence index
order (duplicates and records that belong to no pair are refused). No model call, no NuSMV; the solver is z3 inside the legacy code (the venv python of the tool run).
"""
import argparse
import json
import os
import sys
import time

sys.dont_write_bytecode = True

CLASS_ROLE = {
    "equivalent_bounded": "SAME", "equivalent_under_renaming": "SAME",
    "stronger_under_renaming": "PROOF", "generated_stronger": "PROOF",
    "weaker_under_renaming": "REFUTE", "generated_weaker": "REFUTE",
    "incomparable": "NEITHER", "incomparable_under_renaming": "NEITHER",
    "unsupported": "N/M", "atomization_mismatch": "UND",
}
RANK = {"SAME": 0, "PROOF": 1, "REFUTE": 1, "NEITHER": 2, "N/M": 3, "UND": 4}      # judge.RANK of the tool


def role_of(cls):
    return CLASS_ROLE.get(cls, "N/M")          # an unknown or empty class counts as not decided (reported by the checks)


def nm_reason(role, detail):
    if role == "UND":
        return "atomization_mismatch"
    if role == "N/M":
        return "solver_unknown" if "solver unknown" in (detail or "") else "unsupported"
    return None


def load(tool_dir, units_path, ltl_path):
    sys.path.insert(0, os.path.join(tool_dir, "judging"))
    from nl2fret_judge import units as U                  # noqa: E402  (frozen tool code, read-only import)
    units = U.load_units(units_path, ltl_path, None)
    return U, units


def pairs_of(units):
    """-> list of (pair_id, unit, sentence index, sentence): the pairs that nl2fret_judge judge visits (parser ok and a past-time formula)"""
    out = []
    for u in units:
        for i, s in enumerate(u["sentences"]):
            if s["parser_ok"] and s["ltl_pt"]:
                out.append((f"{u['item']}|{u['arm']}|{u['rep']}|{i}", u, i, s))
    return out


def read_done(path):
    """pair ids already written; a partial last line (interrupted write) is cut off the file"""
    done = {}
    if not os.path.exists(path):
        return done
    raw = open(path, "rb").read()
    cut = raw.rfind(b"\n") + 1
    if cut != len(raw):
        with open(path, "r+b") as f:
            f.truncate(cut)
        raw = raw[:cut]
    for ln in raw.decode("utf-8").split("\n"):
        if ln.strip():
            done[json.loads(ln)["pair_id"]] = True
    return done


def cmd_run(a):
    sys.path.insert(0, os.path.join(a.tool_dir, "judging", "legacy"))
    import judge5                                          # noqa: E402  (legacy code, read-only import)
    U, units = load(a.tool_dir, a.units, a.ltl)
    refs = U.load_reference(os.path.join(a.tool_dir, "data", "reference", "lm_reference_with_ltl.jsonl"))
    items = sorted({u["item"] for u in units})
    mine = {it for k, it in enumerate(items) if (k % a.nshards) + 1 == a.shard}          # same rule as shard_units.py
    todo = [p for p in pairs_of(units) if p[1]["item"] in mine]
    if a.limit:
        todo = todo[:a.limit]
    done = read_done(a.out)
    n = 0
    t_start = time.time()
    with open(a.out, "a", encoding="utf-8") as f:
        for pid, u, i, s in todo:
            if pid in done:
                continue
            t0 = time.time()
            best, trials = None, []
            for ref_id, ref_pt, _ref_ft in refs.get(u["item"], []):
                try:
                    r = judge5.skeleton_compare(s["ltl_pt"], ref_pt)
                except Exception as e:                  # noqa: BLE001  (an exception of the legacy code or of z3 must not stop the run: the pair counts as not decided)
                    r = {"cls": "unsupported", "detail": "exception " + type(e).__name__ + ": " + str(e)[:60], "ngen": None, "nref": None}
                role = role_of(r.get("cls"))
                trials.append(r.get("cls"))
                rank = RANK[role]
                if best is None or rank < best[0]:
                    best = (rank, role, r, ref_id)
                if rank == 0:
                    break
            if best is None:
                continue                                    # the item has no reference part: best_over_references returns None, the judge writes no record either
            _, role, r, ref_id = best
            rec = {"pair_id": pid, "item": u["item"], "arm": u["arm"], "rep": u["rep"], "sentence_index": i, "cls": r.get("cls"), "skel_role": role,
                   "reason": nm_reason(role, r.get("detail")), "detail": r.get("detail") or None, "ngen": r.get("ngen"), "nref": r.get("nref"),
                   "gen_skel": r.get("gen_skel"), "ref_skel": r.get("ref_skel"), "reference_part": ref_id, "n_trials": len(trials), "trial_classes": trials,
                   "elapsed_sec": round(time.time() - t0, 3)}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            n += 1
            if n % 100 == 0:
                print(f"{n} pairs, {time.time() - t_start:.0f}s", flush=True)
    print(f"skeleton pairs written: {n} (already present: {len(done)}, pairs of this shard: {len(todo)})")
    return 0


def cmd_merge(a):
    _, units = load(a.tool_dir, a.units, a.ltl)
    order = {pid: k for k, (pid, _u, _i, _s) in enumerate(pairs_of(units))}
    rows, seen, problems = [], {}, []
    for part in a.parts:
        for ln in open(part, encoding="utf-8").read().split("\n"):
            if not ln.strip():
                continue
            rec = json.loads(ln)
            pid = rec["pair_id"]
            if pid not in order:
                problems.append(f"{pid}: belongs to no pair")
            elif pid in seen:
                problems.append(f"duplicate {pid} ({seen[pid]} and {part})")
            else:
                seen[pid] = part
                rows.append((order[pid], ln))
    if problems:
        print("NOT MERGED:", *problems[:20], sep="\n - ")
        return 1
    rows.sort(key=lambda x: x[0])
    with open(a.out, "w", encoding="utf-8") as f:
        for _, ln in rows:
            f.write(ln + "\n")
    print(f"merged {len(rows)} skeleton records of {len(order)} pairs (missing {len(order) - len(rows)}) into {a.out}")
    return 0


def main():
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest="cmd", required=True)
    r = sp.add_parser("run")
    r.add_argument("--tool-dir", required=True)
    for k in ("units", "ltl", "out"):
        r.add_argument("--" + k, required=True)
    r.add_argument("--shard", type=int, default=1)
    r.add_argument("--nshards", type=int, default=1)
    r.add_argument("--limit", type=int, default=0)
    r.set_defaults(f=cmd_run)
    m = sp.add_parser("merge")
    m.add_argument("--tool-dir", required=True)
    for k in ("units", "ltl", "out"):
        m.add_argument("--" + k, required=True)
    m.add_argument("--parts", nargs="+", required=True)
    m.set_defaults(f=cmd_merge)
    a = p.parse_args()
    return a.f(a)


if __name__ == "__main__":
    sys.exit(main())
