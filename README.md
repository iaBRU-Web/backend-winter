# Winter AI — Backend (Hypertrained Edition) ❄️

**Multi-paradigm reasoning engine — EN → FR → RW**
Created by INEZA Aime Bruno, Rwanda

This is the backend only. It's a self-contained FastAPI service — no Node,
no GPU, no internet connection required once dependencies are installed.

## What's new in this edition

- **Real retrieval, not keyword counting.** `api/engines/retrieval.py` implements
  a genuine TF-IDF + cosine similarity search engine in pure Python, so answers
  are ranked by actual relevance.
- **A real decision/logic layer.** `api/engines/decision_engine.py` is a
  Scheme-inspired forward-chaining rule engine — the same idea as a Lisp
  `cond` expression. Rules live in `api/engines/schema/decision_rules.json`
  and can be edited or extended without touching any Python code. Call
  `POST /api/v1/reason` to see the literal S-expression trace of how Winter
  decided what your message meant.
- **A bigger, hypertrained knowledge base.** `api/brain.txt` and everything in
  `api/info/` (dictionary, grammar, logics, info, and a new `qa.txt`) has been
  substantially expanded. You can keep growing it live via the API — no
  retraining or restart needed.
- **Legacy paradigm sketches kept for reference** in `api/engines/legacy/`
  (Prolog, Mercury, OCaml, LISP, C++ source files) documenting the original
  multi-language design intent; the Python backend now performs the
  equivalent logic natively so the whole thing runs with just Python.

## Run it (no terminal typing needed)

- **Windows:** double-click `start_windows.bat`
- **macOS:** double-click `start_mac.command` (first time: right-click → Open,
  to bypass Gatekeeper's "unidentified developer" warning)
- **Linux:** double-click `start_linux.sh` (or run `bash start_linux.sh` if
  your file manager doesn't execute scripts directly)

Each script installs the Python dependencies automatically and opens
`http://localhost:10000/docs` (interactive Swagger UI) in your browser.

Requires **Python 3.10+**. If Python isn't installed, download it from
https://python.org (check "Add Python to PATH" during Windows setup).

## API Endpoints

```
POST /api/v1/chats/message       — Chat with Winter AI
POST /api/v1/reason              — Debug: see the raw decision trace + top retrieval matches
POST /api/v1/brain/update        — Update knowledge base
POST /api/v1/knowledge/upload    — Upload new knowledge file (.txt/.md)
GET  /api/v1/knowledge/list      — List knowledge files
GET  /api/v1/knowledge/{file}    — Read a knowledge file
GET  /api/v1/brain               — Read brain.txt
GET  /api/v1/health              — Health check
GET  /docs                       — Swagger UI
```

## Architecture — 7 reasoning layers per query

| Layer | Engine | Role |
|-------|--------|------|
| 1 | Python | Orchestration & language detection |
| 2 | Scheme | Forward-chaining decision rules (intent + sentiment) |
| 3 | Retrieval | TF-IDF cosine similarity search over the knowledge base |
| 4 | Mercury | Determinism / confidence check |
| 5 | OCaml | UTF-8 type validation |
| 6 | LISP | Symbolic tokenization |
| 7 | C++ / Schema | Unreal Engine formatting + final output validation |

## Teaching Winter new things

Add plain text to `api/brain.txt` or drop a new `.txt`/`.md` file in
`api/info/`, or call the API live:

```
POST /api/v1/knowledge/upload   (multipart file upload)
POST /api/v1/brain/update       { "content": "..." }
```

Facts follow the pattern `EN: fact | FR: fait | RW: ukuri` for trilingual
lines, or a plain sentence for English-only facts. The retrieval index
rebuilds automatically after every update.

## Deploying to the cloud (optional)

A `Dockerfile` and `render.yaml` are included if you'd rather deploy Winter
to Render.com or any Docker host instead of running it locally.
