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