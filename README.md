# Winter AI -- Backend (polyglot reasoning engine)

Created by INEZA Aime Bruno, Rwanda.

Live at: **https://backend-winter.onrender.com** (once deployed -- see below)

A chat backend that genuinely runs seven language layers per request, not
seven Python functions wearing other languages' names:

| Layer | Runtime | Real job |
|---|---|---|
| Python | native | orchestration, language detection, TF-IDF retrieval |
| Scheme | GNU Guile (subprocess) | `cond`-based intent + sentiment classification |
| Prolog | SWI-Prolog (subprocess) | fact/rule intent matching + transitive translation via backtracking |
| Common Lisp | SBCL (subprocess) | symbolic frame building + exact keyword-overlap match |
| OCaml | compiled native binary | algebraic-type input validation (UTF-8, length, whitespace) |
| C++ | compiled native binary | Levenshtein fuzzy match + Unreal Engine Remote Control payload |
| Mercury-style | Python | determinism classification (`det`/`nondet`/`failure`) -- see note below |

## About the "Mercury" layer

Mercury's real compiler has no maintained package on modern Ubuntu/Debian
and bootstraps from itself, so building it from source takes 30-60+ minutes
-- impractical for a Render Docker build. Rather than quietly faking it (as
an earlier draft of this project did), `api/engines/mercury/determinism.py`
is an openly documented Python re-implementation of Mercury's determinism
concept. If you want to attempt a real from-source build anyway, see
`api/engines/mercury/BUILD_REAL_MERCURY.md`.

## Repository layout

```
api/
  index.py                  FastAPI app / routes
  engines/
    orchestrator.py         runs every layer per request, composes the answer
    proc.py                 shared subprocess helper
    retrieval.py            TF-IDF search + knowledge-file loading
    output_validator.py     final response-shape checks
    scheme/decision.scm     real Guile Scheme source
    prolog/knowledge.pl     real SWI-Prolog source
    lisp/reasoner.lisp      real Common Lisp (SBCL) source
    ocaml/validator.ml      real OCaml source (compiled in Docker build)
    cpp/engine.cpp          real C++ source (compiled in Docker build)
    mercury/                Python re-implementation + BUILD_REAL_MERCURY.md
  info/                     curated knowledge base (.txt, trilingual EN/FR/RW where relevant)
  inf/teach/                <-- drop your own .txt/.md files here to teach Winter new facts
Dockerfile                  multi-stage build: compiles C++/OCaml, then assembles the runtime image
render.yaml                 Render blueprint
requirements.txt
```

## Deploying (GitHub -> Render)

1. Push this repository to GitHub.
2. In Render: **New -> Blueprint**, point it at the repo. Render reads
   `render.yaml` and creates a Docker web service named `backend-winter`
   (giving you `https://backend-winter.onrender.com` if that name is free --
   otherwise Render will suggest an alternative and you can rename it).
3. First build installs Python, SWI-Prolog, SBCL, and GNU Guile, and
   compiles the C++/OCaml binaries -- expect the first build to take a few
   minutes. Subsequent deploys reuse Docker layer caching where possible.
4. Once live, check `GET /api/v1/health`.

No terminal access is required on Render itself -- the Dockerfile does
everything at build time.

### A note on cold starts

Guile compiles each `.scm` script to bytecode the first time it runs and
caches the result on disk. The app fires one throwaway Scheme call during
FastAPI startup specifically to absorb that one-time ~1s cost before any
real user hits it. SBCL and SWI-Prolog don't have this issue -- they're
consistently fast (10-40ms) on every call.

## Teaching Winter new things

Two ways:

- **Permanent (recommended):** add a `.txt` or `.md` file to `api/inf/teach/`
  in this repo and push. It's picked up automatically on the next deploy.
- **Live, without redeploying:** `POST /api/v1/teach/upload` (multipart
  `file` field), then it's searchable immediately. Note this only persists
  until the container restarts/redeploys unless you also commit the file to
  git -- Render's filesystem is not permanent storage.

Format is plain text. For trilingual answers, use:
```
EN: your fact in English.
FR: le fait en français.
RW: ukuri mu Kinyarwanda.
```

## API

```
POST /api/v1/chats/message   {prompt, chat_id, lang}   -> answer + full reasoning trace
POST /api/v1/reason          {prompt, lang}             -> trace only, for debugging
GET  /api/v1/health
GET  /api/v1/brain
POST /api/v1/brain/update    {content}
POST /api/v1/teach/upload    (multipart file)
POST /api/v1/teach/reload
GET  /api/v1/teach/list
```

## Connecting the frontend (Vercel)

CORS is currently open (`allow_origins=["*"]`) in `api/index.py` so you can
get the Vercel deploy working first. Once your Vercel domain is live, narrow
`allow_origins` to that exact domain. Point the frontend's backend URL at
`https://backend-winter.onrender.com`.

## Local development (optional)

You don't need Docker to hack on this locally -- install Python 3.11+,
`swi-prolog`, `sbcl`, and `guile-3.0` via your package manager, compile the
two native engines once (`g++ -O2 -std=c++17 -o api/engines/cpp/engine
api/engines/cpp/engine.cpp` and `ocamlfind ocamlopt -package str
api/engines/ocaml/validator.ml -o api/engines/ocaml/validator`), `pip install
-r requirements.txt`, then `uvicorn api.index:app --reload`. This is for
development only -- the actual deployment path is the Dockerfile on Render.
