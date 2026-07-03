"""Shared helper for invoking the polyglot subprocess engines safely."""
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger("winter.proc")

DEFAULT_TIMEOUT = 5.0


def run(cmd: list[str], timeout: float = DEFAULT_TIMEOUT) -> dict:
    """Run a subprocess, return {ok, lines(dict of KEY->value), raw, error}."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8", "GUILE_AUTO_COMPILE": "0"},
        )
        parsed = parse_lines(result.stdout)
        if result.returncode != 0:
            logger.warning("subprocess %s exited %s: %s", cmd[0], result.returncode, result.stderr[:300])
        return {"ok": result.returncode == 0, "lines": parsed, "raw": result.stdout, "error": result.stderr}
    except FileNotFoundError:
        return {"ok": False, "lines": {}, "raw": "", "error": f"executable not found: {cmd[0]}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "lines": {}, "raw": "", "error": "timeout"}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "lines": {}, "raw": "", "error": str(e)}


def parse_lines(text: str) -> dict:
    """Parse the shared `KEY: value` line protocol used by every engine."""
    out: dict[str, str] = {}
    for line in text.splitlines():
        if ": " in line:
            key, _, value = line.partition(": ")
            key = key.strip()
            if key.isupper() or "_" in key:
                out[key] = value.strip()
    return out
