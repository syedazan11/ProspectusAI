import re

from src.embeddings.embedder import EmbeddingService
from src.vector_store.qdrant_store import QdrantStore
from src.services.document_manager import DocumentManager


class Retriever:
    """
    Retrieves relevant chunks from Qdrant.

    Strategy:
    1. Vector search with a larger candidate pool.
    2. Detect exact structured identifiers in the query.
    3. Boost chunks containing those exact identifiers.
    4. Return the best final results.
    """

    CANDIDATE_MULTIPLIER = 5

    def __init__(self):

        self.embedder = EmbeddingService()
        self.vector_store = QdrantStore()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ):

        query_embedding = (
            self.embedder.embed_query(query)
        )

        candidate_limit = max(
            top_k * self.CANDIDATE_MULTIPLIER,
            20,
        )

        active_document = (
            DocumentManager()
            .get_active_document()
        )

        document_id = active_document["filename"]

        results = self.vector_store.search(
            query_vector=query_embedding.tolist(),
            limit=candidate_limit,
            document_id=document_id,
        )

        exact_terms = self._extract_exact_terms(
            query
        )

        retrieved_chunks = []

        for result in results:

            content = result.payload.get(
                "content",
                "",
            )

            exact_match_count = sum(
                1
                for term in exact_terms
                if term.lower() in content.lower()
            )

            final_score = (
                float(result.score)
                + exact_match_count
            )

            retrieved_chunks.append(
                {
                    "score": result.score,
                    "final_score": final_score,
                    "exact_match_count": (
                        exact_match_count
                    ),
                    "heading": result.payload[
                        "heading"
                    ],
                    "page_number": result.payload[
                        "page_number"
                    ],
                    "content": content,
                    "document": result.payload[
                        "document"
                    ],
                    "parent_chunk_id": (
                        result.payload[
                            "parent_chunk_id"
                        ]
                    ),
                    "chunk_id": result.payload[
                        "chunk_id"
                    ],
                }
            )

        retrieved_chunks.sort(
            key=lambda chunk: (
                chunk["exact_match_count"],
                chunk["final_score"],
            ),
            reverse=True,
        )

        return retrieved_chunks[:top_k]

    def _extract_exact_terms(
        self,
        query: str,
    ) -> list[str]:

        category_pattern = (
            r"\b(?:R|SF)-\d+"
            r"(?:\([a-z]\))?"
        )

        terms = re.findall(
            category_pattern,
            query,
            flags=re.IGNORECASE,
        )

        return list(
            dict.fromkeys(
                term.lower()
                for term in terms
            )
        )