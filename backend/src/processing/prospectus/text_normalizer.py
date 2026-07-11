import re


class ProspectusTextNormalizer:
    """
    Normalizes OCR text without destroying
    document structure.
    """

    REPEATED_HEADER_LINES = {
        "NED UNIVERSITY",
        "UNIVERSITY OF ENGINEERING & TECHNOLOGY",
        "OF ENGINEERING & TECHNOLOGY",
        "UNDERGRADUATE",
        "KARACHI",
        "KARACH",
    }

    TABLE_SIGNALS = {
        "fall semester",
        "spring semester",
        "course",
        "course title",
        "credit hours",
        "theory",
        "practical",
    }

    def normalize_page(self, text: str) -> list[str]:
        lines = []

        for raw_line in text.splitlines():
            line = self._normalize_line(raw_line)

            if not line:
                continue

            if self._is_repeated_header(line):
                continue

            if self._is_noise_line(line):
                continue

            lines.append(line)

        return lines

    def is_heading(self, line: str) -> bool:
        text = line.strip()

        if not text:
            return False

        if self.is_table_signal(text):
            return False

        if len(text) > 120:
            return False

        words = text.split()

        if len(words) > 16:
            return False

        numbered_match = re.match(
            r"^(\d+(?:\.\d+)+)\.?\s+(.+)$",
            text,
        )

        if numbered_match:
            title = numbered_match.group(2).strip()
            return len(title) >= 3

        if re.fullmatch(
            r"CHAPTER(?:\s+\d+)?",
            text,
            flags=re.IGNORECASE,
        ):
            return True

        known_headings = {
            "FOREWORD",
            "VISION",
            "MISSION",
            "QUALITY POLICY",
            "QUALITY ASSURANCE",
            "ADMISSION POLICY",
            "ELIGIBILITY",
            "FEE AND CHARGES",
            "HISTORICAL BACKGROUND OF THE UNIVERSITY",
        }

        return text.upper() in known_headings

    def is_table_signal(self, line: str) -> bool:
        return (
            line.strip().lower()
            in self.TABLE_SIGNALS
        )

    def _is_repeated_header(
        self,
        line: str,
    ) -> bool:
        normalized = re.sub(
            r"\s+",
            " ",
            line,
        ).strip().upper()

        if normalized in self.REPEATED_HEADER_LINES:
            return True

        return bool(
            re.fullmatch(
                r"(?:UNDERGRADUATE\s+)?"
                r"PROSPECTUS\s+20\d{2}",
                normalized,
            )
        )

    @staticmethod
    def _is_noise_line(line: str) -> bool:
        normalized = line.strip().lower()

        if normalized in {
            "www.neduet.edu.pk",
            "+neduet official",
            "?+neduet official",
            "?+ neduet official",
        }:
            return True

        if "neduet official" in normalized:
            return True

        if normalized.startswith("?"):
            return True

        if normalized.isdigit():
            return True

        return False

    @staticmethod
    def _normalize_line(line: str) -> str:
        line = line.replace("\u00ad", "")
        line = line.replace("\u00a0", " ")

        return re.sub(
            r"[ \t]+",
            " ",
            line,
        ).strip()
