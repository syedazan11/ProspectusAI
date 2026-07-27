import re

from src.processing.prospectus.person_record import (
    PersonRecord,
)
from dataclasses import dataclass


@dataclass(slots=True)
class LayoutBlock:
    role: str | None
    lines: list[str]


class PersonExtractor:
    """
    Extracts structured people information
    from prospectus sections.
    """

    TITLE_PATTERN = re.compile(
        r"\b("
        r"Prof\.?|Professor|"
        r"Dr\.?|"
        r"Mr\.?|Mrs\.?|Ms\.?|"
        r"Engr\.?"
        r")\b",
        re.IGNORECASE,
    )

    # DEGREE_PATTERN = re.compile(
    #     r"\b("
    #     r"BE|B\.E\.|"
    #     r"BS|B\.S\.|"
    #     r"ME|M\.E\.|"
    #     r"MS|M\.S\.|"
    #     r"MBA|"
    #     r"MPhil|"
    #     r"Ph\.?D|"
    #     r"PhD"
    #     r")\b",
    #     re.IGNORECASE,
    # )

    ROLE_PATTERN = re.compile(
        r"\b("
        r"Vice[- ]?Chancellor|"
        r"Pro[- ]?Vice[- ]?Chancellor|"
        r"Dean|"
        r"Chairman|"
        r"Chairperson|"
        r"Co[- ]?Chairperson|"
        r"Director|"
        r"Registrar|"
        r"Treasurer|"
        r"Controller of Examinations|"

        r"Professor|"
        r"Professors|"

        r"Associate Professor|"
        r"Associate Professors|"

        r"Assistant Professor|"
        r"Assistant Professors|"
    
        r"Lecturer|"
        r"Lecturers"
        r")\b",
        re.IGNORECASE,
    )

    SINGLE_PERSON_ROLES = {
        "vice chancellor",
        "pro vice chancellor",
        "chairman",
        "chairperson",
        "co-chairperson",
        "director",
        "registrar",
        "treasurer",
        "controller of examinations",
        "dean",
    }

    GROUP_ROLE_MAP = {
        "professor": "Professor",
        "professors": "Professor",
    
        "associate professor": "Associate Professor",
        "associate professors": "Associate Professor",

        "assistant professor": "Assistant Professor",
        "assistant professors": "Assistant Professor",

        "lecturer": "Lecturer",
        "lecturers": "Lecturer",
    }

    def extract(
        self,
        pages: list[dict],
    ) -> list[PersonRecord]:

        records: list[PersonRecord] = []

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
                    self._extract_people(
                        section=section,
                        page_number=page_number,
                        heading=heading,
                    )
                )

        return self._deduplicate(records)

    def _deduplicate(
        self,
        records: list[PersonRecord],
    ) -> list[PersonRecord]:

        merged: dict[str, PersonRecord] = {}

        for record in records:

            key = re.sub(
                r"\s+",
                " ",
                record.name.lower(),
            ).strip()

            existing = merged.get(key)

            if existing is None:
                merged[key] = record
                continue

            # Prefer a discovered role.
            if existing.role is None and record.role:
                existing.role = record.role

            # Prefer a discovered department.
            if existing.department is None and record.department:
                existing.department = record.department

            # Merge qualifications.
            for qualification in record.qualifications:
                if qualification not in existing.qualifications:
                    existing.qualifications.append(
                        qualification
                    )

        return list(merged.values())
    
    def _normalize_person_name(
        self,
        line: str,
    ) -> str:

        text = line.strip()

        text = re.sub(
            r"^\d+\.\s*",
            "",
            text,
        )

        text = re.sub(
            r"^[ivxlcdmIVXLCDM]+\)\s*",
            "",
            text,
        )

        text = re.sub(
            r"^[A-Za-z]\)\s*",
            "",
            text,
        )

        # Collapse whitespace.
        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        # Remove trailing punctuation.
        text = text.strip(
            " ,;:-."
        )

        return text.strip()
    
    def _extract_department(
        self,
        heading: str,
        section: dict,
    ) -> str | None:
        """
        Extract a department/faculty name
        from the section heading.
        """

        heading = heading.strip()

        if not heading:
            return None

        lower = heading.lower()

        keywords = (
            "department",
            "faculty",
            "school",
            "institute",
            "centre",
            "center",
        )

        # 1. Prefer heading.
        candidate = heading.strip()

        if any(k in candidate.lower() for k in keywords):
            return candidate

        # 2. Otherwise inspect the first few lines.
        for line in section.get("content", [])[:6]:

            text = line.strip()

            if any(k in text.lower() for k in keywords):

                if len(text) <= 100:
                    return text

        return None
    
    def _looks_like_qualification(
        self,
        line: str,
    ) -> bool:
        """
        Decide whether a line is likely to be
        a qualification of the previously
        detected person.

        Uses generic document structure rather
        than specific degree names.
        """

        text = line.strip()

        if not text:
            return False
        
        # Ignore isolated footnote/page numbers.
        if text.isdigit():
            return False

        if re.fullmatch(
            r"\d+(?:\.\d+)?",
            text,
        ):
            return False

        # Another person's name starts a new record.
        if self.TITLE_PATTERN.search(text):
            return False

        # Roles also start new records.
        if self.ROLE_PATTERN.search(text):
            return False

        # Qualifications are usually concise.
        if len(text) > 120:
            return False
        
        # Headings are not qualifications.
        if text.endswith(":"):
            return False

        # Numbered headings are not qualifications.
        if re.match(
            r"^\d+(\.\d+)*",
            text,
        ):
            return False

        # Institution names, years, commas and
        # parentheses are common in qualifications.
        score = 0

        if "," in text:
            score += 1

        if "(" in text or ")" in text:
            score += 1

        if any(ch.isdigit() for ch in text):
            score += 1

        if len(text.split()) <= 10:
            score += 1

        # Qualifications often mention an institution.
        institution_words = (
            "university",
            "institute",
            "college",
            "school",
        )

        if any(
            word in text.lower()
            for word in institution_words
        ):
            score += 2

        return score >= 3
    
    def _looks_like_person_name(
        self,
        text: str,
    ) -> bool:
        """
        Generic validation for person names.
        """

        text = text.strip()

        if not text:
            return False

        # Person names rarely contain digits.
        if any(
            ch.isdigit()
            for ch in text
        ):
            return False

        # Paragraphs are not names.
        if len(text) > 80:
            return False

        # Names are short.
        if len(text.split()) > 8:
            return False

        # Too many commas usually means
        # qualifications or prose.
        if text.count(",") > 1:
            return False

        # Semicolons usually separate qualifications.
        if ";" in text:
            return False

        # Reject headings written entirely
        # in uppercase.
        letters = "".join(
            ch
            for ch in text
            if ch.isalpha()
        )

        if (
            letters
            and letters == letters.upper()
        ):
            return False

        # Qualification lines must never become people.
        if self._looks_like_qualification(text):
            return False

        # Degree abbreviations at the beginning are
        # almost certainly qualifications.
        if re.match(
            r"^(B\.?E\.?|B\.?S\.?|M\.?E\.?|M\.?S\.?|M\.?Engg\.?|MBA|M\.?Phil\.?|Ph\.?D)",
            text,
            re.IGNORECASE,
        ):
            return False

        # Institution-only lines are not names.
        institution_words = (
            "university",
            "institute",
            "college",
            "school",
            "faculty",
            "department",
        )

        if any(
            word in text.lower()
            for word in institution_words
        ):
            return False

        # Titles strongly indicate a person.
        if self.TITLE_PATTERN.search(text):
            return True

        return False

    def _is_non_person(
        self,
        text: str,
    ) -> bool:
        """
        Reject obvious facilities or organizations
        that contain a title but are not people.
        """

        text = text.lower()

        blocked = (
            "library",
            "department",
            "faculty",
            "school",
            "centre",
            "center",
            "office",
            "hostel",
            "laboratory",
            "lab",
            "complex",
            "building",
        )

        return any(
            word in text
            for word in blocked
        )
    
    def _build_layout_blocks(
        self,
        section: dict,
    ) -> list[LayoutBlock]:

        blocks: list[LayoutBlock] = []

        current_role = None
        current_lines: list[str] = []
        previous_bottom = None
        previous_x = None

        for entry in self._iter_layout_lines(section):

            raw_line = entry["text"]

            line = self._normalize_person_name(
                raw_line
            )

            numbered_entry = bool(
                re.fullmatch(
                    r"\d+\.",
                    raw_line.strip(),
                )
            )

            if not line:
                continue

            #
            # Large vertical gaps usually indicate
            # a new logical block.
            #
            if (
                previous_bottom is not None
                and entry["top"] is not None
                and entry["height"] is not None
            ):

                gap = entry["top"] - previous_bottom

                if gap > (entry["height"] * 1.5):

                    if current_lines:

                        blocks.append(
                            LayoutBlock(
                                role=current_role,
                                lines=current_lines,
                            )
                        )

                    current_lines = []
                    current_role = None

            role_match = self.ROLE_PATTERN.search(line)

            previous_bottom = entry["bottom"]

            if role_match:

                if current_lines:
                    blocks.append(
                        LayoutBlock(
                            role=current_role,
                            lines=current_lines,
                        )
                    )

                role_text = role_match.group(0).strip().lower()

                current_role = self.GROUP_ROLE_MAP.get(
                    role_text,
                    role_match.group(0).strip(),
                )

                current_lines = []

                continue

            if (
                numbered_entry
                and current_lines
            ):
                blocks.append(
                    LayoutBlock(
                        role=current_role,
                        lines=current_lines,
                    )
                )
                current_lines = []

            current_lines.append(line)

        if current_lines:

            blocks.append(
                LayoutBlock(
                    role=current_role,
                    lines=current_lines,
                )
            )
        
        #for i, block in enumerate(blocks):
            # print(
            #     f"[BLOCK {i}] "
            #     f"role={block.role} "
            #     f"lines={len(block.lines)} "
            #     f"first={block.lines[:3]}"
            # )

        return blocks
    
    def _iter_layout_lines(
        self,
        section: dict,
    ):
        """
        Yield OCR lines in visual reading order.

        - Falls back to plain text when layout is unavailable.
        - Detects visual columns dynamically.
        - Reads each column from top to bottom.
        """

        layout_items = section.get("layout_items")

        if not layout_items:

            for line in section.get("content", []):

                yield {
                    "text": line,
                    "top": None,
                    "bottom": None,
                    "height": None,
                    "x": None,
                }

            return

        def get(item, key):
            if isinstance(item, dict):
                return item[key]
            return getattr(item, key)

        items = list(layout_items)

        # Primary sort by X then Y.
        items.sort(
            key=lambda item: (
                get(item, "x"),
                get(item, "top"),
            )
        )

        columns: list[dict] = []

        for item in items:

            x = float(get(item, "x"))

            assigned = False

            for column in columns:

                if abs(x - column["center"]) <= column["width"]:

                    column["items"].append(item)

                    xs = [
                        float(get(i, "x"))
                        for i in column["items"]
                    ]

                    column["min_x"] = min(xs)
                    column["max_x"] = max(xs)
                    column["center"] = (
                        column["min_x"]
                        + column["max_x"]
                    ) / 2.0

                    assigned = True
                    break

            if assigned:
                continue

            columns.append(
                {
                    "items": [item],
                    "min_x": x,
                    "max_x": x,
                    "center": x,
                    # Initial tolerance grows automatically
                    # as more items are added.
                    "width": 140.0,
                }
            )

        # Finalize adaptive widths.
        for column in columns:

            spread = (
                column["max_x"]
                - column["min_x"]
            )

            column["width"] = max(
                140.0,
                spread + 40.0,
            )

        # Read columns left-to-right.
        columns.sort(
            key=lambda c: c["center"]
        )

        ordered_items = []

        for column in columns:

            column["items"].sort(
                key=lambda item: (
                    get(item, "top"),
                    get(item, "x"),
                )
            )

            ordered_items.extend(
                column["items"]
            )

        for item in ordered_items:

            yield {
                "text": get(item, "text"),
                "top": get(item, "top"),
                "bottom": get(item, "bottom"),
                "height": get(item, "height"),
                "x": get(item, "x"),
            }
    
    def _extract_people(
        self,
        *,
        section: dict,
        page_number: int,
        heading: str,
    ) -> list[PersonRecord]:

        records: list[PersonRecord] = []

        blocks = self._build_layout_blocks(section)

        for block in blocks:

            current_person: PersonRecord | None = None

            pending_role = None
            current_group_role = block.role

            for line in block.lines:

                line = line.strip()

                line = self._normalize_person_name(
                    line
                )

                # Qualification lines belong to the
                # previously detected person.
                if (
                    current_person is not None
                    and self._looks_like_qualification(
                        line
                    )
                ):
                    current_person.qualifications.append(
                        line
                    )
                    continue

                if not line:
                    continue

                role_match = self.ROLE_PATTERN.search(line)

                if role_match:

                    role_text = role_match.group(0).strip()

                    normalized = role_text.lower()

                    if normalized in self.GROUP_ROLE_MAP:

                        current_group_role = self.GROUP_ROLE_MAP[
                            normalized
                        ]

                        pending_role = None

                    else:

                        pending_role = role_text

                    continue

                # if self._looks_like_degree(line):
                #     continue

                if not self._looks_like_person_name(
                    line
                ):
                    continue
                if self._is_non_person(
                    line
                ):
                    continue

                assigned_role = pending_role

                if assigned_role is None:
                    assigned_role = current_group_role

                current_person = PersonRecord(
                    name=line,
                    role=assigned_role,
                    department=self._extract_department(heading, section),
                    qualifications=[],
                    source_page=page_number,
                    source_heading=heading,
                    source_text=line,
                )

                records.append(
                    current_person
                )
                pending_role = None

        return records