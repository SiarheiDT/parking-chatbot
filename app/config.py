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

    # Reservation capacity search
    PARKING_SLOT_STEP_MINUTES: int
    PARKING_SLOT_SEARCH_MAX_DAYS: int

    # Guardrails — pre-trained transformer (SentenceTransformer) semantic check
    GUARDRAILS_SEMANTIC_ENABLED: bool
    GUARDRAILS_SEMANTIC_THRESHOLD: float

    # Stage 2 — Telegram admin notifications (optional; empty = disabled)
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_ADMIN_CHAT_ID: str
    TELEGRAM_API_BASE: str
    # POST /telegram/webhook/<secret> must match; empty disables webhook validation (not for production)
    TELEGRAM_WEBHOOK_SECRET: str

    # Stage 2 — how admin Confirm/Reject is executed (see app/stage2/admin_agent.py)
    # direct: no LLM (default, tests/CI). langchain_tools: OpenAI tool-calling agent.
    STAGE2_ADMIN_HANDLER: str
    # Model for the admin agent; defaults to MODEL_NAME when empty
    ADMIN_AGENT_MODEL: str

    # Stage 3 — MCP-like confirmed reservation persistence
    STAGE3_MCP_ENABLED: bool
    STAGE3_MCP_ENDPOINT: str
    STAGE3_MCP_API_KEY: str
    STAGE3_MCP_TIMEOUT_SECONDS: float
    STAGE3_MCP_OUTPUT_FILE: Path


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
        PARKING_SLOT_STEP_MINUTES=int(os.getenv("PARKING_SLOT_STEP_MINUTES", "30")),
        PARKING_SLOT_SEARCH_MAX_DAYS=int(os.getenv("PARKING_SLOT_SEARCH_MAX_DAYS", "14")),
        GUARDRAILS_SEMANTIC_ENABLED=os.getenv("GUARDRAILS_SEMANTIC_ENABLED", "true").lower()
        in ("1", "true", "yes"),
        GUARDRAILS_SEMANTIC_THRESHOLD=float(os.getenv("GUARDRAILS_SEMANTIC_THRESHOLD", "0.52")),
        TELEGRAM_BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        TELEGRAM_ADMIN_CHAT_ID=os.getenv("TELEGRAM_ADMIN_CHAT_ID", ""),
        TELEGRAM_API_BASE=os.getenv("TELEGRAM_API_BASE", "https://api.telegram.org"),
        TELEGRAM_WEBHOOK_SECRET=os.getenv("TELEGRAM_WEBHOOK_SECRET", ""),
        STAGE2_ADMIN_HANDLER=_normalize_stage2_handler(os.getenv("STAGE2_ADMIN_HANDLER", "direct")),
        ADMIN_AGENT_MODEL=os.getenv("ADMIN_AGENT_MODEL", "").strip(),
        STAGE3_MCP_ENABLED=os.getenv("STAGE3_MCP_ENABLED", "false").lower() in ("1", "true", "yes"),
        STAGE3_MCP_ENDPOINT=os.getenv(
            "STAGE3_MCP_ENDPOINT",
            "http://localhost:9191/mcp/v1/confirmed-reservations",
        ).strip(),
        STAGE3_MCP_API_KEY=os.getenv("STAGE3_MCP_API_KEY", "").strip(),
        STAGE3_MCP_TIMEOUT_SECONDS=float(os.getenv("STAGE3_MCP_TIMEOUT_SECONDS", "5")),
        STAGE3_MCP_OUTPUT_FILE=Path(
            os.getenv("STAGE3_MCP_OUTPUT_FILE", "data/processed/confirmed_reservations.txt")
        ),
    )


def _normalize_stage2_handler(raw: str) -> str:
    v = (raw or "direct").strip().lower()
    if v in ("langchain", "langchain_tools", "agent", "tools"):
        return "langchain_tools"
    return "direct"