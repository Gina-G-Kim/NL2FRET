"""Code freeze helpers (v1.2.0): hashes of the judging code, the release manifest, and the check that `judge` runs before it starts.

Code files = judging/nl2fret_judge/*.py and judging/legacy/*.py (not recursive), identified by their path relative to the package root.
Manifest JUDGE_FROZEN_MANIFEST.sha256 (package root) = one line "<sha256>  <relative path>" per code file, in ascending path order (sha256sum -c format).
code_tree_sha256 = sha256 of exactly that text, so for a released tree it equals the sha256 of the manifest file.
The check protects against code that was changed by accident. It is not a protection against tampering (the checking code is itself one of the code files);
the independent check is `shasum -a 256 -c JUDGE_FROZEN_MANIFEST.sha256` run in the package root.
"""
import hashlib
import os
import platform
import re
from importlib import metadata

from .engines import AUX, KINDS, SMV_TEMPLATE_ID, spec_text
from .recorder import sha256_file

MANIFEST_NAME = "JUDGE_FROZEN_MANIFEST.sha256"
CODE_DIRS = ("judging/nl2fret_judge", "judging/legacy")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))      # package root (this file is root/judging/nl2fret_judge/freeze.py)
_LINE = re.compile(r"([0-9a-f]{64})  (\S.*)")


def code_files(root=None):
    """Relative paths (separator '/') of the code files, ascending."""
    root = root or ROOT
    out = []
    for d in CODE_DIRS:
        full = os.path.join(root, *d.split("/"))
        if os.path.isdir(full):
            out += [f"{d}/{n}" for n in os.listdir(full) if n.endswith(".py") and not n.startswith(".") and os.path.isfile(os.path.join(full, n))]
    return sorted(out)


def code_hashes(root=None):
    """-> [(relative path, sha256)] in manifest order."""
    root = root or ROOT
    return [(p, sha256_file(os.path.join(root, *p.split("/")))) for p in code_files(root)]


def manifest_text(entries):
    return "".join(f"{h}  {p}\n" for p, h in entries)


def tree_sha256(entries):
    return hashlib.sha256(manifest_text(entries).encode("utf-8")).hexdigest()


def read_manifest(path):
    """-> [(relative path, sha256)]; ValueError for an empty file, a line that is not '<sha256>  <path>', or a repeated path."""
    out, seen = [], set()
    with open(path, encoding="utf-8") as f:
        for n, line in enumerate(f, 1):
            m = _LINE.fullmatch(line.rstrip("\n"))
            if not m:
                raise ValueError(f"line {n} is not '<sha256>  <path>'")
            if m.group(2) in seen:
                raise ValueError(f"line {n}: path {m.group(2)} listed twice")
            seen.add(m.group(2))
            out.append((m.group(2), m.group(1)))
    if not out:
        raise ValueError("no entries")
    return out


def write_manifest(root=None):
    """Write JUDGE_FROZEN_MANIFEST.sha256 into the package root. Raises FileExistsError when it exists (a released tree is never released again).
    -> (manifest path, entries, sha256 of the manifest text)."""
    root = root or ROOT
    path = os.path.join(root, MANIFEST_NAME)
    entries = code_hashes(root)
    text = manifest_text(entries)
    with open(path, "x", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return path, entries, hashlib.sha256(text.encode("utf-8")).hexdigest()


def check_manifest(root=None):
    """Compare the code files with the manifest. -> {"status": absent | match | mismatch | invalid, "manifest": path, "manifest_sha256": hex or None,
    "diff": None | {"modified": [...], "missing": [...], "extra": [...]} | {"error": "..."}}.
    modified = listed and present but with another hash, missing = listed but not present, extra = a code file that the manifest does not list."""
    root = root or ROOT
    path = os.path.join(root, MANIFEST_NAME)
    if not os.path.exists(path):
        return {"status": "absent", "manifest": path, "manifest_sha256": None, "diff": None}
    msha = sha256_file(path)
    try:
        want = dict(read_manifest(path))
    except (ValueError, UnicodeDecodeError) as e:
        return {"status": "invalid", "manifest": path, "manifest_sha256": msha, "diff": {"error": str(e)}}
    have = dict(code_hashes(root))
    diff = {"modified": sorted(p for p in want if p in have and want[p] != have[p]), "missing": sorted(p for p in want if p not in have),
            "extra": sorted(p for p in have if p not in want)}
    ok = not any(diff.values())
    return {"status": "match" if ok else "mismatch", "manifest": path, "manifest_sha256": msha, "diff": None if ok else diff}


def describe(chk):
    """One line that names what differs (refusal message and warning)."""
    d = chk["diff"] or {}
    if "error" in d:
        return "manifest not readable: " + d["error"]
    return "; ".join(f"{k}: {', '.join(d[k])}" for k in ("modified", "missing", "extra") if d.get(k))


def versions():
    """python_version, and z3_version = the installed z3-solver distribution (what pip freeze shows), else the version string of an importable z3 module, else None."""
    try:
        z3 = metadata.version("z3-solver")
    except metadata.PackageNotFoundError:
        try:
            import z3 as _z3
            z3 = _z3.get_version_string()
        except Exception:  # noqa: BLE001
            z3 = None
    return {"python_version": platform.python_version(), "z3_version": z3}


def provenance(root=None):
    """Header fields that identify the code and the SMV query format of a run (v1.2.0)."""
    entries = code_hashes(root)
    out = versions()
    out["code_sha256"] = [{"file": p, "sha256": h} for p, h in entries]
    out["code_tree_sha256"] = tree_sha256(entries)
    out["smv_template_id"] = SMV_TEMPLATE_ID
    out["query_templates"] = {k: spec_text(k, "GS", "RS") for k in KINDS + AUX}      # GS = generated formula, RS = reference formula
    return out
