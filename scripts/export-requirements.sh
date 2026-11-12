#!/usr/bin/env bash
# Export the API's locked dependencies for the Docker images, without GPU-only packages.
# The images install CPU-only torch, so CUDA/NVIDIA/Triton wheels (several GB) are never needed.
source "$(dirname "$0")/lib.sh"
need uv
cd "$(dirname "$0")/.."
uv export --frozen --no-dev --no-hashes --no-emit-workspace --package nyaya-api \
  | grep -vE '^(nvidia-|cuda-|triton==)' > deploy/requirements-api.txt
log "wrote deploy/requirements-api.txt ($(grep -c '==' deploy/requirements-api.txt) packages)"
