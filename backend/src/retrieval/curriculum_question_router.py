import re


class CurriculumQuestionRouter:
    """
    Detects curriculum questions and extracts
    structured filters from natural language.

    Programme identities come from the current
    document's validated curriculum records.
    """

    CURRICULUM_TERMS = (
        "curriculum",
        "course",
        "courses",
        "subject",
        "subjects",
        "semester",
        "credit hour",
        "credit hours",
        "theory hour",
        "theory hours",
        "practical hour",
        "practical hours",
    )

    YEAR_PATTERNS = (
        (
            "FIRST YEAR",
            (
                r"\bfirst[\s-]*year\b",
                r"\b1st[\s-]*year\b",
            ),
        ),
        (
            "SECOND YEAR",
            (
                r"\bsecond[\s-]*year\b",
                r"\b2nd[\s-]*year\b",
            ),
        ),
        (
            "THIRD YEAR",
            (
                r"\bthird[\s-]*year\b",
                r"\b3rd[\s-]*year\b",
            ),
        ),
        (
            "FINAL YEAR",
            (
                r"\bfinal[\s-]*year\b",
                r"\bfourth[\s-]*year\b",
                r"\b4th[\s-]*year\b",
            ),
        ),
    )

    COURSE_CODE_PATTERN = re.compile(
        r"\b[A-Z]{2,5}"
        r"(?:/[A-Z]{2,5})?"
        r"[- ]"
        r"(?:\d{2,4}|#{3})"
        r"\b",
        flags=re.IGNORECASE,
    )

    def route(
        self,
        *,
        question: str,
        curriculum_scheme: str | None = None,
        term_names: list[str] | None = None,
    ) -> dict | None:
        normalized = self._normalize(question)
        if term_names is None:
            term_names = []

        mapped_year = None
        mapped_term = None

        if curriculum_scheme == "year_term":
            mapped_year, mapped_term = (
                self._map_semester_number(
                    normalized,
                    curriculum_scheme=curriculum_scheme,
                    term_names=term_names,
                )
            )

        if not self._is_curriculum_question(
            normalized
        ):
            return None

        matched_study_year = (
            self._match_study_year(normalized)
            or mapped_year
        )

        common = {
           "study_year": (
               matched_study_year
               or mapped_year
           ),
           "semester": (
               self._match_semester(normalized)
               or mapped_term
           ),
            "course_code": self._match_course_code(
                question
            ),
        }

        if (
            matched_study_year is None
            and self._has_explicit_unsupported_year(
                normalized
            )
        ):
            return {
                "status": "unsupported_study_year",
                **common,
            }

        return {
            "status": "curriculum",
            **common,
        }


    def _is_curriculum_question(
        self,
        normalized: str,
    ) -> bool:
        return any(
            term in normalized
            for term in self.CURRICULUM_TERMS
        )

    def _match_study_year(
        self,
        normalized: str,
    ) -> str | None:
        for study_year, patterns in self.YEAR_PATTERNS:
            if any(
                re.search(pattern, normalized)
                for pattern in patterns
            ):
                return study_year

        return None
    
    @staticmethod
    def _map_semester_number(
        normalized: str,
        *,
        curriculum_scheme: str | None,
        term_names: list[str],
    ) -> tuple[str | None, str | None]:

        if curriculum_scheme != "year_term":
            return None, None

        semester_number = None

        # Numeric forms:
        # semester 1, semester 2, ...
        match = re.search(
            r"\bsemester\s*(\d+)\b",
            normalized,
        )

        if match is None:
            match = re.search(
                r"\b(\d+)(?:st|nd|rd|th)?\s*semester\b",
                normalized,
            )

        if match:
            semester_number = int(match.group(1))
        else:
            # Ordinal word forms:
            # first semester, second semester, ...
            ordinal_map = {
                "first": 1,
                "second": 2,
                "third": 3,
                "fourth": 4,
                "fifth": 5,
                "sixth": 6,
                "seventh": 7,
                "eighth": 8,
                "ninth": 9,
                "tenth": 10,
            }

            for word, number in ordinal_map.items():
                if re.search(
                    rf"\b{word}[\s-]*semester\b",
                    normalized,
                ):
                    semester_number = number
                    break

        if semester_number is None or semester_number <= 0:
            return None, None

        if semester_number <= 0:
            return None, None

        year_names = (
            "FIRST YEAR",
            "SECOND YEAR",
            "THIRD YEAR",
            "FINAL YEAR",
            "FIFTH YEAR",
            "SIXTH YEAR",
        )

        terms = [
            term.strip()
            for term in term_names
            if term.strip()
        ]

        if len(terms) < 2:
            return None, None

        year_index = (
            semester_number - 1
        ) // len(terms)

        term = terms[
            (semester_number - 1)
            % len(terms)
        ]

        return (
            year_names[year_index],
            term,
        )

    @staticmethod
    def _has_explicit_unsupported_year(
        normalized: str,
    ) -> bool:
        word_years = (
            "fifth",
            "sixth",
            "seventh",
            "eighth",
            "ninth",
            "tenth",
        )

        if any(
            re.search(
                rf"\b{word}[\s-]*year\b",
                normalized,
            )
            for word in word_years
        ):
            return True

        numeric_match = re.search(
            r"\b(\d+)(?:st|nd|rd|th)[\s-]*year\b",
            normalized,
        )

        if numeric_match is None:
            return False

        return int(numeric_match.group(1)) > 4

    @staticmethod
    def _match_semester(
        normalized: str,
    ) -> str | None:
        # -------- Fall / Semester I --------
        if re.search(
            r"\b("
            r"fall|autumn|"
            r"first[\s-]*semester|"
            r"1st[\s-]*semester|"
            r"semester[\s-]*1|"
            r"semester[\s-]*i"
            r")\b",
            normalized,
        ):
            return "Fall"

        # -------- Spring / Semester II --------
        if re.search(
            r"\b("
            r"spring|"
            r"second[\s-]*semester|"
            r"2nd[\s-]*semester|"
            r"semester[\s-]*2|"
            r"semester[\s-]*ii"
            r")\b",
            normalized,
        ):
            return "Spring"

        return None

    def _match_course_code(
        self,
        question: str,
    ) -> str | None:
        match = self.COURSE_CODE_PATTERN.search(
            question
        )

        if match is None:
            return None

        return re.sub(
            r"\s+",
            " ",
            match.group(0).upper(),
        ).strip()

    @staticmethod
    def _normalize(
        text: str,
    ) -> str:
        return re.sub(
            r"\s+",
            " ",
            text.casefold(),
        ).strip()
