import re


class CurriculumSemesterMapper:
    YEAR_NAMES = (
        "FIRST YEAR",
        "SECOND YEAR",
        "THIRD YEAR",
        "FOURTH YEAR",
        "FINAL YEAR",
        "FIFTH YEAR",
        "SIXTH YEAR",
    )

    @classmethod
    def map_query(
        cls,
        query: str,
        *,
        curriculum_scheme: str | None,
        term_names: list[str],
    ) -> str:

        if curriculum_scheme != "year_term":
            return query

        match = re.search(
            r"\bsemester\s*(\d+)\b",
            query,
            flags=re.IGNORECASE,
        )

        if not match:
            return query

        semester_number = int(match.group(1))

        if semester_number <= 0:
            return query

        terms_per_year = len(term_names)

        if terms_per_year == 0:
            return query

        year_index = (
            semester_number - 1
        ) // terms_per_year

        if year_index >= len(cls.YEAR_NAMES):
            return query

        term = term_names[
            (semester_number - 1)
            % terms_per_year
        ]

        replacement = (
            f"{cls.YEAR_NAMES[year_index]} "
            f"{term}"
        )

        return re.sub(
            r"\bsemester\s*\d+\b",
            replacement,
            query,
            flags=re.IGNORECASE,
        )