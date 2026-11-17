"""One isolated, memoryless agent call through the Claude Code CLI (headless). Used by batch_pipeline.py.

Isolation (checked, not assumed)
  * the child process gets a WHITELISTED environment (PATH, HOME, locale, proxy and certificate variables, ANTHROPIC_BASE_URL and the names given with --env-pass); every other
    variable of the parent is dropped. A CLI started from inside another Claude Code session otherwise inherits the parent's project, connectors and memory (observed, see isolation_probe).
  * the working directory is a new empty folder, the CLI runs with --tools "" --no-session-persistence --setting-sources "" --disable-slash-commands --strict-mcp-config.
  * isolation_probe() asks a call to list everything visible to it. The run refuses to start unless the answer is an empty list; the probe call is stored in the run folder.
Output
  * --json-schema forces the reply into a JSON object; the script reads only that object (field structured_output of the CLI result, else the JSON of the result text).
"""
import json
import os
import re
import subprocess
import tempfile
import time

BASE_ENV = ["PATH", "HOME", "USER", "LOGNAME", "LANG", "LC_ALL", "TMPDIR", "SHELL", "TERM", "XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA",
            "SYSTEMROOT", "HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "https_proxy", "http_proxy", "no_proxy", "SSL_CERT_FILE", "SSL_CERT_DIR", "NODE_EXTRA_CA_CERTS", "REQUESTS_CA_BUNDLE",
            "CURL_CA_BUNDLE", "ANTHROPIC_BASE_URL"]
ISOLATION_FLAGS = ["--tools", "", "--no-session-persistence", "--setting-sources", "", "--disable-slash-commands", "--strict-mcp-config"]

BATCH_SCHEMA = {"type": "object", "properties": {"results": {"type": "array", "items": {"type": "object", "properties": {"id": {"type": "string"}, "answer": {"type": "object"}},
                                                                                         "required": ["id", "answer"]}}}, "required": ["results"]}
PROBE_SCHEMA = {"type": "object", "properties": {"visible": {"type": "array", "items": {"type": "string"}}}, "required": ["visible"]}
ALLOWED_VISIBLE = {"StructuredOutput", "userEmail"}       # StructuredOutput: the CLI's own tool that carries the --json-schema answer; userEmail: the CLI puts the login account's e-mail into the context, the same for every approach (allowed 2026-11-16, docs/V20_BATCH_DESIGN.md)
PROBE_SYSTEM = "Answer the question."
PROBE_USER = ("List by name every tool, skill, plugin, connector, memory file, project, project document and instruction file that is visible to you in this conversation. "
              "Reply with the JSON object {\"visible\": [names]}; the list is empty when nothing is visible.")


class AgentConfig:
    def __init__(self, claude_bin="claude", model="", extra="", env_pass=(), timeout=900):
        self.claude_bin, self.model, self.extra, self.timeout = claude_bin, model, extra, timeout
        self.env_pass = list(env_pass)

    def env(self):
        keep = set(BASE_ENV) | set(self.env_pass)
        return {k: v for k, v in os.environ.items() if k in keep}

    def command(self, system_prompt, schema):
        import shlex
        cmd = [self.claude_bin, "-p", "--output-format", "json", "--system-prompt", system_prompt] + ISOLATION_FLAGS
        if schema is not None:
            cmd += ["--json-schema", json.dumps(schema, separators=(",", ":"))]
        if self.model:
            cmd += ["--model", self.model]
        if self.extra:
            cmd += shlex.split(self.extra)
        return cmd


def _result_object(stdout):
    s = (stdout or "").strip()
    if not s:
        return None
    try:
        o = json.loads(s)
    except json.JSONDecodeError:
        return None
    if isinstance(o, list):
        res = [x for x in o if isinstance(x, dict) and x.get("type") == "result"]
        return res[-1] if res else None
    return o if isinstance(o, dict) else None


def answer_object(cli_obj):
    """The JSON object the agent answered: structured_output when the CLI gives it, else the JSON text of result."""
    if not cli_obj:
        return None
    so = cli_obj.get("structured_output")
    if isinstance(so, dict):
        return so
    txt = cli_obj.get("result")
    if isinstance(txt, str):
        try:
            o = json.loads(txt)
            return o if isinstance(o, dict) else None
        except json.JSONDecodeError:
            return None
    return None


def call_agent(cfg, system_prompt, user_prompt, schema=BATCH_SCHEMA):
    """-> dict(rc, stdout, stderr, obj (CLI result object), answer (dict or None), wall_s, timed_out, cwd_empty)"""
    cmd = cfg.command(system_prompt, schema)
    t0 = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="nl2fret_agent_") as cwd:
        try:
            p = subprocess.run(cmd, input=user_prompt, capture_output=True, text=True, timeout=cfg.timeout, cwd=cwd, env=cfg.env())
            rc, out, err, to = p.returncode, p.stdout, p.stderr, False
        except subprocess.TimeoutExpired as e:
            rc, out, err, to = -9, e.stdout or "", e.stderr or "", True
            out = out.decode("utf-8", "replace") if isinstance(out, bytes) else out
            err = err.decode("utf-8", "replace") if isinstance(err, bytes) else err
        except FileNotFoundError:
            raise SystemExit(f"claude binary not found: {cfg.claude_bin}")
        cwd_empty = not os.listdir(cwd)
    obj = _result_object(out)
    return {"rc": rc, "stdout": out or "", "stderr": err or "", "obj": obj, "answer": answer_object(obj) if (obj and not obj.get("is_error")) else None,
            "wall_s": time.perf_counter() - t0, "timed_out": to, "cwd_empty": cwd_empty}


def isolation_probe(cfg):
    """-> (ok, record). ok when the call succeeded and nothing is visible to the agent."""
    res = call_agent(cfg, PROBE_SYSTEM, PROBE_USER, PROBE_SCHEMA)
    vis = (res["answer"] or {}).get("visible")
    ok = isinstance(vis, list) and not (set(map(str, vis)) - ALLOWED_VISIBLE) and res["cwd_empty"]
    usage = (res["obj"] or {}).get("usage") or {}
    redact = lambda x: re.sub(r"\S+@\S+", "<redacted>", str(x))          # the record keeps names only, never an e-mail value
    rec = {"ok": ok, "visible": [redact(v) for v in vis] if isinstance(vis, list) else vis, "env_names": sorted(cfg.env()), "flags": ISOLATION_FLAGS, "model": cfg.model, "extra": cfg.extra, "rc": res["rc"],
           "cache_read_input_tokens": usage.get("cache_read_input_tokens"), "input_tokens_total": sum(int(usage.get(k) or 0) for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens")),
           "stderr": redact(res["stderr"][:300]), "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z")}
    return ok, rec
