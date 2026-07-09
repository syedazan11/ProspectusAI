import os

import numpy as np
from dotenv import load_dotenv
from fastembed import TextEmbedding


class EmbeddingService:
    """
    Provider-configured embedding service.

    The active embedding provider and model are
    selected entirely through environment variables.
    """

    SUPPORTED_PROVIDERS = {
        "fastembed",
    }

    def __init__(
        self,
        provider: str | None = None,
        model_name: str | None = None,
    ):
        load_dotenv()

        self.provider = (
            provider
            or os.getenv(
                "EMBEDDING_PROVIDER",
                "fastembed",
            )
        ).strip().lower()

        self.model_name = (
            model_name
            or os.getenv(
                "EMBEDDING_MODEL",
                "BAAI/bge-small-en-v1.5",
            )
        ).strip()

        if (
            self.provider
            not in self.SUPPORTED_PROVIDERS
        ):
            raise ValueError(
                "Unsupported embedding provider: "
                f"{self.provider}"
            )

        self.model = TextEmbedding(
            model_name=self.model_name
        )

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[np.ndarray]:
        if not texts:
            return []

        return list(
            self.model.embed(texts)
        )

    def embed_query(
        self,
        query: str,
    ) -> np.ndarray:
        if not query.strip():
            raise ValueError(
                "Query cannot be empty."
            )

        embeddings = list(
            self.model.embed([query])
        )

        return embeddings[0]

    @property
    def vector_size(self) -> int:
        embedding = self.embed_query(
            "vector dimension probe"
        )

        return int(embedding.shape[0])
