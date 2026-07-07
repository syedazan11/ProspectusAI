from pathlib import Path
from typing import Any

import fitz


class PageRouter:
    """
    Performs cheap local page analysis before
    expensive extraction.

    Routes pages into broad processing paths:

    - scanned
    - digital_text
    - digital_table_candidate

    A table candidate is not automatically sent
    to the vision model. Detailed table analysis
    happens later.
    """

    def analyze_page(
        self,
        page_path: Path,
        page_number: int,
        page_type: str,
    ) -> dict[str, Any]:

        if page_type == "scanned":
            return {
                "page_number": page_number,
                "page_path": str(page_path),
                "page_type": page_type,
                "route": "scanned",
                "text_length": 0,
                "drawing_count": 0,
            }

        document = fitz.open(page_path)

        try:
            page = document[0]

            text = page.get_text().strip()
            drawings = page.get_drawings()

            drawing_count = len(drawings)

        finally:
            document.close()

        route = "digital_text"

        if self._is_table_candidate(
            text=text,
            drawing_count=drawing_count,
        ):
            route = "digital_table_candidate"

        return {
            "page_number": page_number,
            "page_path": str(page_path),
            "page_type": page_type,
            "route": route,
            "text_length": len(text),
            "drawing_count": drawing_count,
        }

    def route_document(
        self,
        page_paths: list[Path],
        page_classifications: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

        classifications_by_page = {
            item["page_number"]: item
            for item in page_classifications
        }

        routes = []

        for page_number, page_path in enumerate(
            page_paths,
            start=1,
        ):
            classification = (
                classifications_by_page.get(
                    page_number,
                    {},
                )
            )

            page_type = classification.get(
                "page_type",
                "digital",
            )

            result = self.analyze_page(
                page_path=page_path,
                page_number=page_number,
                page_type=page_type,
            )

            routes.append(result)

        return routes

    def _is_table_candidate(
        self,
        text: str,
        drawing_count: int,
    ) -> bool:

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        short_lines = sum(
            1
            for line in lines
            if len(line) <= 20
        )

        short_line_ratio = (
            short_lines / len(lines)
            if lines
            else 0.0
        )

        return (
            drawing_count >= 20
            or (
                len(lines) >= 15
                and short_line_ratio >= 0.55
            )
        )