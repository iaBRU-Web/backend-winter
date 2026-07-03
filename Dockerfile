# =============================================================================
# Winter AI -- polyglot backend image
# Stage 1 compiles the C++ and OCaml engines natively.
# Stage 2 is the runtime image: Python + the interpreters each engine needs
# (Guile for Scheme, SBCL for Common Lisp, SWI-Prolog for Prolog) plus the two
# natively-compiled binaries copied over from the build stage.
# Mercury is intentionally not built here -- see
# api/engines/mercury/BUILD_REAL_MERCURY.md for why and for an optional path.
# =============================================================================

FROM ubuntu:22.04 AS builder
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
        g++ \
        ocaml-nox \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY api/engines/cpp/engine.cpp ./cpp/engine.cpp
COPY api/engines/ocaml/validator.ml ./ocaml/validator.ml

RUN g++ -O2 -std=c++17 -o /build/cpp/engine /build/cpp/engine.cpp
RUN ocamlfind ocamlopt -package str /build/ocaml/validator.ml -o /build/ocaml/validator \
    || ocamlopt /build/ocaml/validator.ml -o /build/ocaml/validator


FROM ubuntu:22.04 AS runtime
ENV DEBIAN_FRONTEND=noninteractive \
    PORT=10000 \
    PYTHONUNBUFFERED=1 \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    GUILE_AUTO_COMPILE=0

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-pip \
        swi-prolog \
        sbcl \
        guile-3.0 \
        libstdc++6 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=builder /build/cpp/engine        ./api/engines/cpp/engine
COPY --from=builder /build/ocaml/validator   ./api/engines/ocaml/validator

RUN chmod +x ./api/engines/cpp/engine ./api/engines/ocaml/validator \
    && mkdir -p api/inf/teach api/info \
    && chmod -R 755 api/info api/inf

EXPOSE 10000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/api/v1/health')" || exit 1

CMD ["sh", "-c", "uvicorn api.index:app --host 0.0.0.0 --port ${PORT}"]
