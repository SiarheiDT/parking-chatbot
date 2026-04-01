from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    # Database
    DB_PATH: Path

    # RAG
    VECTOR_DB_PATH: Path
    TOP_K: int

    # LLM
    MODEL_NAME: str

    # Embeddings
    EMBEDDING_MODEL_NAME: str

    # Weaviate
    WEAVIATE_HTTP_HOST: str
    WEAVIATE_HTTP_PORT: int
    WEAVIATE_GRPC_HOST: str
    WEAVIATE_GRPC_PORT: int
    WEAVIATE_COLLECTION_NAME: str

    # Ingestion
    CHUNK_SIZE: int
    CHUNK_OVERLAP: int


def get_config() -> Config:
    return Config(
        DB_PATH=Path(os.getenv("DB_PATH", "data/db/parking_dev.db")),
        VECTOR_DB_PATH=Path(os.getenv("VECTOR_DB_PATH", "data/processed/vector_store")),
        TOP_K=int(os.getenv("TOP_K", "3")),
        MODEL_NAME=os.getenv("MODEL_NAME", "gpt-4o-mini"),
        EMBEDDING_MODEL_NAME=os.getenv("EMBEDDING_MODEL_NAME", "all-MiniLM-L6-v2"),
        WEAVIATE_HTTP_HOST=os.getenv("WEAVIATE_HTTP_HOST", "localhost"),
        WEAVIATE_HTTP_PORT=int(os.getenv("WEAVIATE_HTTP_PORT", "8081")),
        WEAVIATE_GRPC_HOST=os.getenv("WEAVIATE_GRPC_HOST", "localhost"),
        WEAVIATE_GRPC_PORT=int(os.getenv("WEAVIATE_GRPC_PORT", "50051")),
        WEAVIATE_COLLECTION_NAME=os.getenv("WEAVIATE_COLLECTION_NAME", "ParkingDoc"),
        CHUNK_SIZE=int(os.getenv("CHUNK_SIZE", "700")),
        CHUNK_OVERLAP=int(os.getenv("CHUNK_OVERLAP", "100")),
    )