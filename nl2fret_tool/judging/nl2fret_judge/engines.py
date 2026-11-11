"""Query engines. One query = one formula check, one SMV file per query (NuSMV 2.6.0 prints the results of several LTLSPEC lines in an order that
differs from the declaration order, so results are never matched by output position).

Query kinds (GT = reference formula, Pred = generated formula; Danso et al. Figure 3):
  equiv  : GT <-> Pred          holds on every trace end
  sound  : GT -> Pred           (the generated formula admits everything the reference admits; failure = ALARM)
  compl  : Pred -> GT           (the generated formula admits nothing the reference forbids; failure = MISS)
  sat    : auxiliary, G !Pred   (verdict true means Pred is unsatisfiable)
  valid  : auxiliary, G Pred    (verdict true means Pred is valid)
"""
import hashlib
import os
import re
import subprocess
import time
from dataclasses import dataclass, field

KINDS = ("equiv", "sound", "compl")
AUX = ("sat", "valid")
# v1.2.0: identifier of the structure of the SMV file that smv_file_text() writes (one file per query, one LTLSPEC line); recorded in run_header.json.
# Change it only together with smv_file_text (a test pins the structure to this identifier).
SMV_TEMPLATE_ID = "single_ltlspec_v1"


def spec_text(kind, gs, rs):
    """gs = Pred (generated) in SMV syntax, rs = GT (reference) in SMV syntax."""
    return {
        "equiv": f"G (({rs}) <-> ({gs}))",
        "sound": f"G (({rs}) -> ({gs}))",
        "compl": f"G (({gs}) -> ({rs}))",
        "sat": f"G (! ({gs}))",
        "valid": f"G ({gs})",
    }[kind]


def smv_file_text(spec, atoms):
    body = "MODULE main\nVAR\n"
    for a in (sorted(atoms) or ["dummy_ap"]):
        body += f"  {a} : boolean;\n"
    return body + f"LTLSPEC {spec}\n"


@dataclass
class QueryResult:
    kind: str
    spec_text: str
    verdict: object = None          # True, False or None (no verdict)
    executed: bool = True
    stdout: str = ""
    stderr: str = ""
    exit_code: object = None
    elapsed_sec: float = 0.0
    timed_out: bool = False
    cmd: list = field(default_factory=list)
    smv_text: str = ""
    smv_sha256: str = ""
    reason: str = ""                # '' | timeout | nusmv_output | no_verdict | other

    def to_record(self, limit=1_000_000):
        so, se = self.stdout, self.stderr
        trunc = len(so) > limit
        return {
            "kind": self.kind, "spec_text": self.spec_text, "smv_sha256": self.smv_sha256, "smv_path": f"smv/{self.smv_sha256}.smv" if self.smv_sha256 else None,
            "verdict": self.verdict, "executed": self.executed, "stdout": so[:limit], "stdout_truncated": trunc, "stderr": se[:limit],
            "exit_code": self.exit_code, "elapsed_sec": round(self.elapsed_sec, 4), "timed_out": self.timed_out, "cmd": self.cmd,
            "query_mode": "single_spec_per_file", "reason": self.reason,
        }


class NuSMVEngine:
    """cmd: the NuSMV invocation as a list (an executable that takes the path of an .smv file as its last argument; a docker wrapper script is fine)."""
    name = "nusmv"

    def __init__(self, cmd, timeout=120, workdir="work"):
        self.cmd = list(cmd) if isinstance(cmd, (list, tuple)) else [cmd]
        self.timeout = timeout
        self.workdir = workdir
        os.makedirs(workdir, exist_ok=True)

    def query(self, kind, gs, rs, atoms, **_):
        spec = spec_text(kind, gs, rs)
        text = smv_file_text(spec, atoms)
        sha = hashlib.sha256(text.encode()).hexdigest()
        path = os.path.join(self.workdir, sha + ".smv")
        if not os.path.exists(path):
            with open(path, "w") as f:
                f.write(text)
        cmd = self.cmd + [path]
        r = QueryResult(kind=kind, spec_text=spec, cmd=cmd, smv_text=text, smv_sha256=sha)
        t0 = time.time()
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
            r.stdout, r.stderr, r.exit_code = p.stdout, p.stderr, p.returncode
        except subprocess.TimeoutExpired as e:
            r.timed_out = True
            r.reason = "timeout"
            r.stdout = (e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or ""))
            r.stderr = (e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or ""))
        r.elapsed_sec = time.time() - t0
        if not r.timed_out:
            m = re.findall(r"-- specification .* is (true|false)", r.stdout)
            if len(m) == 1:
                r.verdict = (m[0] == "true")
            else:
                r.reason = "no_verdict" if not r.stdout.strip() else "nusmv_output"
        return r

    def version(self):
        try:
            p = subprocess.run(self.cmd + ["-h"], capture_output=True, text=True, timeout=30)
            m = re.search(r"NuSMV[^\n]*", p.stdout + p.stderr)
            return m.group(0).strip() if m else (p.stdout + p.stderr)[:120]
        except Exception as e:  # noqa: BLE001
            return f"unknown ({e})"


class Z3Engine:
    """Cross-check engine: bounded z3 evaluation (horizon H) of the same boolean abstraction. Used in the sandbox and as an independent check; it is NOT
    the reference semantics (finite horizon). Queries are answered from one miss/alarm computation per pair."""
    name = "z3-bounded"

    def __init__(self, horizon=8):
        self.horizon = horizon
        self._cache = {}

    def query(self, kind, gs, rs, atoms, gen_text=None, ref_text=None, **_):
        from . import abstraction as A
        key = (gen_text, ref_text)
        if key not in self._cache:
            try:
                self._cache[key] = A.LE.z3_roles(gen_text, ref_text, H=self.horizon)
            except A.Unsupported as e:
                self._cache[key] = e
        d = self._cache[key]
        if isinstance(d, Exception):
            return QueryResult(kind=kind, spec_text=spec_text(kind, gs, rs), verdict=None, stdout="(z3 bounded)", reason="converter_limit", cmd=["z3-bounded", f"H={self.horizon}"])
        verdict = {"equiv": (not d["miss"] and not d["alarm"]), "sound": not d["alarm"], "compl": not d["miss"],
                   "sat": not d["gen_sat"], "valid": bool(d["gen_valid"])}[kind]
        return QueryResult(kind=kind, spec_text=spec_text(kind, gs, rs), verdict=verdict, stdout="(z3 bounded)", exit_code=0, cmd=["z3-bounded", f"H={self.horizon}"])
