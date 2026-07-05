from pathlib import Path
from typing import Any

from src.llm.llm_service import LLMService
from src.retrieval.context_builder import ContextBuilder
from src.retrieval.hybrid_retriever import HybridRetriever


class RAGService:
    """
    Orchestrates the complete Hybrid GraphRAG
    question-answering pipeline.
    """

    def __init__(
        self,
        graph_path: Path,
    ):
        self.retriever = HybridRetriever(
            graph_path=graph_path,
        )
        self.context_builder = ContextBuilder()
        self.llm_service = LLMService()

    def ask(
        self,
        question: str,
        vector_top_k: int = 5,
        graph_top_k: int = 5,
    ) -> dict[str, Any]:

        retrieval_result = self.retriever.retrieve(
            query=question,
            vector_top_k=vector_top_k,
            graph_top_k=graph_top_k,
        )

        context = self.context_builder.build(
            retrieved_chunks=(
                retrieval_result["vector_chunks"]
            ),
            graph_results=(
                retrieval_result["graph_results"]
            ),
        )

        answer = self.llm_service.generate_answer(
            question=question,
            context=context,
        )

        return {
            "question": question,
            "answer": answer,
            "sources": [
                {
                    "page_number": chunk[
                        "page_number"
                    ],
                    "heading": chunk["heading"],
                    "document": chunk["document"],
                }
                for chunk in retrieval_result[
                    "vector_chunks"
                ]
            ],
            "retrieval_metadata": (
                retrieval_result["metadata"]
            ),
        }