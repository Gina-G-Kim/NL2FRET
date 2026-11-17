"""Claude Code CLI wrapper with session limit handling (subscription login only, no API key, no local model).

Kept from the previous bench (run1 proved it on a real session limit):
  headless call `claude -p --output-format json --system-prompt ... --tools "" --no-session-persistence`,
  limit detection from the CLI message, wait until the reset time + margin, probe with a tiny call, then retry the SAME call.
Observed real message (run1, 2026-10-23): "You've hit your session limit · resets 8am (Asia/Seoul)"  (waited 5183.6 s, parsed 08:00 KST).
Changes in this bench:
  * parse_reset also reads "resets Oct 27, 8am (Asia/Seoul)" style dates (wording NOT observed yet, the generic probe loop is the safety net)
  * every call row stores waited_s separately, so run time of a stage never contains waiting
  * the caller checkpoints after every stage (stage A is not repeated when the limit hits between stage A and stage B)
  * `python3 cli.py --selftest` checks the parser on the observed message before a long run
"""
import datetime as dt
import json
import os
import re
import shlex
import subprocess
import sys
import time

STOP = {"flag": False}


def now():
    return time.time()


def iso(t):
    return dt.datetime.fromtimestamp(t, dt.timezone.utc).astimezone().isoformat(timespec="seconds")


class Ctx:
    pass


def log(ctx, msg):
    line = f"[{iso(now())}] {msg}"
    print(line, flush=True)
    with open(ctx.results / "run.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def write_state(ctx, **kw):
    ctx.state.update(kw)
    ctx.state["heartbeat"] = iso(now())
    tmp = ctx.results / "run_state.json.tmp"
    tmp.write_text(json.dumps(ctx.state, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, ctx.results / "run_state.json")


def append_jsonl(path, obj):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())


def sleep_chunked(ctx, seconds, why):
    end = now() + seconds
    last_beat = 0
    while now() < end:
        if STOP["flag"]:
            raise KeyboardInterrupt
        time.sleep(min(15, max(0.05, end - now())))
        if now() - last_beat > 60:
            write_state(ctx, status="waiting_limit", waiting_for=why, wait_until=iso(end))
            last_beat = now()


def call_cli(ctx, system_prompt, user_prompt):
    cmd = [ctx.args.claude_bin, "-p", "--output-format", "json", "--system-prompt", system_prompt, "--tools", "", "--no-session-persistence"]
    if getattr(ctx.args, "model", ""):
        cmd += ["--model", ctx.args.model]
    if getattr(ctx.args, "cli_extra", ""):
        cmd += shlex.split(ctx.args.cli_extra)
    t0 = time.perf_counter()
    try:
        p = subprocess.run(cmd, input=user_prompt, capture_output=True, text=True, timeout=ctx.args.call_timeout)
        rc, out, err, timed_out = p.returncode, p.stdout, p.stderr, False
    except subprocess.TimeoutExpired as e:
        rc, out, err, timed_out = -9, (e.stdout or ""), (e.stderr or ""), True
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        if isinstance(err, bytes):
            err = err.decode("utf-8", "replace")
    except FileNotFoundError:
        raise SystemExit(f"claude binary not found: {ctx.args.claude_bin}")
    wall = time.perf_counter() - t0
    obj = None
    s = (out or "").strip()
    if s:
        try:
            obj = json.loads(s)
            if isinstance(obj, list):
                res = [x for x in obj if isinstance(x, dict) and x.get("type") == "result"]
                obj = res[-1] if res else None
        except json.JSONDecodeError:
            obj = None
    return {"rc": rc, "stdout": out or "", "stderr": err or "", "obj": obj, "wall_s": wall, "timed_out": timed_out}


LIMIT_PATTERNS = [r"usage limit", r"session limit", r"weekly limit", r"limit reached", r"rate.?limit", r"too many requests", r"\b429\b",
                  r"quota", r"exceeded your", r"out of (extra )?usage", r"limit will reset", r"you.?ve hit your", r"resets? (at|in|on)\b", r"resets? \d"]
STRICT_LIMIT = r"usage limit reached|session limit|weekly limit|limit reached|hit your .{0,20}limit"


def detect_limit(res):
    """Return (is_limit, message)."""
    obj = res["obj"]
    failed = res["rc"] != 0 or obj is None or bool(obj.get("is_error"))
    texts = [res["stderr"]]
    if obj is None:
        texts.append(res["stdout"])
    elif obj.get("is_error"):
        texts.append(str(obj.get("result", "")))
    msg = " ".join(t for t in texts if t).strip()
    if failed and msg and any(re.search(p, msg, re.I) for p in LIMIT_PATTERNS):
        if not re.search(r"overloaded|\b529\b", msg, re.I) or re.search(r"limit", msg, re.I):
            return True, msg[:500]
    if obj is not None and not obj.get("is_error"):
        r = str(obj.get("result", ""))
        if "{" not in r and re.search(STRICT_LIMIT, r, re.I):  # the limit text can come back as a normal result
            return True, r[:500]
    return False, msg[:500]


MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def _tz(name):
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except Exception:
        return None


def parse_reset(msg, ref=None):
    """Extract the reset time (epoch seconds) from a limit message, or None when unknown."""
    ref = ref or now()
    m = re.search(r"limit reached\|(\d{10,13})", msg)
    if m:
        v = int(m.group(1))
        return v / 1000.0 if v > 1e11 else float(v)
    m = re.search(r"retry[- ]after[:\s]+(\d+)", msg, re.I)
    if m:
        return ref + int(m.group(1))
    # month day form (wording not observed yet): "resets Oct 27, 8am (Asia/Seoul)"
    m = re.search(r"resets?\s+(?:on\s+)?([A-Za-z]{3,9})\.?\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s*(?:at\s*)?(\d{1,2})(?::(\d{2}))?\s*([ap]m)?)?\s*(?:\(([A-Za-z_]+/[A-Za-z_]+|UTC)\))?", msg, re.I)
    if m and m.group(1)[:3].lower() in MONTHS:
        tz = _tz(m.group(6)) if m.group(6) else None
        base = dt.datetime.fromtimestamp(ref, tz) if tz else dt.datetime.fromtimestamp(ref).astimezone()
        h = int(m.group(3) or 0)
        ap = (m.group(5) or "").lower()
        if ap == "pm" and h < 12:
            h += 12
        if ap == "am" and h == 12:
            h = 0
        try:
            cand = base.replace(month=MONTHS[m.group(1)[:3].lower()], day=int(m.group(2)), hour=h, minute=int(m.group(4) or 0), second=0, microsecond=0)
            if cand.timestamp() <= ref - 300:
                cand = cand.replace(year=cand.year + 1)
            return max(cand.timestamp(), ref)
        except ValueError:
            pass
    m = re.search(r"reset[s]?\s*(?:at\s*)?(\d{1,2})(?::(\d{2}))?\s*([ap]m)?\s*(?:\(([A-Za-z_]+/[A-Za-z_]+|UTC)\))?", msg, re.I)
    if m and (m.group(2) or m.group(3)):
        h = int(m.group(1))
        mi = int(m.group(2) or 0)
        ap = (m.group(3) or "").lower()
        if ap == "pm" and h < 12:
            h += 12
        if ap == "am" and h == 12:
            h = 0
        if 0 <= h < 24 and 0 <= mi < 60:
            tz = _tz(m.group(4)) if m.group(4) else None
            base = dt.datetime.fromtimestamp(ref, tz) if tz else dt.datetime.fromtimestamp(ref).astimezone()
            cand = base.replace(hour=h, minute=mi, second=0, microsecond=0)
            if cand.timestamp() <= ref:
                if ref - cand.timestamp() < 300:
                    return ref
                cand += dt.timedelta(days=1)
            return cand.timestamp()
    if re.search(r"reset|retry|limit", msg, re.I):
        m = re.search(r"\b(?:in|after)\s+(\d+(?:\.\d+)?)\s*(hour|hr|minute|min|second|sec)s?", msg, re.I)
        if m:
            v = float(m.group(1))
            u = m.group(2).lower()
            return ref + v * (3600 if u.startswith("h") else 60 if u.startswith("m") else 1)
    return None


def probe(ctx):
    res = call_cli(ctx, "Reply with the single word OK.", "ping")
    is_lim, msg = detect_limit(res)
    obj = res["obj"]
    append_jsonl(ctx.results / "probes.jsonl", {"ts": iso(now()), "rc": res["rc"], "limit": is_lim, "msg": msg[:300],
                                                "usage": (obj or {}).get("usage"), "cost": (obj or {}).get("total_cost_usd")})
    if is_lim:
        return "limit", msg, parse_reset(msg)
    if res["rc"] == 0 and obj is not None and not obj.get("is_error"):
        return "ok", "", None
    return "error", msg or res["stdout"][:300], None


def wait_for_limit(ctx, msg, reset_epoch, key):
    t0 = now()
    ev = {"ts": iso(t0), "key": key, "message": msg[:300], "reset_parsed": iso(reset_epoch) if reset_epoch else None}
    log(ctx, f"LIMIT detected at {key}. reset={ev['reset_parsed']} msg={msg[:160]!r}")

    def mk_target(rs):
        if not rs:
            return None
        t = max(rs + ctx.args.reset_margin, now() + 5)
        return t if t - now() <= 8 * 86400 else None

    target = mk_target(reset_epoch)
    interval = ctx.args.probe_interval
    consec_err = 0
    while True:
        wait = min(max(target - now(), 1), ctx.args.probe_max) if target else interval
        sleep_chunked(ctx, wait, key)
        if target and target - now() > 30:
            status, pmsg, new_reset = "wait_more", "", None
        else:
            status, pmsg, new_reset = probe(ctx)
        if status == "ok":
            break
        if status == "wait_more":
            continue
        if status == "limit":
            consec_err = 0
            nt = mk_target(new_reset)
            if nt:
                target = nt
            elif not (target and target > now()):
                target = None
                interval = min(interval * 1.5, ctx.args.probe_max)
            log(ctx, f"probe: still limited; next check in ~{int(target - now()) if target else int(interval)}s")
        else:
            consec_err += 1
            log(ctx, f"probe: non-limit error ({consec_err}/{ctx.args.max_probe_errors}): {pmsg[:160]!r}")
            if consec_err >= ctx.args.max_probe_errors:
                write_state(ctx, status="aborted_probe_errors")
                raise SystemExit(3)
            target = None
    waited = now() - t0
    ev["waited_s"] = round(waited, 1)
    ctx.state["waited_total_s"] = ctx.state.get("waited_total_s", 0.0) + waited
    append_jsonl(ctx.results / "limit_events.jsonl", ev)
    log(ctx, f"limit lifted after {waited:.0f}s")
    return waited


def call_with_limits(ctx, system_prompt, user_prompt, key, max_attempts=None):
    """One logical call: retries after limits (not counted) and after plain CLI errors (counted). Returns (res, obj, ok, attempts, waited_s)."""
    max_attempts = max_attempts or ctx.args.max_attempts
    waited_total, attempts = 0.0, 0
    while True:
        if STOP["flag"]:
            raise KeyboardInterrupt
        if getattr(ctx.args, "strict_deadline", False) and getattr(ctx, "deadline", None) and now() >= ctx.deadline:
            return None, None, False, attempts, waited_total
        res = call_cli(ctx, system_prompt, user_prompt)
        is_lim, msg = detect_limit(res)
        if is_lim:
            waited_total += wait_for_limit(ctx, msg, parse_reset(msg), key)
            continue
        attempts += 1
        obj = res["obj"]
        ok = res["rc"] == 0 and obj is not None and not obj.get("is_error")
        if ok or attempts >= max_attempts:
            return res, obj, ok, attempts, waited_total
        log(ctx, f"{key}: CLI error rc={res['rc']} attempt {attempts}/{max_attempts}; retry in 20s")
        sleep_chunked(ctx, 20, key)


def usage_fields(obj):
    u = (obj or {}).get("usage") or {}
    it, ot = u.get("input_tokens") or 0, u.get("output_tokens") or 0
    cc, cr = u.get("cache_creation_input_tokens") or 0, u.get("cache_read_input_tokens") or 0
    return {"input_tokens": it, "output_tokens": ot, "cache_creation_input_tokens": cc, "cache_read_input_tokens": cr,
            "total_tokens": it + ot + cc + cr, "cost_usd": (obj or {}).get("total_cost_usd"),
            "duration_ms": (obj or {}).get("duration_ms"), "duration_api_ms": (obj or {}).get("duration_api_ms"),
            "model_used": sorted(((obj or {}).get("modelUsage") or {}).keys()), "num_turns": (obj or {}).get("num_turns"),
            "stop_reason": (obj or {}).get("stop_reason"), "session_id": (obj or {}).get("session_id")}


def cli_version(claude_bin):
    try:
        p = subprocess.run([claude_bin, "--version"], capture_output=True, text=True, timeout=60, stdin=subprocess.DEVNULL)
        return (p.stdout or p.stderr).strip()[:200]
    except Exception as e:
        return f"unknown ({type(e).__name__})"


def selftest():
    kst = _tz("Asia/Seoul")
    ref = dt.datetime(2026, 10, 23, 6, 34, 40, tzinfo=kst).timestamp()
    r = parse_reset("You've hit your session limit · resets 8am (Asia/Seoul)", ref)
    assert r and abs(r - dt.datetime(2026, 10, 23, 8, 0, tzinfo=kst).timestamp()) < 1, r
    assert detect_limit({"rc": 1, "stdout": "", "stderr": "", "obj": {"is_error": True, "result": "You've hit your session limit · resets 8am (Asia/Seoul)"}})[0]
    assert detect_limit({"rc": 0, "stdout": "", "stderr": "", "obj": {"is_error": False, "result": "You've hit your session limit · resets 8am (Asia/Seoul)"}})[0]
    assert not detect_limit({"rc": 0, "stdout": "", "stderr": "", "obj": {"is_error": False, "result": '{"sentences": ["x"]}'}})[0]
    r2 = parse_reset("Weekly limit reached · resets Oct 27, 8am (Asia/Seoul)", ref)
    assert r2 and abs(r2 - dt.datetime(2026, 10, 27, 8, 0, tzinfo=kst).timestamp()) < 1, r2
    r3 = parse_reset("limit reached|1790000000", ref)
    assert r3 == 1790000000.0
    r4 = parse_reset("Rate limited, retry-after: 90", ref)
    assert r4 == ref + 90
    print("cli selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
