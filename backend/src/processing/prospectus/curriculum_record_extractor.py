import re
from dataclasses import asdict, dataclass

from bs4 import BeautifulSoup


@dataclass(slots=True)
class CurriculumRecord:
    programme_code: str
    programme: str
    study_year: str
    semester: str
    course_code: str
    course_title: str
    theory_hours: str
    practical_hours: str
    total_credit_hours: str
    source_page: int

    def to_dict(self) -> dict:
        return asdict(self)


class CurriculumRecordExtractor:
    PROGRAMME_PATTERN = re.compile(
        r"^(\d+\.\d+\.\d+)\s+(.+)$"
    )

    STUDY_YEARS = (
        "FIRST YEAR",
        "SECOND YEAR",
        "THIRD YEAR",
        "FINAL YEAR",
    )

    TABLE_PATTERN = re.compile(
        r"<table\b.*?</table>",
        flags=re.IGNORECASE | re.DOTALL,
    )

    def extract(
        self,
        markdown_pages: list[dict],
        *,
        first_source_page: int = 38,
    ) -> list[CurriculumRecord]:
        records: list[CurriculumRecord] = []

        current_programme_code: str | None = None
        current_programme: str | None = None
        current_study_year: str | None = None

        for page_index, page in enumerate(markdown_pages):
            markdown = page.get("markdown", "")

            if not markdown:
                continue

            source_page = first_source_page + page_index

            detected_programme = (
                self._find_programme_identity(markdown)
            )

            if detected_programme:
                (
                    current_programme_code,
                    current_programme,
                ) = detected_programme

                current_study_year = None

            if (
                not current_programme_code
                or not current_programme
            ):
                continue

            cursor = 0

            for table_match in self.TABLE_PATTERN.finditer(
                markdown
            ):
                preceding_text = markdown[
                    cursor:table_match.start()
                ]

                detected_year = self._find_study_year_text(
                    preceding_text
                )

                if detected_year:
                    current_study_year = detected_year

                table = BeautifulSoup(
                    table_match.group(0),
                    "lxml",
                ).find("table")

                if table is None:
                    cursor = table_match.end()
                    continue

                table_year = self._find_study_year(table)

                if table_year:
                    current_study_year = table_year

                if not current_study_year:
                    cursor = table_match.end()
                    continue

                for row in table.find_all("tr"):
                    cells = [
                        cell.get_text(" ", strip=True)
                        for cell in row.find_all(
                            ["td", "th"]
                        )
                    ]

                    if len(cells) == 10:
                        self._append_semester_record(
                            records=records,
                            programme_code=(
                                current_programme_code
                            ),
                            programme=current_programme,
                            study_year=current_study_year,
                            semester="Fall",
                            cells=cells[:5],
                            source_page=source_page,
                        )

                        self._append_semester_record(
                            records=records,
                            programme_code=(
                                current_programme_code
                            ),
                            programme=current_programme,
                            study_year=current_study_year,
                            semester="Spring",
                            cells=cells[5:],
                            source_page=source_page,
                        )

                    elif len(cells) == 5:
                        semester = self._find_semester(table)

                        if semester:
                            self._append_semester_record(
                                records=records,
                                programme_code=(
                                    current_programme_code
                                ),
                                programme=current_programme,
                                study_year=current_study_year,
                                semester=semester,
                                cells=cells,
                                source_page=source_page,
                            )

                cursor = table_match.end()

        return self._deduplicate(records)

    def _append_semester_record(
        self,
        *,
        records: list[CurriculumRecord],
        programme_code: str,
        programme: str,
        study_year: str,
        semester: str,
        cells: list[str],
        source_page: int,
    ) -> None:
        code, title, theory, practical, total = cells

        code = self._clean(code)
        title = self._clean(title)

        if not code or not title:
            return

        if code.lower() == "course code":
            return

        if not self._looks_like_course_code(code):
            return

        records.append(
            CurriculumRecord(
                programme_code=programme_code,
                programme=programme,
                study_year=study_year,
                semester=semester,
                course_code=code,
                course_title=title,
                theory_hours=self._clean(theory),
                practical_hours=self._clean(practical),
                total_credit_hours=self._clean(total),
                source_page=source_page,
            )
        )

    def _find_programme_identity(
        self,
        markdown: str,
    ) -> tuple[str, str] | None:
        for line in markdown.splitlines():
            text = re.sub(
                r"^#{1,6}\s*",
                "",
                line.strip(),
            )

            match = self.PROGRAMME_PATTERN.match(text)

            if match:
                return (
                    self._clean(match.group(1)),
                    self._clean(match.group(2)),
                )

        return None

    def _find_programme(
        self,
        markdown: str,
    ) -> str | None:
        identity = self._find_programme_identity(
            markdown
        )

        if identity is None:
            return None

        return identity[1]

    def _find_study_year_text(
        self,
        text: str,
    ) -> str | None:
        upper_text = text.upper()

        found: list[tuple[int, str]] = []

        for study_year in self.STUDY_YEARS:
            position = upper_text.rfind(study_year)

            if position >= 0:
                found.append(
                    (position, study_year)
                )

        if not found:
            return None

        return max(found)[1]

    def _find_study_year(
        self,
        table,
    ) -> str | None:
        return self._find_study_year_text(
            table.get_text(" ", strip=True)
        )

    @staticmethod
    def _find_semester(table) -> str | None:
        text = table.get_text(
            " ",
            strip=True,
        ).lower()

        has_fall = "fall semester" in text
        has_spring = "spring semester" in text

        if has_fall and not has_spring:
            return "Fall"

        if has_spring and not has_fall:
            return "Spring"

        return None

    @staticmethod
    def _looks_like_course_code(
        code: str,
    ) -> bool:
        return bool(
            re.fullmatch(
                r"[A-Z]{2,5}"
                r"(?:/[A-Z]{2,5})?"
                r"[- ]"
                r"(?:\d{2,4}|#{3})"
                r"(?:\s*/\s*"
                r"[A-Z]{2,5}"
                r"[- ]?"
                r"(?:\d{2,4}|#{3}))?",
                code,
            )
        )

    @staticmethod
    def _clean(text: str) -> str:
        return re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

    @staticmethod
    def _deduplicate(
        records: list[CurriculumRecord],
    ) -> list[CurriculumRecord]:
        unique: list[CurriculumRecord] = []
        seen: set[tuple] = set()

        for record in records:
            key = (
                record.programme_code,
                record.programme,
                record.study_year,
                record.semester,
                record.course_code,
                record.course_title,
                record.theory_hours,
                record.practical_hours,
                record.total_credit_hours,
                record.source_page,
            )

            if key in seen:
                continue

            seen.add(key)
            unique.append(record)

        return unique
