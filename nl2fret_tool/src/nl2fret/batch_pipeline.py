#!/usr/bin/env python3
"""v2.0 generation: one isolated agent per (approach, challenge, repetition) instead of one call per sentence.

Agent scope
  DIRECT           one agent: every requirement of the challenge -> FRETish (FRETish guide)
  <TPL>+G          one agent per template: requirement -> template sentence -> FRETish (template specification and FRETish guide)
  <TPL>+R2         the same scope; the script assembles the FRETish sentence from the slots the agent filled
The template stage A of one (template, challenge, repetition) is one call that both +G and +R2 continue from (the two arms differ only after the template sentences).
An "agent call" is one fresh claude CLI process (agent_call.py: whitelisted environment, empty working directory, no tools, no session, JSON schema answer). Nothing is remembered
between two calls except what the script writes into the next user message (the same rule as before: previous answers and the FRET parser verdicts of the feedback log).
Every call answers all items of its group: {"results": [{"id": ..., "answer": <the per-item answer object of the stage>}]}. Each answer is stored as one stage row in calls.jsonl, in the
format of run_pipeline.py, so units3.derive, make_judge_inputs.py and the analysis tools read a batch run unchanged. Raw batch replies and usage are in batch_calls.jsonl.
Items that are missing from a reply are requested again once (the same for every approach); a reply that declines to write any FRETish is status ok with an empty list (code no_output),
not a parse error.
"""
import argparse
import json
import os
import random
import signal
import sys
from pathlib import Path

from nl2fret import agent_call as AC
from nl2fret import cli
from nl2fret import prompts3 as P
from nl2fret import tpl_rules as T
from nl2fret import units3 as U
from nl2fret import run_pipeline as RP
from nl2fret import rt_stage as RT
from nl2fret import kc_stage as KC
from nl2fret.cli import Ctx, append_jsonl, call_with_limits, iso, log, now, usage_fields, write_state
from nl2fret.common import ROOT, load_jsonl, parse_output, sha, sigdict_block, user_prompt_A, user_prompt_B, user_prompt_D
from nl2fret.ext import DICTIONARY, parse as parse_ext
from nl2fret.ext.dictionary import attach as DICT_ATTACH

BATCH_RULES = """
BATCH
The user message holds several items of one software component. Each item starts with a line "### id: <id>" followed by its input.
Reply with exactly one JSON object {"results": [{"id": "<id>", "answer": <the JSON object defined above for one item>}]} with one entry for every id of the user message, in the order of the user message."""


def batch_system(sysp):
    return sysp.rstrip() + "\n" + BATCH_RULES + "\n"


def sd_challenge(ctx, it, a):
    return RP.sd_of(ctx, it, a)


def block_text(tasks, sigtext):
    if tasks and tasks[0]["stage"] == KC.KC_STAGE:
        return KC.block_text(tasks, sigtext, sigdict_block)
    out = [f"ITEMS: {len(tasks)}", ""]
    for t in tasks:
        out.append(f"### id: {t['it']['id']}")
        out.append(t["body"].rstrip())
        out.append("")
    if sigtext:
        out.append(sigdict_block(sigtext).strip("\n"))
    return "\n".join(out).rstrip() + "\n"


def mk_task(it, arm, rep, stage, kind, sysp, hs, sp, body, block, sigtext, extra=None):
    return {"it": it, "arm": arm, "rep": rep, "stage": stage, "kind": kind, "key": U.skey(it["id"], arm, rep, stage), "sysp": sysp, "hs": hs, "sp": sp, "body": body,
            "block": block, "sig": sigtext, "extra": extra or {}}


# ------------------------------------------------------------------ rows
def declined(kind, errs, answer):
    return isinstance(answer, dict) and ((kind in ("B",) and errs == ["schema_fretish"]) or (kind == "A" and errs == ["schema_sentences"]))


def build_row(ctx, t, brec, answer, miss_reason=None):
    it = t["it"]
    row = RP.base_row(it, t["arm"], t["rep"], t["stage"], t["block"])
    row.update({"ts_start": brec["ts_start"], "ts_end": brec["ts_end"], "wall_s": brec["wall_s"], "waited_s": brec["waited_s"], "attempts": brec["attempts"],
                "model_arg": ctx.args.model or "", "cli_extra": ctx.args.cli_extra, "prompt_hash": brec["system_hash"], "spec_status": t["sp"], "user_prompt": t["body"],
                "batch_id": brec["batch_id"], "batch_size": brec["n"], "batch_pos": brec["order"].index(it["id"]) + 1,
                "input_tokens": None, "output_tokens": None, "total_tokens": None, "cost_usd": None})
    text = json.dumps(answer, ensure_ascii=False) if isinstance(answer, dict) else None
    status, parsed, errs = "ok", None, []
    if answer is None:
        status, errs = ("timeout" if brec.get("timed_out") else "cli_error") if brec.get("failed") else "parse_error", [miss_reason or "batch_missing"]
    elif t["kind"] == "S":
        parsed, errs = P.parse_slot_output(text, ctx.n_sent_of(t["key"]))
        if parsed is None or errs:
            status = "parse_error"
    else:
        parsed, errs = parse_output(text, "A" if t["kind"] == "A" else "B")
        if declined(t["kind"], errs, answer):
            status, errs = ("ok", ["declined"]) if t["kind"] == "B" else ("declined", ["declined"])
        elif parsed is None or any(e.startswith("schema_") for e in errs):
            status = "parse_error"
    row.update({"status": status, "errors": errs, "raw_result": text if text is not None else (brec.get("raw", "")[:1500]), "parsed": parsed if status == "ok" else None})
    row.update({k: v for k, v in (t.get("extra") or {}).items() if k == "kc_groups"})        # keyword check step: the groups of every sentence that the message listed
    return row


def run_group(ctx, tasks, rnd):
    """One agent call for all tasks of a group; the items missing from the reply are asked once more. Writes one stage row per task."""
    first = tasks[0]
    sysp = batch_system(first["sysp"])
    hs = sha(sysp)
    todo = list(tasks)
    rnd.shuffle(todo)
    attempts_left = 1 + ctx.args.batch_retries
    answers, brecs = {}, []
    while todo and attempts_left > 0:
        attempts_left -= 1
        order = [t["it"]["id"] for t in todo]
        user = block_text(todo, first["sig"])
        bid = f"{first['stage']}|{first['it']['challenge']}|{first['arm'] if first['stage'] != 'A' else U.akey(first['arm'])}|{first['rep']}|{hs[:8]}|{len(brecs)}"
        t_start = now()
        res, obj, ok, attempts, waited = call_with_limits(ctx, sysp, user, bid)
        if res is None:
            return False
        ans = AC.answer_object(obj) if ok else None
        got = {}
        for r in (ans or {}).get("results") or []:
            if isinstance(r, dict) and isinstance(r.get("id"), str) and isinstance(r.get("answer"), dict) and r["id"] in order and r["id"] not in got:
                got[r["id"]] = r["answer"]
        brec = {"batch_id": bid, "stage": first["stage"], "challenge": first["it"]["challenge"], "rep": first["rep"], "system_hash": hs, "n": len(todo), "order": order, "n_answered": len(got),
                "ts_start": iso(t_start), "ts_end": iso(now()), "wall_s": round(res["wall_s"], 3), "waited_s": round(waited, 1), "attempts": attempts, "failed": not ok,
                "timed_out": res["timed_out"], "raw": (obj or {}).get("result") if obj else (res["stdout"][:2000] + res["stderr"][:500]), "user_prompt": user}
        brec.update(usage_fields(obj))
        append_jsonl(ctx.results / "batch_calls.jsonl", brec)
        log(ctx, f"{bid} answered {len(got)}/{len(todo)} tok={brec.get('total_tokens')} wall={brec['wall_s']}s")
        brecs.append(brec)
        for t in todo:
            if t["it"]["id"] in got:
                answers[t["key"]] = (got[t["it"]["id"]], brec)
        todo = [t for t in todo if t["key"] not in answers]
    for t in tasks:
        if t["key"] in answers:
            ans, brec = answers[t["key"]]
            row = build_row(ctx, t, brec, ans)
        else:
            row = build_row(ctx, t, brecs[-1], None)
        append_jsonl(ctx.calls_path, row)
        ctx.rows[row["stage_key"]] = row
    return True


def execute(ctx, tasks, rnd):
    """group the tasks (same system prompt, challenge, repetition), run the groups in a seeded random order"""
    groups = {}
    for t in tasks:
        groups.setdefault((t["hs"], t["it"]["challenge"], t["rep"], t["stage"]), []).append(t)
    keys = sorted(groups)
    rnd.shuffle(keys)
    for k in keys:
        g = groups[k]
        if not run_group(ctx, g, rnd):
            return False
    return True


def pending(ctx, key):
    r = ctx.rows.get(key)
    return not (r is not None and (r["status"] in ("ok", "declined") or not ctx.args.retry_errors))


# ------------------------------------------------------------------ phases (the same state machine as run_pipeline.py, emitting tasks)
def phase_A(ctx, items, arms, reps, block, rnd):
    tpls = sorted({P.akey(a) for a in arms if not P.is_direct(a)})
    tasks = []
    for it in items:
        for t in tpls:
            for r in reps:
                key = U.skey(it["id"], t, r, "A")
                if not pending(ctx, key):
                    continue
                sysp, hs, st = ctx.prompts[("A", t)]
                tasks.append(mk_task(it, t, r, "A", "A", sysp, hs, st, user_prompt_A(it["raw_nl"]), block, None))
    return execute(ctx, tasks, rnd)


def phase_first(ctx, items, arms, reps, block, rnd):
    tasks = []
    for it in items:
        for a in arms:
            for r in reps:
                st = U.first_stage(a)
                key = U.skey(it["id"], a, r, st)
                if not pending(ctx, key):
                    continue
                sig = RP.sd_of(ctx, it, a)
                if P.is_direct(a):
                    sysp, hs, sp = ctx.prompts[("D", P.dkey(a))]
                    tasks.append(mk_task(it, a, r, "D", "B", sysp, hs, sp, user_prompt_D(it["raw_nl"], None), block, sig))
                    continue
                arow = ctx.rows.get(U.skey(it["id"], a, r, "A"))
                if not arow or arow["status"] != "ok":
                    continue
                sents = arow["parsed"]["sentences"]
                if P.is_rule(a):
                    parses = [T.parse_template(P.base_of(a), s) for s in sents]
                    if any(not p["ok"] for p in parses):
                        continue
                    reqs = [T.slot_requests(p, P.is_r2(a)) for p in parses]
                    ctx.sent_counts[key] = len(sents)
                    sysp, hs, sp = ctx.prompts[("S2" if P.is_r2(a) else "S", None)]
                    tasks.append(mk_task(it, a, r, "S", "S", sysp, hs, sp, P.user_prompt_S(parses, reqs, None), block, sig))
                else:
                    sysp, hs, sp = ctx.prompts[("B", a)]
                    tasks.append(mk_task(it, a, r, "B", "B", sysp, hs, sp, user_prompt_B(P.base_of(a), sents, raw=it["raw_nl"] if ctx.args.stageb_sees_raw else None, sigdict=None), block, sig))
    return execute(ctx, tasks, rnd)


def original_body(ctx, it, a, r, rec):
    if P.is_direct(a):
        return user_prompt_D(it["raw_nl"], None)
    sents = rec["A"]["sentences"]
    if P.is_rule(a) and rec.get("fallback"):
        return user_prompt_B(P.base_of(a), sents, raw=None, sigdict=None)
    if P.is_rule(a):
        return P.user_prompt_S(rec["parses"], rec["reqs"], None)
    return user_prompt_B(P.base_of(a), sents, raw=it["raw_nl"] if ctx.args.stageb_sees_raw else None, sigdict=None)


def phase_fallback(ctx, items, arms, reps, block, rnd):
    for _ in range(2):
        recs = RP.units_state(ctx, items, arms, reps)
        by_id = {it["id"]: it for it in items}
        todo = [(k, rec) for k, rec in recs.items() if rec.get("fallback") and rec["pending"] and rec.get("A")]
        if not todo:
            return True
        tasks = []
        for (iid, a, r), rec in todo:
            key = U.skey(iid, a, r, "B")
            if not pending(ctx, key):
                continue
            it = by_id[iid]
            sysp, hs, sp = ctx.prompts[("BF", P.base_of(a))]
            tasks.append(mk_task(it, a, r, "B", "B", sysp, hs, sp, user_prompt_B(P.base_of(a), rec["A"]["sentences"], raw=None, sigdict=None), block, RP.sd_of(ctx, it, a)))
        log(ctx, f"rule layer fallback to the free path: {len(tasks)} units")
        if not execute(ctx, tasks, rnd):
            return False
    return True


def phase_rounds(ctx, items, arms, reps, block, rnd):
    by_id = {it["id"]: it for it in items}
    for k in range(0, P.MAX_ROUNDS + 1):
        recs = RP.units_state(ctx, items, arms, reps)
        RP.do_compile(ctx, recs.values())
        recs = RP.units_state(ctx, items, arms, reps)
        if k == P.MAX_ROUNDS:
            break
        targets = [(key, rec) for key, rec in recs.items() if rec.get("n_feedback", len(rec["rounds"]) - 1) == k and U.needs_feedback(rec)]
        log(ctx, f"feedback round {k + 1}: {len(targets)} units")
        tasks = []
        for (iid, a, r), rec in targets:
            stage = f"F{k + 1}"
            key = U.skey(iid, a, r, stage)
            if not pending(ctx, key):
                continue
            it = by_id[iid]
            body = P.user_prompt_feedback_log(original_body(ctx, it, a, r, rec), RP.history_of(rec))
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
            tasks.append(mk_task(it, a, r, stage, kind, sysp, hs, sp, body, block, RP.sd_of(ctx, it, a)))
        if not execute(ctx, tasks, rnd):
            return False
    return True


def _stage_prompt(ctx, a, rec):
    """system prompt, hash, status and parse kind of the stages after the feedback (keyword check, round trip): the prompt of the first stage of the unit"""
    if P.is_direct(a):
        sysp, hs, sp = ctx.prompts[("D", P.dkey(a))]
        return sysp, hs, sp, "B"
    if P.is_rule(a) and rec.get("fallback"):
        sysp, hs, sp = ctx.prompts[("BF", P.base_of(a))]
        return sysp, hs, sp, "B"
    if P.is_rule(a):
        sysp, hs, sp = ctx.prompts[("S2" if P.is_r2(a) else "S", None)]
        return sysp, hs, sp, "S"
    sysp, hs, sp = ctx.prompts[("B", a)]
    return sysp, hs, sp, "B"


def phase_kc(ctx, items, arms, reps, block, rnd):
    """keyword check (kc_stage.py): the units whose answer the parser accepted in full get the keyword groups of their sentences and the reference text of those groups and answer once more.
    A batch in which no sentence has a group is skipped."""
    recs = RP.units_state(ctx, items, arms, reps)
    targets = [(key, rec) for key, rec in recs.items() if RT.applicable(rec)]
    texts = [t for _, rec in targets for t in RT.last_texts(rec)]
    fl = KC.fields(texts, ctx.args.parser, str(ctx.results / "kc_fields.jsonl")) if texts else {}
    by_id = {it["id"]: it for it in items}
    tasks, skipped = [], 0
    for (iid, a, r), rec in targets:
        key = U.skey(iid, a, r, KC.KC_STAGE)
        if not pending(ctx, key):
            continue
        it = by_id[iid]
        pl = KC.plan(iid, original_body(ctx, it, a, r, rec), RT.last_texts(rec), fl)
        if pl is None:
            skipped += 1
            continue
        body, groups = pl
        sysp, hs, sp, kind = _stage_prompt(ctx, a, rec)
        if kind == "S":
            ctx.sent_counts[key] = len(rec["parses"])
        names = sorted({g["group"] for gs in groups for g in gs})
        tasks.append(mk_task(it, a, r, KC.KC_STAGE, kind, sysp, hs, sp, body, block, RP.sd_of(ctx, it, a), {"kc_groups": groups, "kc_group_names": names}))
    log(ctx, f"keyword check: {len(targets)} units, {len(tasks)} calls to make, {skipped} units without a group (kc_skipped)")
    return execute(ctx, tasks, rnd)


def phase_rt(ctx, items, arms, reps, block, rnd):
    """round trip (rt_stage.py): the units whose answer the parser accepted in full get FRET's English description of every sentence and answer once more. The answer that the round trip starts from is
    the keyword check answer when it was adopted, else the answer after the parser feedback."""
    chain = KC.chain(ctx.rows, items, arms, reps, ctx.args.parser, ctx.cache_path)
    recs = {k: v["in"] for k, v in chain.items()}
    targets = [(key, rec) for key, rec in recs.items() if RT.applicable(rec)]
    texts = [t for _, rec in targets for t in RT.last_texts(rec)]
    descs = RT.descriptions(texts, ctx.args.parser, str(ctx.results / "descriptions.jsonl")) if texts else {}
    by_id = {it["id"]: it for it in items}
    log(ctx, f"round trip: {len(targets)} units")
    tasks = []
    for (iid, a, r), rec in targets:
        key = U.skey(iid, a, r, RT.RT_STAGE)
        if not pending(ctx, key):
            continue
        it = by_id[iid]
        sysp, hs, sp, kind = _stage_prompt(ctx, a, rec)
        if kind == "S":
            ctx.sent_counts[key] = len(rec["parses"])
        tasks.append(mk_task(it, a, r, RT.RT_STAGE, kind, sysp, hs, sp, RT.body(original_body(ctx, it, a, r, rec), rec, descs), block, RP.sd_of(ctx, it, a)))
    return execute(ctx, tasks, rnd)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default="data/lm_items.jsonl")
    ap.add_argument("--results", default="results_batch")
    ap.add_argument("--arms", nargs="+", default=P.ARMS_FSM)
    ap.add_argument("--reps", type=int, default=3)
    ap.add_argument("--block", type=int, default=1)
    ap.add_argument("--hours", type=float, default=20.0)
    ap.add_argument("--strict-deadline", action="store_true")
    ap.add_argument("--reset-clock", action="store_true")
    ap.add_argument("--parser", default="docker", choices=["docker", "node", "mock"])
    ap.add_argument("--claude-bin", default=os.environ.get("CLAUDE_BIN", "claude"))
    ap.add_argument("--model", default=os.environ.get("BENCH_MODEL", ""))
    ap.add_argument("--cli-extra", default=os.environ.get("BENCH_CLI_EXTRA", ""))
    ap.add_argument("--env-pass", nargs="*", default=[], help="extra environment variable names the agent process may inherit (login or proxy setup of this computer)")
    ap.add_argument("--call-timeout", type=int, default=1500)
    ap.add_argument("--max-attempts", type=int, default=3)
    ap.add_argument("--batch-retries", type=int, default=1, help="how many times the items missing from a reply are requested again (the same for every approach)")
    ap.add_argument("--probe-interval", type=int, default=600)
    ap.add_argument("--probe-max", type=int, default=1800)
    ap.add_argument("--reset-margin", type=int, default=60)
    ap.add_argument("--max-probe-errors", type=int, default=30)
    ap.add_argument("--only-challenge", nargs="*", default=None)
    ap.add_argument("--only-id", nargs="*", default=None)
    ap.add_argument("--limit-items", type=int, default=None)
    ap.add_argument("--seed", type=int, default=20261116)
    ap.add_argument("--retry-errors", action="store_true")
    ap.add_argument("--stageb-sees-raw", action="store_true", help="ABLATION, off by default: stage B also sees the original requirement")
    ap.add_argument("--intent-decl", action="store_true")
    ap.add_argument("--g-parity", action="store_true")
    ap.add_argument("--fret-reference", action="store_true")
    ap.add_argument("--guide-sup", action="store_true")
    ap.add_argument("--dict-all", action="store_true", help="old name of `--ext dictionary`")
    ap.add_argument("--ext", nargs="*", default=[], help="extension modules (bench/ext/): dictionary. None given = no extension (no dictionary block in the prompts)")
    ap.add_argument("--tm-source-only", action="store_true")
    ap.add_argument("--sourced-rules-only", action="store_true")
    ap.add_argument("--no-rt", action="store_true", help="debugging only: skip the round trip step")
    ap.add_argument("--no-kc", action="store_true", help="skip the keyword check step KC (kc_stage.py); on by default")
    ap.add_argument("--skip-probe", action="store_true", help="debugging only; the probe result is part of the run record")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    args.stage_a_from = None

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
    if args.only_challenge:
        items = [r for r in items if r["challenge"] in set(args.only_challenge)]
    if args.only_id:
        items = [r for r in items if r["id"] in set(args.only_id)]
    if args.limit_items:
        items = items[:args.limit_items]
    if not items:
        raise SystemExit("no items loaded")
    for a in args.arms:
        if a not in P.ARMS3:
            raise SystemExit(f"unknown arm {a}; choose from {P.ARMS3}")
    ctx.prompts = RP.build_prompts(ctx)
    ctx.exts = exts
    if any(P.is_dict(a) for a in args.arms) or args.dict_all:
        if DICTIONARY not in exts:
            raise SystemExit("+D arms need the extension: pass --ext dictionary")
        miss = DICT_ATTACH.missing(items)
        if miss:
            raise SystemExit(f"the dictionary arms need a signal dictionary for every item; none for: {miss}")
    ctx.sent_counts = {}
    ctx.n_sent_of = lambda key: ctx.sent_counts.get(key, 1)
    chal = sorted({it["challenge"] for it in items})
    n_groups = len(chal) * (len(args.arms) + len({P.akey(a) for a in args.arms if not P.is_direct(a)})) * args.reps
    if args.dry_run:
        print(f"{len(items)} items in {len(chal)} challenges x {len(args.arms)} arms x {args.reps} reps; about {n_groups} first-pass agent calls")
        for k in sorted(ctx.prompts, key=str):
            print(f"--- system prompt {k} ({len(ctx.prompts[k][0])} chars, hash {ctx.prompts[k][1]}) ---")
        print(batch_system("...")[-420:])
        return
    cfg = AC.AgentConfig(args.claude_bin, args.model, args.cli_extra, args.env_pass, args.call_timeout)
    cli.call_cli = lambda c, system_prompt, user_prompt: _call(cfg, system_prompt, user_prompt)
    if not args.skip_probe:
        ok, rec = AC.isolation_probe(cfg)
        with open(ctx.results / "isolation_probe.json", "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=1)
        if not ok:
            raise SystemExit("isolation probe failed: the agent can see " + str(rec.get("visible")) + "; see " + str(ctx.results / "isolation_probe.json") +
                             ". Start from a clean login (pass only the variables that the login needs with --env-pass).")
    rules_hash = RP.snapshot(ctx, items)
    state_path = ctx.results / "run_state.json"
    ctx.state = {}
    prev_arms = []
    if state_path.exists():
        try:
            prev_arms = json.loads(state_path.read_text(encoding="utf-8")).get("arms", [])
            if not args.reset_clock:
                ctx.state = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            ctx.state = {}
    run_flags = {k: bool(getattr(args, k, False)) for k in ("dict_all", "guide_sup", "fret_reference", "g_parity", "intent_decl", "tm_source_only", "sourced_rules_only", "stageb_sees_raw", "no_kc")}
    if "start_epoch" not in ctx.state or args.reset_clock:
        ctx.state = {"start_epoch": now(), "start_iso": iso(now()), "resumes": 0, "rules_hash": rules_hash, "flags": run_flags}
    else:
        ctx.state["resumes"] = ctx.state.get("resumes", 0) + 1
        RP.check_flags(ctx.state, run_flags)
        if ctx.state.get("rules_hash") != rules_hash:
            raise SystemExit("tpl_rules.py / fretlint.py changed since the first start of this run. Use a new --results folder.")
    ctx.deadline = ctx.state["start_epoch"] + args.hours * 3600
    ctx.state.update({"deadline_iso": iso(ctx.deadline), "hours_limit": args.hours, "reps": args.reps, "block": args.block, "mode": "batch", "ext": list(exts),
                      "arms": [x for x in P.ARMS3 if x in set(prev_arms) | set(args.arms)], "n_items": len(items)})
    ctx.rows = {}
    for r in load_jsonl(ctx.calls_path):
        ctx.rows[r["stage_key"]] = r

    def _sig(*_):
        cli.STOP["flag"] = True
    signal.signal(signal.SIGINT, _sig)
    signal.signal(signal.SIGTERM, _sig)
    log(ctx, f"start (batch): {len(items)} items in {len(chal)} challenges x {len(args.arms)} arms x {args.reps} reps; parser={args.parser}; stage rows already done {len(ctx.rows)}")
    write_state(ctx, status="running")
    exit_status = "finished_all"
    try:
        for b0 in range(0, args.reps, args.block):
            if now() >= ctx.deadline:
                exit_status = "stopped_deadline"
                break
            reps = list(range(b0, min(b0 + args.block, args.reps)))
            blk = b0 // args.block
            rnd = random.Random(args.seed + b0)
            ok = (phase_A(ctx, items, args.arms, reps, blk, rnd) and phase_first(ctx, items, args.arms, reps, blk, rnd) and phase_fallback(ctx, items, args.arms, reps, blk, rnd)
                  and phase_rounds(ctx, items, args.arms, reps, blk, rnd)
                  and (args.no_kc or phase_kc(ctx, items, args.arms, reps, blk, rnd))
                  and (args.no_rt or phase_rt(ctx, items, args.arms, reps, blk, rnd)))
            if not ok:
                exit_status = "stopped_deadline"
                break
            log(ctx, f"block {blk} (reps {reps}) complete")
            write_state(ctx, blocks_completed=blk + 1, stage_rows_done=len(ctx.rows))
    except KeyboardInterrupt:
        exit_status = "interrupted"
        log(ctx, "interrupted; progress is saved, rerun the same command to resume")
    write_state(ctx, status=exit_status, end_iso=iso(now()), elapsed_since_first_start_h=round((now() - ctx.state["start_epoch"]) / 3600, 3))
    log(ctx, f"end: {exit_status}")
    sys.exit(0 if exit_status in ("finished_all", "stopped_deadline", "stopped_projection") else 130)


def _call(cfg, system_prompt, user_prompt):
    r = AC.call_agent(cfg, system_prompt, user_prompt, AC.BATCH_SCHEMA)
    return {"rc": r["rc"], "stdout": r["stdout"], "stderr": r["stderr"], "obj": r["obj"], "wall_s": r["wall_s"], "timed_out": r["timed_out"]}


if __name__ == "__main__":
    main()
