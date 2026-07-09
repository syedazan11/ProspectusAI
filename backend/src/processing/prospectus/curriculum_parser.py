import re
from dataclasses import asdict, dataclass

from src.processing.prospectus.text_normalizer import (
    ProspectusTextNormalizer,
)


@dataclass(slots=True)
class CurriculumRecord:
    course_code: str
    course_title: str
    programme: str | None
    study_year: str | None
    page_number: int
    source_file: str

    def to_dict(self) -> dict:
        return asdict(self)


class CurriculumParser:
    COURSE_CODE_PATTERN = re.compile(
        r"^[A-Z]{2,5}(?:/[A-Z]{2,5})?"
        r"[- ](?:\d{2,4}|#{3})$"
    )

    STUDY_YEARS = {
        "FIRST YEAR",
        "SECOND YEAR",
        "THIRD YEAR",
        "FINAL YEAR",
    }

    SKIP_LINES = {
        "Fall Semester",
        "Spring Semester",
        "Course",
        "Credit Hours",
        "Code",
        "Course Title",
        "Th",
        "Pr",
        "Total",
        "NC",
    }

    def __init__(self) -> None:
        self.normalizer = ProspectusTextNormalizer()

    def parse_pages(
        self,
        pages: list[dict],
        source_file: str,
    ) -> list[CurriculumRecord]:
        records: list[CurriculumRecord] = []

        current_programme: str | None = None
        current_year: str | None = None

        for page in pages:
            page_number = page["page_number"]

            lines = self.normalizer.normalize_page(
                page["text"]
            )

            if not self._is_curriculum_page(lines):
                current_programme = None
                current_year = None
                continue

            index = 0

            while index < len(lines):
                line = lines[index]

                if line in self.STUDY_YEARS:
                    current_year = line
                    index += 1
                    continue

                if self._is_programme_heading(line):
                    current_programme = line
                    index += 1
                    continue

                code = self._normalize_code(line)

                if not self.COURSE_CODE_PATTERN.fullmatch(code):
                    index += 1
                    continue

                title_parts = []
                lookahead = index + 1

                while lookahead < len(lines):
                    candidate = lines[lookahead]
                    candidate_code = self._normalize_code(
                        candidate
                    )

                    if self.COURSE_CODE_PATTERN.fullmatch(
                        candidate_code
                    ):
                        break

                    if candidate in self.STUDY_YEARS:
                        break

                    if self._is_programme_heading(candidate):
                        break

                    if candidate in self.SKIP_LINES:
                        lookahead += 1
                        continue

                    if self._is_credit_value(candidate):
                        lookahead += 1
                        continue

                    title_parts.append(candidate)

                    if len(title_parts) >= 3:
                        break

                    lookahead += 1

                title = " ".join(title_parts).strip()

                if title:
                    records.append(
                        CurriculumRecord(
                            course_code=code,
                            course_title=title,
                            programme=current_programme,
                            study_year=current_year,
                            page_number=page_number,
                            source_file=source_file,
                        )
                    )

                index += 1

        return records

    def _is_curriculum_page(
        self,
        lines: list[str],
    ) -> bool:
        normalized_codes = [
            self._normalize_code(line)
            for line in lines
        ]

        course_code_count = sum(
            1
            for code in normalized_codes
            if self.COURSE_CODE_PATTERN.fullmatch(code)
        )

        structure_markers = {
            "Fall Semester",
            "Spring Semester",
            "Course Title",
            "Credit Hours",
        }

        marker_count = sum(
            1
            for marker in structure_markers
            if marker in lines
        )

        return (
            course_code_count >= 2
            or (
                course_code_count >= 1
                and marker_count >= 1
            )
        )

    @staticmethod
    def _normalize_code(text: str) -> str:
        text = text.strip().upper()

        return re.sub(
            r"^([A-Z]{2,5}(?:/[A-Z]{2,5})?) "
            r"(\d{2,4}|#{3})$",
            r"\1-\2",
            text,
        )

    @staticmethod
    def _is_credit_value(text: str) -> bool:
        return bool(
            re.fullmatch(
                r"(?:\d(?:/\d)?|NC)",
                text.strip(),
            )
        )

    @staticmethod
    def _is_programme_heading(text: str) -> bool:
        return bool(
            re.fullmatch(
                r"\d+\.\d+\.\d+",
                text,
            )
        ) is False and (
            text.endswith("Engineering")
            or text.endswith("Sciences")
            or text.endswith("Technology")
            or text.endswith("Architecture")
        )
