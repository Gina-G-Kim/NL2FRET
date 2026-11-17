#!/usr/bin/env python3
"""v3 generation with the Claude Code CLI (headless, subscription login) plus the official FRET parser as a syntax-only feedback source.

Arms: DIRECT, PARA (control: plain English rewrite + free stage B), <TPL> (stage A + free stage B), <TPL>+R (the same stage A + script parse + slot filling + script assembly), <TPL>+U (no-completion rules).  See prompts3.py.
One block = one repetition over every (item, arm). Inside a block the work runs in phases, so the official parser can be called in batches:
  phase A   stage A for every (item, template, rep)                       (shared by <TPL> and <TPL>+R)
  phase 1   DIRECT: stage D; <TPL>: stage B; <TPL>+R: parse by script, then stage S (slots)
  phase 2   round 0 -> official parser (batch) -> units with a rejected sentence get feedback call F1 -> parser -> F2 -> parser
Every call is appended to results/calls.jsonl with tokens and time. Nothing computed later (realizability, similarity, reference FRETish) is ever fed back.
Stopping and restarting is safe: rerun the same command (stage rows are keyed, finished keys are skipped).
"""
import argparse
import json
import os
import random
import shutil
import signal
import sys
from pathlib import Path

from nl2fret import cli
from nl2fret import fretparse
from nl2fret import prompts3 as P
from nl2fret import tpl_rules as T
from nl2fret import units3 as U
from nl2fret.cli import Ctx, append_jsonl, call_with_limits, iso, log, now, usage_fields, write_state
from nl2fret.common import ROOT, build_system, load_jsonl, parse_output, sha, user_prompt_A, user_prompt_B, user_prompt_D
from nl2fret.ext import DICTIONARY, parse as parse_ext
from nl2fret.ext.dictionary import attach as DICT_ATTACH


def base_row(item, arm, rep, stage, block):
    return {"stage_key": U.skey(item["id"], arm, rep, stage), "stage": stage, "item_id": item["id"], "stratum": item.get("stratum"), "family": item.get("family"),
            "arm": arm, "rep": rep, "block": block}


def call_stage(ctx, item, arm, rep, stage, block, system, user, hash_, spec_st, kind):
    """kind: A | B | S (parse rules). Appends one row; returns it (None on strict deadline)."""
    key = U.skey(item["id"], arm, rep, stage)
    t_start = now()
    res, obj, ok, attempts, waited = call_with_limits(ctx, system, user, key)
    if res is None:
        return None
    text = (obj or {}).get("result") if obj else None
    row = base_row(item, arm, rep, stage, block)
    row.update({"ts_start": iso(t_start), "ts_end": iso(now()), "wall_s": round(res["wall_s"], 3), "waited_s": round(waited, 1), "attempts": attempts,
                "model_arg": ctx.args.model or "", "cli_extra": ctx.args.cli_extra, "prompt_hash": hash_, "spec_status": spec_st, "user_prompt": user})
    row.update(usage_fields(obj))
    status, parsed, errs = "ok", None, []
    if not ok:
        status = "timeout" if res["timed_out"] else "cli_error"
        errs = [status]
    elif kind == "S":
        parsed, errs = P.parse_slot_output(text, ctx.n_sent_of(key))
        if parsed is None or errs:
            status = "parse_error"
    else:
        parsed, errs = parse_output(text, "A" if kind == "A" else "B")
        if parsed is None or any(e.startswith("schema_") for e in errs):
            status = "parse_error"
    row.update({"status": status, "errors": errs, "raw_result": text if text is not None else (res["stdout"][:2000] + res["stderr"][:500]),
                "parsed": parsed if status == "ok" else None})
    append_jsonl(ctx.calls_path, row)
    ctx.rows[row["stage_key"]] = row
    log(ctx, f"{row['stage_key']} status={status} tok={row.get('total_tokens')} wall={row['wall_s']}s waited={row['waited_s']}s")
    return row


# ------------------------------------------------------------------ phases
def comp_all(ctx):
    """compile results for every sentence known so far (cache file)."""
    return fretparse._load_cache(ctx.cache_path)


def do_compile(ctx, recs):
    need = []
    for r in recs:
        need += U.pending_compile(r)
    need = list(dict.fromkeys(need))
    if need:
        log(ctx, f"official parser ({ctx.args.parser}): {len(need)} new sentences")
        fretparse.compile_texts(need, ctx.args.parser, ctx.cache_path)


def units_state(ctx, items, arms, reps):
    comp = comp_all(ctx)
    return {(it["id"], a, r): U.derive(ctx.rows, it, a, r, comp) for it in items for a in arms for r in reps}


def sd_of(ctx, it, a):
    """dictionary text of the item's challenge (extension `dictionary`, ext/dictionary/attach.py) for the arms that get it, None for every other arm"""
    if not P.is_dict(a) or DICTIONARY not in ctx.exts:
        return None
    return DICT_ATTACH.prompt_block(it["challenge"])


def reuse_stage_a(ctx, src, items, arms, reps):
    """Copy ok stage A rows from an earlier run (same item, template, rep) when the stage A prompt hash is identical. Refuses a silent mismatch."""
    srcf = src / "calls.jsonl" if src.is_dir() else src
    if not srcf.exists():
        raise SystemExit(f"--stage-a-from: {srcf} not found")
    want = {(it["id"], t, r) for it in items for t in {P.akey(a) for a in arms if not P.is_direct(a)} for r in range(reps)}
    n_new = n_have = n_bad = 0
    for r in load_jsonl(srcf):
        if r.get("stage") != "A" or r.get("status") != "ok":
            continue
        k = (r["item_id"], r["arm"], int(r["rep"]))
        if k not in want:
            continue
        if r["stage_key"] in ctx.rows:
            n_have += 1
            continue
        cur = ctx.prompts.get(("A", r["arm"]))
        if cur is None or r.get("prompt_hash") != cur[1]:
            n_bad += 1
            continue
        row = dict(r)
        row["reused_from"] = str(srcf)
        append_jsonl(ctx.calls_path, row)
        ctx.rows[row["stage_key"]] = row
        n_new += 1
    log(ctx, f"stage A reuse from {srcf}: copied {n_new}, already present {n_have}, hash mismatch {n_bad}, wanted {len(want)}")
    if n_bad:
        raise SystemExit(f"--stage-a-from: {n_bad} stage A rows have a different prompt hash; the stage A prompt changed, reuse would not be a like-for-like comparison")


def phase_A(ctx, items, arms, reps, block, rnd):
    tpls = sorted({P.akey(a) for a in arms if not P.is_direct(a)})
    todo = [(it, t, r) for it in items for t in tpls for r in reps]
    rnd.shuffle(todo)
    for it, t, r in todo:
        key = U.skey(it["id"], t, r, "A")
        if key in ctx.rows and (ctx.rows[key]["status"] == "ok" or not ctx.args.retry_errors):
            continue
        sysp, hs, st = ctx.prompts[("A", t)]
        if call_stage(ctx, it, t, r, "A", block, sysp, user_prompt_A(it["raw_nl"]), hs, st, "A") is None:
            return False
    return True


def phase_first(ctx, items, arms, reps, block, rnd):
    todo = [(it, a, r) for it in items for a in arms for r in reps]
    rnd.shuffle(todo)
    for it, a, r in todo:
        st = U.first_stage(a)
        key = U.skey(it["id"], a, r, st)
        if key in ctx.rows and (ctx.rows[key]["status"] == "ok" or not ctx.args.retry_errors):
            continue
        if P.is_direct(a):
            sysp, hs, sp = ctx.prompts[("D", P.dkey(a))]
            row = call_stage(ctx, it, a, r, "D", block, sysp, user_prompt_D(it["raw_nl"], sd_of(ctx, it, a)), hs, sp, "B")
        else:
            arow = ctx.rows.get(U.skey(it["id"], a, r, "A"))
            if not arow or arow["status"] != "ok":
                continue
            sents = arow["parsed"]["sentences"]
            if P.is_rule(a):
                parses = [T.parse_template(P.base_of(a), s) for s in sents]
                if any(not p["ok"] for p in parses):
                    continue                       # recorded by units3 as a rule layer failure, no call
                reqs = [T.slot_requests(p, P.is_r2(a)) for p in parses]
                ctx.sent_counts[key] = len(sents)
                sysp, hs, sp = ctx.prompts[("S2" if P.is_r2(a) else "S", None)]
                row = call_stage(ctx, it, a, r, "S", block, sysp, P.user_prompt_S(parses, reqs, sd_of(ctx, it, a)), hs, sp, "S")
            else:
                sysp, hs, sp = ctx.prompts[("B", a)]
                row = call_stage(ctx, it, a, r, "B", block, sysp, user_prompt_B(P.base_of(a), sents, raw=it["raw_nl"] if ctx.args.stageb_sees_raw else None, sigdict=sd_of(ctx, it, a)), hs, sp, "B")
        if row is None:
            return False
    return True


def original_user(ctx, it, a, r, rec):
    if P.is_direct(a):
        return user_prompt_D(it["raw_nl"], sd_of(ctx, it, a))
    sents = rec["A"]["sentences"]
    if P.is_rule(a) and rec.get("fallback"):
        return user_prompt_B(P.base_of(a), sents, raw=None, sigdict=sd_of(ctx, it, a))
    if P.is_rule(a):
        return P.user_prompt_S(rec["parses"], rec["reqs"], sd_of(ctx, it, a))
    return user_prompt_B(P.base_of(a), sents, raw=it["raw_nl"] if ctx.args.stageb_sees_raw else None, sigdict=sd_of(ctx, it, a))


def phase_fallback(ctx, items, arms, reps, block, rnd):
    """v9 (no drop): a rule arm whose script layer cannot produce a sentence (template not readable, assembly failure) sends the template sentences through the free
    path with the rule text (the +G prompt), so that the content still reaches the official FRET parser. The failed rule attempt stays in the record (round 0)."""
    for _ in range(2):
        recs = units_state(ctx, items, arms, reps)
        by_id = {it["id"]: it for it in items}
        todo = [(k, rec) for k, rec in recs.items() if rec.get("fallback") and rec["pending"] and rec.get("A")]
        if not todo:
            return True
        rnd.shuffle(todo)
        log(ctx, f"rule layer fallback to the free path: {len(todo)} units")
        for (iid, a, r), rec in todo:
            key = U.skey(iid, a, r, "B")
            if key in ctx.rows and (ctx.rows[key]["status"] == "ok" or not ctx.args.retry_errors):
                continue
            it = by_id[iid]
            sysp, hs, sp = ctx.prompts[("BF", P.base_of(a))]
            userp = user_prompt_B(P.base_of(a), rec["A"]["sentences"], raw=None, sigdict=sd_of(ctx, it, a))
            if call_stage(ctx, it, a, r, "B", block, sysp, userp, hs, sp, "B") is None:
                return False
    return True


def history_of(rec):
    """the whole FRET feedback log of a unit so far: every attempt, the answer and the verdict per sentence (given to the model in full at every feedback call)"""
    hist = []
    for n, rr in enumerate(rec["rounds"], 1):
        note = ""
        if rec.get("fallback") and n == 1:
            note = f"the rule layer could not build a sentence from this input ({rec['fallback']['code']}); this attempt never reached the FRET parser"
        hist.append({"attempt": n, "stage": rr["stage"], "answer": (rr.get("row") or {}).get("raw_result") or "", "statuses": P.statuses_from_round(rr), "note": note})
    return hist


def phase_rounds(ctx, items, arms, reps, block, rnd):
    by_id = {it["id"]: it for it in items}
    for k in range(0, P.MAX_ROUNDS + 1):
        recs = units_state(ctx, items, arms, reps)
        do_compile(ctx, recs.values())
        recs = units_state(ctx, items, arms, reps)
        if k == P.MAX_ROUNDS:
            break
        targets = [(key, rec) for key, rec in recs.items() if rec.get("n_feedback", len(rec["rounds"]) - 1) == k and U.needs_feedback(rec)]
        rnd.shuffle(targets)
        log(ctx, f"feedback round {k + 1}: {len(targets)} units")
        for (iid, a, r), rec in targets:
            stage = f"F{k + 1}"
            key = U.skey(iid, a, r, stage)
            if key in ctx.rows and (ctx.rows[key]["status"] == "ok" or not ctx.args.retry_errors):
                continue
            it = by_id[iid]
            userp = P.user_prompt_feedback_log(original_user(ctx, it, a, r, rec), history_of(rec))
            if P.is_direct(a):
                sysp, hs, sp = ctx.prompts[("D", P.dkey(a))]
                kind = "B"
            elif P.is_rule(a) and rec.get("fallback"):
                sysp, hs, sp = ctx.prompts[("BF", P.base_of(a))]
                kind = "B"
            elif P.is_rule(a):
                sysp, hs, sp = ctx.prompts[("S2" if P.is_r2(a) else "S", None)]
                kind = "S"
                ctx.sent_counts[key] = len(rec["parses"])
            else:
                sysp, hs, sp = ctx.prompts[("B", a)]
                kind = "B"
            if call_stage(ctx, it, a, r, stage, block, sysp, userp, hs, sp, kind) is None:
                return False
    return True


def snapshot(ctx, items):
    from nl2fret import kc_stage as KC_
    snap = ctx.results / "snapshot"
    snap.mkdir(exist_ok=True)
    for (stage, tpl), (sp, hs, st) in ctx.prompts.items():
        if stage == "BF":       # the fallback prompt is the B prompt (+G) of the template: no file of its own; its hash stays in run_info.json under BF:<template>
            continue
        (snap / f"system_prompt_{stage}_{tpl or 'none'}.txt").write_text(sp, encoding="utf-8")
    for f in ROOT.glob("*.py"):
        shutil.copy(f, snap / f.name)
    for sub in ("templates", "prompts", "prompts/kc"):
        d = snap / sub
        d.mkdir(exist_ok=True)
        for f in (ROOT / sub).glob("*.md"):
            shutil.copy(f, d / f.name)
    dp = Path(ctx.args.data)
    shutil.copy(dp if dp.is_absolute() else ROOT / dp, snap / "items_used.jsonl")
    # record only: the slot annotation and the mapping review are never fed to the model
    for nm in ("lm_slot_annotation.jsonl", "lm_mapping_review.json"):
        fp = ROOT / "data" / nm
        if fp.exists():
            shutil.copy(fp, snap / nm)
    rules_hash = sha(open(ROOT / "tpl_rules.py", encoding="utf-8").read() + open(ROOT / "fretlint.py", encoding="utf-8").read(), 16)
    info = {"claude_version": cli.cli_version(ctx.args.claude_bin), "model_arg": ctx.args.model, "cli_extra": ctx.args.cli_extra,
            "prompt_hashes": {f"{s}:{t}": v[1] for (s, t), v in ctx.prompts.items()}, "rules_hash": rules_hash, "n_items": len(items), "arms": ctx.args.arms,
            "seed": ctx.args.seed, "reps": ctx.args.reps, "block": ctx.args.block, "parser": ctx.args.parser, "max_rounds": P.MAX_ROUNDS,
            "stageb_sees_raw": ctx.args.stageb_sees_raw, "no_kc": bool(getattr(ctx.args, "no_kc", False)), "kc_doc_sha": KC_.doc_sha(), "dict_all": bool(ctx.args.dict_all), "guide_sup": bool(ctx.args.guide_sup), "fret_reference": bool(ctx.args.fret_reference), "g_parity": bool(ctx.args.g_parity), "intent_decl": bool(ctx.args.intent_decl), "tm_source_only": bool(ctx.args.tm_source_only), "sourced_rules_only": bool(ctx.args.sourced_rules_only), "stage_a_from": ctx.args.stage_a_from, "python": sys.version.split()[0]}
    (snap / "run_info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
    return rules_hash


def check_flags(state, run_flags):
    """The prompt/assembly flags are fixed at the first start of a run; a resume with other flags would mix two prompt versions in one run.
    A run started before this check has no stored flags: they are recorded now (nothing to compare)."""
    if state.setdefault("flags", run_flags) != run_flags:
        raise SystemExit(f"flags changed since the first start of this run: first {state['flags']}, now {run_flags}. Resume with the same flags or use a new --results folder.")


def build_prompts(ctx):
    pr = {}
    tpls = sorted({P.akey(a) for a in ctx.args.arms if not P.is_direct(a)})
    for t in tpls:
        sp, st = P.build_system_A3(t)
        pr[("A", t)] = (sp, sha(sp), st)
    for a in ctx.args.arms:
        if P.is_direct(a):
            sp, st = P.build_system_D3(a)
            pr[("D", P.dkey(a))] = (sp, sha(sp), st)
        elif P.is_rule(a):
            sp = P.slot_system_r2() if P.is_r2(a) else P.SLOT_SYSTEM
            if P.INTENT_DECL and P.is_r2(a):     # v1.4: the script fixes the condition keywords; the intent can only act on the model-answered tm slot
                sp = sp.rstrip() + "\n\n" + P.intent_declaration() + "\n"
            if P.is_dict(a):
                sp = sp.rstrip() + "\n" + (P.SLOT_D_RULES_V15 if P.FRET_REFERENCE else P.SLOT_D_RULES) + "\n"
            pr[("S2" if P.is_r2(a) else "S", None)] = (sp, sha(sp), {"slots": "bench_rules_v7_timing_slot" if P.is_r2(a) else "bench_rules"})
            fb, fst = P.build_system_B3(P.base_of(a) + P.GUIDE_SUFFIX)     # fallback of the rule arm: the B prompt (+G) of the same template, byte identical, no file of its own (the stage name BF stays in the call records)
            pr[("BF", P.base_of(a))] = (fb, sha(fb), dict(fst, fallback_of="rule_assembly"))
        else:
            sp, st = P.build_system_B3(a)
            pr[("B", a)] = (sp, sha(sp), st)
    return pr


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default="data/lm_items.jsonl")
    ap.add_argument("--results", default="results_nl3")
    ap.add_argument("--arms", nargs="+", default=P.ARMS_V6, help="default: the 13 arms of the v6 main run (DIRECT, PARA control, 4 free templates, 4 +R, DIRECT+V, MASTeR+V, EARS+V); the +G arms, the +U arms and the other +V arms are optional (second run of the same results folder)")
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--block", type=int, default=1)
    ap.add_argument("--hours", type=float, default=20.0)
    ap.add_argument("--strict-deadline", action="store_true")
    ap.add_argument("--reset-clock", action="store_true")
    ap.add_argument("--parser", default="docker", choices=["docker", "node", "mock"], help="official FRET parser: docker image fret-lab (the experiment), a local node copy (sandbox tests, see fret_compile.compile_list_node) or the mock parser (offline test only)")
    ap.add_argument("--claude-bin", default=os.environ.get("CLAUDE_BIN", "claude"))
    ap.add_argument("--model", default=os.environ.get("BENCH_MODEL", ""))
    ap.add_argument("--cli-extra", default=os.environ.get("BENCH_CLI_EXTRA", ""))
    ap.add_argument("--call-timeout", type=int, default=900)
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--probe-interval", type=int, default=600)
    ap.add_argument("--probe-max", type=int, default=1800)
    ap.add_argument("--reset-margin", type=int, default=60)
    ap.add_argument("--max-probe-errors", type=int, default=30)
    ap.add_argument("--only-id", nargs="*", default=None)
    ap.add_argument("--limit-items", type=int, default=None)
    ap.add_argument("--seed", type=int, default=20261029)
    ap.add_argument("--retry-errors", action="store_true")
    ap.add_argument("--stageb-sees-raw", action="store_true", help="ABLATION, off by default")
    ap.add_argument("--intent-decl", action="store_true", help="v1.4: append the NASA-sourced intent declaration (prompts/intent_declaration.md) to the FRETish prompts of Direct and the free arms (diagnostic condition)")
    ap.add_argument("--g-parity", action="store_true", help="v1.4: omit rule R-DEFTIME from the +G rule text (rule parity with +R2, where timing is a model-filled slot)")
    ap.add_argument("--fret-reference", action="store_true", help="v1.5: add the complete official FRET field documents (prompts/fretish_reference.md, built verbatim by tools/build_fretish_reference.py) to every FRETish prompt and the expression sections to the +R2 slot prompt")
    ap.add_argument("--guide-sup", action="store_true", help="v1.4: add the official FRET semantics supplement (prompts/fretish_guide_supplement.md) and dictionary rule D-5 to the FRETish prompts of Direct and the free arms")
    ap.add_argument("--dict-all", action="store_true", help="old name of `--ext dictionary`: every arm gets the signal dictionary of its challenge at the FRETish stage")
    ap.add_argument("--ext", nargs="*", default=[], help="extension modules (bench/ext/): dictionary. None given = no extension (no dictionary block in the prompts)")
    ap.add_argument("--tm-source-only", action="store_true", help="v1.4: the +R2 timing slot prompt keeps documentation facts only; the bench-authored selection procedure V-2/V-3 is removed")
    ap.add_argument("--sourced-rules-only", action="store_true", help="v1.4: the tool maps a template phrase only where the mapping has a source (official document or official parser check); other phrases go to the model (assembly refuses, free path)")
    ap.add_argument("--stage-a-from", help="v1.4: reuse the stage A (template conversion) rows of an earlier run folder, so that a version comparison differs only in the stages after A. "
                    "A row is reused only if its prompt hash equals the current stage A prompt hash; reused rows are copied into this run with reused_from set")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    exts = parse_ext(args.ext, args.dict_all)
    args.dict_all = DICTIONARY in exts          # the run record keeps the key dict_all
    P.DICT_ALL = args.dict_all
    P.GUIDE_SUP = bool(args.guide_sup)
    P.FRET_REFERENCE = bool(args.fret_reference)
    from nl2fret import common as _C
    _C.TPL_V15 = bool(P.FRET_REFERENCE)
    T.SLOT_KW = bool(P.FRET_REFERENCE)
    P.G_PARITY = bool(args.g_parity)
    P.INTENT_DECL = bool(args.intent_decl)
    P.TM_SOURCE_ONLY = bool(args.tm_source_only)
    P.SOURCED_ONLY = T.SOURCED_ONLY = bool(args.sourced_rules_only)
    T.INTENT_COND = bool(args.intent_decl)
    ctx = Ctx()
    ctx.args = args
    ctx.results = Path(args.results) if Path(args.results).is_absolute() else ROOT / args.results
    ctx.results.mkdir(parents=True, exist_ok=True)
    ctx.calls_path = ctx.results / "calls.jsonl"
    ctx.cache_path = str(ctx.results / "parser_cache.jsonl")
    dp = Path(args.data) if Path(args.data).is_absolute() else ROOT / args.data
    items = load_jsonl(dp)
    if args.only_id:
        items = [r for r in items if r["id"] in set(args.only_id)]
    if args.limit_items:
        items = items[:args.limit_items]
    if not items:
        raise SystemExit("no items loaded")
    for a in args.arms:
        if a not in P.ARMS3:
            raise SystemExit(f"unknown arm {a}; choose from {P.ARMS3}")
    ctx.prompts = build_prompts(ctx)
    ctx.exts = exts
    if any(P.is_dict(a) for a in args.arms):
        if DICTIONARY not in exts:
            raise SystemExit("+D arms need the extension: pass --ext dictionary")
        miss = DICT_ATTACH.missing(items)
        if miss:
            raise SystemExit(f"+D arms need a signal dictionary for every item; none for: {miss}")
    ctx.sent_counts = {}
    ctx.n_sent_of = lambda key: ctx.sent_counts.get(key, 1)
    n_units = len(items) * len(args.arms) * args.reps
    if args.dry_run:
        print(f"{len(items)} items x {len(args.arms)} arms x {args.reps} reps = {n_units} units")
        for k in sorted(ctx.prompts, key=str):
            print(f"--- system prompt {k} ({len(ctx.prompts[k][0])} chars, hash {ctx.prompts[k][1]}) ---")
        print(ctx.prompts[("A", P.TPLS[0])][0][-900:])
        return
    rules_hash = snapshot(ctx, items)
    state_path = ctx.results / "run_state.json"
    ctx.state = {}
    prev_arms = []
    if state_path.exists():
        try:
            prev_arms = json.loads(state_path.read_text(encoding="utf-8")).get("arms", [])
        except Exception:
            prev_arms = []
    if state_path.exists() and not args.reset_clock:
        try:
            ctx.state = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            ctx.state = {}
    run_flags = {k: bool(getattr(args, k, False)) for k in ("dict_all", "guide_sup", "fret_reference", "g_parity", "intent_decl", "tm_source_only", "sourced_rules_only")}
    if "start_epoch" not in ctx.state or args.reset_clock:
        ctx.state = {"start_epoch": now(), "start_iso": iso(now()), "resumes": 0, "rules_hash": rules_hash, "flags": run_flags}
    else:
        ctx.state["resumes"] = ctx.state.get("resumes", 0) + 1
        # the prompt/assembly flags are fixed at the first start of a run; a resume with other flags would mix two prompt versions in one run (a run started before this check has no stored flags: they are recorded now)
        check_flags(ctx.state, run_flags)
        if ctx.state.get("rules_hash") != rules_hash:
            raise SystemExit("tpl_rules.py / fretlint.py changed since the first start of this run (rules are frozen once a run has started). "
                             "Use a new --results folder or --reset-clock after a conscious decision.")
    ctx.deadline = ctx.state["start_epoch"] + args.hours * 3600
    ctx.state.update({"deadline_iso": iso(ctx.deadline), "hours_limit": args.hours, "reps": args.reps, "block": args.block,
                      "arms": [x for x in P.ARMS3 if x in set(prev_arms) | set(args.arms)], "n_items": len(items)})
    ctx.rows = {}
    for r in load_jsonl(ctx.calls_path):
        ctx.rows[r["stage_key"]] = r
    if args.stage_a_from:
        reuse_stage_a(ctx, Path(args.stage_a_from), items, args.arms, args.reps)

    def _sig(*_):
        cli.STOP["flag"] = True
    signal.signal(signal.SIGINT, _sig)
    signal.signal(signal.SIGTERM, _sig)

    log(ctx, f"start: {len(items)} items x {len(args.arms)} arms x {args.reps} reps; parser={args.parser}; stage rows already done {len(ctx.rows)}; rules_hash {rules_hash}")
    write_state(ctx, status="running")
    exit_status = "finished_all"
    try:
        for b0 in range(0, args.reps, args.block):
            if now() >= ctx.deadline:
                exit_status = "stopped_deadline"
                break
            last_dur = ctx.state.get("last_block_active_s")
            if last_dur and now() + last_dur > ctx.deadline:
                exit_status = "stopped_projection"
                break
            reps = list(range(b0, min(b0 + args.block, args.reps)))
            blk = b0 // args.block
            rnd = random.Random(args.seed + b0)
            t0, w0 = now(), ctx.state.get("waited_total_s", 0.0)
            ok = phase_A(ctx, items, args.arms, reps, blk, rnd) and phase_first(ctx, items, args.arms, reps, blk, rnd) and phase_fallback(ctx, items, args.arms, reps, blk, rnd) and phase_rounds(ctx, items, args.arms, reps, blk, rnd)
            if not ok:
                exit_status = "stopped_deadline"
                break
            log(ctx, f"block {blk} (reps {reps}) complete")
            ctx.state["last_block_active_s"] = max(0.0, (now() - t0) - (ctx.state.get("waited_total_s", 0.0) - w0))
            write_state(ctx, blocks_completed=blk + 1, stage_rows_done=len(ctx.rows))
    except KeyboardInterrupt:
        exit_status = "interrupted"
        log(ctx, "interrupted; progress is saved, rerun the same command to resume")
    write_state(ctx, status=exit_status, end_iso=iso(now()), elapsed_since_first_start_h=round((now() - ctx.state["start_epoch"]) / 3600, 3))
    log(ctx, f"end: {exit_status}")
    sys.exit(0 if exit_status in ("finished_all", "stopped_deadline", "stopped_projection") else 130)


if __name__ == "__main__":
    main()
