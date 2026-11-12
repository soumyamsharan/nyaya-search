# syntax=docker/dockerfile:1
# Nyaya Search API image (linux/arm64 for Oracle Ampere; also builds on amd64).
# Build from the repo root:  docker build -f api/Dockerfile -t nyaya-api .
FROM python:3.12.16-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/models/hf \
    MODELS_DIR=/models

RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin app \
    && mkdir -p /models && chown app:app /models

WORKDIR /app

# Dependencies first (cached layer). Torch comes from the CPU-only index: no CUDA libraries on a CPU server.
# Optional build secret "ca": a CA bundle for building behind a TLS-inspecting proxy. It is used only by pip
# during this step and is never written into the image.
COPY deploy/requirements-api.txt .
RUN --mount=type=secret,id=ca,required=false \
    if [ -s /run/secrets/ca ]; then export PIP_CERT=/run/secrets/ca; fi; \
    pip install --index-url https://download.pytorch.org/whl/cpu \
        "torch==$(grep -E '^torch==' requirements-api.txt | cut -d= -f3)" \
    && pip install -r requirements-api.txt

COPY core core
COPY api api
RUN pip install --no-deps ./core ./api

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=600s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz', timeout=4)"
CMD ["api"]
