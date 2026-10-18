import json
import re
from pathlib import Path
from typing import Any


class SeatDistributionRouter:
    """
    Routes broad seat-distribution requests to
    dynamically detected official prospectus pages.

    Specific category codes such as R-1(A) stay
    in the normal RAG path.
    """

    SEAT_TERMS = (
        "seats"
        "seat distribution",
        "distribution of seats",
        "seat allocation",
        "seats are available",
        "seats available",
        "available seats",
        "number of seats",
        "how many seats",
        "total seats",
        "regular seats",
        "regular seat",
        "self finance seats",
        "self finance seat",
        "self-finance seats",
        "self-finance seat",
        "seat arrangement",
        "seat matrix",
        "seat breakup",
        "admission category distribution",
    )

    SELF_FINANCE_TERMS = (
        "self finance",
        "self-finance",
        "self financing",
        "self-financing",
    )

    REGULAR_TERMS = (
        "regular",
        "merit seats",
        "open merit seats",
    )

    CATEGORY_CODE_PATTERN = re.compile(
        r"\b(?:r|sf)-\d+(?:\([a-z0-9]+\))?\b",
        re.IGNORECASE,
    )

    def route(
        self,
        question: str,
        official_url: str | None,
        sections_path: Path | None,
    ) -> dict[str, Any] | None:

        normalized = " ".join(
            question.casefold().split()
        )

        # Specific category descriptions belong
        # to normal RAG, not seat-table routing.
        if self.CATEGORY_CODE_PATTERN.search(
            normalized
        ):
            return None

        if not self._is_seat_request(normalized):
            return None

        official_url = str(
            official_url or ""
        ).strip()

        if not official_url:
            return None

        sections = self._load_sections(
            sections_path
        )

        target_types = self._target_types(
            normalized
        )

        matched_sections = [
            section
            for section in sections
            if section.get("section_type")
            in target_types
        ]

        if not matched_sections:
            return None

        page_references = []

        for section in matched_sections:
            section_type = str(
                section["section_type"]
            )

            label = self._label(
                section_type
            )

            start_page = int(
                section["start_page"]
            )

            end_page = int(
                section["end_page"]
            )

            for page_number in range(
                start_page,
                end_page + 1,
            ):
                page_references.append(
                    {
                        "document": (
                            "official_prospectus"
                        ),
                        "page_number": page_number,
                        "page_path": None,
                        "page_url": (
                            f"{official_url}"
                            f"#page={page_number}"
                        ),
                        "reason": (
                            f"Open official {label} "
                            f"seat distribution page "
                            f"{page_number}."
                        ),
                    }
                )

        return {
            "question": question,
            "answer": self._build_answer(
                matched_sections
            ),
            "status": (
                "seat_distribution_official"
            ),
            "sources": [],
            "page_references": page_references,
            "retrieval": {
                "route": "seat_distribution",
                "vector_chunks": [],
                "vector_chunk_count": 0,
            },
        }

    def _is_seat_request(
        self,
        normalized: str,
    ) -> bool:

        if normalized in {"r", "sf"}:
            return True
        
        if self.CATEGORY_CODE_PATTERN.search(normalized):
            return False
        
        if "seat" in normalized:
            return True

        if "seats" in normalized:
            return True

        return any(
            term in normalized
            for term in self.SEAT_TERMS
        )

    def _target_types(
        self,
        normalized: str,
    ) -> set[str]:

        if normalized == "r":
            return {
                "seat_distribution_regular"
            }

        if normalized == "sf":
            return {
                "seat_distribution_self_finance"
            }

        wants_sf = any(
            term in normalized
            for term in self.SELF_FINANCE_TERMS
        )

        wants_regular = any(
            term in normalized
            for term in self.REGULAR_TERMS
        )

        if wants_sf and not wants_regular:
            return {
                "seat_distribution_self_finance"
            }

        if wants_regular and not wants_sf:
            return {
                "seat_distribution_regular"
            }

        return {
            "seat_distribution_regular",
            "seat_distribution_self_finance",
        }

    @staticmethod
    def _load_sections(
        sections_path: Path | None,
    ) -> list[dict[str, Any]]:

        if (
            sections_path is None
            or not sections_path.exists()
        ):
            return []

        try:
            data = json.loads(
                sections_path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ):
            return []

        sections = data.get("sections", [])

        if not isinstance(sections, list):
            return []

        return sections

    @staticmethod
    def _label(
        section_type: str,
    ) -> str:

        if (
            section_type
            == "seat_distribution_regular"
        ):
            return "regular"

        return "self-finance"

    def _build_answer(
        self,
        sections: list[dict[str, Any]],
    ) -> str:

        labels = [
            self._label(
                str(section["section_type"])
            )
            for section in sections
        ]

        if len(labels) == 1:
            return (
                f"The {labels[0]} seat distribution "
                "is available on the official "
                "prospectus pages below."
            )

        return (
            "The regular and self-finance seat "
            "distributions are available on the "
            "official prospectus pages below."
        )
