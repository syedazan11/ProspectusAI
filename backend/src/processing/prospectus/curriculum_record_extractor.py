import re
from dataclasses import asdict, dataclass

from bs4 import BeautifulSoup
from enum import Enum

class CurriculumScheme(str, Enum):
    UNKNOWN = "unknown"
    YEAR_TERM = "year_term"
    SEMESTER = "semester"

@dataclass(slots=True)
class CurriculumRecord:
    parent_section_code: str | None
    parent_section: str | None
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

    def __init__(self):
        self.curriculum_scheme = CurriculumScheme.UNKNOWN
        self.term_names: list[str] = []

    PARENT_SECTION_PATTERN = re.compile(
        r"^(\d+\.\d+)\s+(.+)$"
    )

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
        self.curriculum_scheme = CurriculumScheme.UNKNOWN
        self.term_names = []
        records: list[CurriculumRecord] = []

        current_parent_section_code: str | None = None
        current_parent_section: str | None = None
        current_programme_code: str | None = None
        current_programme: str | None = None
        current_study_year: str | None = None

        for page_index, page in enumerate(markdown_pages):
            markdown = page.get("markdown", "")
            self._detect_curriculum_scheme(markdown)

            if not markdown:
                continue

            source_page = first_source_page + page_index
            cursor = 0

            for table_match in self.TABLE_PATTERN.finditer(
                markdown
            ):
                preceding_text = markdown[
                    cursor:table_match.start()
                ]

                for (
                    identity_type,
                    identity_code,
                    identity_name,
                ) in self._find_identity_events(
                    preceding_text
                ):
                    if identity_type == "parent":
                        current_parent_section_code = (
                            identity_code
                        )
                        current_parent_section = (
                            identity_name
                        )
                        current_programme_code = None
                        current_programme = None
                        current_study_year = None
                    else:
                        current_programme_code = (
                            identity_code
                        )
                        current_programme = identity_name
                        current_study_year = None

                detected_year = self._find_study_year_text(
                    preceding_text
                )

                if detected_year:
                    current_study_year = detected_year

                if (
                    not current_programme_code
                    or not current_programme
                ):
                    if (
                        current_parent_section_code
                        and current_parent_section
                        and current_study_year
                    ):
                        current_programme_code = (
                            current_parent_section_code
                        )
                        current_programme = (
                            current_parent_section
                        )
                    else:
                        cursor = table_match.end()
                        continue

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
                            parent_section_code=(
                                current_parent_section_code
                            ),
                            parent_section=(
                                current_parent_section
                            ),
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
                            parent_section_code=(
                                current_parent_section_code
                            ),
                            parent_section=(
                                current_parent_section
                            ),
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
                                parent_section_code=(
                                    current_parent_section_code
                                ),
                                parent_section=(
                                    current_parent_section
                                ),
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

            trailing_text = markdown[cursor:]

            for (
                identity_type,
                identity_code,
                identity_name,
            ) in self._find_identity_events(
                trailing_text
            ):
                if identity_type == "parent":
                    current_parent_section_code = (
                        identity_code
                    )
                    current_parent_section = identity_name
                    current_programme_code = None
                    current_programme = None
                    current_study_year = None
                else:
                    current_programme_code = identity_code
                    current_programme = identity_name
                    current_study_year = None

        return self._deduplicate(records)

    def _append_semester_record(
        self,
        *,
        records: list[CurriculumRecord],
        parent_section_code: str | None,
        parent_section: str | None,
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
                parent_section_code=parent_section_code,
                parent_section=parent_section,
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

    def _find_identity_events(
        self,
        text: str,
    ) -> list[tuple[str, str, str]]:
        events: list[tuple[str, str, str]] = []

        for line in text.splitlines():
            cleaned = re.sub(
                r"^#{1,6}\s*",
                "",
                line.strip(),
            )

            programme_match = (
                self.PROGRAMME_PATTERN.match(cleaned)
            )

            if programme_match:
                events.append(
                    (
                        "programme",
                        self._clean(
                            programme_match.group(1)
                        ),
                        self._clean(
                            programme_match.group(2)
                        ),
                    )
                )
                continue

            parent_match = (
                self.PARENT_SECTION_PATTERN.match(
                    cleaned
                )
            )

            if parent_match:
                events.append(
                    (
                        "parent",
                        self._clean(
                            parent_match.group(1)
                        ),
                        self._clean(
                            parent_match.group(2)
                        ),
                    )
                )

        return events

    def _find_parent_section_identity(
        self,
        markdown: str,
    ) -> tuple[str, str] | None:
        for line in markdown.splitlines():
            text = re.sub(
                r"^#{1,6}\s*",
                "",
                line.strip(),
            )

            match = self.PARENT_SECTION_PATTERN.match(
                text
            )

            if match:
                return (
                    self._clean(match.group(1)),
                    self._clean(match.group(2)),
                )

        return None

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
    
    def _detect_curriculum_scheme(
        self,
        text: str,
    ) -> None:

        upper = text.upper()

        #
        # Direct semester numbering.
        #
        if re.search(
            r"\bSEMESTER\s*[1-9]\b",
            upper,
        ):
            self.curriculum_scheme = (
                CurriculumScheme.SEMESTER
            )
            return

        #
        # Year-term structure.
        #
        has_year = any(
            year in upper
            for year in self.STUDY_YEARS
        )

        terms = []

        if "FALL" in upper:
            terms.append("Fall")

        if "SPRING" in upper:
            terms.append("Spring")

        if "SUMMER" in upper:
            terms.append("Summer")

        if "WINTER" in upper:
            terms.append("Winter")

        if has_year and len(terms) >= 2:
            self.curriculum_scheme = (
                CurriculumScheme.YEAR_TERM
            )
            self.term_names = terms[:2]

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

    def get_curriculum_metadata(
        self,
    ) -> dict:
        """
        Returns detected curriculum metadata for
        the currently extracted document.
        """

        return {
            "curriculum_scheme": self.curriculum_scheme.value,
            "term_names": list(self.term_names),
        }

    @staticmethod
    def _deduplicate(
        records: list[CurriculumRecord],
    ) -> list[CurriculumRecord]:
        unique: list[CurriculumRecord] = []
        seen: set[tuple] = set()

        for record in records:
            key = (
                record.parent_section_code,
                record.parent_section,
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
