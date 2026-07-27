from __future__ import annotations

from typing import Any


class SeatDistributionProcessor:
    """
    Handles seat distribution processing.
    """

    def process(
        self,
        *,
        section: Any,
        parsed_pages: list[dict],
    ):
        """
        Entry point.

        This will later:
        1. Decide whether extraction is possible.
        2. Route to structured extraction.
        3. Or create complex metadata.
        """

        extractable = self.is_extractable(
            section=section,
            parsed_pages=parsed_pages,
        )

        return {
            "extractable": extractable,
            "section": section,
        }

    def is_extractable(
        self,
        *,
        section,
        parsed_pages,
    ) -> bool:
        """
        Decide whether a seat distribution section
        can be extracted into structured records.
        """

        section_pages = [
            page
            for page in parsed_pages
            if (
                section.start_page
                <= page.get("page_number", 0)
                <= section.end_page
            )
        ]

        print(
            f"\nInspecting "
            f"{section.section_type}"
        )
        print(
            f"Pages: "
            f"{section.start_page}-"
            f"{section.end_page}"
        )
        print(
            f"Collected pages: "
            f"{len(section_pages)}"
        )

        return False