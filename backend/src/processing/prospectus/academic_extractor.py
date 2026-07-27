import re

from src.processing.prospectus.academic_record import (
    AcademicRecord,
)


class AcademicExtractor:
    """
    Extract structured academic programs.
    """

    def extract(
        self,
        pages: list[dict],
    ) -> list[AcademicRecord]:

        records: list[AcademicRecord] = []

        for page in pages:

            page_number = page["page_number"]

            for section in page.get(
                "sections",
                [],
            ):

                heading = (
                    section.get(
                        "heading",
                        "",
                    )
                    .strip()
                )

                records.extend(
                    self._extract_section(
                        section=section,
                        page_number=page_number,
                        heading=heading,
                    )
                )

        return self._deduplicate(
            records
        )
    
    def _deduplicate(
        self,
        records: list[AcademicRecord],
    ) -> list[AcademicRecord]:

        merged: dict[str, AcademicRecord] = {}

        for record in records:

            key = re.sub(
                r"\s+",
                " ",
                record.title.lower(),
            ).strip()

            existing = merged.get(key)

            if existing is None:
                merged[key] = record
                continue

            # Prefer a discovered department.
            if (
                existing.department is None
                and record.department
            ):
                existing.department = (
                    record.department
                )

            # Merge attributes.
            for key_, value in (
                record.attributes.items()
            ):

                existing.attributes.setdefault(
                    key_,
                    value,
                )

            # Keep the richer source text.
            if (
                len(record.source_text)
                >
                len(existing.source_text)
            ):
                existing.source_text = (
                    record.source_text
                )

        return list(
            merged.values()
        )
    
    def _extract_section(
        self,
        *,
        section: dict,
        page_number: int,
        heading: str,
    ) -> list[AcademicRecord]:

        records: list[AcademicRecord] = []

        current_program: str | None = None

        current_title: str | None = None

        current_attributes: dict[str, str] = {}

        current_block: list[str] = []

        content = section.get(
            "content",
            [],
        )

        for index, raw_line in enumerate(
            content
        ):

            line = raw_line.strip()

            if not line:
                continue

            # program = self._extract_program_heading(
            #     line
            # )

            # if program is not None:

            #     current_program = program
            #     continue

            if self._is_table_noise(
                line
            ):
                continue

            if (
                not self._looks_like_attribute(line)
                and self._looks_like_title(line)
            ):
                if self._is_non_academic_title(
                    line
                ):
                    continue

                if current_title is not None:

                    records.append(
                        AcademicRecord(
                            title=current_title,
                            department=current_program,
                            attributes=current_attributes,
                            source_page=page_number,
                            source_heading=heading,
                            source_text="\n".join(
                                current_block
                            ),
                        )
                    )

                current_title = line
                current_attributes = {}
                current_block = [line]

                continue

            if (
                current_title
                and self._looks_like_attribute(
                    line
                )
            ):

                key, value = self._parse_attribute(
                    line
                )

                if key:
                    current_attributes[key] = value
                    current_block.append(line)

        if current_title is not None:

            records.append(
                AcademicRecord(
                    title=current_title,
                    department=current_program,
                    attributes=current_attributes,
                    source_page=page_number,
                    source_heading=heading,
                    source_text="\n".join(
                        current_block
                    ),
                )
            )


        return records
    
    def _parse_attribute(
        self,
        line: str,
    ) -> tuple[str | None, str]:

        text = line.strip()

        separators = (
            ":",
            " - ",
            "...",
        )

        for separator in separators:

            if separator in text:

                key, value = text.split(
                    separator,
                    1,
                )

                key = (
                    key.strip()
                    .lower()
                    .replace(
                        " ",
                        "_",
                    )
                )

                return (
                    key,
                    value.strip(),
                )

        # Fallback parser for lines without
        # explicit separators.

        words = text.split()

        if len(words) >= 2:

            # Find where the value probably begins.
            split_index = None

            for i, word in enumerate(words):

                if any(
                    ch.isdigit()
                    for ch in word
                ):
                    split_index = i
                    break

            if split_index is None:

                # No numbers found.
                # Assume the last word begins the value.
                split_index = len(words) - 1

            if split_index > 0:

                key = "_".join(
                    words[:split_index]
                ).lower()

                value = " ".join(
                    words[split_index:]
                )

                return (
                    key,
                    value,
                )

        return (
            None,
            "",
        )
    

    def _looks_like_title(
        self,
        line: str,
    ) -> bool:
        """
        Decide whether a line is likely to be the
        title of a structured academic item.
        """

        text = line.strip()

        if not text:
            return False

        # URLs are never titles.
        if "www." in text.lower():
            return False

        # Attribute lines belong elsewhere.
        if ":" in text:
            return False

        # Very short / very long lines are unlikely titles.
        if len(text) < 5:
            return False

        if len(text) > 80:
            return False

        words = text.split()

        # Titles are concise.
        if len(words) > 10:
            return False

        # Reject paragraph-like sentences.
        sentence_endings = (
            ".",
            ";",
            "?",
            "!",
        )

        if text.endswith(sentence_endings):
            return False

        # Reject lines dominated by digits.
        letters = sum(
            c.isalpha()
            for c in text
        )

        digits = sum(
            c.isdigit()
            for c in text
        )

        if digits > letters:
            return False

        # Titles should contain enough letters.
        if letters < 5:
            return False
        
        # Titles usually begin with a capital letter.
        if not text[0].isupper():
            return False

        # Reject lines that look like ordinary sentences.
        lowercase_words = sum(
            1
            for word in words
            if word[:1].islower()
        )

        if lowercase_words > len(words) // 2:
            return False

        # Titles usually don't begin with connectors.
        bad_starts = (
            "and",
            "or",
            "the",
            "of",
            "for",
            "to",
            "with",
        )

        if words[0].lower() in bad_starts:
            return False

        return True
    
    def _extract_program_heading(
        self,
        line: str,
    ) -> str | None:
        """
        Return the line if it looks like a
        program/department heading.
        """

        text = line.strip()

        if not text:
            return None

        # Ignore table headings.
        if self._is_table_noise(text):
            return None

        # Ignore attributes.
        if self._looks_like_attribute(text):
            return None

        # Ignore obvious document structure.
        if self._is_non_academic_title(text):
            return None

        # Program headings are concise.
        if len(text.split()) > 6:
            return None

        # They are usually entirely alphabetic.
        letters = sum(
            c.isalpha()
            for c in text
        )

        digits = sum(
            c.isdigit()
            for c in text
        )

        if digits > 0:
            return None

        if letters < 8:
            return None

        return text
    
    def _is_table_noise(
        self,
        line: str,
    ) -> bool:

        text = line.strip().lower()

        if not text:
            return True

        blocked = (
            "course title",
            "course code",
            "credit hour",
            "credit hours",
            "th",
            "pr",
            "total",
            "th pr total",
            "pt tal",
            "pr total",
            "pttl",
            "ttl",
            "semester",
            "first year",
            "second year",
            "third year",
            "fourth year",
            "fifth year",
            "prospectus",
            "course of",
            "studies",
            "courtitle",
            "coureitle",
            "coureitlte",
        )

        if text in blocked:
            return True

        if len(text) <= 2:
            return True

        return False
    
    def _is_non_academic_title(
        self,
        text: str,
    ) -> bool:
        """
        Reject document structure, table headings
        and obvious OCR artifacts that should not
        become AcademicRecord titles.
        """

        text = text.strip()

        if not text:
            return True

        lower = text.lower()

        # Document header/footer.
        if text.upper().startswith(
            "PROSPECTUS"
        ):
            return True

        # Year headings.
        if re.fullmatch(
            r"(first|second|third|fourth|final)\s+year",
            lower,
        ):
            return True

        # Semester headings.
        if re.fullmatch(
            r"(fall|spring|summer)\s+semester",
            lower,
        ):
            return True

        # Common table headings.
        blocked = {
            "chapter",
            "course",
            "course title",
            "credit hours",
            "total",
            "th",
            "pr",
            "credits",
        }

        if lower in blocked:
            return True

        # Reject OCR garbage consisting of very
        # few alphabetic characters.
        if len(text.split()) <= 3:

            letters = sum(
                ch.isalpha()
                for ch in text
            )

            if letters < 5:
                return True

        return False
    
    def _looks_like_attribute(
        self,
        line: str,
    ) -> bool:
        """
        Detect generic key/value style
        academic attributes.
        """

        text = line.strip()

        if not text:
            return False

       # Standard key/value separators.
        if ":" in text:
            return True

        if " - " in text:
            return True

        if "..." in text:
            return True

        # Generic attribute pattern:
        # short label followed by additional information.
        words = text.split()

        if (
            2 <= len(words) <= 8
            and any(
                ch.isdigit()
                for ch in text
            )
        ):
            return True

        return False
    
