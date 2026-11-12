# Hugging Face Space (Docker SDK): one container with Postgres (ParadeDB) and the API, models and data baked in.
# Free CPU Spaces have 2 vCPU / 16 GB RAM and no persistent disk, so everything the API reads is built into the
# image; what it writes at runtime (breakdown cache, LLM call log) lives until the Space restarts.
#
# Build context: the folder prepared by scripts/publish-hf-space.sh (this file, start.sh, core/, api/,
# requirements-api.txt). DB_DUMP_URL points at the pg_dump uploaded by scripts/upload-db-to-hf.sh.
FROM python:3.12.16-slim-trixie AS python

FROM paradedb/paradedb:0.26.6-pg17

# Python 3.12 from the official image (same Debian release); the project pins Python 3.12.
COPY --from=python /usr/local/ /usr/local/

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/models/hf \
    MODELS_DIR=/models \
    PGDATA=/home/user/pgdata

USER root
# Hugging Face runs Space containers as uid 1000.
RUN useradd --uid 1000 --create-home --shell /bin/bash user && mkdir -p /models /app && chown user:user /models /app
WORKDIR /app

# Dependencies (CPU-only torch).
COPY requirements-api.txt .
RUN python3.12 -m pip install --index-url https://download.pytorch.org/whl/cpu \
        "torch==$(grep -E '^torch==' requirements-api.txt | cut -d= -f3)" \
    && python3.12 -m pip install -r requirements-api.txt

COPY core core
COPY api api
RUN python3.12 -m pip install --no-deps ./core ./api
COPY --chmod=755 start.sh /app/start.sh

USER user

# Models: downloaded once at build time. The reranker runs in PyTorch on CPU: exporting it to ONNX needs more
# memory than the Space builder has.
RUN python3.12 -c "from huggingface_hub import snapshot_download as d; \
d('BAAI/bge-m3', ignore_patterns=['onnx/*', 'imgs/*', '*.onnx', 'colbert_linear.pt', 'sparse_linear.pt']); \
d('BAAI/bge-reranker-v2-m3', ignore_patterns=['*.onnx'])"

# Database: restore the published dump into a data directory owned by the runtime user.
# File-backed shared memory: container /dev/shm is too small for HNSW index builds.
ARG DB_DUMP_URL
RUN python3.12 -c "import sys, urllib.request; urllib.request.urlretrieve(sys.argv[1], '/tmp/nyaya.dump')" "$DB_DUMP_URL" \
    && initdb --pgdata="$PGDATA" --username=nyaya --auth=trust --encoding=UTF8 \
    && printf "%s\n" "listen_addresses = '127.0.0.1'" "shared_preload_libraries = 'pg_search'" \
        "dynamic_shared_memory_type = mmap" "shared_buffers = 1GB" "maintenance_work_mem = 512MB" \
        >> "$PGDATA/postgresql.conf" \
    && pg_ctl --pgdata="$PGDATA" --wait start \
    && createdb --username=nyaya nyaya \
    && pg_restore --username=nyaya --dbname=nyaya --no-owner /tmp/nyaya.dump \
    && psql --username=nyaya --dbname=nyaya -c "VACUUM ANALYZE" \
    && pg_ctl --pgdata="$PGDATA" --wait stop \
    && rm /tmp/nyaya.dump

# Runtime settings. Secrets (LLM_API_KEY) and the web origin come from the Space's settings, not from here.
ENV DATABASE_URL=postgresql://nyaya@127.0.0.1:5432/nyaya \
    PORT=7860 \
    MODEL_DEVICE=cpu \
    RERANKER_BACKEND=torch \
    RERANK_DEPTH=10 \
    RERANK_MAX_TOKENS=192 \
    TRUSTED_PROXY_IPS=* \
    HF_HUB_OFFLINE=1 \
    LLM_BASE_URL=https://api.groq.com/openai/v1

EXPOSE 7860
CMD ["/app/start.sh"]
