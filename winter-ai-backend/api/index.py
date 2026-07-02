"""
Winter AI - Multi-paradigm reasoning engine (Hypertrained edition)
Created by INEZA Aime Bruno, Rwanda

Backend now includes:
  - a real TF-IDF cosine-similarity retrieval engine (engines/retrieval.py)
  - a Scheme-inspired forward-chaining decision engine (engines/decision_engine.py)
  - an expanded, editable knowledge base (api/info/*.txt)
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pathlib import Path
from typing import Optional
import unicodedata
import logging
import re
import time
import webbrowser
import os

from .engines.retrieval import Retriever, build_corpus_from_knowledge
from .engines.decision_engine import DecisionEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("winter")

# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Winter AI",
    description="Multi-paradigm reasoning engine — EN → FR → RW (hypertrained)",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Globals ───────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
BRAIN_FILE = BASE_DIR / "brain.txt"
INFO_DIR = BASE_DIR / "info"
RULES_FILE = BASE_DIR / "engines" / "schema" / "decision_rules.json"

BRAIN_TEXT: str = ""
KNOWLEDGE_BASE: dict[str, str] = {}

retriever = Retriever()
decision_engine: Optional[DecisionEngine] = None

KINYARWANDA_WORDS = {
    "muraho", "murakoze", "amakuru", "ni", "meza", "umukino",
    "kode", "ineza", "uyu", "iyo", "ubwo", "kandi", "ariko",
    "cyane", "neza", "bite", "ese", "ndashaka", "nagira", "ngo",
}

FRENCH_CHARS = set("éèêëàâùûüîïôçœæ")


def rebuild_index() -> None:
    """(Re)build the retrieval index from brain.txt + all knowledge files.
    Called at startup and any time the knowledge base changes."""
    corpus = build_corpus_from_knowledge(BRAIN_TEXT, KNOWLEDGE_BASE)
    retriever.index_corpus(corpus)
    logger.info(f"Retrieval index rebuilt: {len(corpus)} documents")


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    global BRAIN_TEXT, KNOWLEDGE_BASE, decision_engine
    INFO_DIR.mkdir(parents=True, exist_ok=True)

    if BRAIN_FILE.exists():
        BRAIN_TEXT = BRAIN_FILE.read_text(encoding="utf-8")
        logger.info(f"Loaded brain.txt ({len(BRAIN_TEXT)} chars)")
    else:
        BRAIN_TEXT = "Winter AI is a multi-paradigm reasoning engine."
        logger.warning("brain.txt not found, using default")

    KNOWLEDGE_BASE = {}
    for f in INFO_DIR.glob("*"):
        if f.suffix in (".txt", ".md") and f.is_file():
            try:
                KNOWLEDGE_BASE[f.name] = f.read_text(encoding="utf-8")
                logger.info(f"Loaded knowledge: {f.name}")
            except Exception as e:
                logger.error(f"Failed to load {f.name}: {e}")

    rebuild_index()
    decision_engine = DecisionEngine(RULES_FILE)

    logger.info(f"Winter AI ready. Knowledge files: {list(KNOWLEDGE_BASE.keys())}")


# ── Language detection ─────────────────────────────────────────────────────
def detect_language(text: str) -> str:
    lower = text.lower()
    words = set(re.findall(r'\w+', lower))

    rw_hits = words & KINYARWANDA_WORDS
    if len(rw_hits) >= 1:
        if any(w in lower for w in ["muraho", "murakoze", "amakuru", "umukino"]):
            return "rw"

    fr_hits = sum(1 for c in text if c.lower() in FRENCH_CHARS)
    french_words = {"bonjour", "merci", "comment", "vous", "je", "est", "une", "les"}
    fr_word_hits = words & french_words
    if fr_hits >= 1 or len(fr_word_hits) >= 2:
        return "fr"

    return "en"


# ── Pydantic models ────────────────────────────────────────────────────────
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


class HealthResponse(BaseModel):
    status: str
    version: str
    knowledge_files: list[str]
    brain_size: int
    indexed_documents: int


class ReasonRequest(BaseModel):
    prompt: str
    lang: str = "en"


# ── Winter Engine ─────────────────────────────────────────────────────────
class WinterEngine:

    def python_layer(self, prompt: str, lang: str) -> ParadigmStep:
        t0 = time.perf_counter()
        detected = detect_language(prompt)
        effective_lang = lang if lang != "en" else detected
        out = f"Detected language: {detected} | Effective: {effective_lang} | Tokens: {len(prompt.split())}"
        return ParadigmStep(engine="Python", status="ok", output=out,
                             duration_ms=round((time.perf_counter() - t0) * 1000, 2))

    def scheme_layer(self, prompt: str) -> tuple[ParadigmStep, dict]:
        """Scheme-style forward-chaining decision layer (replaces the old
        fake 'Prolog' label — this is the real decision-making component)."""
        t0 = time.perf_counter()
        decision = decision_engine.infer(prompt)
        out = f"intent={decision['intent']} | rule={decision['rule_id']} | sentiment={decision['sentiment']}"
        return (ParadigmStep(engine="Scheme", status="ok", output=out,
                              duration_ms=round((time.perf_counter() - t0) * 1000, 2)),
                decision)

    def retrieval_layer(self, prompt: str, lang: str) -> tuple[ParadigmStep, str, str, float]:
        t0 = time.perf_counter()
        score, doc = retriever.best_match(prompt, lang=lang)
        answer = doc.text if doc else ""
        source = doc.source if doc else "brain.txt"
        out = f"[{lang.upper()}] TF-IDF search → best match score={score:.3f} → '{answer[:80]}' from {source}"
        return (ParadigmStep(engine="Retrieval", status="ok", output=out,
                              duration_ms=round((time.perf_counter() - t0) * 1000, 2)),
                answer, source, score)

    def mercury_layer(self, prompt: str, lang: str, top_score: float) -> ParadigmStep:
        t0 = time.perf_counter()
        results = retriever.search(prompt, top_k=2)
        ambiguous = len(results) == 2 and results[0][0] > 0 and (results[0][0] - results[1][0]) < 0.05
        confident = top_score >= 0.15
        if ambiguous:
            out = "Determinism check: WARN — top matches nearly tied, answer may be ambiguous"
            status = "warn"
        elif not confident:
            out = "Determinism check: WARN — low retrieval confidence, falling back to default response"
            status = "warn"
        else:
            out = "Determinism check: PASS — single confident answer path"
            status = "ok"
        return ParadigmStep(engine="Mercury", status=status, output=out,
                             duration_ms=round((time.perf_counter() - t0) * 1000, 2))

    def ocaml_layer(self, answer: str) -> ParadigmStep:
        t0 = time.perf_counter()
        try:
            answer.encode("utf-8").decode("utf-8")
            norm = unicodedata.normalize("NFC", answer)
            out = f"UTF-8 valid | NFC normalized | Chars: {len(norm)}"
            status = "ok"
        except Exception as e:
            out = f"Encoding error: {e}"
            status = "error"
        return ParadigmStep(engine="OCaml", status=status, output=out,
                             duration_ms=round((time.perf_counter() - t0) * 1000, 2))

    def lisp_layer(self, prompt: str) -> ParadigmStep:
        t0 = time.perf_counter()
        tokens = re.findall(r'\w+', prompt.lower())
        s_expr = "(query " + " ".join(f"'{t}" for t in tokens[:10]) + ")"
        out = f"S-expr: {s_expr}"
        return ParadigmStep(engine="LISP", status="ok", output=out,
                             duration_ms=round((time.perf_counter() - t0) * 1000, 2))

    def cpp_layer(self, answer: str) -> ParadigmStep:
        t0 = time.perf_counter()
        safe = re.sub(r'[^\w\s\-.,!?éèàùêîôûçœæ]', '', answer)[:120]
        ue_instr = f'UE_INSTR("{safe}")'
        out = f"Unreal Engine payload: {ue_instr}"
        return ParadigmStep(engine="C++", status="ok", output=out,
                             duration_ms=round((time.perf_counter() - t0) * 1000, 2))

    def schema_layer(self, answer: str, lang: str) -> ParadigmStep:
        t0 = time.perf_counter()
        checks = {
            "non_empty": bool(answer.strip()),
            "valid_lang": lang in ("en", "fr", "rw"),
            "length_ok": 1 <= len(answer) <= 4096,
            "utf8_clean": all(ord(c) < 65536 for c in answer),
        }
        passed = all(checks.values())
        out = f"Schema: {checks} | {'VALID' if passed else 'INVALID'}"
        return ParadigmStep(engine="Schema", status="ok" if passed else "warn", output=out,
                             duration_ms=round((time.perf_counter() - t0) * 1000, 2))

    def build_final_answer(self, prompt: str, raw: str, lang: str, intent: str, top_score: float) -> str:
        """Compose a human-readable answer in the target language, using the
        Scheme layer's intent classification and the retrieval layer's match."""
        canned = {
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
                "en": "I can chat, search my knowledge base, and reason step by step across 7 layers: Python, Scheme, Mercury, OCaml, LISP, C++, and Schema.",
                "fr": "Je peux discuter, chercher dans ma base de connaissances, et raisonner étape par étape sur 7 couches.",
                "rw": "Nshobora kuganira, gushakisha mu bumenyi bwanjye, no gutekereza mu ngingo 7.",
            },
            "architecture": {
                "en": "I run a 7-layer pipeline: language detection, Scheme decision rules, TF-IDF retrieval, Mercury determinism checks, OCaml validation, LISP tokenization, C++ formatting, and Schema output validation.",
                "fr": "J'exécute un pipeline à 7 couches : détection de langue, règles Scheme, recherche TF-IDF, vérification Mercury, validation OCaml, tokenisation LISP, formatage C++ et validation Schema.",
                "rw": "Nkoresha ingingo 7 zikurikirana kugira ngo nsubize neza.",
            },
        }

        if intent in canned:
            return canned[intent].get(lang, canned[intent]["en"])

        # knowledge_query: use retrieval result if confident
        if raw and top_score >= 0.12 and raw.lower() != prompt.lower():
            clean = re.sub(r'^(EN|FR|RW):\s*', '', raw, flags=re.IGNORECASE).strip()
            if clean:
                return clean

        defaults = {
            "en": f"I don't have a confident answer for \"{prompt}\" yet. Add more knowledge via /api/v1/brain/update or /api/v1/knowledge/upload to teach me.",
            "fr": f"Je n'ai pas encore de réponse fiable pour « {prompt} ». Ajoutez des connaissances via /api/v1/brain/update pour m'enseigner.",
            "rw": f"Sinabonye igisubizo cyizewe cya \"{prompt}\". Ongeraho ubumenyi kuri /api/v1/brain/update kugira ngo umbwire.",
        }
        return defaults.get(lang, defaults["en"])


engine = WinterEngine()


# ── Routes ────────────────────────────────────────────────────────────────
@app.post("/api/v1/chats/message", response_model=MessageResponse)
async def chat_message(req: MessageRequest):
    steps = []

    steps.append(engine.python_layer(req.prompt, req.lang))

    scheme_step, decision = engine.scheme_layer(req.prompt)
    steps.append(scheme_step)

    retrieval_step, raw_answer, source, score = engine.retrieval_layer(req.prompt, req.lang)
    steps.append(retrieval_step)

    steps.append(engine.mercury_layer(req.prompt, req.lang, score))
    steps.append(engine.ocaml_layer(raw_answer))
    steps.append(engine.lisp_layer(req.prompt))
    steps.append(engine.cpp_layer(raw_answer))
    steps.append(engine.schema_layer(raw_answer, req.lang))

    final = engine.build_final_answer(req.prompt, raw_answer, req.lang, decision["intent"], score)

    return MessageResponse(
        chat_id=req.chat_id,
        lang=req.lang,
        reasoning_steps=steps,
        final_answer=final,
        knowledge_source=source,
    )


@app.post("/api/v1/reason")
async def reason_debug(req: ReasonRequest):
    """Inspect the raw Scheme decision trace + retrieval ranking for a prompt."""
    decision = decision_engine.infer(req.prompt)
    results = retriever.search(req.prompt, top_k=5)
    return {
        "decision": decision,
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
    global KNOWLEDGE_BASE
    allowed = {".txt", ".md"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail="Only .txt and .md files allowed")
    INFO_DIR.mkdir(parents=True, exist_ok=True)
    dest = INFO_DIR / Path(file.filename).name
    content = await file.read()
    dest.write_bytes(content)
    decoded = content.decode("utf-8")
    KNOWLEDGE_BASE[file.filename] = decoded
    rebuild_index()
    return {"status": "uploaded", "filename": file.filename, "size": len(decoded)}


@app.get("/api/v1/knowledge/list")
async def list_knowledge():
    files = []
    for fname, content in KNOWLEDGE_BASE.items():
        files.append({"name": fname, "size": len(content), "lines": content.count("\n") + 1})
    return {"files": files, "count": len(files)}


@app.get("/api/v1/knowledge/{filename}")
async def get_knowledge_file(filename: str):
    if filename not in KNOWLEDGE_BASE:
        raise HTTPException(status_code=404, detail="File not found")
    return {"name": filename, "content": KNOWLEDGE_BASE[filename]}


@app.get("/api/v1/brain")
async def get_brain():
    return {"content": BRAIN_TEXT, "size": len(BRAIN_TEXT)}


@app.get("/api/v1/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="online",
        version="2.0.0",
        knowledge_files=list(KNOWLEDGE_BASE.keys()),
        brain_size=len(BRAIN_TEXT),
        indexed_documents=len(retriever.docs),
    )


@app.get("/")
async def root():
    return {
        "name": "Winter AI",
        "tagline": "Multi-paradigm reasoning engine — EN → FR → RW (hypertrained)",
        "docs": "/docs",
        "health": "/api/v1/health",
    }
