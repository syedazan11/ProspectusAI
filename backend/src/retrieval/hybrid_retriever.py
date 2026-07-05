from pathlib import Path
from typing import Any

from src.retrieval.retriever import Retriever
from src.retrieval.graph_retriever import GraphRetriever


class HybridRetriever:
    """
    Combines vector retrieval with local
    knowledge-graph retrieval.
    """

    def __init__(
        self,
        graph_path: Path,
    ):
        self.vector_retriever = Retriever()
        self.graph_retriever = GraphRetriever(
            graph_path=graph_path
        )

    def retrieve(
        self,
        query: str,
        vector_top_k: int = 5,
        graph_top_k: int = 5,
    ) -> dict[str, Any]:

        vector_chunks = (
            self.vector_retriever.retrieve(
                query=query,
                top_k=vector_top_k,
            )
        )

        graph_results = (
            self.graph_retriever.retrieve(
                query=query,
                top_k_entities=graph_top_k,
            )
        )

        return {
            "query": query,
            "vector_chunks": vector_chunks,
            "graph_results": graph_results,
            "metadata": {
                "vector_chunk_count": len(
                    vector_chunks
                ),
                "graph_entity_count": (
                    graph_results.get(
                        "metadata",
                        {},
                    ).get(
                        "matched_entity_count",
                        0,
                    )
                ),
                "graph_relationship_count": (
                    graph_results.get(
                        "metadata",
                        {},
                    ).get(
                        "relationship_count",
                        0,
                    )
                ),
            },
        }