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
        curriculum_records: list[dict],
        programme_matches: list[dict] | None = None,
    ) -> dict | None:
        normalized = self._normalize(question)

        if not self._is_curriculum_question(
            normalized
        ):
            return None

        if programme_matches is None:
            programme_matches = self._match_programmes(
                normalized=normalized,
                curriculum_records=curriculum_records,
            )

        matched_study_year = self._match_study_year(
            normalized
        )

        common = {
            "study_year": matched_study_year,
            "semester": self._match_semester(
                normalized
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
                "programme_matches": programme_matches,
                **common,
            }

        if not programme_matches:
            return {
                "status": "programme_not_found",
                "programme_matches": [],
                **common,
            }

        if (
            len(programme_matches) > 1
            and common["course_code"] is not None
        ):
            programme_matches = (
                self._disambiguate_by_course_code(
                    programme_matches=programme_matches,
                    course_code=common["course_code"],
                    curriculum_records=curriculum_records,
                )
            )

        if len(programme_matches) > 1:
            return {
                "status": "programme_ambiguous",
                "programme_matches": (
                    programme_matches
                ),
                **common,
            }

        programme = programme_matches[0]

        return {
            "status": "matched",
            "programme_code": (
                programme["programme_code"]
            ),
            "programme": programme["programme"],
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

    def _match_programmes(
        self,
        *,
        normalized: str,
        curriculum_records: list[dict],
    ) -> list[dict]:
        unique = {}

        for record in curriculum_records:
            code = str(
                record.get("programme_code", "")
            ).strip()

            name = str(
                record.get("programme", "")
            ).strip()

            if not code or not name:
                continue

            unique[(code, name)] = {
                "programme_code": code,
                "programme": name,
            }

        matches = []

        for programme in unique.values():
            normalized_name = self._normalize(
                programme["programme"]
            )

            if normalized_name in normalized:
                matches.append(programme)

        if not matches:
            return []

        longest_name_length = max(
            len(
                self._normalize(
                    item["programme"]
                )
            )
            for item in matches
        )

        return [
            item
            for item in matches
            if len(
                self._normalize(
                    item["programme"]
                )
            ) == longest_name_length
        ]

    @staticmethod
    def _disambiguate_by_course_code(
        *,
        programme_matches: list[dict],
        course_code: str,
        curriculum_records: list[dict],
    ) -> list[dict]:
        candidate_codes = {
            item["programme_code"]
            for item in programme_matches
        }

        matching_codes = {
            str(
                record.get("programme_code", "")
            ).strip()
            for record in curriculum_records
            if (
                str(
                    record.get("programme_code", "")
                ).strip()
                in candidate_codes
                and str(
                    record.get("course_code", "")
                ).strip().casefold()
                == course_code.casefold()
            )
        }

        if len(matching_codes) != 1:
            return programme_matches

        return [
            item
            for item in programme_matches
            if item["programme_code"]
            in matching_codes
        ]

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
        has_fall = bool(
            re.search(
                r"\b(fall|autumn)\b",
                normalized,
            )
        )

        has_spring = bool(
            re.search(
                r"\bspring\b",
                normalized,
            )
        )

        if has_fall and not has_spring:
            return "Fall"

        if has_spring and not has_fall:
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
