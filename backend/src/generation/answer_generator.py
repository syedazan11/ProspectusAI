import json
from pathlib import Path
from typing import Any

from src.llm.llm_service import LLMService
from src.retrieval.context_builder import ContextBuilder
from src.retrieval.hybrid_retriever import HybridRetriever


class AnswerGenerator:

    def __init__(
        self,
        graph_path: Path,
        tables_path: Path | None = None,
    ):
        self.retriever = HybridRetriever(
            graph_path=graph_path,
        )

        self.context_builder = ContextBuilder()
        self.llm_service = LLMService()
        self.tables_path = tables_path

    def answer(
        self,
        question: str,
        vector_top_k: int = 5,
        graph_top_k: int = 5,
    ) -> dict[str, Any]:

        question = question.strip()

        if not question:
            raise ValueError(
                "Question cannot be empty."
            )

        retrieval_result = self.retriever.retrieve(
            query=question,
            vector_top_k=vector_top_k,
            graph_top_k=graph_top_k,
        )

        vector_chunks = retrieval_result.get(
            "vector_chunks",
            [],
        )

        graph_results = retrieval_result.get(
            "graph_results",
            {},
        )

        context = self.context_builder.build(
            retrieved_chunks=vector_chunks,
            graph_results=graph_results,
        )

        answer = self.llm_service.generate_answer(
            question=question,
            context=context,
        )

        sources = []
        seen_sources = set()

        for chunk in vector_chunks:

            source_key = (
                chunk["document"],
                chunk["page_number"],
            )

            if source_key in seen_sources:
                continue

            seen_sources.add(source_key)

            sources.append(
                {
                    "document": chunk["document"],
                    "page_number": chunk[
                        "page_number"
                    ],
                    "heading": chunk["heading"],
                    "score": chunk.get(
                        "final_score",
                        chunk.get("score"),
                    ),
                }
            )

        page_references = []

        if self._is_abstention(answer):
            page_references = (
                self._load_quarantined_pages()
            )

            if not page_references and sources:
                top_source = sources[0]

                page_references = [
                    {
                        "document": top_source[
                            "document"
                        ],
                        "page_number": top_source[
                            "page_number"
                        ],
                        "page_path": None,
                        "page_url": (
                            "/api/v1/pages/"
                            f"{top_source['document']}/"
                            f"{top_source['page_number']}"
                        ),
                        "reason": (
                            "The answer could not be "
                            "reliably extracted, but this "
                            "was the most relevant page."
                        ),
                    }
                ]

            if page_references:
                page_numbers = ", ".join(
                    str(item["page_number"])
                    for item in page_references
                )

                answer = (
                    "I couldn't reliably find the exact "
                    "answer in the processed data. "
                    f"The information may be available "
                    f"on page {page_numbers} of the "
                    "prospectus. Please review that page."
                )

        status = (
            "needs_page_review"
            if page_references
            else "answered"
        )

        return {
            "question": question,
            "answer": answer,
            "status": status,
            "sources": sources,
            "page_references": page_references,
            "retrieval": retrieval_result,
        }

    def _is_abstention(
        self,
        answer: str,
    ) -> bool:

        normalized = answer.casefold()

        markers = [
            "i couldn't find",
            "could not find",
            "not available in the provided context",
            "not available in the provided prospectus",
        ]

        return any(
            marker in normalized
            for marker in markers
        )

    def _load_quarantined_pages(
        self,
    ) -> list[dict[str, Any]]:

        if self.tables_path is None:
            return []

        if not self.tables_path.exists():
            return []

        try:
            data = json.loads(
                self.tables_path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ):
            return []

        quarantined = data.get(
            "metadata",
            {},
        ).get(
            "quarantined_pages",
            [],
        )

        references = []

        for item in quarantined[:5]:
            references.append(
                {
                    "document": item.get(
                        "document",
                        self.tables_path.stem,
                    ),
                    "page_number": item[
                        "page_number"
                    ],
                    "page_path": item.get(
                        "page_path"
                    ),
                    "reason": item.get(
                        "reason"
                    ),
                }
            )

        return references
