from sentence_transformers import SentenceTransformer

from app.config import get_config

config = get_config()
model = SentenceTransformer(config.EMBEDDING_MODEL_NAME)


def embed_text(text: str) -> list[float]:
    return model.encode(text).tolist()