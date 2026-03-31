from __future__ import annotations

from app.rag.embeddings import embed_text
from app.rag.vector_store import WeaviateVectorStore


def retrieve(query: str, top_k: int = 3) -> list[dict]:
    store = WeaviateVectorStore()
    try:
        query_vector = embed_text(query)
        results = store.search(query_vector=query_vector, top_k=top_k)

        return [
            {
                "page_content": item["content"],
                "metadata": {"source": item["source"]},
            }
            for item in results
        ]
    finally:
        store.close()