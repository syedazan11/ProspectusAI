import numpy as np
import pytest

from src.embeddings.embedder import EmbeddingService


@pytest.fixture(scope="module")
def embedder():
    return EmbeddingService()


def test_provider_comes_from_environment(
    embedder,
):
    assert embedder.provider == "fastembed"


def test_model_comes_from_environment(
    embedder,
):
    assert (
        embedder.model_name
        == "BAAI/bge-small-en-v1.5"
    )


def test_embed_query_returns_vector(
    embedder,
):
    vector = embedder.embed_query(
        "What is the admission fee?"
    )

    assert isinstance(vector, np.ndarray)
    assert vector.ndim == 1
    assert vector.shape[0] > 0


def test_embed_documents_returns_one_vector_per_text(
    embedder,
):
    texts = [
        "Civil Engineering courses",
        "Admission fee and charges",
    ]

    vectors = embedder.embed_documents(texts)

    assert len(vectors) == 2
    assert all(
        isinstance(vector, np.ndarray)
        for vector in vectors
    )


def test_vector_size_matches_embedding(
    embedder,
):
    vector = embedder.embed_query(
        "Computer Science curriculum"
    )

    assert embedder.vector_size == vector.shape[0]


def test_empty_query_is_rejected(
    embedder,
):
    with pytest.raises(
        ValueError,
        match="Query cannot be empty",
    ):
        embedder.embed_query("   ")


def test_unsupported_provider_is_rejected():
    with pytest.raises(
        ValueError,
        match="Unsupported embedding provider",
    ):
        EmbeddingService(
            provider="not-real",
        )
