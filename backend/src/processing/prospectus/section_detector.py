from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class ProspectusSection:
    section_type: str
    start_page: int
    end_page: int
    heading: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProspectusSectionDetector:
    CHAPTER_PATTERN = re.compile(
        r"(?:^|\n)\s*(?:"
        r"(?P<number_a>\d+)\s+CHAPTER|"
        r"CHAPTER\s+(?P<number_b>\d+)"
        r")\b",
        re.IGNORECASE,
    )

    REGULAR_SCHEME_PATTERN = re.compile(
        r"\bREGULAR\s+SCHEME\b",
        re.IGNORECASE,
    )

    SELF_FINANCE_SCHEME_PATTERN = re.compile(
        r"\bSELF[\s-]+FINANCE\s+SCHEME\b",
        re.IGNORECASE,
    )

    DESCRIPTION_PATTERN = re.compile(
        r"\bDescription\s+of\s+Categories\b",
        re.IGNORECASE,
    )

    COURSE_OF_STUDIES_PATTERN = re.compile(
        r"\bCourse\s+of\s+Studies\b",
        re.IGNORECASE,
    )

    def detect(
        self,
        pages: list[dict[str, Any]],
    ) -> list[ProspectusSection]:
        ordered_pages = sorted(
            pages,
            key=lambda page: page["page_number"],
        )

        sections: list[ProspectusSection] = []

        curriculum = self._detect_curriculum(
            ordered_pages
        )
        if curriculum:
            sections.append(curriculum)

        regular = self._detect_seat_section(
            pages=ordered_pages,
            section_type="seat_distribution_regular",
            start_pattern=self.REGULAR_SCHEME_PATTERN,
        )
        if regular:
            sections.append(regular)

        self_finance = self._detect_seat_section(
            pages=ordered_pages,
            section_type="seat_distribution_self_finance",
            start_pattern=self.SELF_FINANCE_SCHEME_PATTERN,
        )
        if self_finance:
            sections.append(self_finance)

        return sections

    def _detect_curriculum(
        self,
        pages: list[dict[str, Any]],
    ) -> ProspectusSection | None:
        start_index = None
        chapter_number = None

        for index, page in enumerate(pages):
            text = self._page_text(page)

            if not self.COURSE_OF_STUDIES_PATTERN.search(text):
                continue

            chapter_number = self._chapter_number(text)
            start_index = index
            break

        if start_index is None:
            return None

        end_index = len(pages) - 1

        for index in range(start_index + 1, len(pages)):
            next_chapter = self._chapter_number(
                self._page_text(pages[index])
            )

            if (
                next_chapter is not None
                and next_chapter != chapter_number
            ):
                end_index = index - 1
                break

        return ProspectusSection(
            section_type="curriculum",
            start_page=pages[start_index]["page_number"],
            end_page=pages[end_index]["page_number"],
            heading="Course of Studies",
            metadata={
                "discovery_method": (
                    "course_of_studies_to_next_chapter"
                ),
                "chapter_number": chapter_number,
            },
        )

    def _detect_seat_section(
        self,
        pages: list[dict[str, Any]],
        section_type: str,
        start_pattern: re.Pattern[str],
    ) -> ProspectusSection | None:
        start_index = None
        heading = None

        for index, page in enumerate(pages):
            text = self._page_text(page)
            match = start_pattern.search(text)

            if match:
                start_index = index
                heading = match.group(0)
                break

        if start_index is None:
            return None

        end_index = len(pages) - 1

        for index in range(start_index + 1, len(pages)):
            text = self._page_text(pages[index])

            if self.DESCRIPTION_PATTERN.search(text):
                end_index = index - 1
                break

        return ProspectusSection(
            section_type=section_type,
            start_page=pages[start_index]["page_number"],
            end_page=pages[end_index]["page_number"],
            heading=heading or section_type,
            metadata={
                "discovery_method": (
                    "scheme_heading_to_description_of_categories"
                ),
            },
        )

    @classmethod
    def _chapter_number(
        cls,
        text: str,
    ) -> int | None:
        match = cls.CHAPTER_PATTERN.search(text)

        if not match:
            return None

        value = (
            match.group("number_a")
            or match.group("number_b")
        )

        return int(value)

    @staticmethod
    def _page_text(
        page: dict[str, Any],
    ) -> str:
        return (
            page.get("text")
            or page.get("markdown")
            or ""
        )
