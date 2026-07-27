import os
import re
import math
from collections import Counter
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from qdrant_client import QdrantClient, models
from src.core.qdrant_client import get_qdrant_client
from dataclasses import dataclass

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(
    PROJECT_ROOT / ".env"
)

@dataclass(frozen=True)
class RetrievalIntent:
    name: str
    confidence: float

@dataclass(frozen=True)
class LexicalMatch:

    matched_terms: list[str]

    heading_matches: list[str]

    phrase_matches: list[str]

    code_matches: list[str]

    term_coverage: float

    heading_coverage: float

    matched_query_weight: float

@dataclass(frozen=True)
class QueryAnalysis:

    raw_query: str

    intent: RetrievalIntent

    terms: list[str]

    phrases: list[str]

    codes: list[str]

    role: str | None

    entities: list[str]


@dataclass
class RetrievalCandidate:
    """
    Internal retrieval object.

    Every retrieved chunk is converted into this common
    representation before any matching or evidence
    expansion takes place.
    """

    chunk: dict[str, Any]

    semantic_score: float = 0.0
    bm25_score: float = 0.0
    final_score: float = 0.0

    structured: bool = False
    record_type: str = ""

    metadata: dict[str, Any] | None = None

    matched_terms: set[str] | None = None

    evidence_group: str | None = None

class Retriever:

    MODEL = (
        "sentence-transformers/"
        "all-minilm-l6-v2"
    )
    
    INTENT_KEYWORDS = {
        "fee": {
            "fee",
            "fees",
            "tuition",
            "payment",
            "payments",
            "charges",
            "refund",
        },
        "deadline": {
            "deadline",
            "last date",
            "closing date",
            "apply",
            "application",
            "submission",
        },
        "admission": {
            "admission",
            "admissions",
            "admit",
            "enrollment",
            "enrolment",
        },
        "eligibility": {
            "eligibility",
            "eligible",
            "requirement",
            "requirements",
            "criteria",
            "qualification",
        },
        "hostel": {
            "hostel",
            "hostels",
            "accommodation",
        },
        "curriculum": {
            "curriculum",
            "courses",
            "syllabus",
            "semester",
        },
        "migration": {
            "migration",
            "migrate",
            "transfer",
        },
        "admission_category": {
            "admission category",
            "admission categories",
        },
        "seat": {
            "seat",
            "seats",
            "seat allocation",
            "seat distribution",
            "seat matrix",
            "seat intake",
            "quota",
        },
        "people": {
            "chairperson",
            "chairman",
            "head",
            "hod",
            "professor",
            "associate professor",
            "assistant professor",
            "lecturer",
                "faculty",
            "staff",
            "teacher",
        },
        "administration": {
            "vice chancellor",
            "pro vice chancellor",
            "registrar",
            "treasurer",
            "controller",
            "controller of examinations",
            "dean",
            "director",
            "principal",
        },
        "department": {
            "department",
            "faculty",
            "school",
            "dep",
        },
        "abbreviation": {
            "meaning",
            "stands for",
            "abbreviation",
            "full form",
            "short form",
        },
        "facilities": {
            "library",
            "sport",
            "sports",
            "laboratory",
            "lab",
            "transport",
            "cafeteria",
        },
    }

    ROLE_KEYWORDS = {
        "chairperson": {
            "chairperson",
            "chairman",
            "chair",
            "head",
            "hod",
            "head of department",
            "department head",
            "department chair",
        },

        "co-chairperson": {
            "co-chairperson",
            "co chair"
            "co chairperson"

        },

        "dean": {
            "dean",
            "associate dean",
            "assistant dean",
            "vice dean",
        },

        "director": {
            "director",
            "executive director",
            "programme director",
            "program director",
            "project director",
        },

        "coordinator": {
            "coordinator",
            "programme coordinator",
            "program coordinator",
            "course coordinator",
            "academic coordinator",
        },

        "professor": {
            "professor",
            "full professor",
        },

        "associate professor": {
            "associate professor",
        },

        "assistant professor": {
            "assistant professor",
        },

        "lecturer": {
            "lecturer",
            "senior lecturer",
        },

        "teaching assistant": {
            "teaching assistant",
            "ta",
        },

        "research assistant": {
            "research assistant",
            "ra",
        },

        "research associate": {
            "research associate",
        },

        "research fellow": {
            "research fellow",
            "postdoctoral fellow",
            "postdoctoral researcher",
            "postdoc",
        },

        "emeritus professor": {
            "emeritus professor",
            "professor emeritus",
        },

        "instructor": {
            "instructor",
        },

        "advisor": {
            "advisor",
            "adviser",
            "academic advisor",
            "faculty advisor",
        },

        "registrar": {
            "registrar",
        },

        "controller of examinations": {
            "controller of examinations",
            "controller examination",
            "exam controller",
        },

        "principal": {
            "principal",
        },

        "vice chancellor": {
            "vice chancellor",
            "vice-chancellor",
            "vc",
        },

        "pro vice chancellor": {
            "pro vice chancellor",
            "pro-vice chancellor",
            "pro vc",
        },

        "chancellor": {
            "chancellor",
        },

        "treasurer": {
            "treasurer",
        },

        "secretary": {
            "secretary",
        },
    }

    STOP_WORDS = {
        "a", "an", "and", "are", "as", "at",
        "be", "by", "can", "could", "do",
        "does", "for", "from", "give",
        "how", "i", "in", "is", "it",
        "me", "of", "on", "or", "please",
        "show", "tell", "the", "to", "was",
        "what", "when", "where", "which",
        "who", "with", "would",
    }

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

        self._all_chunks_cache = None
        self._page_context_cache = None
        self._term_document_frequency_cache = None

        # BM25 cache
        self._bm25_documents = None
        self._bm25_document_frequencies = None
        self._bm25_average_length = None

        self._chunk_lookup = None

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

        chunks = []

        for record in records:

            payload = record.payload or {}

            chunks.append(
                {
                    **payload,
                    "score": 0.0,
                    "semantic_score": 0.0,
                    "lexical_score": 0.0,
                    "final_score": 0.0,
                }
            )

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

        chunks = self._all_chunks()

        documents = []
        document_frequencies = {}
        total_length = 0

        for chunk in chunks:

            searchable = (
                f"{chunk.get('heading', '')}\n"
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

        self._bm25_documents = documents
        self._bm25_document_frequencies = (
            document_frequencies
        )

        self._bm25_average_length = (
            total_length / len(documents)
            if documents
            else 0.0
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

        for chunk, document in zip(
            self._all_chunks(),
            self._bm25_documents,
        ):

            if not document:
                continue

            frequencies = Counter(document)

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


    def _page_context(
        self,
    ) -> dict[int, str]:

        if self._page_context_cache is not None:
            return self._page_context_cache

        grouped = {}

        for chunk in self._all_chunks():

            page = chunk.get("page_number")

            if page is None:
                continue

            heading = str(
                chunk.get("heading", "")
            )

            content = str(
                chunk.get("content", "")
            )

            grouped.setdefault(
                page,
                [],
            ).append(
                f"{heading}\n{content}"
            )

        self._page_context_cache = {
            page: "\n".join(parts)
            for page, parts in grouped.items()
        }

        return self._page_context_cache

    def _term_document_frequency(
        self,
    ) -> dict[str, int]:

        if (
            self._term_document_frequency_cache
            is not None
        ):
            return (
                self._term_document_frequency_cache
            )

        frequencies = {}

        for chunk in self._all_chunks():

            text = (
                f"{chunk.get('heading', '')}\n"
                f"{chunk.get('content', '')}"
            ).casefold()

            tokens = set(
                re.findall(
                    r"[a-z0-9]+",
                    text,
                )
            )

            for token in tokens:

                if len(token) <= 1:
                    continue

                frequencies[token] = (
                    frequencies.get(token, 0)
                    + 1
                )

        self._term_document_frequency_cache = (
            frequencies
        )

        return frequencies

    def _term_weight(
        self,
        term: str,
    ) -> float:

        frequencies = (
            self._term_document_frequency()
        )

        total_chunks = max(
            len(self._all_chunks()),
            1,
        )

        frequency = frequencies.get(
            term.casefold(),
            0,
        )

        rarity = (
            total_chunks
            / max(frequency, 1)
        )

        import math

        return 1.0 + min(
            math.log1p(rarity),
            4.0,
        )

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
                chunk.get("page_number")
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


    def _normalize_candidates(
        self,
        candidates: list[RetrievalCandidate],
    ) -> list[RetrievalCandidate]:
        """
        Stage 2.

        Convert every retrieval source into a common
        candidate representation.

        Gate 100:
        Identity function.
        """

        return candidates


    def _match_candidates(
        self,
        query: str,
        candidates: list[RetrievalCandidate],
    ) -> list[RetrievalCandidate]:
        """
        Stage 3.

        Evaluate candidate relevance.

        Gate 100:
        Placeholder.
        """

        return candidates


    def _select_primary_candidates(
        self,
        candidates: list[RetrievalCandidate],
    ) -> list[RetrievalCandidate]:
        """
        Stage 4.
        Select primary evidence.
        Gate 100:
        Placeholder.
        """

        return candidates


    def _expand_evidence(
        self,
        candidates: list[RetrievalCandidate],
    ) -> list[RetrievalCandidate]:
        """
        Stage 5.

        Build evidence groups.

        Gate 100:
        Placeholder.
        """

        return candidates


    def _build_evidence_groups(
        self,
        candidates: list[RetrievalCandidate],
    ) -> list[RetrievalCandidate]:
        """
        Stage 6.

        Final grouping before answer generation.

        Gate 100:
        Placeholder.
        """

        return candidates
    
    def _semantic_candidates(
        self,
        query: str,
        limit: int,
    ):

        return self.client.query_points(
            collection_name=self.collection_name,
            query=models.Document(
                text=query,
                model=self.MODEL,
            ),
            limit=limit,
            with_payload=True,
        ).points
    

    def _heading_candidates(
        self,
        query_terms: list[str],
    ) -> list[dict[str, Any]]:

        candidates = []

        for chunk in self._all_chunks():

            heading = str(
                chunk.get("heading", "")
            ).casefold()

            matches = sum(
                1
                for term in query_terms
                if self._contains_term(
                    heading,
                    term,
                )
            )

            if matches == 0:
                continue

            candidate = dict(chunk)

            candidate["heading_matches"] = matches

            candidates.append(candidate)

        candidates.sort(
            key=lambda c: c["heading_matches"],
            reverse=True,
        )

        return candidates[:40]
    
    def _metadata_candidates(
        self,
        query_terms: list[str],
    ) -> list[dict[str, Any]]:

        candidates = []

        for chunk in self._all_chunks():

            metadata = (
                chunk.get("metadata")
                or {}
            )

            searchable = " ".join(
                str(v)
                for v in metadata.values()
            ).casefold()

            matches = sum(
                1
                for term in query_terms
                if self._contains_term(
                    searchable,
                    term,
                )
            )

            if matches == 0:
                continue

            candidate = dict(chunk)

            candidate["metadata_matches"] = matches

            candidates.append(candidate)

        candidates.sort(
            key=lambda c: c["metadata_matches"],
            reverse=True,
        )

        return candidates[:40]
    
    def _collect_candidates(
        self,
        query: str,
        top_k: int,
        analysis: QueryAnalysis,
    ) -> tuple[set[str], dict[str, float]]:

        query_terms = self._query_terms(query)

        semantic_results = self._semantic_candidates(
            query=query,
            limit=max(top_k * 8, 60),
        )

        semantic_by_id = {}

        for result in semantic_results:

            payload = result.payload or {}

            chunk_id = payload.get("chunk_id")

            if chunk_id:
                semantic_by_id[chunk_id] = float(result.score)

        bm25_results = self._bm25_search(
            query=query,
            limit=max(top_k * 8, 500),
        )

        heading_results = self._heading_candidates(
        query_terms=query_terms,
        )

        metadata_results = self._metadata_candidates(
            query_terms=query_terms,
        )

        structured_results = []

        structured_results.extend(
            self._structured_people_candidates(
                analysis,
            )
        )
        structured_results.extend(
            self._structured_admission_category_candidates(
                analysis,
            )
        )

        candidate_ids = set()

        for source in (
            semantic_by_id.keys(),
            [c.get("chunk_id") for c in bm25_results],
            [c.get("chunk_id") for c in heading_results],
            [c.get("chunk_id") for c in metadata_results],
            [c.get("chunk_id") for c in structured_results],
        ):
            for chunk_id in source:
                if chunk_id:
                    candidate_ids.add(chunk_id)

        print("\n=== Candidate IDs containing structured-people ===")
        for chunk_id in sorted(candidate_ids):
            if chunk_id.startswith("structured-people"):
                print(chunk_id)
        print("========================================")

        print("\n=== Candidate Sources ===")

        sources = {
            "semantic": set(semantic_by_id.keys()),
            "bm25": {
                c.get("chunk_id")
                for c in bm25_results
                if c.get("chunk_id")
            },
            "heading": {
                c.get("chunk_id")
                for c in heading_results
                if c.get("chunk_id")
            },
            "metadata": {
                c.get("chunk_id")
                for c in metadata_results
                if c.get("chunk_id")
            },
            "structured": {
                c.get("chunk_id")
                for c in structured_results
                if c.get("chunk_id")
            },
        }

        for cid in sorted(candidate_ids):
            if not str(cid).startswith("structured-people"):
                continue

            present = [
                name
                for name, ids in sources.items()
                if cid in ids
            ]

            print(cid, "->", present)

        for result in semantic_results:
            payload = result.payload or {}

            cid = payload.get("chunk_id")

            if cid and cid.startswith("structured-people-13"):
                print(
                    cid,
                    result.score,
                )

        return candidate_ids, semantic_by_id
    
    def _rank_candidates(
        self,
        *,
        candidate_ids: set[str],
        semantic_by_id: dict[str, float],
        analysis: QueryAnalysis,
    ) -> list[dict[str, Any]]:

        lookup = self._chunk_lookup_by_id()

        print(lookup["structured-people-137-0"]["content"])
        print()
        print(lookup["structured-people-138-0"]["content"])

        candidates = []

        for chunk_id in candidate_ids:

            chunk = lookup.get(chunk_id)

            if chunk is None:
                continue

            candidate = dict(chunk)

            semantic_score = semantic_by_id.get(chunk_id, 0.0)

            ranking = self._rank_chunk(
                analysis=analysis,
                chunk=candidate,
                semantic_score=semantic_score,
            )

            if semantic_score <= 0 and ranking["lexical_score"] <= 0:
                continue

            candidate.update(ranking)

            candidates.append(candidate)

        return candidates
    
    def _expand_neighbor_pages(
        self,
        candidates: list[dict[str, Any]],
    ) -> None:

        page_scores: dict[int, float] = {}

        for candidate in candidates:

            page = candidate.get("page_number")

            if isinstance(page, int):
                page_scores[page] = max(
                    page_scores.get(page, 0.0),
                    candidate["final_score"],
                )

        for candidate in candidates:

            page = candidate.get("page_number")

            if not isinstance(page, int):
                continue

            neighbor_score = max(
                page_scores.get(page - 1, 0.0),
                page_scores.get(page + 1, 0.0),
            )

            if neighbor_score > candidate["final_score"]:

                candidate["final_score"] += min(
                    (neighbor_score - candidate["final_score"]) * 0.10,
                    2.0,
                )
    

    def _sort_candidates(
        self,
        candidates: list[dict[str, Any]],
    ) -> None:

        candidates.sort(
            key=lambda candidate: (
                candidate["final_score"],
                candidate["semantic_score"],
            ),
            reverse=True,
        )
    
    def _select_candidates(
        self,
        candidates: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:

        return self._diversify(
            candidates=candidates,
            top_k=top_k,
        )


    def retrieve(
        self,
        query: str,
        top_k: int = 8,
    ) -> list[dict[str, Any]]:

        query = query.strip()

        # intent = self._detect_intent(query)

        # print(
        #     f"[INTENT] {intent.name} "
        #     f"(confidence={intent.confidence:.2f})"
        # )

        # if not query:
        #     return []

        # query_terms = self._query_terms(query)
        # query_phrases = self._query_phrases(query)
        # query_codes = self._query_codes(query)
        analysis = self._analyze_query(query)
        print("[CODES]", analysis.codes)

        print(
            f"[INTENT] {analysis.intent.name} "
            f"(confidence={analysis.intent.confidence:.2f})"
        )

        if analysis.role:
            print(f"[ROLE] {analysis.role}")

        if analysis.entities:
            print(f"[ENTITIES] {analysis.entities}")

        # 1. Close the query_points call here
        # semantic_results = self.client.query_points(
        #     collection_name=self.collection_name,
        #     query=models.Document(
        #         text=query,
        #         model=self.MODEL,
        #     ),
        #     limit=max(
        #         top_k * 8,
        #         60,
        #     ),
        #     with_payload=True,
        # ).points

        # semantic_results = self._semantic_candidates(
        #     query=query,
        #     limit=max(
        #         top_k * 8,
        #         60,
        #     ),
        # )

        # # 2. Print logic now exists independently of the assignment
        # # print("\n========== SEMANTIC RESULTS ==========")

        # # for i, result in enumerate(semantic_results[:20], 1):
        # #     payload = result.payload or {}

        # #     print(
        # #         i,
        # #         f"score={result.score:.4f}",
        # #         payload.get("page_number"),
        # #         payload.get("heading"),
        # #         payload.get("chunk_id"),
        # #     )

        # # print("=====================================\n")
        # semantic_by_id = {}

        # for result in semantic_results:

        #     payload = result.payload or {}

        #     chunk_id = payload.get("chunk_id")

        #     if chunk_id:

        #         semantic_by_id[chunk_id] = float(
        #             result.score
        #         )

        # bm25_results = self._bm25_search(
        #     query=query,
        #     limit=max(
        #         top_k * 8,
        #         60,
        #     ),
        # )

        # heading_results = self._heading_candidates(
        #     query_terms=query_terms,
        # )

        # metadata_results = self._metadata_candidates(
        #     query_terms=query_terms,
        # )

        # candidate_ids = set()

        # for chunk_id in semantic_by_id:
        #     candidate_ids.add(chunk_id)

        # for chunk in bm25_results:

        #     chunk_id = chunk.get("chunk_id")

        #     if chunk_id:
        #         candidate_ids.add(chunk_id)

        # for chunk in heading_results:

        #     chunk_id = chunk.get("chunk_id")

        #     if chunk_id:
        #         candidate_ids.add(chunk_id)

        # for chunk in metadata_results:

        #     chunk_id = chunk.get("chunk_id")

        #     if chunk_id:
        #         candidate_ids.add(chunk_id)

        # for chunk in bm25_results:

        #     chunk_id = chunk.get("chunk_id")

        #     if chunk_id:

        #         candidate_ids.add(chunk_id)
        
        # # print()

        # # print("=" * 80)

        # # print("Candidate Sources")

        # # print(
        # #     "Semantic :",
        # #     len(semantic_by_id),
        # # )

        # # print(
        # #     "BM25 :",
        # #     len(bm25_results),
        # # )

        # # print(
        # #     "Heading :",
        # #     len(heading_results),
        # # )

        # # print(
        # #     "Metadata :",
        # #     len(metadata_results),
        # # )

        # # print(
        # #     "Merged :",
        # #     len(candidate_ids),
        # # )

        # # print("=" * 80)

        candidate_ids, semantic_by_id = self._collect_candidates(
            query=query,
            top_k=top_k,
            analysis=analysis,
        )

        # lookup = self._chunk_lookup_by_id()

        # candidates = []

        # for chunk_id in candidate_ids:

        #     chunk = lookup.get(chunk_id)

        #     if chunk is None:
        #         continue

        #     candidate = dict(chunk)
        #     chunk_id = candidate.get("chunk_id")

        #     semantic_score = semantic_by_id.get(
        #         chunk_id,
        #         0.0,
        #     )

        #     ranking = self._rank_chunk(
        #         query=query,
        #         query_terms=query_terms,
        #         query_phrases=query_phrases,
        #         query_codes=query_codes,
        #         chunk=candidate,
        #         semantic_score=semantic_score,
        #         intent=intent,
        #     )

        #     if (
        #         semantic_score <= 0
        #         and ranking["lexical_score"] <= 0
        #     ):
        #         continue

        #     candidate.update(ranking)

        #     # if candidate.get("page_number") in (104, 105):
        #     #     print(
        #     #         f"PAGE={candidate.get('page_number')}",
        #     #         f"semantic={candidate['semantic_score']:.4f}",
        #     #         f"lexical={candidate['lexical_score']:.4f}",
        #     #         f"final={candidate['final_score']:.4f}",
        #     #         f"heading={candidate.get('heading','')}"
        #     #     )

        #     candidates.append(candidate)

        #     # candidate_heading = str(candidate.get("heading", ""))
        #     # candidate_content = str(candidate.get("content", ""))

        #     # if (
        #     #     "mechanical" in query.casefold()
        #     #     and (
        #     #         "mechanical" in candidate_heading.casefold()
        #     #         or "mechanical" in candidate_content.casefold()
        #     #     )
        #     # ):
        #     #     print(
        #     #         "MECHANICAL CANDIDATE:",
        #     #         candidate.get("chunk_id"),
        #     #         candidate.get("page_number"),
        #     #         candidate_heading,
        #     #         candidate["final_score"],
        #     #     )

        candidates = self._rank_candidates(
            candidate_ids=candidate_ids,
            semantic_by_id=semantic_by_id,
            analysis=analysis,
        )

        # Boost chunks that have strong neighboring chunks on adjacent pages
        # page_scores: dict[int, float] = {}

        # for item in candidates:
        #     page = item.get("page_number")
        #     if isinstance(page, int):
        #         page_scores[page] = max(
        #             page_scores.get(page, 0.0),
        #             item["final_score"],
        #         )

        # for item in candidates:
        #     page = item.get("page_number")

        #     if not isinstance(page, int):
        #         continue

        #     neighbor_score = max(
        #         page_scores.get(page - 1, 0.0),
        #         page_scores.get(page + 1, 0.0),
        #     )

        #     if neighbor_score > item["final_score"]:
        #         item["final_score"] += min(
        #             (neighbor_score - item["final_score"]) * 0.10,
        #             2.0,
        #         )

        self._expand_neighbor_pages(candidates)

        self._sort_candidates(candidates)
        print("\n========== AFTER SORT ==========")
        for i, c in enumerate(candidates[:20], 1):
            print(
                i,
                c.get("chunk_id"),
                c.get("final_score"),
            )
        print("===============================")

        # Debug: print top 15 ranked chunks (rank, final_score, page_number, heading, parent_heading, first 150 chars)
        # print("\n--- Debug Top 15 Chunks ---")
        # for rank, candidate in enumerate(candidates[:15], start=1):
        #     print(f"Rank: {rank}")
        #     print(f"final_score   : {candidate.get('final_score'):.4f}")
        #     print(f"page_number   : {candidate.get('page_number')}")
        #     print(f"heading       : {candidate.get('heading')}")
        #     print(f"parent_heading: {candidate.get('parent_heading')}")
        #     content_preview = str(candidate.get('content', ''))[:150].replace('\n', ' ')
        #     print(f"content preview: {content_preview}")
        #     print("-")

        # print("\n" + "=" * 100)
        # print(f"QUERY: {query}")
        # print("=" * 100)

        # for index, candidate in enumerate(candidates[:20], start=1):

        #     print(f"\n#{index}")

        #     print(
        #         f"Page        : {candidate.get('page_number')}"
        #     )
        #     print(
        #         f"Heading     : {candidate.get('heading', '')}"
        #     )

        #     print(
        #         f"Chunk ID    : {candidate.get('chunk_id')}"
        #     )

        #     print(
        #         f"Semantic    : {candidate['semantic_score']:.4f}"
        #     )

        #     print(
        #         f"Lexical     : {candidate['lexical_score']:.4f}"
        #     )

        #     print(
        #         f"Final       : {candidate['final_score']:.4f}"
        #     )

        #     print(
        #         f"Coverage    : {candidate.get('term_coverage', 0):.2f}"
        #     )

        #     print(
        #         f"Heading Cov : {candidate.get('heading_coverage', 0):.2f}"
        #     )

        #     print(
        #         "-" * 100
        #     )

        return self._select_candidates(
            candidates,
            top_k,
        )

    def _detect_intent(
        self,
        query: str,
    ) -> RetrievalIntent:

        query = query.casefold()
        if self._query_codes(query):
            return RetrievalIntent(
                name="admission_category",
                confidence=1.0,
            )

        for intent, keywords in self.INTENT_KEYWORDS.items():

            for keyword in keywords:

                if self._contains_term(
                    query,
                    keyword,
                ):
                    return RetrievalIntent(
                        name=intent,
                        confidence=1.0,
                    )

        return RetrievalIntent(
            name="general",
            confidence=0.5,
        )
    
    def _extract_role(
        self,
        query: str,
    ) -> str | None:

        query = query.casefold()

        for canonical_role, aliases in self.ROLE_KEYWORDS.items():

            for alias in aliases:

                if self._contains_term(query, alias):
                    return canonical_role

        return None
    
    def _extract_entities(
        self,
        query: str,
    ) -> list[str]:

        terms = self._query_terms(query)

        role_words = {
            alias.casefold()
            for aliases in self.ROLE_KEYWORDS.values()
            for alias in aliases
        }

        entities = []

        for size in range(min(5, len(terms)), 1, -1):

            for i in range(len(terms) - size + 1):

                phrase = " ".join(terms[i:i + size])

                if any(
                    word in role_words
                    for word in phrase.split()
                ):
                    continue

                entities.append(phrase)

        return list(dict.fromkeys(entities))

    def _analyze_query(
        self,
        query: str,
    ) -> QueryAnalysis:

        query = query.strip()

        return QueryAnalysis(
            raw_query=query,
            intent=self._detect_intent(query),
            terms=self._query_terms(query),
            phrases=self._query_phrases(query),
            codes=self._query_codes(query),
            role=self._extract_role(query),
            entities=self._extract_entities(query),
        )
    
    def _structured_people_candidates(
        self,
        analysis: QueryAnalysis,
    ) -> list[dict[str, Any]]:

        results: list[dict[str, Any]] = []

        if analysis.intent.name != "people":
            return results

        for chunk in self._all_chunks():

            content = str(chunk.get("content", ""))
            searchable = content.casefold()

            if "record type: person" not in searchable:
                continue

            # content = str(chunk.get("content", ""))
            # searchable = content.casefold()

            score = 0

            # scoring goes here
            # -------------------------
            # Role Match
            # -------------------------
            if analysis.role:
                if f"role:\n{analysis.role}".casefold() in searchable:
                    score += 30
                elif f"role: {analysis.role}".casefold() in searchable:
                    score += 30

            # -------------------------
            # Entity / Department Match
            # -------------------------
            for entity in analysis.entities:

                entity = entity.casefold()

                if entity in searchable:
                    score += 25

                department_text = f"department:\ndepartment of {entity}"

                if department_text.casefold() in searchable:
                    score += 10

            if score > 0:
                candidate = dict(chunk)
                candidate["structured_score"] = score
                results.append(candidate)

        results.sort(
            key=lambda c: c["structured_score"],
            reverse=True,
        )

        return results

    def _structured_admission_category_candidates(
        self,
        analysis: QueryAnalysis,
    ) -> list[dict[str, Any]]:

        results: list[dict[str, Any]] = []

        for chunk in self._all_chunks():

            content = str(chunk.get("content", ""))
            searchable = content.casefold()

            if "record type: admission category" not in searchable:
                continue

            score = 0
        # Category Code Match
            for code in analysis.codes:

                code = code.casefold()

                print(
                    "CHECK",
                    code,
                    chunk.get("chunk_id"),
                    chunk.get("metadata", {}).get("page"),
                    self._contains_code(searchable, code),
                )

                if self._contains_code(searchable, code):
                    score += 100

            if score > 0:
                candidate = dict(chunk)
                candidate["structured_score"] = score
                results.append(candidate)

        results.sort(
            key=lambda c: c["structured_score"],
            reverse=True,
        )

        return results

    def _heading_policy(
        self,
        intent: RetrievalIntent,
    ) -> dict[str, tuple[str, ...]]:
        """
        Returns heading boost and penalty terms for the detected intent.

        This controls retrieval behaviour without hardcoding answers,
        pages, years, or document structure.
        """

        policies = {

            "fee": {
                "boost": (
                    "admission fee",
                    "fee",
                    "fees",
                    "charges",
                    "payment",
                ),
                "penalty": (
                    "refund",
                ),
            },

            "deadline": {
                "boost": (
                    "admission",
                    "application",
                    "schedule",
                    "important dates",
                    "last date",
                ),
                "penalty": (),
            },

            "eligibility": {
                "boost": (
                    "eligibility",
                    "criteria",
                    "requirements",
                    "qualification",
                ),
                "penalty": (),
            },

            "hostel": {
                "boost": (
                    "hostel",
                    "accommodation",
                ),
                "penalty": (),
            },

            "seat": {
                "boost": (
                    "seat",
                    "seat distribution",
                    "seat allocation",
                    "seat matrix",
                    "quota",
                ),
                "penalty": (),
            },

            "curriculum": {
                "boost": (
                    "curriculum",
                    "programme",
                    "program",
                    "course",
                    "courses",
                    "semester",
                    "study scheme",
                    "scheme of studies",
                ),
                "penalty": (),
            },

            "people": {
                "boost": (
                     "chairperson",
                     "chairman",
                     "dean",
                     "director",
                     "head",
                     "hod",
                     "faculty",
                     "staff",
                     "professor",
                     "lecturer",
                ),
                "penalty": (),
            },

            "department": {
                "boost": (
                    "department",
                    "faculty",
                ),
                "penalty": (),
            },

            "abbreviation": {
                "boost": (
                    "abbreviation",
                    "stands for",
                    "full form",
                ),
                "penalty": (),
            },

            "facilities": {
                "boost": (
                    "library",
                    "hostel",
                    "sports",
                    "laboratory",
                    "lab",
                    "transport",
                    "cafeteria",
                    "gymnasium",
                    "medical",
                ),
                "penalty": (),
            },

            "general": {
                "boost": (),
                "penalty": (),
            },
            "administration": {
                "boost": (
                    "administration",
                    "academic support",
                    "administration & academic support",
                    "vice chancellor",
                    "pro vice chancellor",
                    "registrar",
                    "treasurer",
                    "controller",
                    "dean",
                ),
                "penalty": (
                    "history",
                    "historical",
                    "introduction",
                    "background",
                ),
            },
        }

        return policies.get(
            intent.name,
            policies["general"],
        )
    
    def _lexical_match(
        self,
        *,
        query: str,
        query_terms: list[str],
        query_phrases: list[str],
        query_codes: list[str],
        heading: str,
        content: str,
    ) -> LexicalMatch:

        heading_folded = heading.casefold()
        content_folded = content.casefold()

        searchable = f"{heading_folded}\n{content_folded}"

        matched_terms = [
            term
            for term in query_terms
            if self._contains_term(searchable, term)
        ]

        heading_matches = [
            term
            for term in query_terms
            if self._contains_term(heading_folded, term)
        ]

        phrase_matches = [
            phrase
            for phrase in query_phrases
            if phrase in searchable
        ]

        code_matches = [
            code
            for code in query_codes
            if self._contains_code(
                f"{heading}\n{content}",
                code,
            )
        ]

        total_query_weight = sum(
            self._term_weight(term)
            for term in query_terms
        )

        matched_query_weight = sum(
            self._term_weight(term)
            for term in matched_terms
        )

        heading_query_weight = sum(
            self._term_weight(term)
            for term in heading_matches
        )

        return LexicalMatch(
            matched_terms=matched_terms,
            heading_matches=heading_matches,
            phrase_matches=phrase_matches,
            code_matches=code_matches,
            matched_query_weight=matched_query_weight,
            term_coverage=matched_query_weight / max(total_query_weight, 1.0),
            heading_coverage=heading_query_weight / max(total_query_weight, 1.0),
        )
    
    def _lexical_score(
        self,
        *,
        match: LexicalMatch,
        content: str,
        is_table: bool,
        heading: str,
    ) -> float:

        score = 0.0

        score += match.term_coverage * 6.0
        score += match.heading_coverage * 4.0

        score += min(match.matched_query_weight, 18.0)
        score += len(match.phrase_matches) * 4.0
        score += len(match.code_matches) * 6.0

        if len(match.matched_terms) >= 2 and match.term_coverage >= 0.80:
            score += 6.0

        if len(match.matched_terms) >= 3 and match.term_coverage >= 1.0:
            score += 5.0

        if is_table and match.term_coverage >= 0.60:
            score += 2.0

        if len(content) > 8000 and match.term_coverage < 0.50:
            score -= 4.0

        if self._looks_like_contents(
            heading=heading,
            content=content,
        ):
            score -= 5.0

        return min(score, 25.0)
    
    def _semantic_score(
        self,
        *,
        analysis: QueryAnalysis,
        heading: str,
        content: str,
        chunk: dict[str, Any],
        semantic_score: float,
        match: LexicalMatch,
    ) -> float:
        
        query = analysis.raw_query
        intent = analysis.intent

        heading_score = self._heading_score(
            query=query,
            intent=intent,
            heading=heading,
            content=content,
            chunk=chunk,
        )

        intent_score = self._intent_score(
            intent=intent,
            heading=heading,
            content=content,
            chunk=chunk,
        )

        entity_score = self._entity_score(
            match=match,
        )

        entity_phrase_score = self._entity_phrase_score(
            analysis=analysis,
            chunk=chunk,
        )

        page_score = self._page_score(
            intent=intent,
            chunk=chunk,
        )

        compound_score = 0.0

        if entity_score >= 4.0 and intent_score >= 3.0:
            compound_score += 6.0
        elif entity_score >= 2.0 and intent_score >= 2.0:
            compound_score += 3.0

        boilerplate_penalty = (
            -8.0 if self._is_boilerplate(chunk) else 0.0
        )

        heading_multiplier = (
            1.25
            if intent.name != "general" and heading_score > 0
            else 1.0
        )

        print(
            chunk.get("chunk_id"),
            "semantic=", semantic_score * 6.0,
            "heading=", heading_score,
            "intent=", intent_score,
            "entity=", entity_score,
            "entity_phrase=", entity_phrase_score,
            "compound=", compound_score,
            "page=", page_score,
        )

        return (
            semantic_score * 6.0
            + heading_score * heading_multiplier
            + intent_score
            + entity_score
            + entity_phrase_score
            + compound_score
            + page_score
            + boilerplate_penalty
        )


    def _rank_chunk(
        self,
        analysis: QueryAnalysis,
        chunk: dict[str, Any],
        semantic_score: float,
    ) -> dict[str, float]:
        
        #print(">>> _rank_chunk EXECUTED <<<")

        heading = str(chunk.get("heading", ""))
        content = str(chunk.get("content", ""))

        # heading_folded = heading.casefold()
        # content_folded = content.casefold()

        # searchable = f"{heading_folded}\n{content_folded}"

        # matched_terms = [
        #     term
        #     for term in query_terms
        #     if self._contains_term(searchable, term)
        # ]

        # # if "mechanical" in query.casefold():
        # #     print("\nQUERY TERM WEIGHTS")
        # #     for term in query_terms:
        # #         print(
        # #             term,
        # #             "weight=",
        # #             round(self._term_weight(term), 2),
        # #             "matched=",
        # #             term in matched_terms,
        # #         )

        # heading_matches = [
        #     term
        #     for term in query_terms
        #     if self._contains_term(heading_folded, term)
        # ]

        # phrase_matches = [
        #     phrase
        #     for phrase in query_phrases
        #     if phrase in searchable
        # ]

        # code_matches = [
        #     code
        #     for code in query_codes
        #     if self._contains_code(f"{heading}\n{content}", code)
        # ]

        # total_query_weight = sum(self._term_weight(term) for term in query_terms)
        # matched_query_weight = sum(self._term_weight(term) for term in matched_terms)
        # heading_query_weight = sum(self._term_weight(term) for term in heading_matches)

        # term_coverage = matched_query_weight / max(total_query_weight, 1.0)
        # heading_coverage = heading_query_weight / max(total_query_weight, 1.0)

        match = self._lexical_match(
            query=analysis.raw_query,
            query_terms=analysis.terms,
            query_phrases=analysis.phrases,
            query_codes=analysis.codes,
            heading=heading,
            content=content,
        )

        matched_query_weight = match.matched_query_weight

        term_coverage = match.term_coverage
        heading_coverage = match.heading_coverage

        phrase_matches = match.phrase_matches
        code_matches = match.code_matches

        # lexical_score = 0.0

        # lexical_score += term_coverage * 6.0
        # lexical_score += heading_coverage * 4.0

        # lexical_score += min(matched_query_weight, 18.0)
        # lexical_score += len(phrase_matches) * 4.0
        # lexical_score += len(code_matches) * 6.0

        # if len(query_terms) >= 2 and term_coverage >= 0.80:
        #     lexical_score += 6.0

        # if len(query_terms) >= 3 and term_coverage >= 1.0:
        #     lexical_score += 5.0

        # is_table = bool(chunk.get("is_complex_table", False))

        # if is_table and term_coverage >= 0.60:
        #     lexical_score += 2.0

        # if len(content) > 8000 and term_coverage < 0.50:
        #     lexical_score -= 4.0

        # if self._looks_like_contents(heading=heading, content=content):
        #     lexical_score -= 5.0

        # heading_score = self._heading_score(
        #     query=query, intent=intent, heading=heading, content=content, chunk=chunk
        # )

        # intent_score = self._intent_score(
        #     intent=intent, heading=heading, content=content, chunk=chunk
        # )

        # entity_score = self._entity_score(
        #     query=query, heading=heading, content=content, chunk=chunk
        # )

        # page_score = self._page_score(
        #     intent=intent,
        #     chunk=chunk,
        # )

        # compound_score = 0.0

        # if (
        #     entity_score >= 4.0
        #     and intent_score >= 3.0
        # ):
        #     compound_score += 6.0

        # elif (
        #     entity_score >= 2.0
        #     and intent_score >= 2.0
        # ):
        #     compound_score += 3.0

        # # Apply boilerplate/footer/header penalty if detected
        # boilerplate_penalty = 0.0
        # if self._is_boilerplate(chunk):
        #     # Heavy negative impact to push these chunks down
        #     boilerplate_penalty = -8.0

        # # Cap lexical contribution to prevent domination over semantics
        # # Maximum lexical score allowed (tuned to keep semantics primary)
        # max_lexical = 25.0
        # capped_lexical = min(lexical_score, max_lexical)

        capped_lexical = self._lexical_score(
            match=match,
            content=content,
            heading=heading,
            is_table=bool(chunk.get("is_complex_table", False)),
        )

        # # Increase heading relevance for intent‑specific sections
        # # Apply a multiplier to heading_score when the intent matches a boost term
        # heading_multiplier = 1.0
        # if intent.name != "general" and heading_score > 0:
        #     heading_multiplier = 1.25

        # final_score = (
        #     capped_lexical
        #     + (semantic_score * 6.0)
        #     + (heading_score * heading_multiplier)
        #     + intent_score
        #     + entity_score
        #     + compound_score
        #     + page_score
        #     + boilerplate_penalty
        # )

        semantic_component = self._semantic_score(
            analysis=analysis,
            heading=heading,
            content=content,
            chunk=chunk,
            semantic_score=semantic_score,
            match=match,
        )

        final_score = capped_lexical + semantic_component

        # if "mechanical" in query.casefold():

        #     print()
        #     print("=" * 60)
        #     print(chunk.get("chunk_id"))
        #     print(chunk.get("heading"))

        #     print("semantic :", semantic_score * 6)
        #     print("lexical  :", capped_lexical)
        #     print("heading  :", heading_score)
        #     print("intent   :", intent_score)
        #     print("entity   :", entity_score)
        #     print("compound :", compound_score)
        #     print("page      :", page_score)
        #     print("final     :", final_score)

        if chunk.get("page_number") == 19:
            print()
            print(chunk.get("chunk_id"))
            print("FINAL :", final_score)
            print("LEX   :", capped_lexical)
            print("SEM   :", semantic_component)
            print("ROLE? :", "chairperson" in content.casefold())
            print("CONTENT ROLE:")
            m = re.search(r"Role:\s*(.+)", content, re.IGNORECASE)
            print(m.group(1) if m else "None")
        
        print(
            chunk.get("chunk_id"),
            chunk.get("structured_score"),
        )

        return {
            "score": semantic_score,
            "semantic_score": semantic_score,
            "lexical_score": capped_lexical,
            "term_coverage": term_coverage,
            "heading_coverage": heading_coverage,
            "phrase_matches": float(len(phrase_matches)),
            "code_matches": float(len(code_matches)),
            "final_score": final_score,
        }

    def _heading_score(
        self,
        *,
        query: str,
        intent: RetrievalIntent,
        heading: str,
        content: str,
        chunk: dict[str, Any],
    ) -> float:
        """
        Scores heading relevance using heading plus the beginning of
        the section text.
        """

        policy = self._heading_policy(intent)

        heading_text = heading.casefold()
        preview = content[:300].casefold()

        searchable = f"{heading_text}\n{preview}"

        score = 0.0

        if intent.name == "administration":

            if (
                "administration" in heading_text
                or "academic support" in heading_text
            ):
                score += 20

            history_words = (
                "history",
                "historical",
                "background",
            )

            if any(word in heading_text for word in history_words):
                score -= 20

        query_terms = self._query_terms(query)
        query_phrases = self._query_phrases(query)

        for phrase in query_phrases:

            if phrase in heading_text:
                score += 8.0
        
        # Reward headings that contain important query terms.
        for term in query_terms:

            if len(term) < 3:
                continue

            if self._contains_term(
                heading_text,
                term,
            ):
                score += 3.0

        # Positive boosts
        for term in policy["boost"]:

            term = term.casefold()

            if term in heading_text:
                score += 4.0

            elif term in searchable:
                score += 2.0

        # Penalties
        for term in policy["penalty"]:

            term = term.casefold()

            if term in heading_text:
                score -= 3.0

            elif term in searchable:
                score -= 1.5

        return score

    def _intent_score(
        self,
        *,
        intent: RetrievalIntent,
        heading: str,
        content: str,
        chunk: dict[str, Any],
    ) -> float:

        metadata = (
            chunk.get(
                "metadata",
                {},
            )
            or {}
        )

        score = 0.0

        record_type = (
            metadata.get(
                "record_type",
                "",
            )
            .casefold()
        )

        intent_name = (
            intent.name.casefold()
        )

        mapping = {
            "people": "people",
            "contacts": "contact",
            "fees": "fee",
            "academics": "curriculum",
            "student_life": "facilities",
            "research": "research",
            "governance": "governance",
            "admissions": "admission",
            "admission_categories": "admission_category",
        }

        expected = mapping.get(
            record_type,
        )

        if (
            expected
            and expected == intent_name
        ):
            score += 2.5

        heading_text = (
            heading.casefold()
        )

        if (
            intent_name != "general"
            and intent_name in heading_text
        ):
            score += 1.5

        return score

    def _entity_score(
        self,
        *,
        # query: str,
        # heading: str,
        # content: str,
        # chunk: dict[str, Any],
        match: LexicalMatch,
    ) -> float:
        """
        Rewards chunks whose heading contains important
        query entities.

        Completely generic.
        """
        # score = 0.0
        # heading = heading.casefold()
        # content = content.casefold()
        # query_terms = self._query_terms(query)
        # for term in query_terms:
        #     if self._contains_term(heading, term):
        #         score += 2.5

        #     if self._contains_term(content, term):
        #         score += 1.5

        # return score
        return (
                len(match.heading_matches) * 2.5
                + (
                    len(match.matched_terms)
                    - len(match.heading_matches)
                ) * 1.5
            )
    def _entity_phrase_score(
        self,
        *,
        analysis: QueryAnalysis,
        chunk: dict[str, Any],
    ) -> float:

        if not analysis.entities:
            return 0.0

        heading = str(chunk.get("heading", "")).casefold()

        parent = str(
            chunk.get("parent_heading", "")
        ).casefold()

        metadata = " ".join(
            str(v)
            for v in (chunk.get("metadata") or {}).values()
        ).casefold()

        preview = str(
            chunk.get("content", "")
        )[:300].casefold()

        score = 0.0

        for entity in analysis.entities:

            entity = entity.casefold()

            if entity in heading:
                score += 8.0

            elif entity in parent:
                score += 6.0

            elif entity in metadata:
                score += 5.0

            elif entity in preview:
                score += 2.0

        return score

    def _page_score(
        self,
        *,
        intent: RetrievalIntent,
        chunk: dict[str, Any],
    ) -> float:
        return 0.0
        

    def _query_terms(self, query: str) -> list[str]:
        terms = []
        for token in re.findall(r"[A-Za-z0-9]+", query.casefold()):
            if len(token) <= 1 or token in self.STOP_WORDS:
                continue
            if token.endswith("ies") and len(token) > 4:
                token = token[:-3] + "y"
            elif token.endswith("s") and not token.endswith("ss") and len(token) > 3:
                token = token[:-1]
            terms.append(token)
        return list(dict.fromkeys(terms))

    def _query_phrases(
        self,
        query: str,
    ) -> list[str]:

        terms = self._query_terms(query)

        phrases = []

        for size in (4, 3, 2):

            for index in range(
                0,
                len(terms) - size + 1,
            ):

                phrases.append(
                    " ".join(
                        terms[
                            index:index + size
                        ]
                    )
                )

        return list(dict.fromkeys(phrases))

    def _query_codes(
        self,
        query: str,
    ) -> list[str]:

        # codes = re.findall(
        #     r"\b[A-Za-z]{1,8}"
        #     r"(?:[-()][A-Za-z0-9]+)+\b"
        #     r"|\b[A-Z]{2,8}\b",
        #     query,
        # )
        codes = re.findall(
            r"\b(?:R|SF)-\d+(?:\([A-Za-z0-9]+\))?",
            query,
            flags=re.IGNORECASE,
        )

        return list(dict.fromkeys(codes))

    def _contains_term(
        self,
        text: str,
        term: str,
    ) -> bool:

        pattern = (
            r"(?<![A-Za-z0-9])"
            + re.escape(term)
        )

        if (
            term.isalpha()
            and len(term) > 3
        ):
            pattern += r"(?:s|es)?"

        pattern += r"(?![A-Za-z0-9])"

        return bool(
            re.search(
                pattern,
                text,
                flags=re.IGNORECASE,
            )
        )

    def _contains_code(
        self,
        text: str,
        code: str,
    ) -> bool:

        return self._contains_term(
            text=text,
            term=code,
        )

    def _looks_like_contents(
        self,
        heading: str,
        content: str,
    ) -> bool:

        text = (
            f"{heading}\n{content}"
        ).casefold()

        if "table of contents" in text:
            return True

        numbered_lines = len(
            re.findall(
                r"(?m)^\s*\d+(?:\.\d+)+",
                content,
            )
        )

        return (
            numbered_lines >= 12
            and len(content) < 6000
        )

    def _is_boilerplate(self, chunk: dict[str, Any]) -> bool:
        """
        Detect obvious page headers/footers only.
        Never classify a chunk as boilerplate merely because
        its content mentions NED University or Prospectus.
        """

        heading = str(chunk.get("heading", "")).casefold().strip()

        parent = str(
            chunk.get("parent_heading", "")
        ).casefold().strip()

        text = f"{heading}\n{parent}"

        boilerplate_phrases = (
            "prospectus 2026",
            "prospectus 2025",
            "of engineering & technology",
            "of engineering and technology",
        )

        return any(
            phrase == heading
            or phrase == parent
            for phrase in boilerplate_phrases
        )

    def _diversify(
        self,
        candidates: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:

        selected = []

        seen_chunk_ids = set()
        page_counts = {}
        heading_counts = {}

        for candidate in candidates:

            chunk_id = candidate.get("chunk_id")

            if chunk_id in seen_chunk_ids:
                continue

            page = candidate.get("page_number")
            heading = str(candidate.get("heading", "")).strip().casefold()
            chunk_id = str(candidate.get("chunk_id", ""))

            is_people = chunk_id.startswith("structured-people")

            # Keep the best result from a page, but don't let one page dominate.
            if page_counts.get(page, 0) >= 3:
                continue

            # Avoid many nearly identical heading chunks.
            if (
                not is_people
                and heading
                and heading_counts.get(heading, 0) >= 2
            ):
                continue

            selected.append(candidate)

            seen_chunk_ids.add(chunk_id)
            page_counts[page] = page_counts.get(page, 0) + 1

            if heading:
                heading_counts[heading] = heading_counts.get(heading, 0) + 1

            if len(selected) >= top_k:
                break

        return selected


