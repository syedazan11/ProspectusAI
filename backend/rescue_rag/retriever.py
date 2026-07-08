import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from qdrant_client import QdrantClient, models


PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(
    PROJECT_ROOT / "backend" / ".env"
)


class RescueRetriever:

    MODEL = (
        "sentence-transformers/"
        "all-minilm-l6-v2"
    )

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

        if not collection_name:
            raise ValueError(
                "Qdrant collection name is required."
            )

        self.collection_name = collection_name

        self.client = QdrantClient(
            url=os.getenv("QDRANT_HOST"),
            api_key=os.getenv(
                "QDRANT_API_KEY"
            ),
            cloud_inference=True,
            timeout=180,
            check_compatibility=False,
        )

        self._all_chunks_cache = None
        self._page_context_cache = None
        self._term_document_frequency_cache = None

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

    def retrieve(
        self,
        query: str,
        top_k: int = 8,
    ) -> list[dict[str, Any]]:

        query = query.strip()

        if not query:
            return []

        query_terms = self._query_terms(query)
        query_phrases = self._query_phrases(query)
        query_codes = self._query_codes(query)

        semantic_results = (
            self.client.query_points(
                collection_name=self.collection_name,
                query=models.Document(
                    text=query,
                    model=self.MODEL,
                ),
                limit=max(
                    top_k * 8,
                    60,
                ),
                with_payload=True,
            ).points
        )

        semantic_by_id = {}

        for result in semantic_results:

            payload = result.payload or {}
            chunk_id = payload.get("chunk_id")

            if chunk_id:
                semantic_by_id[chunk_id] = float(
                    result.score
                )

        candidates = []

        for chunk in self._all_chunks():

            candidate = dict(chunk)
            chunk_id = candidate.get("chunk_id")

            semantic_score = semantic_by_id.get(
                chunk_id,
                0.0,
            )

            ranking = self._rank_chunk(
                query=query,
                query_terms=query_terms,
                query_phrases=query_phrases,
                query_codes=query_codes,
                chunk=candidate,
                semantic_score=semantic_score,
            )

            if (
                semantic_score <= 0
                and ranking["lexical_score"] <= 0
            ):
                continue

            candidate.update(ranking)
            candidates.append(candidate)

        candidates.sort(
            key=lambda item: (
                item["final_score"],
                item["semantic_score"],
            ),
            reverse=True,
        )

        return self._diversify(
            candidates=candidates,
            top_k=top_k,
        )

    def _rank_chunk(
        self,
        query: str,
        query_terms: list[str],
        query_phrases: list[str],
        query_codes: list[str],
        chunk: dict[str, Any],
        semantic_score: float,
    ) -> dict[str, float]:

        heading = str(
            chunk.get("heading", "")
        )

        content = str(
            chunk.get("content", "")
        )

        heading_folded = heading.casefold()
        content_folded = content.casefold()

        searchable = (
            f"{heading_folded}\n"
            f"{content_folded}"
        )

        matched_terms = [
            term
            for term in query_terms
            if self._contains_term(
                searchable,
                term,
            )
        ]

        heading_matches = [
            term
            for term in query_terms
            if self._contains_term(
                heading_folded,
                term,
            )
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

        term_coverage = (
            matched_query_weight
            / max(total_query_weight, 1.0)
        )

        heading_coverage = (
            heading_query_weight
            / max(total_query_weight, 1.0)
        )

        lexical_score = 0.0

        lexical_score += term_coverage * 12.0
        lexical_score += heading_coverage * 12.0

        lexical_score += min(
            matched_query_weight,
            18.0,
        )
        lexical_score += len(phrase_matches) * 4.0
        lexical_score += len(code_matches) * 6.0

        if (
            len(query_terms) >= 2
            and term_coverage >= 0.80
        ):
            lexical_score += 6.0

        if (
            len(query_terms) >= 3
            and term_coverage >= 1.0
        ):
            lexical_score += 5.0

        is_table = bool(
            chunk.get(
                "is_complex_table",
                False,
            )
        )

        if (
            is_table
            and term_coverage >= 0.60
        ):
            lexical_score += 2.0

        if (
            len(content) > 8000
            and term_coverage < 0.50
        ):
            lexical_score -= 4.0

        if self._looks_like_contents(
            heading=heading,
            content=content,
        ):
            lexical_score -= 5.0

        final_score = (
            lexical_score
            + (semantic_score * 6.0)
        )

        return {
            "score": semantic_score,
            "semantic_score": semantic_score,
            "lexical_score": lexical_score,
            "term_coverage": term_coverage,
            "heading_coverage": heading_coverage,
            "phrase_matches": float(
                len(phrase_matches)
            ),
            "code_matches": float(
                len(code_matches)
            ),
            "final_score": final_score,
        }

    def _query_terms(
        self,
        query: str,
    ) -> list[str]:

        terms = []

        for token in re.findall(
            r"[A-Za-z0-9]+",
            query.casefold(),
        ):

            if len(token) <= 1:
                continue

            if token in self.STOP_WORDS:
                continue

            if (
                token.endswith("ies")
                and len(token) > 4
            ):
                token = token[:-3] + "y"

            elif (
                token.endswith("s")
                and not token.endswith("ss")
                and len(token) > 3
            ):
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

        codes = re.findall(
            r"\b[A-Za-z]{1,8}"
            r"(?:[-()][A-Za-z0-9]+)+\b"
            r"|\b[A-Z]{2,8}\b",
            query,
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

    def _diversify(
        self,
        candidates: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:

        selected = []
        seen_chunk_ids = set()

        for candidate in candidates:

            chunk_id = candidate.get(
                "chunk_id"
            )

            if chunk_id in seen_chunk_ids:
                continue

            selected.append(candidate)
            seen_chunk_ids.add(chunk_id)

            if len(selected) >= top_k:
                break

        return selected
