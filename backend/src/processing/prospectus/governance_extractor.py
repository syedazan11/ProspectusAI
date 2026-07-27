import re

from src.processing.prospectus.governance_record import (
    GovernanceRecord,
)


class GovernanceExtractor:
    """
    Extract structured governance information.
    """

    def extract(
        self,
        pages: list[dict],
    ) -> list[GovernanceRecord]:

        records: list[GovernanceRecord] = []

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

                if not self._is_relevant_section(
                    heading,
                    section,
                ):
                    continue

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
    def _is_relevant_section(
        self,
        heading: str,
        section: dict,
    ) -> bool:

        heading_text = heading.lower()

        heading_keywords = (
            "syndicate",
            "senate",
            "board",
            "committee",
            "council",
            "governor",
            "governance",
            "registrar",
            "vice chancellor",
            "treasurer",
            "organization",
            "academic council",
            "board of governors",
            "finance and planning",
            "finance & planning",
            "selection board",
            "advanced studies",
            "board of faculty",
        )

        if any(
            keyword in heading_text
            for keyword in heading_keywords
        ):
            return True

        text = "\n".join(
            section.get(
                "content",
                [],
            )[:2]
        ).lower()

        content_keywords = (
            "academic council",
            "board of governors",
            "finance committee",
            "planning committee",
            "selection board",
            "syndicate",
        )

        return any(
            keyword in text
            for keyword in content_keywords
        )
    def _extract_section(
        self,
        *,
        section: dict,
        page_number: int,
        heading: str,
    ) -> list[GovernanceRecord]:

        records: list[GovernanceRecord] = []

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

            if (
                self._looks_like_person(line)
            ):
                continue

            if not line:
                continue

            roles = {
                "chairman",
                "chairperson",
                "member",
                "secretary",
                "registrar",
                "treasurer",
                "director",
                "dean",
                "professor",
                "associate professor",
                "assistant professor",
                "lecturer",
            }

            if line.lower() in roles:
                continue

            # Don't create a record from the
            # section heading itself.
            if (
                line.lower()
                == heading.lower()
            ):
                continue

            if (
                self._looks_like_title(line)
            and not self._looks_like_attribute(line)
            ):

                if self._is_non_governance_title(
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
                        GovernanceRecord(
                            title=current_title,
                            category=heading,
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

                current_block.append(
                    line
                )

        if current_title is not None:

            records.append(
                GovernanceRecord(
                    title=current_title,
                    category=heading,
                    attributes=current_attributes,
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
        if self._is_non_governance_title(
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
        
        # Reject titles containing common sentence verbs.
        sentence_words = (
            "shall",
            "should",
            "must",
            "may",
            "will",
            "required",
            "advised",
            "contains",
            "include",
            "includes",
            "including",
            "provides",
            "provide",
            "available",
            "located",
            "established",
        )

        if any(
            word in text.lower()
            for word in sentence_words
        ):
            return False
        
        # Reject titles ending with punctuation that
        # usually indicates continuation.
        if text.endswith(","):
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
        
        # Reject lines containing too many commas.
        if text.count(",") >= 2:
            return False

        return True
    
    def _looks_like_person(
        self,
        text: str,
    ) -> bool:

        return bool(
            re.search(
                r"\b(Prof|Professor|Dr|Mr|Mrs|Ms|Engr)\b",
                text,
                re.IGNORECASE,
            )
        )
    
    def _deduplicate(
        self,
        records: list[GovernanceRecord],
    ) -> list[GovernanceRecord]:

        merged: dict[str, GovernanceRecord] = {}

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
                existing.category is None
                and record.category
            ):
                existing.category = (
                    record.category
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
    def _is_non_governance_title(
        self,
        text: str,
    ) -> bool:

        text = text.strip()

        if not text:
            return True

        lower = text.lower()

        blocked = {
            "prospectus",
            "contents",
            "chapter",
            "page",
            "figure",
            "table",
            "appendix",
            "curriculum",
            "semester",
            "credit hours",
            "hostel",
            "sports",
            "library",
            "scholarship",
            "financial assistance",
        }

        if lower in blocked:
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
        
        if len(text) > 120:
            return False

        if re.fullmatch(
            r"\d+(?:\.\d+)+",
            text,
        ):
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