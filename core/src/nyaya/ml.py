"""Embedding and reranking models behind small interfaces, so callers never depend on a library."""

import logging
from pathlib import Path
from typing import Protocol

import numpy as np
import torch
from sentence_transformers import CrossEncoder, SentenceTransformer

from nyaya.config import Settings

log = logging.getLogger(__name__)

EMBEDDING_DIM = 1024


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> np.ndarray: ...


class Reranker(Protocol):
    def score(self, query: str, documents: list[str]) -> list[float]:
        """Relevance of each document to the query, in 0..1."""
        ...


def resolve_device(setting: str) -> str:
    if setting != "auto":
        return setting
    return "mps" if torch.backends.mps.is_available() else "cpu"


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str, device: str, max_tokens: int, batch_size: int = 16) -> None:
        # Half precision on the Mac GPU roughly doubles throughput; vectors are stored as halfvec anyway.
        dtype = torch.float16 if device == "mps" else torch.float32
        self._model = SentenceTransformer(model_name, device=device, model_kwargs={"dtype": dtype})
        self._model.max_seq_length = max_tokens
        self._batch_size = batch_size

    def embed(self, texts: list[str]) -> np.ndarray:
        return self._model.encode(
            texts, batch_size=self._batch_size, normalize_embeddings=True, convert_to_numpy=True
        )


class CrossEncoderReranker:
    def __init__(self, model: CrossEncoder) -> None:
        self._model = model

    def score(self, query: str, documents: list[str]) -> list[float]:
        if not documents:
            return []
        scores = self._model.predict([(query, doc) for doc in documents], batch_size=16)
        return [float(s) for s in np.atleast_1d(scores)]


def _int8_onnx_cross_encoder(model_name: str, max_tokens: int, models_dir: Path) -> CrossEncoder:
    """CPU-friendly reranker: export to ONNX once, quantise dynamically to int8 for Arm64, then reuse."""
    from sentence_transformers import export_dynamic_quantized_onnx_model

    local_dir = models_dir / (model_name.replace("/", "__") + "-onnx")
    quantised = local_dir / "onnx" / "model_qint8_arm64.onnx"
    if not quantised.exists():
        log.info("exporting int8 ONNX reranker to %s", local_dir)
        exported = CrossEncoder(model_name, backend="onnx", max_length=max_tokens)
        exported.save_pretrained(str(local_dir))
        export_dynamic_quantized_onnx_model(exported, "arm64", str(local_dir))
    return CrossEncoder(
        str(local_dir),
        backend="onnx",
        max_length=max_tokens,
        model_kwargs={"file_name": "onnx/model_qint8_arm64.onnx", "provider": "CPUExecutionProvider"},
    )


def build_embedder(settings: Settings) -> Embedder:
    return SentenceTransformerEmbedder(
        settings.embedding_model, resolve_device(settings.model_device), settings.embed_max_tokens
    )


def build_reranker(settings: Settings) -> Reranker | None:
    if settings.rerank_depth <= 0:
        return None
    if settings.reranker_backend == "onnx-int8":
        model = _int8_onnx_cross_encoder(
            settings.reranker_model, settings.rerank_max_tokens, settings.models_dir
        )
    else:
        model = CrossEncoder(
            settings.reranker_model,
            max_length=settings.rerank_max_tokens,
            device=resolve_device(settings.model_device),
        )
    return CrossEncoderReranker(model)
