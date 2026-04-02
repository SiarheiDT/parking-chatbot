from unittest.mock import MagicMock, patch

from app.rag import embeddings, ingest, vector_store


def test_load_documents_reads_markdown_files(tmp_path) -> None:
    file_path = tmp_path / "faq.md"
    file_path.write_text("hello", encoding="utf-8")
    with patch("app.rag.ingest.DATA_DIR", tmp_path):
        docs = ingest.load_documents()
    assert docs == [("hello", "faq.md")]


def test_split_documents_returns_chunks() -> None:
    chunks = ingest.split_documents([("a " * 1000, "faq.md")])
    assert len(chunks) > 1
    assert all(source == "faq.md" for _, source in chunks)


@patch("app.rag.ingest.WeaviateVectorStore")
def test_ingest_skips_when_no_documents(mock_store_cls) -> None:
    mock_store = mock_store_cls.return_value
    with patch("app.rag.ingest.load_documents", return_value=[]):
        ingest.ingest()
    mock_store.create_schema.assert_called_once()
    mock_store.add_document.assert_not_called()


def test_embed_text_returns_python_list() -> None:
    mocked_vector = MagicMock()
    mocked_vector.tolist.return_value = [0.1, 0.2]
    fake_model = MagicMock()
    fake_model.encode.return_value = mocked_vector
    with patch("app.rag.embeddings._get_model", return_value=fake_model):
        result = embeddings.embed_text("hello")
    assert result == [0.1, 0.2]


def test_embed_text_passes_input_to_model_encode() -> None:
    mocked_vector = MagicMock()
    mocked_vector.tolist.return_value = [1.0]
    fake_model = MagicMock()
    fake_model.encode.return_value = mocked_vector
    with patch("app.rag.embeddings._get_model", return_value=fake_model):
        _ = embeddings.embed_text("parking question")
    fake_model.encode.assert_called_once_with("parking question")


@patch("app.rag.vector_store.weaviate.connect_to_custom")
def test_vector_store_create_schema_calls_collection_create(mock_connect) -> None:
    fake_client = MagicMock()
    fake_client.collections.list_all.return_value = {}
    mock_connect.return_value = fake_client

    store = vector_store.WeaviateVectorStore()
    store.create_schema()
    fake_client.collections.create.assert_called_once()


@patch("app.rag.vector_store.weaviate.connect_to_custom")
def test_vector_store_search_maps_response_objects(mock_connect) -> None:
    fake_obj = MagicMock()
    fake_obj.properties = {"content": "text", "source": "faq.md"}
    fake_query = MagicMock()
    fake_query.near_vector.return_value.objects = [fake_obj]
    fake_collection = MagicMock()
    fake_collection.query = fake_query
    fake_client = MagicMock()
    fake_client.collections.get.return_value = fake_collection
    fake_client.collections.list_all.return_value = {"ParkingDoc": object()}
    mock_connect.return_value = fake_client

    store = vector_store.WeaviateVectorStore()
    results = store.search([0.1], top_k=1)
    assert results == [{"content": "text", "source": "faq.md"}]
