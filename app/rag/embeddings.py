from __future__ import annotations

import numpy as np
from sentence_transformers import SentenceTransformer

from app.config import get_config

config = get_config()
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(config.EMBEDDING_MODEL_NAME)
    return _model


def embed_text(text: str) -> list[float]:
    return _get_model().encode(text).tolist()


def encode_normalized(texts: list[str]) -> np.ndarray:
    """
    Batch embeddings with L2 normalization (cosine similarity = dot product).
    Used by guardrails semantic analysis.
    """
    return _get_model().encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )