"""Winter AI - Schema validator (final output gatekeeper)."""

from __future__ import annotations


def validate(data: str, lang: str = "en") -> dict:
    checks = {
        "non_empty": isinstance(data, str) and len(data.strip()) > 0,
        "valid_lang": lang in ("en", "fr", "rw"),
        "length_ok": isinstance(data, str) and 1 <= len(data) <= 4096,
        "utf8_safe": all(ord(c) < 65536 for c in data) if isinstance(data, str) else False,
        "no_control_chars": isinstance(data, str) and not any(
            ord(c) < 32 and c not in ("\n", "\t") for c in data
        ),
    }
    return {
        "valid": all(checks.values()),
        "checks": checks,
    }


if __name__ == "__main__":
    import sys
    text = sys.argv[1] if len(sys.argv) > 1 else ""
    lang = sys.argv[2] if len(sys.argv) > 2 else "en"
    result = validate(text, lang)
    print(f"Schema validation: {'PASS' if result['valid'] else 'FAIL'} — {result['checks']}")
