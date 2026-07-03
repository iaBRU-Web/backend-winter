"""
Winter AI -- polyglot reasoning backend.
Created by INEZA Aime Bruno, Rwanda.

Pipeline per request: Python -> Scheme (Guile) -> Prolog (SWI-Prolog) ->
Common Lisp (SBCL) -> OCaml (native) -> C++ (native) -> Mercury-style check
-> TF-IDF retrieval ties it together and composes the final answer.

Deploy target: Render (Docker). See ../Dockerfile and ../render.yaml.
Frontend (deployed separately on Vercel) talks to this over CORS.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .engines.retrieval import KnowledgeIndex
from .engines.orchestrator import WinterOrchestrator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("winter")

app = FastAPI(
    title="Winter AI",
    description="Polyglot reasoning backend -- Python + Scheme + Prolog + Lisp + OCaml + C++ + Mercury-style logic",
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your Vercel domain once it's live
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
INFO_DIR = BASE_DIR / "info"
TEACH_DIR = BASE_DIR / "inf" / "teach"
BRAIN_FILE = INFO_DIR / "brain.txt"

knowledge = KnowledgeIndex(info_dir=INFO_DIR, teach_dir=TEACH_DIR)
orchestrator: Optional[WinterOrchestrator] = None


@app.on_event("startup")
async def startup_event():
    global orchestrator
    stats = knowledge.reload()
    orchestrator = WinterOrchestrator(knowledge)

    # Guile compiles each script to bytecode on its first run and caches the
    # result on disk; without this warm-up, whichever user sends the very
    # first chat message after a cold start would eat that one-time ~1s
    # compile cost. Firing it once here keeps that off the request path.
    try:
        orchestrator.scheme_layer(["hello"], "en")
        logger.info("Scheme (Guile) engine warmed up")
    except Exception as e:  # noqa: BLE001
        logger.warning("Scheme warm-up skipped: %s", e)

    logger.info("Winter AI ready. Loaded files: %s", stats["files"])


# ---- Models ----------------------------------------------------------------
class MessageRequest(BaseModel):
    prompt: str
    chat_id: str = "default"
    lang: str = "en"


class ParadigmStep(BaseModel):
    engine: str
    status: str
    output: str
    duration_ms: float


class MessageResponse(BaseModel):
    chat_id: str
    lang: str
    reasoning_steps: list[dict]
    final_answer: str
    knowledge_source: str
    output_valid: bool


class BrainUpdateRequest(BaseModel):
    content: str


class HealthResponse(BaseModel):
    status: str
    version: str
    engines: list[str]
    indexed_documents: int
    knowledge_files: list[str]
    teach_files: list[str]


# ---- Routes ------------------------------------------------------------------
@app.post("/api/v1/chats/message", response_model=MessageResponse)
async def chat_message(req: MessageRequest):
    if not req.prompt or not req.prompt.strip():
        raise HTTPException(status_code=400, detail="prompt cannot be empty")
    result = orchestrator.run(req.prompt, req.lang, req.chat_id)
    return result


@app.post("/api/v1/reason")
async def reason(req: MessageRequest):
    """Same pipeline, but framed for callers who just want the raw trace."""
    result = orchestrator.run(req.prompt, req.lang, req.chat_id)
    return {"trace": result["reasoning_steps"], "answer": result["final_answer"]}


@app.get("/api/v1/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="online",
        version="3.0.0",
        engines=["Python", "Scheme (Guile)", "Prolog (SWI-Prolog)", "Common Lisp (SBCL)",
                 "OCaml (native)", "C++ (native)", "Mercury-style (Python)"],
        indexed_documents=len(knowledge.index.docs),
        knowledge_files=[f for f in knowledge.loaded_files if f.startswith("info/")],
        teach_files=[f for f in knowledge.loaded_files if f.startswith("teach/")],
    )


@app.get("/api/v1/brain")
async def get_brain():
    text = BRAIN_FILE.read_text(encoding="utf-8") if BRAIN_FILE.exists() else ""
    return {"content": text, "size": len(text)}


@app.post("/api/v1/brain/update")
async def update_brain(req: BrainUpdateRequest):
    if not req.content.strip():
        raise HTTPException(status_code=400, detail="content cannot be empty")
    INFO_DIR.mkdir(parents=True, exist_ok=True)
    BRAIN_FILE.write_text(req.content, encoding="utf-8")
    stats = knowledge.reload()
    return {"status": "updated", "size": len(req.content), "documents": stats["documents"]}


# ---- Teach folder: api/inf/teach/ ------------------------------------------
@app.post("/api/v1/teach/upload")
async def teach_upload(file: UploadFile = File(...)):
    """Drop a .txt or .md file into api/inf/teach/ via the API (equivalent to
    just copying a file into that folder yourself before deploying)."""
    allowed = {".txt", ".md"}
    suffix = Path(file.filename).suffix.lower()
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail="Only .txt and .md files are accepted")
    TEACH_DIR.mkdir(parents=True, exist_ok=True)
    dest = TEACH_DIR / Path(file.filename).name
    content = await file.read()
    dest.write_bytes(content)
    stats = knowledge.reload()
    return {"status": "taught", "filename": file.filename, "documents": stats["documents"]}


@app.post("/api/v1/teach/reload")
async def teach_reload():
    """Re-scan api/info/ and api/inf/teach/ without restarting the server --
    use this after manually adding files to the teach folder and redeploying,
    or after uploading through /api/v1/teach/upload."""
    stats = knowledge.reload()
    return {"status": "reloaded", **stats}


@app.get("/api/v1/teach/list")
async def teach_list():
    return {
        "teach_dir": str(TEACH_DIR),
        "files": {k: v for k, v in knowledge.loaded_files.items() if k.startswith("teach/")},
    }


@app.get("/")
async def root():
    return {
        "name": "Winter AI",
        "tagline": "Polyglot reasoning backend -- Python, Scheme, Prolog, Common Lisp, OCaml, C++, Mercury-style logic",
        "docs": "/docs",
        "health": "/api/v1/health",
        "teach_folder": "api/inf/teach/ -- drop .txt or .md files here to teach Winter new information",
    }
