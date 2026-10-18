from __future__ import annotations
from typing import TYPE_CHECKING
import time
if TYPE_CHECKING:
    from src.retrieval.retriever import Retriever
from src.retrieval.models import (
    RetrievalCandidate,
    RetrievalIntent,
    RetrievalPlan,
    ChunkKind,
)


class Collector:

    """
    Responsible only for collecting retrieval candidates.

    No scoring.

    No ranking.

    No filtering.

    No reranking.
    """

    def __init__(
        self,
        retriever: "Retriever",
    ) -> None:

        self._retriever = retriever

    def collect(
        self,
        plan: RetrievalPlan,
        top_k: int,
    ) -> list[RetrievalCandidate]:

        if plan.intent == RetrievalIntent.GENERAL:
            return self._collect_general(
                plan,
                top_k,
            )

        if plan.intent == RetrievalIntent.PEOPLE:
            return self._collect_people(
                plan,
                top_k,
            )

        if plan.intent == RetrievalIntent.FEES:
            return self._collect_fees(
                plan,
                top_k,
            )

        if (
            plan.intent
            == RetrievalIntent.ADMISSION_CATEGORY
        ):
            return self._collect_admission(
                plan,
                top_k,
            )

        return []

    def _collect_general(
        self,
        plan: RetrievalPlan,
        top_k: int,
    ) -> list[RetrievalCandidate]:

        primary_chunks = self._collect_hybrid(
            query=plan.raw_query,
            limit=top_k * 2,
        )

        if plan.topics:
            topic_chunks = self._collect_hybrid(
                query=" ".join(plan.topics),
                limit=top_k * 2,
            )

            chunks = self._merge_chunks(
                primary_chunks,
                topic_chunks,
            )

        else:
            chunks = primary_chunks

        return self._wrap_candidates(
            chunks,
        )


    # def _collect_people(
    #     self,
    #     plan: RetrievalPlan,
    #     top_k: int,
    # ) -> list[RetrievalCandidate]:

    #     chunks = self._collect_structured(
    #         query=plan.raw_query,
    #         record_type="people",
    #         limit=top_k * 2,
    #     )

    #     return self._wrap_candidates(chunks)
    def _collect_people(
        self,
        plan: RetrievalPlan,
        top_k: int,
    ) -> list[RetrievalCandidate]:

    # People records are already structured in Qdrant.
    # Collect the complete people set so list queries are
    # not limited by semantic/BM25 top-k retrieval.
        chunks = self._retriever._structured_candidates(
            record_type="people",
        )

        return self._wrap_candidates(chunks)

    @staticmethod
    def _canonical_role(value: str) -> str:
        value = value.casefold().strip()
        if value.endswith("s") and not value.endswith("'s"):
            value = value[:-1]
        return value

    def _collect_fees(
        self,
        plan: RetrievalPlan,
        top_k: int,
    ) -> list[RetrievalCandidate]:

        print("[FEE PLAN]", plan)

        chunks = self._collect_structured(
            query=plan.raw_query,
            record_type="fees",
            limit=top_k * 2,
        )

        return self._wrap_candidates(chunks)


    def _collect_admission(
        self,
        plan: RetrievalPlan,
        top_k: int,
    ) -> list[RetrievalCandidate]:

        chunks = self._collect_structured(
            query=plan.raw_query,
            record_type="admission_categories",
            limit=top_k * 2,
            codes=plan.admission_codes,
        )

        return self._wrap_candidates(chunks)

    def _collect_hybrid(
        self,
        query: str,
        limit: int,
    ) -> list[dict]:
        
        print(
            f"[COLLECTOR] hybrid limit={limit}"
        )

        total_start = time.perf_counter()

        semantic_start = time.perf_counter()

        semantic_chunks = (
            self._retriever._semantic_candidates(
                query=query,
                limit=limit,
            )
        )

        print(
            f"[COLLECTOR TIMING] Semantic: "
            f"{time.perf_counter() - semantic_start:.3f}s"
        )

        bm25_start = time.perf_counter()

        lexical_chunks = (
            self._retriever._bm25_search(
                query=query,
                limit=limit,
            )
        )

        print(
            f"[COLLECTOR TIMING] BM25: "
            f"{time.perf_counter() - bm25_start:.3f}s"
        )

        merge_start = time.perf_counter()

        merged = self._merge_chunks(
            semantic_chunks,
            lexical_chunks,
        )

        print(
            f"[COLLECTOR TIMING] Merge: "
            f"{time.perf_counter() - merge_start:.3f}s"
        )

        print(
            f"[COLLECTOR TIMING] Hybrid TOTAL: "
            f"{time.perf_counter() - total_start:.3f}s"
        )

        return merged
    
    def _collect_structured(
        self,
        *,
        query: str,
        record_type: str,
        limit: int,
        codes: list[str] | None = None,
    ) -> list[dict]:

        hybrid_chunks = self._collect_hybrid(
            query=query,
            limit=limit,
        )

        structured_chunks = (
            self._retriever._structured_candidates(
                record_type=record_type,
                codes=codes,
            )
        )

        return self._merge_chunks(
            hybrid_chunks,
            structured_chunks,
        )


    def _wrap_candidates(
        self,
        chunks: list[dict],
    ) -> list[RetrievalCandidate]:

        candidates = []

        for chunk in chunks:

            if chunk.get("structured"):

                kind = ChunkKind.STRUCTURED

            else:

                kind = ChunkKind.SEMANTIC

            candidates.append(

                RetrievalCandidate(

                    chunk=chunk,

                    kind=kind,

                )

            )

        return candidates

    def _merge_chunks(
        self,
        *collections: list[dict],
    ) -> list[dict]:

        merged: dict[str, dict] = {}

        for collection in collections:

            for chunk in collection:

                chunk_id = chunk.get("chunk_id")

                if chunk_id is None:
                    continue

                if chunk_id not in merged:

                    merged[chunk_id] = dict(chunk)

                else:

                    merged[chunk_id].update(chunk)

        return list(
            merged.values()
        )