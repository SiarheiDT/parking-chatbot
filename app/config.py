from dataclasses import dataclass
from pathlib import Path
import os


@dataclass
class Config:
    # Database
    DB_PATH: Path

    # RAG
    VECTOR_DB_PATH: Path
    TOP_K: int

    # LLM
    MODEL_NAME: str


def get_config() -> Config:
    return Config(
        DB_PATH=Path(os.getenv("DB_PATH", "data/db/parking_dev.db")),
        VECTOR_DB_PATH=Path(os.getenv("VECTOR_DB_PATH", "data/processed/vector_store")),
        TOP_K=int(os.getenv("TOP_K", "3")),
        MODEL_NAME=os.getenv("MODEL_NAME", "gpt-4o-mini"),
    )