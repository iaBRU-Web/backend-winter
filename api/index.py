"""
Winter AI - Backend (Real 7-language reasoning pipeline)
Created by INEZA Aime Bruno, Rwanda

Deploys to Render.com (or any Docker host). CORS is open by default so it
can be called from a Vercel-hosted frontend; set ALLOWED_ORIGINS to lock
it down once you know your frontend's URL.

Reasoning pipeline (7 layers, all real, no simulation):
  1. Python   - orchestration, language detection
  2. Prolog   - forward-chaining intent classification (SWI-Prolog subprocess)
  3. Retrieval- BM25 search over the knowledge base (pure Python)
  4. Mercury  - determinism/confidence check (Python port of engine.m; see engines/mercury/)
  5. OCaml    - UTF-8 validation (native compiled binary)
  6. LISP     - symbolic tokenization (SBCL subprocess)
  7. C++/Schema - Unreal Engine payload formatting (native compiled binary) + output validation
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from typing import Optional
import logging
import os
import re
import time

from .engines.retrieval import Retriever, build_corpus_from_knowledge
from .engines.mercury.determinism import determinism_check
from .engines.schema.validator import validate as schema_validate
from .engines import orchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("winter")

app = FastAPI(
    title="Winter AI",
    description="Multi-paradigm reasoning engine — EN → FR → RW (hypertrained)",
    version="3.0.0",
)

allowed_origins_env = os.environ.get("ALLOWED_ORIGINS", "*")
allowed_origins = ["*"] if allowed_origins_env == "*" else [o.strip() for o in allowed_origins_env.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allowed_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Globals ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
BRAIN_FILE = BASE_DIR / "brain.txt"
INFO_DIR = BASE_DIR / "info"
TEACH_DIR = INFO_DIR / "teach"

BRAIN_TEXT: str = ""
KNOWLEDGE_BASE: dict[str, str] = {}
retriever = Retriever()

KINYARWANDA_WORDS = {
    "muraho", "murakoze", "amakuru", "ni", "meza", "umukino", "kode",
    "ineza", "uyu", "iyo", "ubwo", "kandi", "ariko", "cyane", "neza",
    "bite", "ese", "ndashaka", "nagira", "ngo",
}
FRENCH_CHARS = set("éèêëàâùûüîïôçœæ")


def rebuild_index() -> None:
    corpus = build_corpus_from_knowledge(BRAIN_TEXT, KNOWLEDGE_BASE)
    retriever.index_corpus(corpus)
    logger.info(f"Retrieval index rebuilt: {len(corpus)} documents")


def _load_knowledge_dir(directory: Path, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    if not directory.exists():
        return out
    for f in sorted(directory.glob("*")):
        if f.is_file() and f.suffix in (".txt", ".md"):
            try:
                key = f"{prefix}{f.name}" if prefix else f.name
                out[key] = f.read_text(encoding="utf-8")
            except Exception as e:  # noqa: BLE001
                logger.error(f"Failed to load {f}: {e}")
    return out


@app.on_event("startup")
async def startup_event():
    global BRAIN_TEXT, KNOWLEDGE_BASE
    INFO_DIR.mkdir(parents=True, exist_ok=True)
    TEACH_DIR.mkdir(parents=True, exist_ok=True)

    BRAIN_TEXT = BRAIN_FILE.read_text(encoding="utf-8") if BRAIN_FILE.exists() \
        else "Winter AI is a multi-paradigm reasoning engine."

    KNOWLEDGE_BASE = _load_knowledge_dir(INFO_DIR)
    KNOWLEDGE_BASE.update(_load_knowledge_dir(TEACH_DIR, prefix="teach/"))

    rebuild_index()
    logger.info(f"Winter AI ready. Knowledge files: {list(KNOWLEDGE_BASE.keys())}")
    logger.info(f"allowed_origins={allowed_origins}")


# ── Language detection ──────────────────────────────────────────────────
def detect_language(text: str) -> str:
    lower = text.lower()
    words = set(re.findall(r"\w+", lower))

    if words & KINYARWANDA_WORDS and any(
        w in lower for w in ["muraho", "murakoze", "amakuru", "umukino"]
    ):
        return "rw"

    fr_hits = sum(1 for c in text if c.lower() in FRENCH_CHARS)
    french_words = {"bonjour", "merci", "comment", "vous", "je", "est", "une", "les"}
    if fr_hits >= 1 or len(words & french_words) >= 2:
        return "fr"

    return "en"


# ── Pydantic models ──────────────────────────────────────────────────────
class MessageRequest(BaseModel):
    prompt: str
    chat_id: str
    lang: str = "en"


class ParadigmStep(BaseModel):
    engine: str
    status: str
    output: str
    duration_ms: float


class MessageResponse(BaseModel):
    chat_id: str
    lang: str
    reasoning_steps: list[ParadigmStep]
    final_answer: str
    knowledge_source: str


class BrainUpdateRequest(BaseModel):
    content: str


class ReasonRequest(BaseModel):
    prompt: str
    lang: str = "en"


class HealthResponse(BaseModel):
    status: str
    version: str
    knowledge_files: list[str]
    brain_size: int
    indexed_documents: int
    toolchains: dict[str, bool]


# ── Canned intent responses ───────────────────────────────────────────────
CANNED = {
    "greeting": {
        "en": "Hello! I am Winter AI, your multi-paradigm reasoning assistant. How can I help you today?",
        "fr": "Bonjour ! Je suis Winter AI, votre assistant de raisonnement multi-paradigme. Comment puis-je vous aider ?",
        "rw": "Muraho! Ndi Winter AI, umufasha wawe wo gutekereza. Nigute nakugira?",
    },
    "thanks": {
        "en": "You're welcome! Winter AI is here to assist you.",
        "fr": "De rien ! Winter AI est là pour vous aider.",
        "rw": "Ntacyo! Winter AI iri hano kugufasha.",
    },
    "wellbeing": {
        "en": "I'm running perfectly — all 7 reasoning layers online. How can I assist you?",
        "fr": "Je fonctionne parfaitement — les 7 couches de raisonnement sont actives. Comment puis-je vous aider ?",
        "rw": "Ndakora neza — ingingo 7 zose zirakora. Nakugira nte?",
    },
    "farewell": {
        "en": "Goodbye! Come back anytime.",
        "fr": "Au revoir ! Revenez quand vous voulez.",
        "rw": "Murabeho! Garuka igihe cyose ubishaka.",
    },
    "identity": {
        "en": "I'm Winter AI, a multi-paradigm reasoning assistant created by INEZA Aime Bruno in Rwanda.",
        "fr": "Je suis Winter AI, un assistant de raisonnement multi-paradigme créé par INEZA Aime Bruno au Rwanda.",
        "rw": "Ndi Winter AI, umufasha wo gutekereza wakozwe na INEZA Aime Bruno mu Rwanda.",
    },
    "capabilities": {
        "en": "I can chat, search my knowledge base, and reason step by step across 7 real language engines: Python, Prolog, Mercury, OCaml, LISP, C++, and Schema.",
        "fr": "Je peux discuter, chercher dans ma base de connaissances, et raisonner étape par étape sur 7 moteurs.",
        "rw": "Nshobora kuganira, gushakisha mu bumenyi bwanjye, no gutekereza mu ngingo 7.",
    },
    "architecture": {
        "en": "I run a 7-layer pipeline across real language runtimes: Prolog for decisions, BM25 retrieval, Mercury-style determinism checking, OCaml for validation, LISP for tokenization, and C++ for output formatting.",
        "fr": "J'exécute un pipeline à 7 couches utilisant Prolog, une recherche BM25, une vérification de déterminisme, OCaml, LISP et C++.",
        "rw": "Nkoresha ingingo 7 zikurikirana harimo Prolog, gushakisha, na OCaml, LISP, na C++.",
    },
}


def build_final_answer(prompt: str, raw: str, lang: str, intent: str, top_score: float) -> str:
    if intent in CANNED:
        return CANNED[intent].get(lang, CANNED[intent]["en"])

    if raw and top_score >= 0.5 and raw.lower() != prompt.lower():
        clean = re.sub(r"^(EN|FR|RW):\s*", "", raw, flags=re.IGNORECASE).strip()
        if clean:
            return clean

    defaults = {
        "en": f"I don't have a confident answer for \"{prompt}\" yet. Teach me by dropping a fact into api/info/teach/ or calling /api/v1/knowledge/upload.",
        "fr": f"Je n'ai pas encore de réponse fiable pour « {prompt} ». Ajoutez un fait dans api/info/teach/ pour m'enseigner.",
        "rw": f"Sinabonye igisubizo cyizewe cya \"{prompt}\". Nyibwira wongera ikintu muri api/info/teach/.",
    }
    return defaults.get(lang, defaults["en"])


# ── Routes ────────────────────────────────────────────────────────────────
@app.post("/api/v1/chats/message", response_model=MessageResponse)
async def chat_message(req: MessageRequest):
    steps: list[ParadigmStep] = []

    # 1. Python layer
    t0 = time.perf_counter()
    detected = detect_language(req.prompt)
    effective_lang = req.lang if req.lang != "en" else detected
    steps.append(ParadigmStep(
        engine="Python", status="ok",
        output=f"Detected language: {detected} | Effective: {effective_lang} | Tokens: {len(req.prompt.split())}",
        duration_ms=round((time.perf_counter() - t0) * 1000, 2),
    ))

    # 2. Prolog layer (real swipl subprocess)
    t0 = time.perf_counter()
    prolog_result = orchestrator.run_prolog(req.prompt)
    intent = prolog_result.get("intent", "knowledge_query") if prolog_result.get("ok") else "knowledge_query"
    steps.append(ParadigmStep(
        engine="Prolog",
        status="ok" if prolog_result.get("ok") else "warn",
        output=(f"intent={intent} sentiment={prolog_result.get('sentiment')}" if prolog_result.get("ok")
                else f"fallback (reason: {prolog_result.get('error')})"),
        duration_ms=round((time.perf_counter() - t0) * 1000, 2),
    ))

    # 3. Retrieval layer (BM25, pure Python)
    t0 = time.perf_counter()
    score, doc = retriever.best_match(req.prompt, lang=effective_lang)
    raw_answer = doc.text if doc else ""
    source = doc.source if doc else "brain.txt"
    steps.append(ParadigmStep(
        engine="Retrieval", status="ok",
        output=f"[{effective_lang.upper()}] BM25 search -> score={score:.3f} match='{raw_answer[:80]}' source={source}",
        duration_ms=round((time.perf_counter() - t0) * 1000, 2),
    ))

    # 4. Mercury layer (Python port of engine.m)
    t0 = time.perf_counter()
    results = retriever.search(req.prompt, top_k=2)
    second_score = results[1][0] if len(results) > 1 else 0.0
    verdict = determinism_check(score, second_score)
    steps.append(ParadigmStep(
        engine="Mercury", status="ok" if verdict == "confident" else "warn",
        output=f"determinism check -> {verdict} (top={score:.3f}, second={second_score:.3f})",
        duration_ms=round((time.perf_counter() - t0) * 1000, 2),
    ))

    # 5. OCaml layer (native compiled binary)
    t0 = time.perf_counter()
    ocaml_result = orchestrator.run_ocaml(raw_answer or req.prompt)
    steps.append(ParadigmStep(
        engine="OCaml",
        status="ok" if ocaml_result.get("ok") else "warn",
        output=(f"UTF-8 valid={ocaml_result.get('valid')} chars={ocaml_result.get('char_len')}"
                if ocaml_result.get("ok") else f"fallback (reason: {ocaml_result.get('error')})"),
        duration_ms=round((time.perf_counter() - t0) * 1000, 2),
    ))

    # 6. LISP layer (real sbcl subprocess)
    t0 = time.perf_counter()
    lisp_result = orchestrator.run_lisp(req.prompt)
    steps.append(ParadigmStep(
        engine="LISP",
        status="ok" if lisp_result.get("ok") else "warn",
        output=(f"S-expr: {lisp_result.get('sexpr')}" if lisp_result.get("ok")
                else f"fallback (reason: {lisp_result.get('error')})"),
        duration_ms=round((time.perf_counter() - t0) * 1000, 2),
    ))

    # 7. C++ layer (native compiled binary) + Schema validation
    t0 = time.perf_counter()
    final_answer = build_final_answer(req.prompt, raw_answer, effective_lang, intent, score)
    cpp_result = orchestrator.run_cpp(final_answer)
    schema_result = schema_validate(final_answer, effective_lang)
    steps.append(ParadigmStep(
        engine="C++/Schema",
        status="ok" if (cpp_result.get("ok") and schema_result["valid"]) else "warn",
        output=(f"payload_len={cpp_result.get('length', '?')} schema_valid={schema_result['valid']}"),
        duration_ms=round((time.perf_counter() - t0) * 1000, 2),
    ))

    return MessageResponse(
        chat_id=req.chat_id,
        lang=effective_lang,
        reasoning_steps=steps,
        final_answer=final_answer,
        knowledge_source=source,
    )


@app.post("/api/v1/reason")
async def reason_debug(req: ReasonRequest):
    """Inspect the raw Prolog decision output + BM25 ranking for a prompt."""
    prolog_result = orchestrator.run_prolog(req.prompt)
    lisp_result = orchestrator.run_lisp(req.prompt)
    results = retriever.search(req.prompt, top_k=5)
    return {
        "prolog": prolog_result,
        "lisp": lisp_result,
        "top_matches": [
            {"score": round(s, 4), "text": d.text, "source": d.source, "lang": d.lang}
            for s, d in results
        ],
    }


@app.post("/api/v1/brain/update")
async def update_brain(req: BrainUpdateRequest):
    global BRAIN_TEXT
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    BRAIN_FILE.write_text(req.content, encoding="utf-8")
    BRAIN_TEXT = req.content
    rebuild_index()
    return {"status": "updated", "size": len(req.content), "indexed_documents": len(retriever.docs)}


@app.post("/api/v1/knowledge/upload")
async def upload_knowledge(file: UploadFile = File(...)):
    """Uploads go straight into api/info/teach/ so curated core knowledge
    (dictionary/grammar/logics/info/qa) stays separate from user-taught facts."""
    global KNOWLEDGE_BASE
    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".txt", ".md"):
        raise HTTPException(status_code=400, detail="Only .txt and .md files allowed")
    TEACH_DIR.mkdir(parents=True, exist_ok=True)
    dest = TEACH_DIR / Path(file.filename).name
    content = await file.read()
    dest.write_bytes(content)
    decoded = content.decode("utf-8")
    KNOWLEDGE_BASE[f"teach/{file.filename}"] = decoded
    rebuild_index()
    return {"status": "uploaded", "filename": f"teach/{file.filename}", "size": len(decoded)}


@app.get("/api/v1/knowledge/list")
async def list_knowledge():
    files = [{"name": n, "size": len(c), "lines": c.count("\n") + 1} for n, c in KNOWLEDGE_BASE.items()]
    return {"files": files, "count": len(files)}


@app.get("/api/v1/knowledge/{filename:path}")
async def get_knowledge_file(filename: str):
    if filename not in KNOWLEDGE_BASE:
        raise HTTPException(status_code=404, detail="File not found")
    return {"name": filename, "content": KNOWLEDGE_BASE[filename]}


@app.get("/api/v1/brain")
async def get_brain():
    return {"content": BRAIN_TEXT, "size": len(BRAIN_TEXT)}


@app.get("/api/v1/health", response_model=HealthResponse)
async def health():
    import shutil as _shutil
    return HealthResponse(
        status="online",
        version="3.0.0",
        knowledge_files=list(KNOWLEDGE_BASE.keys()),
        brain_size=len(BRAIN_TEXT),
        indexed_documents=len(retriever.docs),
        toolchains={
            "prolog": _shutil.which("swipl") is not None,
            "lisp": _shutil.which("sbcl") is not None,
            "ocaml_binary": (BASE_DIR / "engines" / "ocaml" / "validator").exists(),
            "cpp_binary": (BASE_DIR / "engines" / "cpp" / "formatter").exists(),
        },
    )


@app.get("/")
async def root():
    return {
        "name": "Winter AI",
        "tagline": "Multi-paradigm reasoning engine — EN → FR → RW (hypertrained)",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
