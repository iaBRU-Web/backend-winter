"""
Winter AI -- Orchestrator.

Runs the prompt through every real language layer in turn and assembles the
reasoning trace + final answer. Each layer is a genuine subprocess call into
that language's own runtime (Guile, SBCL, SWI-Prolog, a natively-compiled
OCaml binary, a natively-compiled C++ binary) except:
  - Python itself (native, no subprocess needed)
  - Mercury (Python re-implementation -- see engines/mercury/determinism.py
    for why there is no real `mmc` subprocess call)
"""
from __future__ import annotations

import re
import time
import shutil
from pathlib import Path
from typing import Optional

from . import proc
from .mercury.determinism import classify as mercury_classify
from .retrieval import KnowledgeIndex
from .output_validator import validate_output

BASE = Path(__file__).resolve().parent

SCHEME_SCRIPT = BASE / "scheme" / "decision.scm"
LISP_SCRIPT = BASE / "lisp" / "reasoner.lisp"
PROLOG_SCRIPT = BASE / "prolog" / "knowledge.pl"
OCAML_BIN = BASE / "ocaml" / "validator"
CPP_BIN = BASE / "cpp" / "engine"

GUILE_BIN = shutil.which("guile") or "guile"
SBCL_BIN = shutil.which("sbcl") or "sbcl"
SWIPL_BIN = shutil.which("swipl") or "swipl"

KINYARWANDA_HINTS = {"muraho", "murakoze", "amakuru", "witwa", "murabeho", "byiza", "cyane", "neza"}
FRENCH_CHARS = set("éèêëàâùûüîïôçœæ")
FRENCH_HINTS = {"bonjour", "merci", "comment", "vous", "je", "suis", "salut"}


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Zàâäéèêëïîôöùûüç]+", text.lower())


def detect_language(text: str) -> str:
    tokens = set(tokenize(text))
    if tokens & KINYARWANDA_HINTS:
        return "rw"
    if (any(c in FRENCH_CHARS for c in text.lower())) or len(tokens & FRENCH_HINTS) >= 1:
        return "fr"
    return "en"


class WinterOrchestrator:
    def __init__(self, knowledge: KnowledgeIndex):
        self.knowledge = knowledge

    # -- Layer 1: Python -----------------------------------------------------
    def python_layer(self, prompt: str, lang: str) -> dict:
        t0 = time.perf_counter()
        detected = detect_language(prompt)
        effective = lang if lang in ("fr", "rw") else detected
        tokens = tokenize(prompt)
        return {
            "engine": "Python",
            "status": "ok",
            "output": f"tokens={tokens[:12]} detected_lang={detected} effective_lang={effective}",
            "duration_ms": round((time.perf_counter() - t0) * 1000, 2),
            "tokens": tokens,
            "effective_lang": effective,
        }

    # -- Layer 2: Scheme (Guile) ---------------------------------------------
    def scheme_layer(self, tokens: list[str], lang: str) -> dict:
        t0 = time.perf_counter()
        res = proc.run([GUILE_BIN, str(SCHEME_SCRIPT), lang, ",".join(tokens)])
        dur = round((time.perf_counter() - t0) * 1000, 2)
        if not res["ok"] and not res["lines"]:
            return {"engine": "Scheme", "status": "error", "output": res["error"] or "unavailable",
                    "duration_ms": dur, "intent": "lookup", "sentiment": "neutral"}
        lines = res["lines"]
        return {
            "engine": "Scheme (GNU Guile)", "status": "ok",
            "output": lines.get("TRACE", ""), "duration_ms": dur,
            "intent": lines.get("INTENT", "lookup").lower(),
            "sentiment": lines.get("SENTIMENT", "neutral").lower(),
            "confidence": lines.get("CONFIDENCE", "0"),
        }

    # -- Layer 3: Prolog (SWI-Prolog) ----------------------------------------
    def prolog_layer(self, tokens: list[str], lang: str) -> dict:
        t0 = time.perf_counter()
        cmd = [SWIPL_BIN, str(PROLOG_SCRIPT), lang, *tokens[:20]]
        res = proc.run(cmd)
        dur = round((time.perf_counter() - t0) * 1000, 2)
        lines = res["lines"]
        return {
            "engine": "Prolog (SWI-Prolog)", "status": "ok" if res["ok"] else "error",
            "output": lines.get("TRACE", res["error"]), "duration_ms": dur,
            "matched_intents": lines.get("MATCHED_INTENTS", "[]"),
            "back_translation": lines.get("BACK_TRANSLATION", "none"),
        }

    # -- Layer 4: Common Lisp (SBCL) -----------------------------------------
    def lisp_layer(self, tokens: list[str], corpus_path: Optional[Path]) -> dict:
        t0 = time.perf_counter()
        cmd = [SBCL_BIN, "--script", str(LISP_SCRIPT), ",".join(tokens)]
        if corpus_path:
            cmd.append(str(corpus_path))
        res = proc.run(cmd, timeout=8.0)
        dur = round((time.perf_counter() - t0) * 1000, 2)
        lines = res["lines"]
        return {
            "engine": "Common Lisp (SBCL)", "status": "ok" if res["ok"] else "error",
            "output": lines.get("TRACE", res["error"]), "duration_ms": dur,
            "match_line": lines.get("MATCH-LINE", ""), "match_score": lines.get("MATCH-SCORE", "0"),
        }

    # -- Layer 5: OCaml (compiled native) ------------------------------------
    def ocaml_layer(self, prompt: str) -> dict:
        t0 = time.perf_counter()
        res = proc.run([str(OCAML_BIN), prompt])
        dur = round((time.perf_counter() - t0) * 1000, 2)
        if not res["ok"] and not res["lines"]:
            return {"engine": "OCaml", "status": "error", "output": res["error"] or "binary missing",
                    "duration_ms": dur, "normalised": prompt.strip()}
        lines = res["lines"]
        return {
            "engine": "OCaml (native)", "status": lines.get("STATUS", "unknown"),
            "output": lines.get("TRACE", ""), "duration_ms": dur,
            "normalised": lines.get("NORMALISED", prompt.strip()),
        }

    # -- Layer 6: C++ (compiled native) --------------------------------------
    def cpp_layer(self, query: str, candidates: list[str]) -> dict:
        t0 = time.perf_counter()
        cmd = [str(CPP_BIN), query, *candidates[:15]]
        res = proc.run(cmd)
        dur = round((time.perf_counter() - t0) * 1000, 2)
        lines = res["lines"]
        return {
            "engine": "C++ (native)", "status": "ok" if res["ok"] else "error",
            "output": lines.get("TRACE", res["error"]), "duration_ms": dur,
            "best_match": lines.get("BEST_MATCH", "none"),
            "edit_distance": lines.get("EDIT_DISTANCE", "-1"),
            "ue_payload": lines.get("UE_REMOTE_CONTROL_PAYLOAD", ""),
        }

    # -- Layer 7: Mercury (documented Python re-implementation) -------------
    def mercury_layer(self, matches: list[str]) -> dict:
        t0 = time.perf_counter()
        result = mercury_classify(matches)
        return {
            "engine": result["engine"], "status": "ok",
            "output": result["trace"], "duration_ms": round((time.perf_counter() - t0) * 1000, 2),
            "determinism": result["determinism"],
        }

    # -- Full pipeline ---------------------------------------------------------
    def run(self, prompt: str, lang: str, chat_id: str) -> dict:
        steps = []

        py = self.python_layer(prompt, lang)
        steps.append(py)
        effective_lang = py["effective_lang"]
        tokens = py["tokens"]

        scheme = self.scheme_layer(tokens, effective_lang)
        steps.append(scheme)

        prolog = self.prolog_layer(tokens, effective_lang)
        steps.append(prolog)

        retrieval_hits = self.knowledge.search(prompt, effective_lang, top_k=5)
        top_lines = [h["line"] for h in retrieval_hits]

        lisp = self.lisp_layer(tokens, self.knowledge.primary_corpus_path())
        steps.append(lisp)

        ocaml = self.ocaml_layer(prompt)
        steps.append(ocaml)

        cpp = self.cpp_layer(prompt, top_lines or [""])
        steps.append(cpp)

        mercury = self.mercury_layer([h for h in top_lines if h])
        steps.append(mercury)

        final_answer, source = self._compose_answer(
            prompt=prompt, lang=effective_lang, scheme=scheme,
            retrieval_hits=retrieval_hits, lisp=lisp, cpp=cpp,
        )

        validation = validate_output(final_answer, effective_lang)

        return {
            "chat_id": chat_id,
            "lang": effective_lang,
            "reasoning_steps": steps,
            "final_answer": final_answer,
            "knowledge_source": source,
            "output_valid": validation["valid"],
        }

    def _compose_answer(self, prompt, lang, scheme, retrieval_hits, lisp, cpp) -> tuple[str, str]:
        intent = scheme.get("intent", "lookup")
        canned = CANNED_REPLIES.get(intent, {}).get(lang) or CANNED_REPLIES.get(intent, {}).get("en")
        if canned:
            return canned, "scheme:intent"

        if retrieval_hits:
            best = retrieval_hits[0]
            if best["score"] > 0.05:
                return best["line"], f"retrieval:{best['source']}"

        if lisp.get("match_line") and lisp.get("match_score", "0") not in ("0", ""):
            return lisp["match_line"], "lisp:exact-match"

        if cpp.get("best_match") not in (None, "none", ""):
            return f"Closest known phrase: \"{cpp['best_match']}\".", "cpp:fuzzy-match"

        defaults = {
            "en": f'I do not have a confident answer for "{prompt}" yet. Drop more information into api/inf/teach/ and I will learn it.',
            "fr": f'Je n\'ai pas encore de reponse sure pour "{prompt}". Ajoutez des informations dans api/inf/teach/ pour que j\'apprenne.',
            "rw": f'Simbizi neza igisubizo cya "{prompt}". Ongeraho amakuru muri api/inf/teach/ kugira ngo nyige.',
        }
        return defaults.get(lang, defaults["en"]), "default"


CANNED_REPLIES = {
    "greeting": {
        "en": "Hello! I'm Winter AI -- a multi-language reasoning assistant. How can I help?",
        "fr": "Bonjour ! Je suis Winter AI, un assistant de raisonnement multi-langage. Comment puis-je vous aider ?",
        "rw": "Muraho! Ndi Winter AI, umufasha ukoresha ururimi rwinshi rwo gutekereza. Nigute nakugira?",
    },
    "thanks": {
        "en": "You're welcome!",
        "fr": "De rien !",
        "rw": "Ntacyo!",
    },
    "wellbeing": {
        "en": "I'm running well -- every engine is online. How can I help you today?",
        "fr": "Je fonctionne bien -- tous les moteurs sont actifs. Comment puis-je vous aider ?",
        "rw": "Ndakora neza -- imashini zose zirakora. Nakugira nte uyu munsi?",
    },
    "identity": {
        "en": "I'm Winter AI, a polyglot reasoning assistant that combines Python, Scheme, Prolog, Common Lisp, OCaml, C++ and Mercury-style logic.",
        "fr": "Je suis Winter AI, un assistant de raisonnement polyglotte combinant Python, Scheme, Prolog, Common Lisp, OCaml, C++ et une logique inspiree de Mercury.",
        "rw": "Ndi Winter AI, umufasha ukoresha indimi nyinshi mu gutekereza.",
    },
    "farewell": {
        "en": "Goodbye! Talk soon.",
        "fr": "Au revoir !",
        "rw": "Murabeho!",
    },
}
