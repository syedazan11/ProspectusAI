import os
import re
import math
import time
from collections import Counter
from pathlib import Path
from typing import Any
from pprint import pprint
from dotenv import load_dotenv
from src.retrieval.models import ChunkKind
from src.retrieval.models import RetrievalIntent
from src.core.qdrant_client import get_qdrant_client
from src.embeddings.embedder import EmbeddingService
from src.retrieval.planner import (
    RetrievalPlanner,
)

from src.embeddings.embedder import (
    EmbeddingService,
)

from src.retrieval.collector import (
    Collector,
)

from src.retrieval.ranker import (
    Ranker,
)

from src.retrieval.chunk_classifier import (
    ChunkClassifier,
)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(
    PROJECT_ROOT / ".env"
)


class Retriever:


    def __init__(
        self,
        collection_name: str,
    ):
        import inspect

        print("=" * 80)
        print(inspect.getfile(self.__class__))
        print("=" * 80)

        if not collection_name:
            raise ValueError(
                "Qdrant collection name is required."
            )

        self.collection_name = collection_name

        self.client = get_qdrant_client()
        self.embedding_service = EmbeddingService()

        self._all_chunks_cache = None
        self._page_context_cache = None

        # BM25 cache
        self._bm25_chunks = None
        self._bm25_documents = None
        self._bm25_term_frequencies = None
        self._bm25_document_frequencies = None
        self._bm25_average_length = None

        self._chunk_lookup = None
        self._ordered_chunks = None

        self._chunk_positions = None

        self._planner = RetrievalPlanner()

        self._classifier = ChunkClassifier()

        self._collector = Collector(
            self,
        )

        self._ranker = Ranker(
            self,
        )

        self._embedder = EmbeddingService()

    def _detect_person_name(
        self,
        query: str,
    ) -> str | None:

        query_normalized = " ".join(
            query.casefold().split()
        )

        for chunk in self._all_chunks():

            if not chunk.get("structured"):
                continue

            if chunk.get("record_type") != "people":
                continue

            content = chunk.get("content", "")
            lines = [
                line.strip()
                for line in content.splitlines()
            ]

            for index, line in enumerate(lines):

                if line.casefold() != "name:":
                    continue

                if index + 1 >= len(lines):
                    continue

                name = lines[index + 1].strip()

                if not name:
                    continue

                name_normalized = " ".join(
                    name.casefold().split()
                )

                if name_normalized in query_normalized:
                    return name

        return None

    def retrieve(
        self,
        query: str,
        top_k: int = 8,
        *,
        is_follow_up: bool = False,
        context: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:

        print(
            "[PEOPLE CONTEXT CHECK]",
            {
                "query": query,
                "topic": (context or {}).get("topic"),
                "person_name": (context or {}).get("person_name"),
                "role": (context or {}).get("role"),
                "department": (context or {}).get("department"),
                "programme": (context or {}).get("programme"),
            },
        )
        
        retrieval_start = time.perf_counter()
        plan_start = time.perf_counter()

        plan = self._planner.plan(
            query=query,
            is_follow_up=is_follow_up,
        )

        if context and context.get("topic") == "people":
            plan.intent = RetrievalIntent.PEOPLE
        
        print(
            "[RETRIEVER CONTEXT]",
            context,
            "| FINAL INTENT:",
            plan.intent,
        )

##change on 17 oct
        # person_name = self._detect_person_name(query)

        # if person_name is not None:
        #     plan.intent = RetrievalIntent.PEOPLE
        #     print(
        #         f"[PEOPLE NAME DETECTED] {person_name}"
        #     )

        person_name = self._detect_person_name(query)

        if person_name is not None:
            plan.intent = RetrievalIntent.PEOPLE

            context = dict(context or {})
            context["topic"] = "people"
            context["person_name"] = person_name

            # print(
            #     f"[PEOPLE NAME DETECTED] {person_name}"
            # )

        print(
            f"[RETRIEVER TIMING] Planner: "
            f"{time.perf_counter() - plan_start:.3f}s"
        )

        collector_start = time.perf_counter()

        candidates = self._collector.collect(
            plan=plan,
            top_k=top_k,
        )

        print(
            f"[RETRIEVER TIMING] Collector: "
            f"{time.perf_counter() - collector_start:.3f}s"
        )
        print("\n========== COLLECTOR CANDIDATES ==========")

        for i, candidate in enumerate(
            candidates[:20],
            1,
        ):
            chunk = candidate.chunk

            print(
                i,
                chunk.get("chunk_id"),
                chunk.get("page"),
                chunk.get("record_type"),
                chunk.get("structured"),
                candidate.final_score,
            )

        print("==========================================")
        ranker_start = time.perf_counter()

        ranked = self._ranker.rank(
            plan=plan,
            candidates=candidates,
            top_k=top_k,
            context=context,
        )

        print(
            f"[RETRIEVER TIMING] Ranker: "
            f"{time.perf_counter() - ranker_start:.3f}s"
        )

        # if plan.intent == RetrievalIntent.PEOPLE:
            # print(
            #     "[PEOPLE RANKED]",
            #     [
            #         {
            #             "chunk_id": candidate.chunk.get("chunk_id"),
            #             "name": re.search(
            #                 r"(?mi)^Name:\s*(?:\n\s*)?(.+)$",
            #                 candidate.chunk.get("content", ""),
            #             ).group(1).strip()
            #             if re.search(
            #                 r"(?mi)^Name:\s*(?:\n\s*)?(.+)$",
            #                 candidate.chunk.get("content", ""),
            #             )
            #             else None,
            #             "score": candidate.final_score,
            #         }
            #         for candidate in ranked
            #     ],
            # )

        # fee_recovery_start = time.perf_counter()

        # # Fee queries need both structured fee records and
        # # the semantic fee section. The Ranker may prefer
        # # structured records exclusively, so recover the
        # # strongest semantic evidence when none survived.
        # if plan.intent == RetrievalIntent.FEES:

        #     has_semantic = any(
        #         candidate.kind == ChunkKind.SEMANTIC
        #         for candidate in ranked
        #     )

        #     if not has_semantic:

        #         semantic_candidates = [
        #             candidate
        #             for candidate in candidates
        #             if candidate.kind == ChunkKind.SEMANTIC
        #         ]

        #         if semantic_candidates:

        #             semantic_candidates.sort(
        #                 key=lambda candidate: (
        #                     candidate.final_score
        #                 ),
        #                 reverse=True,
        #             )

        #             best_semantic = (
        #             semantic_candidates[0]
        #             )

        #             if ranked:

        #                 ranked[-1] = best_semantic

        #             else:

        #                 ranked = [
        #                     best_semantic
        #                 ]

        # print(
        #     f"[RETRIEVER TIMING] Fee recovery: "
        #     f"{time.perf_counter() - fee_recovery_start:.3f}s"
        # )
        supporting_recovery_start = time.perf_counter()

        # Structured intents may intentionally be dominated by
        # their specialized structured records. Preserve that
        # behavior, but recover the strongest semantic evidence
        # when no semantic candidate survived ranking.
        supporting_intents = {
            RetrievalIntent.PEOPLE,
            RetrievalIntent.FEES,
            RetrievalIntent.ADMISSION_CATEGORY,
        }

##change on 17 oct
        # if plan.intent in supporting_intents:

        #     has_semantic = any(
        #         candidate.kind == ChunkKind.SEMANTIC
        #         for candidate in ranked
        #     )

        #     if not has_semantic:

        #         semantic_candidates = [
        #             candidate
        #             for candidate in candidates
        #             if candidate.kind == ChunkKind.SEMANTIC
        #         ]

        #         if semantic_candidates:
        if (
            plan.intent in supporting_intents
            and not (
                context
                and context.get("person_name")
            )
        ):

            has_semantic = any(
                candidate.kind == ChunkKind.SEMANTIC
                for candidate in ranked
            )

            if not has_semantic:

                semantic_candidates = [
                    candidate
                    for candidate in candidates
                    if candidate.kind == ChunkKind.SEMANTIC
                ]

                if semantic_candidates:
                    def supporting_score(candidate):
                        content = (
                            candidate.chunk.get("content", "")
                        ).casefold()

                        phrase_matches = sum(
                            1
                            for phrase in plan.phrases
                            if phrase.casefold().strip()
                            and phrase.casefold().strip() in content
                        )

                        keyword_matches = sum(
                            1
                            for keyword in plan.keywords
                            if keyword.casefold().strip()
                            and re.search(
                                rf"\b{re.escape(keyword.casefold().strip())}\b",
                                content,
                            )
                        )

                        return (
                            phrase_matches,
                            keyword_matches,
                            candidate.final_score,
                        )


                    semantic_candidates.sort(
                        key=supporting_score,
                        reverse=True,
                    )

                    best_semantic = semantic_candidates[0]

                    if ranked:
                        ranked[-1] = best_semantic

                    else:
                        ranked = [
                            best_semantic
                        ]

        print(
            f"[RETRIEVER TIMING] Supporting recovery: "
            f"{time.perf_counter() - supporting_recovery_start:.3f}s"
        )

        print(
            f"[RETRIEVER TIMING] TOTAL: "
            f"{time.perf_counter() - retrieval_start:.3f}s"
        )

        return {
            "plan": plan,
            "chunks": [
                candidate.chunk
                for candidate in ranked
            ],
        }

    def _all_chunks(
        self,
    ) -> list[dict[str, Any]]:

        if self._all_chunks_cache is not None:
            return self._all_chunks_cache

        records = []
        offset = None

        while True:

            batch, offset = self.client.scroll(
                collection_name=self.collection_name,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            records.extend(batch)

            if offset is None:
                break

        chunks = [
            record.payload or {}
            for record in records
        ]

        self._all_chunks_cache = chunks

        return chunks
    
    def _chunk_lookup_by_id(
        self,
    ) -> dict[str, dict[str, Any]]:

        if self._chunk_lookup is not None:
            return self._chunk_lookup

        lookup = {}

        for chunk in self._all_chunks():

            chunk_id = chunk.get("chunk_id")

            if chunk_id:
                lookup[chunk_id] = chunk

        self._chunk_lookup = lookup

        return lookup
    
    def _build_bm25_index(
        self,
    ) -> None:

        if self._bm25_documents is not None:
            return
        
        started = time.perf_counter()

        chunks = self._all_chunks()

        documents = []
        term_frequencies = []
        indexed_chunks = []
        document_frequencies = {}
        total_length = 0

        print(
            f"[BM25 TIMING] _all_chunks: "
            f"{time.perf_counter() - started:.3f}s"
        )

        for chunk in chunks:

            if (
                chunk.get("content_type")
                != "text"
            ):
                continue

            if (
                chunk.get("chunk_type")
                != "semantic"
            ):
                continue

            indexed_chunks.append(chunk)

            searchable = (
                f"{chunk.get('heading_path', '')}\n"
                f"{chunk.get('content', '')}"
            )

            tokens = [
                token.casefold()
                for token in re.findall(
                    r"[a-z0-9][a-z0-9.+#/-]*",
                    searchable,
                )
            ]

            documents.append(tokens)
            term_frequencies.append(
                Counter(tokens)
            )

            total_length += len(tokens)

            seen = set()

            for token in tokens:

                if token in seen:
                    continue

                seen.add(token)

                document_frequencies[token] = (
                    document_frequencies.get(token, 0)
                    + 1
                )
        print(
            f"[BM25 TIMING] index construction: "
            f"{time.perf_counter() - started:.3f}s"
        )

        self._bm25_chunks = indexed_chunks
        self._bm25_documents = documents
        self._bm25_term_frequencies = term_frequencies
        self._bm25_document_frequencies = (
            document_frequencies
        )

        self._bm25_average_length = (
            total_length / len(documents)
            if documents
            else 0.0
        )

        print(
            f"[BM25 TIMING] TOTAL: "
            f"{time.perf_counter() - started:.3f}s"
        )

    def _bm25_search(
        self,
        query: str,
        limit: int = 60,
    ) -> list[dict[str, Any]]:

        self._build_bm25_index()

        if not self._bm25_documents:
            return []

        query_tokens = [
            token.casefold()
            for token in re.findall(
                r"[a-z0-9][a-z0-9.+#/-]*",
                query,
            )
        ]

        if not query_tokens:
            return []

        query_terms = Counter(query_tokens)

        N = len(self._bm25_documents)
        avgdl = self._bm25_average_length or 1.0

        k1 = 1.5
        b = 0.75

        scored = []

        for chunk, document, frequencies in zip(
            self._bm25_chunks,
            self._bm25_documents,
            self._bm25_term_frequencies,
        ):

            if not document:
                continue

            score = 0.0
            doc_length = len(document)

            for term in query_terms:

                tf = frequencies.get(term, 0)

                if tf == 0:
                    continue

                df = (
                    self._bm25_document_frequencies.get(
                        term,
                        0,
                    )
                )

                idf = math.log(
                    1
                    + (
                        (N - df + 0.5)
                        / (df + 0.5)
                    )
                )

                numerator = tf * (k1 + 1)

                denominator = (
                    tf
                    + k1
                    * (
                        1
                        - b
                        + b
                        * (doc_length / avgdl)
                    )
                )

                score += idf * (
                    numerator / denominator
                )

            if score > 0:

                candidate = dict(chunk)

                candidate["bm25_score"] = score

                scored.append(candidate)

        scored.sort(
            key=lambda x: x["bm25_score"],
            reverse=True,
        )

        return scored[:limit]

    def _semantic_candidates(
        self,
        query: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Returns semantic chunks retrieved from Qdrant.

        Only semantic chunks are returned.

        Structured records and curriculum records
        are ignored.
        """

        if not query.strip():
            return []
        
        start = time.perf_counter()

        query_vector = self._embedder.embed_query(
            query,
        )

        # query_vector = (
        #     self.embedding_service
        #     .embed_query(query)
        #     .tolist()
        # )

        embedding_time = (
            time.perf_counter() - start
        )

        qdrant_start = time.perf_counter()

        # query_vector = self._embedder.embed_query(
        #     query,
        # )

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector.tolist(),
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        qdrant_time = (
            time.perf_counter() - qdrant_start
        )

        print(
            f"[SEMANTIC TIMING] Embedding: "
            f"{embedding_time:.3f}s"
        )

        print(
            f"[SEMANTIC TIMING] Qdrant: "
            f"{qdrant_time:.3f}s"
        )

        print(
            f"[SEMANTIC TIMING] Total: "
            f"{embedding_time + qdrant_time:.3f}s"
        )

        candidates = []

        for point in results.points:

            payload = point.payload or {}
            if not candidates:
                from pprint import pprint

                pprint(payload)


            # print("=" * 80)
            # print(payload.get("content_type"))
            # print(payload.get("chunk_type"))
            # pprint(payload)
            # break

        #
        # General retriever only searches
        # layout-aware semantic chunks.
        #

            # if (
            #     payload.get("content_type")
            #     != "text"
            # ):
            #     continue

            if (
                payload.get("chunk_type")
                != "semantic"
            ):
                continue

            candidate = dict(payload)

            candidate["semantic_score"] = point.score

            candidates.append(candidate)

        return candidates

    def _structured_candidates(
        self,
        *,
        record_type: str,
        codes: list[str] | None = None,
    ) -> list[dict[str, Any]]:

        candidates = []

        for chunk in self._all_chunks():

            if not chunk.get("structured"):
                continue

            if (
                chunk.get("record_type")
                != record_type
            ):
                continue

            # if codes:

            #     content = (
            #         chunk.get("content", "")
            #         .upper()
            #    )

            #     matched = False

            #     for code in codes:

            #         if code.upper() in content:
            #             matched = True
            #             break

            #     if not matched:
            #         continue
            if codes:

                content = (
                    chunk.get("content", "")
                    .upper()
                )

                matched = False

                for code in codes:

                    normalized_code = code.upper().strip()

        # --------------------------------------------------
        # Base category: R-1 / SF-1
        #
        # Retrieve the complete category family dynamically.
        # Example:
        # R-1 -> R-1(A), R-1(B), R-1(C), ...
        # --------------------------------------------------
                    if re.fullmatch(
                        r"(?:R|SF)-\d+",
                        normalized_code,
                    ):

                        family_pattern = re.compile(
                            rf"\b{re.escape(normalized_code)}"
                            rf"(?:\([A-Z0-9]+\))?\b",
                            re.IGNORECASE,
                        )

                        if family_pattern.search(content):
                            matched = True
                            break

        # --------------------------------------------------
        # Specific category: R-1(A)
        #
        # Match that exact category only.
        # --------------------------------------------------
                    else:

                        specific_pattern = re.compile(
                            rf"(?<![A-Z0-9]){re.escape(normalized_code)}(?![A-Z0-9])",
                            re.IGNORECASE,
                        )

                        if specific_pattern.search(content):
                            matched = True
                            break

                if not matched:
                    continue

            candidates.append(
                dict(chunk)
            )

        return candidates


    def retrieve_page_chunks(
        self,
        page_numbers: list[int],
        complex_only: bool = False,
    ) -> list[dict[str, Any]]:

        target_pages = set(page_numbers)

        if not target_pages:
            return []

        chunks = []

        for chunk in self._all_chunks():

            if (
                chunk.get("page")
                not in target_pages
            ):
                continue

            if (
                complex_only
                and not chunk.get(
                    "is_complex_table",
                    False,
                )
            ):
                continue

            chunks.append(dict(chunk))

        return chunks

    def _build_chunk_order(
        self,
    ) -> None:

        if self._ordered_chunks is not None:
            return

        ordered = []

        positions = {}

        for chunk in self._all_chunks():

            if (
                chunk.get("chunk_type")
                != "semantic"
            ):
                continue

            if (
                chunk.get("content_type")
                != "text"
            ):
                continue

            positions[
                chunk["chunk_id"]
            ] = len(ordered)

            ordered.append(chunk)

        self._ordered_chunks = ordered

        self._chunk_positions = positions 

    def _neighbor_chunks(
        self,
        chunk_id: str,
        window: int = 1,
    ) -> list[dict[str, Any]]:

        self._build_chunk_order()

        position = (
            self._chunk_positions.get(
                chunk_id,
            )
        )

        if position is None:
            return []

        start = max(
            0,
            position - window,
        )

        end = min(
            len(self._ordered_chunks),
            position + window + 1,
        )

        neighbors = []

        for index in range(
            start,
            end,
        ):

            if index == position:
                continue

            neighbors.append(
                dict(
                    self._ordered_chunks[
                        index
                    ]
                )
            )

        return neighbors 
