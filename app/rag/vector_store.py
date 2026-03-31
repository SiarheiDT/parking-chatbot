from __future__ import annotations

import weaviate
from weaviate.classes.config import Configure, Property, DataType


class WeaviateVectorStore:
    def __init__(self) -> None:
        self.client = weaviate.connect_to_custom(
            http_host="localhost",
            http_port=8081,
            http_secure=False,
            grpc_host="localhost",
            grpc_port=50051,
            grpc_secure=False,
        )
        self.collection_name = "ParkingDoc"

    def close(self) -> None:
        self.client.close()

    def create_schema(self) -> None:
        existing = self.client.collections.list_all()
        if self.collection_name in existing:
            return

        self.client.collections.create(
            name=self.collection_name,
            vector_config=Configure.Vectors.self_provided(),
            properties=[
                Property(name="content", data_type=DataType.TEXT),
                Property(name="source", data_type=DataType.TEXT),
            ],
        )

    def delete_schema_if_exists(self) -> None:
        existing = self.client.collections.list_all()
        if self.collection_name in existing:
            self.client.collections.delete(self.collection_name)

    def add_document(self, content: str, source: str, vector: list[float]) -> None:
        collection = self.client.collections.get(self.collection_name)
        collection.data.insert(
            properties={
                "content": content,
                "source": source,
            },
            vector=vector,
        )

    def search(self, query_vector: list[float], top_k: int = 3) -> list[dict]:
        collection = self.client.collections.get(self.collection_name)
        response = collection.query.near_vector(
            near_vector=query_vector,
            limit=top_k,
            return_properties=["content", "source"],
        )

        results: list[dict] = []
        for obj in response.objects:
            results.append(
                {
                    "content": obj.properties["content"],
                    "source": obj.properties["source"],
                }
            )
        return results