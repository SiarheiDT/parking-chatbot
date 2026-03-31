from unittest.mock import patch

from app.rag.retriever import retrieve


@patch("app.rag.retriever.WeaviateVectorStore")
@patch("app.rag.retriever.embed_text")
def test_retrieve_returns_expected_structure(mock_embed_text, mock_store_class) -> None:
    mock_embed_text.return_value = [0.1, 0.2, 0.3]

    mock_store = mock_store_class.return_value
    mock_store.search.return_value = [
        {
            "content": "The parking operates daily from 06:00 to 23:00.",
            "source": "faq.md",
        }
    ]

    result = retrieve("What are the working hours?", top_k=3)

    assert isinstance(result, list)
    assert result[0]["page_content"] == "The parking operates daily from 06:00 to 23:00."
    assert result[0]["metadata"]["source"] == "faq.md"


@patch("app.rag.retriever.WeaviateVectorStore")
@patch("app.rag.retriever.embed_text")
def test_retrieve_closes_store_on_exception(mock_embed_text, mock_store_class) -> None:
    mock_embed_text.return_value = [0.1, 0.2, 0.3]
    mock_store = mock_store_class.return_value
    mock_store.search.side_effect = RuntimeError("boom")

    try:
        retrieve("question", top_k=3)
    except RuntimeError:
        pass

    mock_store.close.assert_called_once()