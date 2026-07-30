import re

from src.processing.prospectus.student_life_record import (
    StudentLifeRecord,
)


class StudentLifeExtractor:
    """
    Extract structured student life
    information.
    """

    def extract(
        self,
        pages: list[dict],
    ) -> list[StudentLifeRecord]:

        records: list[StudentLifeRecord] = []

        for page in pages:

            page_number = page["page_number"]

            for section in page.get(
                "sections",
                [],
            ):
                heading = self._derive_heading(section)

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

    def _looks_like_index_section(
        self,
        content: list[str],
    ) -> bool:

        lines = [
            line.strip()
            for line in content
            if line.strip()
        ]
    
        if len(lines) < 8:
            return False
        page_numbers = sum(
            1
            for line in lines
            if re.fullmatch(r"\d{1,3}", line)
        )
    
        numbered_headings = sum(
            1
            for line in lines
            if re.match(
                r"^\d+(?:\.\d+)+",
                line,
            )
        )

        prose = sum(
            1
            for line in lines
            if len(line.split()) >= 8
        )

        return (
            page_numbers >= 3
            and numbered_headings >= 3
            and prose <= max(2, len(lines) // 5)
        )

    def _derive_heading(
        self,
        section: dict,
    ) -> str:

        content = [
            line.strip()
            for line in section.get("content", [])
            if line.strip()
        ]
        candidates = []
        for i, line in enumerate(content[:20]):
            match = re.match(
                r"^(\d+(?:\.\d+)+)\s+(.+)$",
                line,
            )

            if match:
                return match.group(2).strip()

            if not self._looks_like_title(line):
                continue
            if self._is_non_studentlife_title(line):
                continue
            candidates.append(line)
        if candidates:
        # Prefer the longest meaningful title
            for title in candidates:
                if len(title.split()) >= 2:
                    return title
            return candidates[0]

        return section.get("heading", "").strip()

    # def _derive_heading(
    #     self,
    #     section: dict,
    # ) -> str:

    #     content = [
    #         line.strip()
    #         for line in section.get("content", [])
    #         if line.strip()
    #     ]

    #     best_title = None
    #     best_score = -1

    #     for line in content[:20]:

    #         match = re.match(
    #             r"^(\d+(?:\.\d+)+)\s+(.+)$",
    #             line,
    #         )

    #         if match:
    #             candidate = match.group(2).strip()
    #         else:
    #             candidate = line

    #         if not self._looks_like_title(candidate):
    #             continue

    #         if self._is_non_studentlife_title(candidate):
    #             continue

    #         score = 0

    #         words = candidate.split()
    #         # Prefer descriptive headings.
    #         score += min(len(words), 6)
    #         # Prefer mixed case over ALL CAPS.
    #         if not candidate.isupper():
    #             score += 3
    #         # Prefer headings that aren't extremely short.
    #         if len(words) >= 2:
    #             score += 2
    #         # Penalize OCR fragments.
    #         if len(words) == 1:
    #             score -= 2
    #         if score > best_score:
    #             best_score = score
    #             best_title = candidate

    #     if best_title:
    #         return best_title

    #    return section.get("heading", "").strip()
    
    def _is_relevant_section(
        self,
        heading: str,
        section: dict,
    ) -> bool:
        """
        Score whether this section genuinely belongs
        to Student Life.
        """
        score = 0

        # lines = [
        #     line.strip()
        #     for line in section.get("content", [])
        #     if line.strip()
        # ]

        if self._looks_like_index_section(
            section.get("content", [])
        ):
            return False

        heading_text = heading.lower().strip()

        content = "\n".join(
            section.get("content", [])[:10]
        ).lower()

        text = f"{heading_text}\n{content}"

        positive = {
            "student affairs": 6,
            "student welfare": 6,
            "hostel": 6,
            "hostel facilities": 7,
            "hostel charges": 6,
            "library": 6,
            "sports": 1,
            "sport": 1,
            "gymnasium": 5,
            "common room": 5,
            "sports section": 5,
            "sports facilities": 5,
            "sports complex": 5,
            "transport": 5,
            "canteen": 4,
            "stationery": 4,
            "scholarship": 2,
            "financial assistance": 5,
            "accessibility": 4,
            "medical centre": 4,
            "medical center": 4,
        }

        negative = {
            "admission": -8,
            "eligibility": -8,
            "admission process": -8,
            "admission categories": -8,
            "fee": -6,
            "curriculum": -8,
            "department": -5,
            "faculty": -5,
            "dean": -5,
            "chairman": -5,
            "professor": -5,
            "medical fitness": -10,
            "migration": -8,
            "transfer of seats": -8,
            "seat distribution": -8,
            "biomedical": -8,
            "electrical": -5,
            "civil engineering": -5,
            "computer engineering": -5,
            "chemical engineering": -5,
        }

        for keyword, value in positive.items():
            if keyword in text:
                score += value

        for keyword, value in negative.items():
            if keyword in text:
                score += value

        if score >= 5:
            print(f"[StudentLife] ACCEPT ({score}) {heading}")
        if score >= 5:
            print("=" * 80)
            print(f"Heading: {heading}")
            print(f"Score: {score}")
            print(text[:1000])

        return score >= 5
    

    def _extract_section(
        self,
        *,
        section: dict,
        page_number: int,
        heading: str,
    ) -> list[StudentLifeRecord]:

        records: list[StudentLifeRecord] = []

        current_title: str | None = None

        current_attributes: dict[str, str] = {}

        current_block: list[str] = []

        content = section.get(
            "content",
            [],
        )
        if self._looks_like_index_section(content):
            return []

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

                if self._is_non_studentlife_title(
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
                        StudentLifeRecord(
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
                StudentLifeRecord(
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
        if self._is_non_studentlife_title(
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
        records: list[StudentLifeRecord],
    ) -> list[StudentLifeRecord]:

        merged: dict[str, StudentLifeRecord] = {}

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
    

    def _is_non_studentlife_title(
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
            "table",
            "figure",
            "appendix",

            "chairperson",
            "co-chairperson",
            "chairman",
            "director",
            "dean",
            "professor",
            "associate professor",
            "assistant professor",
            "lecturer",
            "registrar",
            "vice chancellor",
            "treasurer",
        }

        if lower in blocked:
            return True
        
        # Reject person titles.
        if re.search(
            r"\b("
            r"Prof\.?|Professor|"
            r"Dr\.?|"
            r"Mr\.?|Mrs\.?|Ms\.?|"
            r"Engr\.?"
            r")\b",
            text,
            re.IGNORECASE,
        ):
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
    

        

