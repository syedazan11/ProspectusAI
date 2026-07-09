from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.vector_store.qdrant_store import QdrantStore


def make_store(
    vector_size: int = 384,
) -> tuple[QdrantStore, MagicMock]:
    mock_client = MagicMock()

    with patch(
        "src.vector_store.qdrant_store.QdrantClient",
        return_value=mock_client,
    ):
        with patch.dict(
            "os.environ",
            {
                "QDRANT_HOST": "localhost",
                "QDRANT_PORT": "6333",
                "QDRANT_COLLECTION": "test_collection",
            },
        ):
            store = QdrantStore(
                vector_size=vector_size
            )

    return store, mock_client


def test_rejects_invalid_vector_size():
    with pytest.raises(
        ValueError,
        match="vector_size must be greater than 0",
    ):
        QdrantStore(vector_size=0)


def test_stores_vector_size():
    store, _ = make_store(
        vector_size=384
    )

    assert store.vector_size == 384


def test_create_collection_uses_dynamic_vector_size():
    store, mock_client = make_store(
        vector_size=768
    )

    mock_client.get_collections.return_value = (
        SimpleNamespace(collections=[])
    )

    store.create_collection()

    call = (
        mock_client
        .create_collection
        .call_args
    )

    vector_config = (
        call.kwargs["vectors_config"]
    )

    assert vector_config.size == 768


def test_existing_collection_is_not_recreated():
    store, mock_client = make_store()

    mock_client.get_collections.return_value = (
        SimpleNamespace(
            collections=[
                SimpleNamespace(
                    name="test_collection"
                )
            ]
        )
    )

    store.create_collection()

    mock_client.create_collection.assert_not_called()


def test_reset_collection_uses_dynamic_vector_size():
    store, mock_client = make_store(
        vector_size=512
    )

    mock_client.get_collections.return_value = (
        SimpleNamespace(collections=[])
    )

    store.reset_collection()

    call = (
        mock_client
        .create_collection
        .call_args
    )

    vector_config = (
        call.kwargs["vectors_config"]
    )

    assert vector_config.size == 512
