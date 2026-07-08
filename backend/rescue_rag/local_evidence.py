import json
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_CHUNKS_PATH = (
    PROJECT_ROOT
    / "storage"
    / "rescue"
    / "UGProspectus2025_chunks.json"
)


class LocalEvidenceService:
    """
    Searches already parsed prospectus chunks directly.

    This is NOT university-specific.

    It provides exact lexical evidence for:
    - department staff
    - chairpersons
    - programme curriculum
    - course codes
    - year and semester tables
    - credit hours
    - large structured tables

    Qdrant remains the semantic fallback.
    """

    STOP_WORDS = {
        "a",
        "an",
        "and",
        "are",
        "at",
        "be",
        "for",
        "from",
        "give",
        "in",
        "is",
        "me",
        "of",
        "on",
        "please",
        "show",
        "tell",
        "the",
        "to",
        "what",
        "which",
        "who",
        "with",
    }

    def __init__(
        self,
        chunks_path: Path | None = None,
    ) -> None:

        self.chunks_path = (
            chunks_path
            or DEFAULT_CHUNKS_PATH
        )

        if not self.chunks_path.exists():
            raise FileNotFoundError(
                "Chunk file not found: "
                f"{self.chunks_path}"
            )

        data = json.loads(
            self.chunks_path.read_text(
                encoding="utf-8"
            )
        )

        self.chunks = data.get(
            "chunks",
            []
        )

        if not self.chunks:
            raise RuntimeError(
                "No chunks found in "
                f"{self.chunks_path}"
            )


    def search(
        self,
        query: str,
        limit: int = 12,
    ) -> list[dict[str, Any]]:

        query = query.strip()

        if not query:
            return []

        query_terms = self._query_terms(
            query
        )

        exact_phrases = (
            self._important_phrases(
                query
            )
        )

        scored = []

        for chunk in self.chunks:

            heading = str(
                chunk.get(
                    "heading",
                    ""
                )
            )

            content = str(
                chunk.get(
                    "content",
                    ""
                )
            )

            searchable = (
                f"{heading}\n{content}"
            ).casefold()

            heading_folded = (
                heading.casefold()
            )

            score = 0.0
            matched_terms = []

            for term in query_terms:

                term_folded = (
                    term.casefold()
                )

                content_count = (
                    searchable.count(
                        term_folded
                    )
                )

                if content_count:

                    matched_terms.append(
                        term
                    )

                    score += min(
                        content_count,
                        5,
                    ) * 1.0

                if (
                    term_folded
                    in heading_folded
                ):

                    score += 6.0

            for phrase in exact_phrases:

                phrase_folded = (
                    phrase.casefold()
                )

                if (
                    phrase_folded
                    in searchable
                ):

                    score += 8.0

                if (
                    phrase_folded
                    in heading_folded
                ):

                    score += 12.0

            coverage = (
                len(matched_terms)
                / max(
                    len(query_terms),
                    1,
                )
            )

            score += coverage * 10.0

            if self._looks_like_course_query(
                query
            ):

                score += (
                    self._course_evidence_score(
                        searchable
                    )
                )

            if self._looks_like_staff_query(
                query
            ):

                score += (
                    self._staff_evidence_score(
                        searchable
                    )
                )

            if self._looks_like_table_query(
                query
            ):

                if chunk.get(
                    "is_complex_table",
                    False,
                ):

                    score += 5.0

            if score <= 0:
                continue

            scored.append(
                {
                    **chunk,
                    "local_score": round(
                        score,
                        4,
                    ),
                    "matched_terms": (
                        matched_terms
                    ),
                }
            )

        scored.sort(
            key=lambda item: (
                item["local_score"],
                len(
                    item.get(
                        "matched_terms",
                        []
                    )
                ),
            ),
            reverse=True,
        )

        return scored[:limit]


    def _query_terms(
        self,
        query: str,
    ) -> list[str]:

        raw_terms = re.findall(
            r"[A-Za-z0-9]+(?:[-/][A-Za-z0-9]+)*",
            query,
        )

        terms = []

        for term in raw_terms:

            normalized = (
                term.casefold()
            )

            if (
                normalized
                in self.STOP_WORDS
            ):
                continue

            if len(normalized) < 2:
                continue

            terms.append(term)

        return list(
            dict.fromkeys(terms)
        )


    def _important_phrases(
        self,
        query: str,
    ) -> list[str]:

        query = re.sub(
            r"\s+",
            " ",
            query,
        ).strip()

        phrases = []

        patterns = [
            r"department of ([a-z0-9 &/-]+)",
            r"([a-z0-9 &/-]+) department",
            r"([a-z0-9 &/-]+) engineering",
            r"([a-z0-9 &/-]+) science",
            r"(first year)",
            r"(second year)",
            r"(third year)",
            r"(final year)",
            r"(fall semester)",
            r"(spring semester)",
            r"(course code)",
            r"(credit hours)",
            r"(seat distribution)",
        ]

        for pattern in patterns:

            matches = re.findall(
                pattern,
                query,
                flags=re.IGNORECASE,
            )

            for match in matches:

                if isinstance(
                    match,
                    tuple,
                ):
                    match = " ".join(
                        match
                    )

                match = match.strip()

                if match:
                    phrases.append(
                        match
                    )

        return list(
            dict.fromkeys(phrases)
        )


    def _looks_like_course_query(
        self,
        query: str,
    ) -> bool:

        query = query.casefold()

        terms = (
            "course",
            "courses",
            "course code",
            "curriculum",
            "semester",
            "credit hour",
            "credit hours",
            "first year",
            "second year",
            "third year",
            "final year",
        )

        return any(
            term in query
            for term in terms
        )


    def _looks_like_staff_query(
        self,
        query: str,
    ) -> bool:

        query = query.casefold()

        terms = (
            "chairperson",
            "co-chairperson",
            "chairman",
            "chairwoman",
            "professor",
            "faculty",
            "lecturer",
            "staff",
            "head of department",
            "hod",
        )

        return any(
            term in query
            for term in terms
        )


    def _looks_like_table_query(
        self,
        query: str,
    ) -> bool:

        query = query.casefold()

        terms = (
            "distribution",
            "seats",
            "fee",
            "fees",
            "course",
            "courses",
            "semester",
            "credit",
            "table",
        )

        return any(
            term in query
            for term in terms
        )


    def _course_evidence_score(
        self,
        searchable: str,
    ) -> float:

        score = 0.0

        signals = (
            "course code",
            "course title",
            "credit hours",
            "fall semester",
            "spring semester",
            "first year",
            "second year",
            "third year",
            "final year",
        )

        for signal in signals:

            if signal in searchable:
                score += 3.0

        course_codes = re.findall(
            r"\b[A-Z]{2,4}[-/]\d{3}\b",
            searchable.upper(),
        )

        score += min(
            len(course_codes),
            10,
        ) * 0.5

        return score


    def _staff_evidence_score(
        self,
        searchable: str,
    ) -> float:

        score = 0.0

        signals = (
            "chairperson",
            "co-chairperson",
            "professor",
            "associate professor",
            "assistant professor",
            "lecturer",
        )

        for signal in signals:

            if signal in searchable:
                score += 4.0

        return score
