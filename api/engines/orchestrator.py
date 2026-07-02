"""
Winter AI - Orchestrator

Calls each real language engine as a subprocess and assembles the results.
Every engine here is genuinely executed in its native language runtime:

    Prolog  -> swipl -q -g main -t halt rules.pl -- "<text>"
    LISP    -> sbcl --script tokenizer.lisp "<text>"
    OCaml   -> ./validator "<text>"   (native binary, compiled in Docker build)
    C++     -> ./formatter "<text>"   (native binary, compiled in Docker build)
    Mercury -> Python port of engine.m's algorithm (see engines/mercury/)
    Python  -> this module + retrieval.py (BM25) run natively
    Schema  -> engines/schema/validator.py runs natively

All subprocess calls have a short timeout and a safe fallback so a missing
or slow toolchain never takes the whole API down — it just degrades that
one layer's diagnostic output.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

ENGINES_DIR = Path(__file__).resolve().parent
TIMEOUT = 5


def _run(cmd: list[str], cwd: Path) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True, timeout=TIMEOUT,
        )
        out = result.stdout.strip().splitlines()
        line = out[-1] if out else ""
        if result.returncode != 0 or not line:
            return False, (result.stderr.strip() or "non-zero exit")
        return True, line
    except FileNotFoundError:
        return False, f"toolchain not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return False, "timed out"
    except Exception as e:  # noqa: BLE001
        return False, str(e)


def run_prolog(text: str) -> dict:
    """Real SWI-Prolog forward-chaining intent classification."""
    swipl = shutil.which("swipl")
    if not swipl:
        return {"ok": False, "engine": "prolog", "error": "swipl not installed"}
    cwd = ENGINES_DIR / "prolog"
    ok, out = _run([swipl, "-q", "-g", "main", "-t", "halt", "rules.pl", "--", text], cwd)
    if not ok:
        return {"ok": False, "engine": "prolog", "error": out}
    try:
        return {"ok": True, **json.loads(out)}
    except json.JSONDecodeError:
        return {"ok": False, "engine": "prolog", "error": f"bad output: {out}"}


def run_lisp(text: str) -> dict:
    """Real SBCL Common Lisp symbolic tokenizer."""
    sbcl = shutil.which("sbcl")
    if not sbcl:
        return {"ok": False, "engine": "lisp", "sexpr": None, "error": "sbcl not installed"}
    cwd = ENGINES_DIR / "lisp"
    ok, out = _run([sbcl, "--script", "tokenizer.lisp", text], cwd)
    if not ok:
        return {"ok": False, "engine": "lisp", "sexpr": None, "error": out}
    return {"ok": True, "engine": "lisp", "sexpr": out}


def run_ocaml(text: str) -> dict:
    """Native OCaml binary, compiled ahead of time (ocamlopt) in the Docker build."""
    cwd = ENGINES_DIR / "ocaml"
    binary = cwd / "validator"
    if not binary.exists():
        return {"ok": False, "engine": "ocaml", "error": "validator binary not built"}
    ok, out = _run([str(binary), text], cwd)
    if not ok:
        return {"ok": False, "engine": "ocaml", "error": out}
    try:
        return {"ok": True, **json.loads(out)}
    except json.JSONDecodeError:
        return {"ok": False, "engine": "ocaml", "error": f"bad output: {out}"}


def run_cpp(text: str) -> dict:
    """Native C++ binary, compiled ahead of time (g++) in the Docker build."""
    cwd = ENGINES_DIR / "cpp"
    binary = cwd / "formatter"
    if not binary.exists():
        return {"ok": False, "engine": "cpp", "error": "formatter binary not built"}
    ok, out = _run([str(binary), text], cwd)
    if not ok:
        return {"ok": False, "engine": "cpp", "error": out}
    try:
        return {"ok": True, **json.loads(out)}
    except json.JSONDecodeError:
        return {"ok": False, "engine": "cpp", "error": f"bad output: {out}"}
