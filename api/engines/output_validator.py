"""
Winter AI -- Output contract validator.

Note on naming: an earlier draft of this project called this the "Schema"
layer, which reads as an abbreviation of "Scheme" and caused confusion with
the actual Scheme (Guile) engine in engines/scheme/. This module is about a
JSON *response shape* contract, not the Scheme programming language, so it is
named output_validator.py instead.
"""
from __future__ import annotations

MAX_LEN = 4096


def validate_output(answer: str, lang: str) -> dict:
    checks = {
        "non_empty": bool(answer and answer.strip()),
        "valid_lang": lang in ("en", "fr", "rw"),
        "length_ok": 1 <= len(answer or "") <= MAX_LEN,
        "utf8_safe": all(ord(c) < 0x110000 for c in (answer or "")),
    }
    return {"valid": all(checks.values()), "checks": checks}
