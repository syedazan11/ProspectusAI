from __future__ import annotations

import re
from typing import Any
from dataclasses import dataclass
from typing import Pattern
from src.retrieval.models import ChunkCategory

@dataclass(frozen=True)
class CategoryRule:
    category: ChunkCategory
    pattern: Pattern[str]

class ChunkClassifier:
    """
    Classifies semantic chunks.

    Runs exactly once while building indexes.

    Classification is cached afterwards.
    """

    TOC_MAIN_ENTRY = re.compile(
        r"^\d+\.\s+.+$",
        re.MULTILINE,
    )

    TOC_SUB_ENTRY = re.compile(
        r"^\d+(?:\.\d+)+\s+.+$",
        re.MULTILINE,
    )

    TOC_PAGE_NUMBER = re.compile(
        r"\s+\d+\s*$",
        re.MULTILINE,
    )

    TOC_CONTINUATION = re.compile(
        r"^\(.+\)$",
        re.MULTILINE,
    )

    TOC_SEARCH_PAGES = 7

    CURRICULUM_PATTERNS = (
        "course code",
        "course title",
        "credit hours",
        "prerequisite",
        "fall semester",
        "spring semester",
        "elective",
        "theory",
        "practical",
    )


    @classmethod
    def classify(
        cls,
        chunk: dict[str, Any],
    ) -> ChunkCategory:
        metadata = chunk.get("metadata") or {}

    #
    # Ignore structured records.
    #

        if chunk.get("chunk_type") != "semantic":
            return ChunkCategory.GENERAL

        if cls._is_table_of_contents(chunk):
            return ChunkCategory.TABLE_OF_CONTENTS

        if cls._is_curriculum(chunk):
            return ChunkCategory.CURRICULUM

        return ChunkCategory.GENERAL


    @staticmethod
    def _search_text(chunk: dict[str, Any]) -> str:

        metadata = chunk.get("metadata") or {}

        parts = [
            chunk.get("content", ""),
            chunk.get("embedding_text", ""),
            chunk.get("heading_path", ""),
            chunk.get("section_title", ""),
            chunk.get("h1", ""),
            chunk.get("h2", ""),
            chunk.get("h3", ""),
            chunk.get("h4", ""),
        ]

        return "\n".join(
            str(part)
            for part in parts
            if part
        ).casefold()

    @classmethod
    def _is_table_of_contents(
        cls,
        chunk: dict[str, Any],
    ) -> bool:

        text = cls._search_text(chunk)

        if not text:
            return False

    #
    # Structured chunks are never TOCs.
    #

        metadata = chunk.get("metadata") or {}

        if chunk.get("chunk_type") != "semantic":
            return False
        page = chunk.get("page")
        # if not isinstance(page, int):
        #     return False

        if page > 7:
            return False

        text = chunk.get("content", "")

        if not text:
            return False


    #
    # TOCs almost always contain
    # multiple title → page patterns.
    #

        main = len(cls.TOC_MAIN_ENTRY.findall(text))
        sub = len(cls.TOC_SUB_ENTRY.findall(text))
        page_refs = len(cls.TOC_PAGE_NUMBER.findall(text))
        continuation = len(cls.TOC_CONTINUATION.findall(text))

        return (
            (main >= 2 and page_refs >= 3)
            or (sub >= 4)
            or (page_refs >= 6)
            or (sub >= 2 and continuation >= 2)
        )

    @classmethod
    def _is_curriculum(
        cls,
        chunk: dict[str, Any],
    ) -> bool:

        if chunk.get("chunk_type") != "semantic":
            return False

        text = cls._search_text(chunk)

    #
    # Strong combinations
    #

        has_course_code = "course code" in text
        has_course_title = "course title" in text
        has_credit_hours = "credit hours" in text

        if has_course_code and has_credit_hours:
            return True
    
        if has_course_title and has_credit_hours:
            return True

        if "fall semester" in text:
            return True

        if "spring semester" in text:
            return True

    #
    # Otherwise require multiple curriculum terms
    #

        matches = sum(
            keyword in text
            for keyword in cls.CURRICULUM_PATTERNS
        )

        return matches