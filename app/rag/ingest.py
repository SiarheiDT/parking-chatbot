from __future__ import annotations

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.paths import RAW_DATA_DIR
from app.rag.embeddings import embed_text
from app.rag.vector_store import WeaviateVectorStore

DATA_DIR = RAW_DATA_DIR

def load_documents() -> list[tuple[str, str]]:
    documents: list[tuple[str, str]] = []

    for file_path in DATA_DIR.glob("*.md"):
        content = file_path.read_text(encoding="utf-8")
        documents.append((content, file_path.name))

    return documents


def split_documents(documents: list[tuple[str, str]]) -> list[tuple[str, str]]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,
        chunk_overlap=100,
    )

    chunks: list[tuple[str, str]] = []

    for content, source in documents:
        for chunk in splitter.split_text(content):
            chunks.append((chunk, source))

    return chunks


def ingest() -> None:
    store = WeaviateVectorStore()
    try:
        store.delete_schema_if_exists()
        store.create_schema()

        documents = load_documents()
        if not documents:
            print(f"No source markdown files found in: {DATA_DIR}")
            return

        chunks = split_documents(documents)

        for chunk, source in chunks:
            vector = embed_text(chunk)
            store.add_document(content=chunk, source=source, vector=vector)

        print("Ingestion completed.")
    finally:
        store.close()


if __name__ == "__main__":
    ingest()