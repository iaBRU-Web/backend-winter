# Winter AI — Backend ❄️

**Multi-paradigm reasoning engine — EN → FR → RW**
Created by INEZA Aime Bruno, Rwanda

Deploy target: **GitHub → Render.com** (Docker). This package is not meant
to be run locally — push it to a GitHub repo and connect that repo to a new
Render Web Service (Render reads `render.yaml` automatically, or you can
configure a Docker service manually pointing at `Dockerfile`).

## Real 7-language reasoning pipeline

Every layer genuinely executes in its own language runtime — nothing here
is a Python simulation of another language:

| # | Layer | Runtime | What it does |
|---|-------|---------|---------------|
| 1 | **Python** | CPython | Orchestration, language detection (`api/index.py`) |
| 2 | **Prolog** | SWI-Prolog (`swipl`), real subprocess | Forward-chaining intent classification (`api/engines/prolog/rules.pl`) |
| 3 | **Retrieval** | Pure Python | BM25-ranked search over the knowledge base (`api/engines/retrieval.py`) |
| 4 | **Mercury** | Python port of `engine.m`'s algorithm | Determinism/confidence check (`api/engines/mercury/`) |
| 5 | **OCaml** | Native binary, compiled with `ocamlopt` in the Docker build | UTF-8 validation (`api/engines/ocaml/validator.ml`) |
| 6 | **LISP** | SBCL (`sbcl --script`), real subprocess | Symbolic tokenization into S-expressions (`api/engines/lisp/tokenizer.lisp`) |
| 7 | **C++ / Schema** | Native binary, compiled with `g++` in the Docker build, + Python schema check | Unreal-Engine-style payload formatting + final output validation |

**Why Mercury is a Python port, not a compiled binary:** the Mercury
compiler (`mmc`) isn't available through the standard Debian/Ubuntu apt
repositories that Docker base images (and Render's build environment) can
reach. `api/engines/mercury/engine.m` is kept as the authoritative
reference source — `api/engines/mercury/determinism.py` is a line-for-line
port of the exact same `determinism_check/6` predicate, so the logic is
identical even though it isn't shelled out to a compiled Mercury binary.

## Docker build (multi-stage)

`Dockerfile` has two stages:
1. **builder** (`debian:bookworm-slim` + `g++` + `ocaml-nox`) compiles
   `formatter.cpp` and `validator.ml` into native binaries.
2. **runtime** (`python:3.11-slim` + `swi-prolog` + `sbcl`) copies in just
   those two compiled binaries — no compiler toolchain ships in the final
   image, keeping it small.

Render builds this automatically from `render.yaml`.

## Deploying

1. Push this folder to a GitHub repository.
2. On Render: **New → Web Service → connect the repo** → Render detects
   `render.yaml` and builds the Docker image automatically. (Or configure
   manually: Environment = Docker, Dockerfile path = `./Dockerfile`.)
3. Once live, note your service URL, e.g. `https://winter-ai-backend.onrender.com`.
4. In your Vercel-hosted frontend, set `VITE_BACKEND_URL` to
   `https://winter-ai-backend.onrender.com/api/v1`.
5. Optional but recommended: once you know your Vercel URL, set the
   `ALLOWED_ORIGINS` env var on Render to that exact URL instead of `*`
   to lock down CORS.

Render's free tier spins down when idle — the first request after a
period of inactivity can take ~30-60s to wake up.

## Teaching Winter new things — `api/info/teach/`

Drop any `.txt` or `.md` file into `api/info/teach/` and it's indexed
automatically at startup — no code changes, no retraining. This folder is
kept separate from the curated core knowledge files
(`dictionary.txt`, `grammar.txt`, `logics.txt`, `info.txt`, `qa.txt`) in
`api/info/`, so your own additions never get overwritten by updates to the
core knowledge base.

You can also teach it live once deployed:

```
POST /api/v1/knowledge/upload      (multipart .txt/.md file -> saved into api/info/teach/)
POST /api/v1/brain/update          { "content": "..." }   (replaces brain.txt)
```

Facts follow the pattern `EN: fact | FR: fait | RW: ukuri` for trilingual
lines, or a plain sentence for English-only facts.

## API Endpoints

```
POST /api/v1/chats/message       — Chat with Winter AI (runs the full 7-layer pipeline)
POST /api/v1/reason              — Debug: raw Prolog/LISP output + BM25 ranking for a prompt
POST /api/v1/brain/update        — Replace brain.txt
POST /api/v1/knowledge/upload    — Upload a new knowledge file into api/info/teach/
GET  /api/v1/knowledge/list      — List all indexed knowledge files
GET  /api/v1/knowledge/{file}    — Read a knowledge file
GET  /api/v1/brain               — Read brain.txt
GET  /api/v1/health              — Health check + which toolchains are live
GET  /docs                       — Swagger UI
```

## Local development (optional)

You don't need this to deploy, but if you want to run it on your own
machine while developing: install Python 3.11+, SWI-Prolog, SBCL, OCaml,
and a C++ compiler, then:

```
pip install -r requirements.txt
ocamlopt api/engines/ocaml/validator.ml -o api/engines/ocaml/validator
g++ -O2 -std=c++17 api/engines/cpp/formatter.cpp -o api/engines/cpp/formatter
uvicorn api.index:app --reload --port 10000
```

If a toolchain isn't installed, that layer degrades gracefully (reports
`status: "warn"` with a reason) instead of crashing the whole pipeline.
