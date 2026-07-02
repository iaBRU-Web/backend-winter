# Winter AI — multi-stage build
# Stage 1 compiles the native C++ and OCaml engines with the full build
# toolchain. Stage 2 is the slim runtime image: it only carries the
# interpreters actually needed at request time (SWI-Prolog for decision
# rules, SBCL for symbolic tokenization) plus the two precompiled binaries
# copied over from the builder — no compilers ship in the final image.

# ---------- Stage 1: builder ----------
FROM debian:bookworm-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    g++ \
    ocaml-nox \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY api/engines/cpp/formatter.cpp ./cpp/formatter.cpp
COPY api/engines/ocaml/validator.ml ./ocaml/validator.ml

RUN g++ -O2 -std=c++17 ./cpp/formatter.cpp -o ./cpp/formatter
RUN cd ./ocaml && ocamlfind ocamlopt validator.ml -o validator \
    || ocamlopt validator.ml -o validator

# ---------- Stage 2: runtime ----------
FROM python:3.11-slim

ENV PORT=10000 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Runtime language interpreters actually invoked per-request.
# (No compilers here — those stayed in the builder stage.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    swi-prolog \
    sbcl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Bring in the natively-compiled binaries from the builder stage.
COPY --from=builder /build/cpp/formatter ./api/engines/cpp/formatter
COPY --from=builder /build/ocaml/validator ./api/engines/ocaml/validator
RUN chmod +x ./api/engines/cpp/formatter ./api/engines/ocaml/validator

RUN mkdir -p /app/api/info/teach && chmod -R 755 /app/api/info

EXPOSE 10000

CMD uvicorn api.index:app --host 0.0.0.0 --port ${PORT}
