from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class ProspectusSection:
    section_type: str
    start_page: int
    end_page: int
    heading: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ProspectusSectionDetector:
    CHAPTER_PATTERN = re.compile(
        r"(?:^|\n)\s*(?:"
        r"(?P<number_a>\d+)\s+CHAPTER|"
        r"CHAPTER\s+(?P<number_b>\d+)"
        r")\b",
        re.IGNORECASE,
    )

    REGULAR_SCHEME_PATTERN = re.compile(
        r"\bREGULAR\s+SCHEME\b",
        re.IGNORECASE,
    )

    SELF_FINANCE_SCHEME_PATTERN = re.compile(
        r"\bSELF[\s-]+FINANCE\s+SCHEME\b",
        re.IGNORECASE,
    )

    DESCRIPTION_PATTERN = re.compile(
        r"\bDescription\s+of\s+Categories\b",
        re.IGNORECASE,
    )

    COURSE_OF_STUDIES_PATTERN = re.compile(
        r"\bCourse\s+of\s+Studies\b",
        re.IGNORECASE,
    )

    # DOMAIN_SECTION_PATTERNS = {
    #     "faculty_roles": re.compile(
    #         r"\bTeaching\s+Departments\b",
    #         re.IGNORECASE,
    #     ),
    #     "eligibility": re.compile(
    #         r"\bEligibility\b",
    #         # r"\bEligibility\s+Conditions\b",
    #         re.IGNORECASE,
    #     ),
    #     "admission_process": re.compile(
    #         r"\bMode\s+of\s+Admission\b",
    #         re.IGNORECASE,
    #     ),
    #     "fee_structure": re.compile(
    #         r"\bFee\s+Structure\b",
    #         re.IGNORECASE,
    #     ),
    # }

    # CHAPTER_SECTION_PATTERNS = {
    #     "academic_programmes": re.compile(
    #         r"\bAcademic\s+Program",
    #         re.IGNORECASE,
    #     ),
    #     "course_of_studies": re.compile(
    #         r"\bCourse\s+of\s+Studies\b",
    #         re.IGNORECASE,
    #     ),
    #     "mode_of_application": re.compile(
    #         r"\bMode\s+of\s+Application\b",
    #         re.IGNORECASE,
    #     ),
    #     "admission_categories": re.compile(
    #         r"\bAdmission\s+Categor",
    #         re.IGNORECASE,
    #     ),
    #     "mode_of_admission": re.compile(
    #         r"\bMode\s+of\s+Admission\b",
    #        re.IGNORECASE,
    #     ),
    #     "examinations": re.compile(
    #         r"\bExamination",
    #         re.IGNORECASE,
    #     ),
    #     "fee_structure": re.compile(
    #         r"\bFee\s+Structure\b",
    #         re.IGNORECASE,
    #     ),
    #     "scholarships": re.compile(
    #         r"\bScholarship|\bStipend|\bAward",
    #         re.IGNORECASE,
    #     ),
    #     "student_support": re.compile(
    #         r"\bInfrastructure\b|\bStudent(?:s)?\s+Facilit",
    #         re.IGNORECASE,
    #     ),
    #     "student_activities": re.compile(
    #         r"\bStudent(?:'s|s')?\s+Activit",
    #         re.IGNORECASE,
    #     ),
    #     "discipline": re.compile(
    #         r"\bDiscipline\b|\bRules?\b",
    #         re.IGNORECASE,
    #     ),
    # }

    CHAPTER_SECTION_PATTERNS = {
        "academics": [
            r"\bacademic\s+program",
            r"\bacademic\s+programme",
            r"\bacademic\s+programmes",
            r"\bfacult(?:y|ies)\b",
        ],
        "application": [
            r"\bapplication\b",
            r"\bapply\b",
            r"\badmission\s+application\b",
            r"\bapplication\s+procedure\b",
        ],
        "admissions": [
            r"\bmode\s+of\s+admission\b",
            r"\badmission\s+process\b",
            r"\bhow\s+admission\s+works\b",
        ],
        "assessment": [
            r"\bexamination",
            r"\bassessment\b",
            r"\bgrading\b",
            r"\bevaluation\b",
        ],
        "finance": [
            r"\bfee\b",
            r"\btuition\b",
            r"\bcharges?\b",
            r"\bexpenses?\b",
        ],
        "scholarships": [
            r"\bscholarship",
            r"\bstipend",
            r"\bfinancial\s+assistance\b",
            r"\baward",
        ],
        "student_support": [
            r"\bstudent\s+facilit",
            r"\bstudent\s+services?\b",
            r"\binfrastructure\b",
            r"\blibrary\b",
            r"\bhostel\b",
        ],
        "student_life": [
            r"\bstudent(?:'s|s')?\s+activit",
            r"\bstudent\s+activit",
            r"\bsociet",
            r"\bclubs?\b",
            r"\bsports?\b",
        ],
            "policies": [
            r"\bdiscipline\b",
            r"\brules?\b",
            r"\bregulations?\b",
            r"\bcode\s+of\s+conduct\b",
        ],
    }

    SUBSECTION_PATTERNS = {
        "faculty_roles": re.compile(
            r"\bTeaching\s+Departments\b",
            re.IGNORECASE,
        ),
        "eligibility": re.compile(
            r"\bEligibility\b",
            re.IGNORECASE,
        ),
    }

    CATEGORY_DESCRIPTION_PATTERN = re.compile(
        r"\bDescription\s+of\s+Categories\b",
        re.IGNORECASE,
    )

    REGULAR_CATEGORY_CODE_PATTERN = re.compile(
        r"\bR[-=]?\s*\d+(?:\s*\([a-z]\))?\b",
        re.IGNORECASE,
    )

    SELF_FINANCE_CATEGORY_CODE_PATTERN = re.compile(
        r"\bSF[-=]?\s*\d+(?:\s*\([a-z]\))?\b",
        re.IGNORECASE,
    )


    def detect(
        self,
        pages: list[dict[str, Any]],
    ) -> list[ProspectusSection]:
        ordered_pages = sorted(
            pages,
            key=lambda page: page["page_number"],
        )

        sections: list[ProspectusSection] = []

        curriculum = self._detect_curriculum(
            ordered_pages
        )
        if curriculum:
            sections.append(curriculum)

        regular = self._detect_seat_section(
            pages=ordered_pages,
            section_type="seat_distribution_regular",
            category_section_type=(
                "regular_category_descriptions"
            ),
        )
        if regular:
            sections.append(regular)

        self_finance = self._detect_seat_section(
            pages=ordered_pages,
            section_type="seat_distribution_self_finance",
            category_section_type=(
                "self_finance_category_descriptions"
            ),
        )
        if self_finance:
            sections.append(self_finance)

        sections.extend(
            self._detect_domain_sections(
                ordered_pages
            )
        )

        sections.extend(
            self._detect_category_description_sections(
                ordered_pages
            )
        )


        return sorted(
            sections,
            key=lambda section: (
                section.start_page,
                section.end_page,
                section.section_type,
            ),
        )

    def _detect_curriculum(
        self,
        pages: list[dict[str, Any]],
    ) -> ProspectusSection | None:
        start_index = None
        chapter_number = None

        for index, page in enumerate(pages):
            text = self._page_text(page)

            if not self.COURSE_OF_STUDIES_PATTERN.search(text):
                continue

            chapter_number = self._chapter_number(text)
            start_index = index
            break

        if start_index is None:
            return None

        end_index = len(pages) - 1

        for index in range(start_index + 1, len(pages)):
            next_chapter = self._chapter_number(
                self._page_text(pages[index])
            )

            if (
                next_chapter is not None
                and next_chapter != chapter_number
            ):
                end_index = index - 1
                break

        return ProspectusSection(
            section_type="curriculum",
            start_page=pages[start_index]["page_number"],
            end_page=pages[end_index]["page_number"],
            heading="Course of Studies",
            metadata={
                "discovery_method": (
                    "course_of_studies_to_next_chapter"
                ),
                "chapter_number": chapter_number,
            },
        )

    def _detect_seat_section(
        self,
        pages: list[dict[str, Any]],
        section_type: str,
        category_section_type: str,
    ) -> ProspectusSection | None:
        category_sections = (
            self._detect_category_description_sections(
                pages
            )
        )

        boundary_section = next(
            (
                section
                for section in category_sections
                if section.section_type
                == category_section_type
            ),
            None,
        )

        if boundary_section is None:
            return None

        page_index = {
            page["page_number"]: index
            for index, page in enumerate(pages)
        }

        boundary_index = page_index.get(
            boundary_section.start_page
        )

        if (
            boundary_index is None
            or boundary_index <= 0
        ):
            return None

        end_index = boundary_index - 1

        # print("\n=== REGULAR SEAT DEBUG ===")

        # for i in range(max(0, end_index - 4), end_index + 1):
        #     page = pages[i]
        #     print(
        #         f"Page {page['page_number']}: "
        #         f"{self._is_dense_seat_table_page(page)}"
        #     )

        if not self._is_dense_seat_table_page(
            pages[end_index]
        ):
            return None

        start_index = end_index

        while start_index > 0:
            previous_index = start_index - 1

            if not self._is_dense_seat_table_page(
                pages[previous_index]
            ):
                break

            start_index = previous_index

        return ProspectusSection(
            section_type=section_type,
            start_page=pages[start_index]["page_number"],
            end_page=pages[end_index]["page_number"],
            heading="Distribution of Seats",
            metadata={
                "discovery_method": (
                    "dense_table_block_before_exact_"
                    "category_description"
                ),
                "boundary_section_type": category_section_type,
                "boundary_section_number": (
                    boundary_section.metadata.get(
                        "section_number"
                    )
                ),
            },
        )

    def _is_dense_seat_table_page(
        self,
        page: dict[str, Any],
    ) -> bool:
        text = self._page_text(page)

        if not text:
            return False

        if self.CATEGORY_DESCRIPTION_PATTERN.search(text):
            return False

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        # if len(lines) < 40:
        #     return False

        if len(lines) < 10:
            return False

        numeric_lines = sum(
            1
            for line in lines
            if re.fullmatch(
                r"[\d\s.,()%/+*-]+",
                line,
            )
        )

        short_lines = sum(
            1
            for line in lines
            if len(line) <= 16
        )

        code_like_lines = sum(
            1
            for line in lines
            if re.fullmatch(
                r"[A-Z]{1,6}"
                r"(?:[-/][A-Z0-9()]{1,10})?",
                line,
            )
        )

        numeric_ratio = numeric_lines / len(lines)
        short_ratio = short_lines / len(lines)

        # print(
        #     f"Page {page['page_number']}: "
        #     f"lines={len(lines)} "
        #     f"numeric={numeric_lines} "
        #     f"short={short_lines} "
        #     f"codes={code_like_lines} "
        #     f"numeric_ratio={numeric_ratio:.2f} "
        #     f"short_ratio={short_ratio:.2f}"
        # )

        score = 0

        if numeric_ratio >= 0.10:
            score += 2

        if short_ratio >= 0.25:
            score += 2

        if code_like_lines >= 4:
            score += 2

        if numeric_lines >= 15:
            score += 1

        if short_lines >= 20:
            score += 1

        drawing_count = (
            page.get("metadata", {})
                .get("cheap_route", {})
                .get("drawing_count", 0)
        )

        if drawing_count >= 2000:
            score += 2
        
        # print(
        #     f"drawing={drawing_count} score={score}"
        # )

        has_strong_structure = (
            drawing_count >= 2000
            or code_like_lines >= 4
            or numeric_lines >= 15
        )

        return score >= 4 and has_strong_structure

    def _detect_chapter_covers(
        self,
        pages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        covers = []

        for index, page in enumerate(pages):
            text = self._page_text(page)

            if self._looks_like_table_of_contents(text):
                continue

            lines = [
                line.strip()
                for line in text.splitlines()
                if line.strip()
            ]

            chapter_positions = [
                position
                for position, line in enumerate(lines)
                if re.fullmatch(
                    r"CHAPTER",
                    line,
                    re.IGNORECASE,
                )
            ]

            if not chapter_positions:
                continue

            # Real cover pages are short and contain a standalone
            # chapter marker. Ordinary content pages mentioning
            # "Chapter" are rejected.
            if len(lines) > 30:
                continue

            position = chapter_positions[0]

            nearby = lines[
                max(0, position - 3):
                min(len(lines), position + 8)
            ]

            raw_number = None

            for line in nearby:
                if re.fullmatch(r"\d{1,2}", line):
                    value = int(line)

                    if 1 <= value <= 30:
                        raw_number = value
                        break

            title_lines = []

            for line in lines[position + 1:]:
                if re.fullmatch(r"\d{1,3}", line):
                    continue

                if re.search(
                    r"(?:neduet|prospectus|university|"
                    r"engineering|technology|www\.)",
                    line,
                    re.IGNORECASE,
                ):
                    continue

                title_lines.append(line)

            title = " ".join(title_lines).strip()

            covers.append(
                {
                    "index": index,
                    "page_number": page["page_number"],
                    "raw_number": raw_number,
                    "chapter_number": raw_number,
                    "title": title,
                }
            )

        # Repair isolated OCR number errors only when both
        # neighbouring covers establish the missing sequence.
        for position in range(1, len(covers) - 1):
            previous = covers[position - 1][
                "chapter_number"
            ]
            current = covers[position][
                "chapter_number"
            ]
            following = covers[position + 1][
                "chapter_number"
            ]

            if (
                previous is not None
                and following is not None
                and following == previous + 2
                and current != previous + 1
            ):
                covers[position][
                    "chapter_number"
                ] = previous + 1

                covers[position][
                    "number_repaired"
                ] = True

        return covers

    def _chapter_ranges(
        self,
        pages: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        covers = self._detect_chapter_covers(pages)
        ranges = []

        for position, cover in enumerate(covers):
            if position + 1 < len(covers):
                end_index = (
                    covers[position + 1]["index"] - 1
                )
            else:
                end_index = len(pages) - 1

            ranges.append(
                {
                    **cover,
                    "start_page": cover["page_number"],
                    "end_page": pages[end_index][
                        "page_number"
                    ],
                }
            )

        return ranges

    def _detect_domain_sections(
        self,
        pages: list[dict[str, Any]],
    ) -> list[ProspectusSection]:
        sections: list[ProspectusSection] = []

        # chapter_level_domains = {
        #     "admission_process",
        #     "fee_structure",
        # }

        for section_type, patterns in self.CHAPTER_SECTION_PATTERNS.items():
            section = self._chapter_section_from_title(
                pages=pages,
                section_type=section_type,
                patterns=patterns,
            )

            if section:
                sections.append(section)

        for section_type, pattern in self.SUBSECTION_PATTERNS.items():
            section = self._detect_heading_to_next_chapter(
                pages=pages,
                section_type=section_type,
                pattern=pattern,
            )

            if section:
                sections.append(section)

            # if section_type in chapter_level_domains:
            #     section = self._chapter_section_from_title(
            #         pages=pages,
            #         section_type=section_type,
            #         pattern=pattern,
            #     )
            # else:
            #     section = self._detect_heading_to_next_chapter(
            #         pages=pages,
            #         section_type=section_type,
            #         pattern=pattern,
            #     )

            # if section:
            #     sections.append(section)

        # for section in sections:
        #     print(
        #         section.section_type,
        #         section.start_page,
        #         section.end_page,
        #     )

        return sections

    def _find_chapter_by_title(
        self,
        pages: list[dict[str, Any]],
        patterns: list[str],
    ) -> dict[str, Any] | None:

        compiled = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in patterns
        ]

        matches = []

        for chapter in self._chapter_ranges(pages):
            title = chapter.get("title", "")

            if any(p.search(title) for p in compiled):
                matches.append(chapter)
        # matches = []

        # for chapter in self._chapter_ranges(pages):
        #     title = chapter.get("title", "")

        #     if pattern.search(title):
        #         matches.append(chapter)

        if len(matches) != 1:
            return None

        # for chapter in self._chapter_ranges(pages):
        #     print(chapter["title"])

        return matches[0]

    def _chapter_section_from_title(
        self,
        pages: list[dict[str, Any]],
        section_type: str,
        patterns: list[str],
    ) -> ProspectusSection | None:
        chapter = self._find_chapter_by_title(
            pages=pages,
            patterns=patterns,
        )

        if chapter is None:
            return None

        return ProspectusSection(
            section_type=section_type,
            start_page=chapter["start_page"],
            end_page=chapter["end_page"],
            heading=chapter["title"],
            metadata={
                "discovery_method": (
                    "detected_chapter_title_and_boundaries"
                ),
                "chapter_number": chapter[
                    "chapter_number"
                ],
                "raw_chapter_number": chapter[
                    "raw_number"
                ],
                "chapter_number_repaired": chapter.get(
                    "number_repaired",
                    False,
                ),
            },
        )

    # def _find_chapter_by_title(
    #     self,
    #     pages: list[dict[str, Any]],
    #     pattern: re.Pattern[str],
    # ) -> dict[str, Any] | None:
    #     matches = []

    #     for chapter in self._chapter_ranges(pages):
    #         title = chapter.get("title", "")

    #         if pattern.search(title):
    #             matches.append(chapter)

    #     if len(matches) != 1:
    #         return None

    #     return matches[0]

    # def _chapter_section_from_title(
    #     self,
    #     pages: list[dict[str, Any]],
    #     section_type: str,
    #     pattern: re.Pattern[str],
    # ) -> ProspectusSection | None:
    #     chapter = self._find_chapter_by_title(
    #         pages=pages,
    #         pattern=pattern,
    #     )

    #     if chapter is None:
    #         return None

    #     return ProspectusSection(
    #         section_type=section_type,
    #         start_page=chapter["start_page"],
    #         end_page=chapter["end_page"],
    #         heading=chapter["title"],
    #         metadata={
    #             "discovery_method": (
    #                 "detected_chapter_title_and_boundaries"
    #             ),
    #             "chapter_number": chapter[
    #                 "chapter_number"
    #             ],
    #             "raw_chapter_number": chapter[
    #                 "raw_number"
    #             ],
    #             "chapter_number_repaired": chapter.get(
    #                 "number_repaired",
    #                 False,
    #             ),
    #         },
    #     )

    def _detect_heading_to_next_chapter(
        self,
        pages: list[dict[str, Any]],
        section_type: str,
        pattern: re.Pattern[str],
    ) -> ProspectusSection | None:
        candidates = []

        for index, page in enumerate(pages):
            text = self._page_text(page)

            if not pattern.search(text):
                continue

            score = self._heading_candidate_score(
                text=text,
                pattern=pattern,
            )

            candidates.append((score, index))

        if not candidates:
            return None

        candidates.sort(reverse=True)
        best_score, start_index = candidates[0]

        if best_score <= 0:
            return None

        start_text = self._page_text(
            pages[start_index]
        )

        section_number = self._numbered_heading_for_pattern(
            text=start_text,
            pattern=pattern,
        )

        end_index = self._subsection_end_index(
            pages=pages,
            start_index=start_index,
            section_number=section_number,
        )

        match = pattern.search(start_text)

        return ProspectusSection(
            section_type=section_type,
            start_page=pages[start_index]["page_number"],
            end_page=pages[end_index]["page_number"],
            heading=(
                match.group(0)
                if match
                else section_type
            ),
            metadata={
                "discovery_method": (
                    "exact_numbered_subsection_boundary"
                ),
                "section_number": section_number,
                "candidate_score": best_score,
            },
        )

    # def _numbered_heading_for_pattern(
    #     self,
    #     text: str,
    #     pattern: re.Pattern[str],
    # ) -> str | None:
    #     lines = [
    #         line.strip()
    #         for line in text.splitlines()
    #         if line.strip()
    #     ]

    #     for index, line in enumerate(lines):
    #         if not pattern.search(line):
    #             continue

    #         for previous in reversed(
    #             lines[max(0, index - 3):index]
    #         ):
    #             if re.fullmatch(
    #                 r"\d+(?:\.\d+)+",
    #                 previous,
    #             ):
    #                 return previous

    #     return None

    def _numbered_heading_for_pattern(
        self,
        text: str,
        pattern: re.Pattern[str],
    ) -> str | None:

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        number_pattern = re.compile(
            r"^(\d+(?:\.\d+)+)"
        )

        for index, line in enumerate(lines):

            if not pattern.search(line):
                continue

            # Case 1:
            # 4.2 ELIGIBILITY
            match = number_pattern.match(line)

            if match:
                return match.group(1)

            # Case 2:
            # 4.2
            # ELIGIBILITY
            for previous in reversed(
                lines[max(0, index - 3):index]
            ):

                match = number_pattern.match(
                    previous
                )

                if match:
                    return match.group(1)

        return None

    def _subsection_end_index(
        self,
        pages: list[dict[str, Any]],
        start_index: int,
        section_number: str | None,
    ) -> int:
        if section_number is None:
            return start_index

        parts = section_number.split(".")

        if len(parts) < 2:
            return start_index

        parent = ".".join(parts[:-1])

        sibling_pattern = re.compile(
            rf"(?m)^\s*{re.escape(parent)}\.(\d+)\s*$"
        )

        chapter_ranges = self._chapter_ranges(pages)

        containing_chapter = next(
            (
                chapter
                for chapter in chapter_ranges
                if (
                    chapter["start_page"]
                    <= pages[start_index]["page_number"]
                    <= chapter["end_page"]
                )
            ),
            None,
        )

        chapter_end_index = len(pages) - 1

        if containing_chapter is not None:
            for index, page in enumerate(pages):
                if (
                    page["page_number"]
                    == containing_chapter["end_page"]
                ):
                    chapter_end_index = index
                    break

        current_leaf = int(parts[-1])

        for index in range(
            start_index + 1,
            chapter_end_index + 1,
        ):
            text = self._page_text(pages[index])

            sibling_numbers = [
                int(match.group(1))
                for match in sibling_pattern.finditer(text)
            ]

            if any(
                number > current_leaf
                for number in sibling_numbers
            ):
                return index - 1

        return chapter_end_index

    def _heading_candidate_score(
        self,
        text: str,
        pattern: re.Pattern[str],
    ) -> int:
        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        score = 0

        for index, line in enumerate(lines):
            if not pattern.search(line):
                continue

            if len(line) <= 100:
                score += 4

            if pattern.fullmatch(line):
                score += 6

            nearby = "\n".join(
                lines[
                    max(0, index - 3):
                    min(len(lines), index + 8)
                ]
            )

            if re.search(
                r"\bCHAPTER\b",
                nearby,
                re.IGNORECASE,
            ):
                score += 5

            if re.search(
                r"^\d+(?:\.\d+)*\s*$",
                nearby,
                re.MULTILINE,
            ):
                score += 3

            following = lines[
                index + 1:
                min(len(lines), index + 12)
            ]

            if any(
                len(item) > 80
                for item in following
            ):
                score += 2

        if self._looks_like_table_of_contents(text):
            score -= 30

        return score

    @staticmethod
    def _looks_like_table_of_contents(
        text: str,
    ) -> bool:
        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        numeric_lines = sum(
            1
            for line in lines
            if re.fullmatch(
                r"\d{1,3}",
                line,
            )
        )

        numbered_headings = sum(
            1
            for line in lines
            if re.match(
                r"^\d+(?:\.\d+){0,3}\.?\s*$",
                line,
            )
        )

        return (
            numeric_lines >= 8
            and numbered_headings >= 5
        )

    def _resolve_chapter_from_toc(
        self,
        pages: list[dict[str, Any]],
        pattern: re.Pattern[str],
    ) -> int | None:
        chapter_number = None

        for page in pages:
            text = self._page_text(page)

            if not self._looks_like_table_of_contents(
                text
            ):
                continue

            lines = [
                line.strip()
                for line in text.splitlines()
                if line.strip()
            ]

            for index, line in enumerate(lines):
                if not pattern.search(line):
                    continue

                for previous in reversed(
                    lines[max(0, index - 4):index]
                ):
                    match = re.fullmatch(
                        r"(\d+)\.?",
                        previous,
                    )

                    if match:
                        chapter_number = int(
                            match.group(1)
                        )
                        break

                if chapter_number is not None:
                    break

            if chapter_number is not None:
                break

        if chapter_number is None:
            return None

        for index, page in enumerate(pages):
            text = self._page_text(page)

            if self._looks_like_table_of_contents(
                text
            ):
                continue

            if re.search(
                rf"(?im)^\s*{chapter_number}\s*$",
                text,
            ) and re.search(
                r"(?im)^\s*CHAPTER\s*$",
                text,
            ):
                return index

        return None

    def _nearest_chapter_number(
        self,
        pages: list[dict[str, Any]],
        start_index: int,
    ) -> int | None:
        for index in range(
            start_index,
            max(-1, start_index - 4),
            -1,
        ):
            chapter = self._chapter_number(
                self._page_text(pages[index])
            )

            if chapter is not None:
                return chapter

        return None

    def _section_end_index(
        self,
        pages: list[dict[str, Any]],
        start_index: int,
        chapter_number: int | None,
    ) -> int:
        for index in range(
            start_index + 1,
            len(pages),
        ):
            text = self._page_text(pages[index])

            next_chapter = self._chapter_number(text)

            if (
                chapter_number is not None
                and next_chapter is not None
                and next_chapter != chapter_number
            ):
                return index - 1

            if (
                chapter_number is not None
                and re.search(
                    r"(?im)^\s*CHAPTER\s*$",
                    text,
                )
                and re.search(
                    rf"(?im)^\s*(?!{chapter_number}\s*$)"
                    r"\d+\s*$",
                    text,
                )
            ):
                return index - 1

        return len(pages) - 1

    def _detect_category_description_sections(
        self,
        pages: list[dict[str, Any]],
    ) -> list[ProspectusSection]:
        candidates: list[dict[str, Any]] = []

        for index, page in enumerate(pages):
            # print(f"\nPAGE {page['page_number']}")
            # text = self._page_text(page)
            # print(text[:300])
            text = self._page_text(page)

            matched = self.CATEGORY_DESCRIPTION_PATTERN.search(text)

            # print(f"Pattern matched: {bool(matched)}")

            if not matched:
                continue

            # if not self.CATEGORY_DESCRIPTION_PATTERN.search(
            #     text
            # ):
            #     continue

            subsection_number = (
                self._category_subsection_number_for_pattern(
                    text=text,
                    pattern=self.CATEGORY_DESCRIPTION_PATTERN,
                )
            )
            # print(
            #     f"Page {page['page_number']} "
            #     f"subsection={subsection_number}"
            # )


            if subsection_number is None:
                continue

            # Classify from the actual description subsection,
            # not from a multi-page look-ahead window.
            has_regular = bool(
                self.REGULAR_CATEGORY_CODE_PATTERN.search(
                    text
                )
            )
            has_self_finance = bool(
                self.SELF_FINANCE_CATEGORY_CODE_PATTERN.search(
                    text
                )
            )

            # print(
            #     f"Page {page['page_number']} "
            #     f"subsection={subsection_number}"
            # )

            # print(
            #     f"regular={has_regular} "
            #     f"self_finance={has_self_finance}"
            # )

            if has_regular == has_self_finance:
                continue


            section_type = (
                "regular_category_descriptions"
                if has_regular
                else "self_finance_category_descriptions"
            )

            candidates.append(
                {
                    "index": index,
                    "section_type": section_type,
                    "section_number": subsection_number,
                }
            )

        sections: list[ProspectusSection] = []
        seen_types: set[str] = set()

        for candidate in candidates:
            section_type = candidate["section_type"]

            if section_type in seen_types:
                continue

            start_index = candidate["index"]
            section_number = candidate["section_number"]
            # print(
            #     f"[CATEGORY] "
            #     f"{section_type} "
            #     f"page={pages[start_index]['page_number']} "
            #     f"number={section_number}"
            # )

            end_index = self._category_subsection_end_index(
                pages=pages,
                start_index=start_index,
                section_number=section_number,
            )


            sections.append(
                ProspectusSection(
                    section_type=section_type,
                    start_page=pages[start_index][
                        "page_number"
                    ],
                    end_page=pages[end_index][
                        "page_number"
                    ],
                    heading="Description of Categories",
                    metadata={
                        "discovery_method": (
                            "exact_numbered_category_subsection"
                        ),
                        "section_number": section_number,
                    },
                )
            )

            # print(
            #     f"ADDED: {section_type} "
            #     f"{pages[start_index]['page_number']}-"
            #     f"{pages[end_index]['page_number']}"
            # )

            seen_types.add(section_type)

        return sections

    def _category_subsection_number_for_pattern(
        self,
        text: str,
        pattern: re.Pattern[str],
    ) -> str | None:
        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        category_number_pattern = re.compile(
            r"^\d+(?:\.\d+)+\s*\([ivxlcdm]+\)?$",
            re.IGNORECASE,
        )

        for index, line in enumerate(lines):
            if not pattern.search(line):
                continue

            # First handle inline OCR such as:
            # 5.2(ii) Description of Categories
            compact_line = re.sub(
                r"\s+",
                "",
                line,
            )

            inline_match = re.match(
                r"^(\d+(?:\.\d+)+\([ivxlcdm]+\)?)",
                compact_line,
                re.IGNORECASE,
            )

            if inline_match:
                return inline_match.group(1)

            # Otherwise look backwards for:
            # 5.2(ii)
            # Description of Categories
            for previous in reversed(
                lines[max(0, index - 3):index]
            ):
                compact = re.sub(
                    r"\s+",
                    "",
                    previous,
                )

                if category_number_pattern.fullmatch(compact):
                    return compact

        return None

    # def _category_subsection_end_index(
    #     self,
    #     pages: list[dict[str, Any]],
    #     start_index: int,
    #     section_number: str,
    # ) -> int:
    #     match = re.fullmatch(
    #         r"(\d+(?:\.\d+)*)\(([ivxlcdm]+)\)",
    #         section_number,
    #         re.IGNORECASE,
    #     )

    #     if match is None:
    #         return start_index

    #     parent = match.group(1)
    #     current_roman = match.group(2).lower()

    #     roman_values = {
    #         "i": 1,
    #         "ii": 2,
    #         "iii": 3,
    #         "iv": 4,
    #         "v": 5,
    #         "vi": 6,
    #         "vii": 7,
    #         "viii": 8,
    #         "ix": 9,
    #         "x": 10,
    #     }

    #     current_value = roman_values.get(current_roman)

    #     if current_value is None:
    #         return start_index

    #     sibling_pattern = re.compile(
    #         rf"(?im)^\s*{re.escape(parent)}\s*"
    #         rf"\(([ivxlcdm]+)\)"
    #     )

    #     chapter_ranges = self._chapter_ranges(pages)
    #     start_page_number = pages[start_index]["page_number"]

    #     containing_chapter = next(
    #         (
    #             chapter
    #             for chapter in chapter_ranges
    #             if (
    #                 chapter["start_page"]
    #                 <= start_page_number
    #                 <= chapter["end_page"]
    #             )
    #         ),
    #         None,
    #     )

    #     chapter_end_index = len(pages) - 1

    #     if containing_chapter is not None:
    #         for index, page in enumerate(pages):
    #             if (
    #                 page["page_number"]
    #                 == containing_chapter["end_page"]
    #             ):
    #                 chapter_end_index = index
    #                 break

    #     for index in range(
    #         start_index + 1,
    #         chapter_end_index + 1,
    #     ):
    #         text = self._page_text(pages[index])

    #         for sibling in sibling_pattern.finditer(text):
    #             sibling_value = roman_values.get(
    #                 sibling.group(1).lower()
    #             )

    #             if (
    #                 sibling_value is not None
    #                 and sibling_value > current_value
    #             ):
    #                 # Keep this page because the final category
    #                 # descriptions and next sibling heading may
    #                 # share the same physical page.
    #                 print(
    #                     f"[SIBLING] "
    #                     f"{section_number} -> "
    #                     f"{sibling.group(1)} "
    #                     f"on page {pages[index]['page_number']}"
    #                 )
    #                 return index
    #     print(
    #         f"[NO SIBLING] "
    #         f"{section_number} "
    #         f"using chapter end "
    #         f"{pages[chapter_end_index]['page_number']}"
    #     )

    #     return chapter_end_index

    def _category_subsection_end_index(
        self,
        pages: list[dict[str, Any]],
        start_index: int,
        section_number: str,
    ) -> int:

        match = re.fullmatch(
            r"(\d+)\.(\d+)\(([ivxlcdm]+)\)?",
            section_number,
            re.IGNORECASE,
        )

        if match is None:
            return start_index

        chapter = int(match.group(1))
        parent = int(match.group(2))

        next_parent_pattern = re.compile(
            rf"(?im)^\s*{chapter}\.{parent+1}\s*"
            r"\(\s*i\s*\)"
        )

        chapter_ranges = self._chapter_ranges(pages)

        start_page = pages[start_index]["page_number"]

        containing_chapter = next(
            (
                chapter_info
                for chapter_info in chapter_ranges
                if (
                    chapter_info["start_page"]
                    <= start_page
                    <= chapter_info["end_page"]
                )
            ),
            None,
        )

        chapter_end_index = len(pages) - 1

        if containing_chapter is not None:
            for i, page in enumerate(pages):
                if (
                    page["page_number"]
                    == containing_chapter["end_page"]
                ):
                    chapter_end_index = i
                    break

        for i in range(
            start_index + 1,
            chapter_end_index + 1,
        ):

            # Stop if the next admission scheme starts
            text = self._page_text(pages[i])

            if next_parent_pattern.search(text):

                # print(
                #     f"[NEXT PARENT] "
                #     f"{section_number} -> "
                #     f"{chapter}.{parent + 1} "
                #     f"page {pages[i]['page_number']}"
                # )

                return i - 1
            # Stop if we encounter another dense seat matrix.
            if self._is_dense_seat_table_page(pages[i]):

                # print(
                #     f"[NEXT TABLE] "
                #     f"{section_number} "
                #     f"stopped by dense table "
                #     f"page {pages[i]['page_number']}"
                # )

                return i - 1

        # print(
        #     f"[NO NEXT PARENT] "
        #     f"{section_number} "
        #     f"chapter end "
        #     f"{pages[chapter_end_index]['page_number']}"
        # )

        return chapter_end_index


    @classmethod
    def _chapter_number(
        cls,
        text: str,
    ) -> int | None:
        match = cls.CHAPTER_PATTERN.search(text)

        if match:
            value = (
                match.group("number_a")
                or match.group("number_b")
            )

            return int(value)

        # Generic OCR fallback:
        # CHAPTER
        # 8

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        for index, line in enumerate(lines):

            if line.upper() != "CHAPTER":
                continue

            if index + 1 >= len(lines):
                continue

            next_line = lines[index + 1]

            if next_line.isdigit():
                return int(next_line)

        return None

    @staticmethod
    def _page_text(
        page: dict[str, Any],
    ) -> str:
        return (
            page.get("text")
            or page.get("markdown")
            or ""
        )
