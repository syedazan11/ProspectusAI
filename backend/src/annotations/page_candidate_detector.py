import re
from typing import Any


class PageCandidateDetector:

    def seat_distribution_candidates(
        self,
        pages: list[dict[str, Any]],
    ) -> tuple[int | None, int | None]:

        page_scores: list[dict[str, int]] = []

        for page in pages:

            score = 0

            score += self._heading_score(page)
            score += self._numeric_density_score(page)
            score += self._row_pattern_score(page)

            # Optional for now.
            score += self._table_score(page)

            page_number = page.get("page")

            if isinstance(page_number, int):
                page_scores.append(
                    {
                        "page": page_number,
                        "score": score,
                    }
                )

        if not page_scores:
            return None, None

        threshold = 12

        candidates = [
            item
            for item in page_scores
            if item["score"] >= threshold
        ]

        if not candidates:
            return None, None

        start_page = candidates[0]["page"]
        end_page = candidates[-1]["page"]

        return start_page, end_page
    
    def _page_text(
        self,
        page: dict[str, Any],
    ) -> str:

        text = (
            page.get("markdown")
            or page.get("text")
            or ""
        )

        return text.strip()
    
    def _heading_score(
        self,
        page: dict[str, Any],
    ) -> int:

        score = 0

        text = (
            self._page_text(page)
        )

        if not text:
            return score

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        if not lines:
            return score

        for line in lines[:8]:

            if len(line) > 100:
                continue

            words = line.split()

            if not words:
                continue

            # Short headings are more likely than paragraphs.
            if len(words) <= 8:
                score += 1

            # ALL CAPS headings.
            if line.isupper() and len(words) >= 2:
                score += 3

            # Title Case headings.
            title_words = sum(
                word[:1].isupper()
                for word in words
                if word
            )

            if (
                len(words) >= 2
                and title_words / len(words) >= 0.8
            ):
                score += 2

            # Numbered headings.
            if re.match(
                r"^\d+(\.\d+)*",
                line,
            ):
                score += 2

        return score
    
    def _numeric_density_score(
        self,
        page: dict[str, Any],
    ) -> int:

        text = self._page_text(page)

        if not text:
            return 0

        tokens = text.split()

        if not tokens:
            return 0

        numeric_tokens = 0

        for token in tokens:

            cleaned = token.strip(
                ",.:;()[]{}%"
            )

            if cleaned.isdigit():
                numeric_tokens += 1

        density = (
            numeric_tokens / len(tokens)
        )

        score = 0

        if density >= 0.30:
            score += 8

        elif density >= 0.20:
            score += 6

        elif density >= 0.10:
            score += 4

        elif density >= 0.05:
            score += 2

        return score
    
    def _row_pattern_score(
        self,
        page: dict[str, Any],
    ) -> int:

        text = self._page_text(page)

        if not text:
            return 0

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        short_lines = 0

        repeated_structure = 0

        for line in lines:

            words = line.split()

            if 2 <= len(words) <= 8:
                short_lines += 1

            if len(words) >= 3:

                digit_count = sum(
                    word.isdigit()
                    for word in words
                )

                if digit_count >= 2:
                    repeated_structure += 1

        score = 0

        if short_lines >= 10:
            score += 3

        elif short_lines >= 5:
            score += 2

        if repeated_structure >= 8:
            score += 5

        elif repeated_structure >= 4:
            score += 3

        return score
    


    def _table_score(
        self,
        page: dict[str, Any],
    ) -> int:

        score = 0

        tables = page.get("tables", [])

        if not isinstance(tables, list):
            return score

        if tables:
            score += 6

        for table in tables:

            rows = table.get("rows", [])
            columns = table.get("columns", [])

            if len(rows) >= 8:
                score += 4

            if len(columns) >= 3:
                score += 2

        return score