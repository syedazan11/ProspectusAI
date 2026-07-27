import re

from src.processing.prospectus.admission_record import (
    AdmissionRecord,
)


class AdmissionExtractor:
    """
    Extract structured admission information.
    """

    def extract(
        self,
        pages: list[dict],
    ) -> list[AdmissionRecord]:

        records: list[AdmissionRecord] = []

        for page in pages:

            page_number = page["page_number"]

            for section in page.get(
                "sections",
                [],
            ):

                heading = section.get(
                    "heading",
                    "",
                ).strip()

                records.extend(
                    self._extract_section(
                        section=section,
                        page_number=page_number,
                        heading=heading,
                    )
                )

        return records

    def _extract_section(
        self,
        *,
        section: dict,
        page_number: int,
        heading: str,
    ) -> list[AdmissionRecord]:

        records: list[AdmissionRecord] = []

        current_title: str | None = None
        current_details: dict[str, str] = {}
        current_block: list[str] = []

        content = section.get(
            "content",
            [],
        )

        for index, line in enumerate(
            content
        ):

            line = line.strip()

            if not line:
                continue

            if len(line) < 3:
                continue

            if line.count("|") >= 2:
                continue

            if line.count("...") >= 2:
                continue

            if (
                not self._looks_like_attribute(line)
                and self._looks_like_title(line)
            ):
                
                if self._is_non_admission_title(
                    line
                ):
                    continue

                if (
                    current_title is not None
                    and index + 1 < len(content)
                ):

                    next_line = (
                        content[index + 1]
                        .strip()
                    )

                    if self._should_merge_title(
                        current_title,
                        next_line,
                    ):

                        current_title += (
                            " " + next_line
                        )

                        current_block.append(
                            next_line
                        )

                        continue

                if current_title is not None:

                    records.append(
                        AdmissionRecord(
                            title=current_title,
                            category=heading,
                            details=current_details,
                            source_page=page_number,
                            source_heading=heading,
                            source_text="\n".join(
                                current_block
                            ),
                        )
                    )

                current_title = line
                current_details = {}
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

                    current_details[key] = value

                current_block.append(
                    line
                )

        if current_title is not None:

            records.append(
                AdmissionRecord(
                    title=current_title,
                    category=heading,
                    details=current_details,
                    source_page=page_number,
                    source_heading=heading,
                    source_text="\n".join(
                        current_block
                    ),
                )
            )

        return records
    
    def _should_merge_title(
        self,
        current: str,
        nxt: str,
    ) -> bool:
        """
        Decide whether the next OCR line
        is a continuation of the current title.
        """

        current = current.strip()
        nxt = nxt.strip()

        if not current or not nxt:
            return False

        # Don't merge attributes.
        if self._looks_like_attribute(
            nxt
        ):
            return False

        # Don't merge document headings.
        if self._is_non_admission_title(
            nxt
        ):
            return False

        # Don't merge URLs.
        if (
            "www." in nxt.lower()
            or "http" in nxt.lower()
        ):
            return False

        # Continuation lines are usually short.
        if len(nxt.split()) > 4:
            return False

        # Lowercase continuation.
        if nxt[0].islower():
            return True

        # One or two trailing words.
        if len(nxt.split()) <= 2:
            return True

        return False
    
    def _looks_like_title(
        self,
        line: str,
    ) -> bool:

        text = line.strip()

        if not text:
            return False

        # Pure section numbers are not titles.
        if re.fullmatch(
            r"\d+(?:\.\d+)+",
            text,
        ):
            return False
        
        if (
                "www." in text.lower()
                or "http" in text.lower()
                or ".pk" in text.lower()
                or ".com" in text.lower()
            ):
                return False


        if ":" in text:
            return False

        if len(text) < 5:
            return False

        if len(text) > 80:
            return False
        
        words = text.split()

        # Headings are concise.
        if len(words) > 8:
            return False
        
        # Reject sentence-like titles.
        common_starts = {
            "the",
            "a",
            "an",
            "all",
            "any",
            "every",
            "each",
            "candidate",
            "candidates",
            "applicant",
            "applicants",
            "students",
            "student",
            "he",
            "she",
            "they",
            "you",
        }

        if words[0].lower() in common_starts:
            return False

        if len(text.split()) > 10:
            return False

        if text.endswith(
            (
                ".",
                ";",
                "?",
                "!",
            )
        ):
            return False

        # Mostly numeric.
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

        if letters < 5:
            return False

        # Starts with lowercase -> probably prose.
        if words[0][0].islower():
            return False
        
        verbs = (
            "shall",
            "should",
            "must",
            "may",
            "will",
            "required",
            "advised",
        )

        if any(
            verb in text.lower()
            for verb in verbs
        ):
            return False
        bad_endings = (
            "and",
            "or",
            "of",
            "to",
            "for",
            "with",
            "in",
        )

        if words[-1].lower() in bad_endings:
            return False

        return True
    
    def _is_non_admission_title(
        self,
        text: str,
    ) -> bool:

        lower = text.lower()

        blocked = {
            "chapter",
            "contents",
            "prospectus",
            "admission",
            "eligibility",
            "general guidance",
            "required documents",
            "document required",
            "notes",
            "note",
            "prospectus",
            "technology",
            "engineering",
            "official",
            "website",
            "facebook",
            "youtube",
            "instagram",
            "twitter",
            "linkedin",
            "neduetofficial",
            "nepoid",
            "nepidl",

        }

        if lower in blocked:
            return True

        # OCR garbage.
        letters = sum(
            c.isalpha()
            for c in text
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
        admission attributes.
        """

        text = line.strip()

        if not text:
            return False
        
        if len(text) > 120:
            return False

        if re.fullmatch(
            r"\d+(?:\.\d+)+",
            text,
        ):
            return False

        if ":" in text:
            return True

        if " - " in text:
            return True

        if "..." in text:
            return True

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

        words = text.split()

        if len(words) >= 2:

            split_index = None

            for i, word in enumerate(words):

                if any(
                    ch.isdigit()
                    for ch in word
                ):
                    split_index = i
                    break

            if split_index is None:
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
    