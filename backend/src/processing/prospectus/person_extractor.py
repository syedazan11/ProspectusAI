
import re
from dataclasses import dataclass
 
from src.processing.prospectus.person_record import (
    PersonRecord,
)
 
 
class PersonExtractor:
    """
    Extracts structured people information from the
    layout-reconstructed prospectus pages (layout.json).
 
    This extractor is page-agnostic: it processes whatever
    pages it is handed and never hardcodes page numbers or
    ranges. Which pages it receives is decided by the caller
    (RecordProcessingService), which resolves them from
    `detected_sections` using `RELEVANT_SECTION_TYPES` below.
    """
 
    # Section types (as produced by the section detector) whose
    # pages are relevant to person extraction. This is the ONLY
    # place page scope is controlled -- by section type, never by
    # page number. Extend this set if other sections also contain
    # named people (e.g. a "governance" / "university_officers"
    # section covering leadership pages).

    DEPARTMENT_PATTERN = re.compile(
        r"""
        ^
        (?:\d+(?:\.\d+)+(?:\([ivxIVX]+\))?\s+)?   # optional 2.2.1 or 2.2.29(i)
        (?P<department>
            Department\s+of\s+[A-Za-z&,\-()/ ]+
        )
        $
        """,
        re.I | re.X,
    )

    # PERSON_PATTERN = re.compile(
    #     r"(Prof\.?\s*Dr\.?|Dr\.?|Mr\.?|Mrs\.?|Ms\.?|Engr\.?)"
    #     r"\s+"
    #     r"[A-Z][A-Za-z.'\-]+"
    #     r"(?:\s+[A-Z][A-Za-z.'\-]+){0,6}"
    # )

    PERSON_PATTERN = re.compile(
        r"(Prof\.?\s*Dr\.?|Dr\.?|Mr\.?|Mrs\.?|Ms\.?|Engr\.?)"
        r"\s+"
        r"(?!"
        r"B\.?E\.?|"
        r"B\.?Sc\.?|"
        r"B\.?Arch\.?|"
        r"BBA|"
        r"MBA|"
        r"M\.?E\.?|"
        r"M\.?Engg\.?|"
        r"M\.?Sc\.?|"
        r"M\.?S\.?|"
        r"M\.?Phil\.?|"
        r"Ph\.?D\.?"
        r"\b)"
        r"[A-Z][A-Za-z.'\-]+"
        r"(?:"
        r"\s+"
        r"(?!"
        r"B\.?E\.?|"
        r"B\.?Sc\.?|"
        r"B\.?Arch\.?|"
        r"BBA|"
        r"MBA|"
        r"M\.?E\.?|"
        r"M\.?Engg\.?|"
        r"M\.?Sc\.?|"
        r"M\.?S\.?|"
        r"M\.?Phil\.?|"
        r"Ph\.?D\.?"
        r"\b)"
        r"[A-Z][A-Za-z.'\-]+"
        r"){0,6}"
    )
 
    TITLE_PATTERN = re.compile(
        r"\b("
        r"Prof\.?|Professor|"
        r"Dr\.?|"
        r"Mr\.?|Mrs\.?|Ms\.?|"
        r"Engr\.?"
        r")\b",
        re.IGNORECASE,
    )

    # FULL_LINE_ROLES = (
    #     "Dean",
    #     "Registrar",
    #     "Additional Registrar",
    #     "Deputy Registrar",
    #     "Controller",
    #     "Additional Controller",
    #     "Director",
    #     "Director of",
    #     "Director, ",
    #     "Director General",
    #     "Principal",
    #     "Treasurer",
    #     "Resident Auditor",
    #     "Principal Medical Officer",
    # )
    FULL_LINE_ROLES = (
        "Vice-Chancellor",
        "Pro-Vice-Chancellor",
        # "Senior Manager",
        # "Manager",
        # "Deputy Manager",
        # "Instrumentation Engineer",
        # "Cooperative Teacher",
        # "Lab Engineer",
        # "Lab Engineers",
        # "Adjunct Faculty",
        # "Sr. Laboratory Engineer",
        "Dean",
        "Registrar",
        "Additional Registrar",
        "Deputy Registrar",
        "Controller",
        "Additional Controller",
        "Additional Controller of Examinations",
        "Additional Controller Student Affairs",
        "Director",
        "Director of",
        "Director,",
        "Director General",
        "Principal Medical Officer",
        "Principal",
        "Treasurer",
        "Resident Auditor",
        "Librarian",
        # "IT Manager",
    )
 
    # ROLE_PATTERN = re.compile(
    #     r"\b("
    #     r"Vice[- ]?Chancellor|"
    #     r"Pro[- ]?Vice[- ]?Chancellor|"
    #     r"Principal|"
    #     r"Dean|"
    #     r"Chairman|"
    #     r"Chairperson|"
    #     r"Co[- ]?Chairperson|"
    #     r"Controller of Examinations|"
    #     r"Librarian|"

    #     r"Associate Professor|"
    #     r"Associate Professors|"
 
    #     r"Assistant Professor|"
    #     r"Assistant Professors|"

    #     r"Professor|"
    #     r"Professors|"

    #     r"Lecturer|"
    #     r"Lecturers|"

    #     r"IT Manager|"
    #     r"IT Managers|"

    #     r"Lab Engineer|"
    #     r"Lab Engineers|"
    #     r"Librarian|"
    #     r"Registrar|"
    #     r"Resident Auditor|"
    #     r"Deputy Registrar|"
    #     r"Additional Registrar|"
    #     r"Additional Controller of Examinations|"
    #     r"Additional Controller Student Affairs|"
    #     r"Principal Medical Officer"

    #     r")\b",
    #     re.IGNORECASE,
    # )

    ROLE_PATTERN = re.compile(
        r"\b("
        r"Vice[- ]?Chancellor|"
        r"Pro[- ]?Vice[- ]?Chancellor|"
        r"Senior Manager(?:\s*,\s*[A-Za-z &(),/\-]+)?|"
        r"Deputy Manager(?:\s*,\s*[A-Za-z &(),/\-]+)?|"
        r"Manager Instrumentation(?:\s*,\s*[A-Za-z &(),/\-]+)?|"
        r"Instrumentation Engineer(?:\s*,\s*[A-Za-z &(),/\-]+)?|"
        r"Cooperative Teacher|"
        r"Sr\.?\s+Laboratory Engineer|"
        r"Laboratory Engineer|"
        r"Lab Engineers?|"
        r"Adjunct Faculty|"
        r"Additional Controller of Examinations|"
        r"Additional Controller Student Affairs|"
        r"Controller of Examinations|"
        r"Controller Student Affairs|"
        r"Additional Registrar|"
        r"Deputy Registrar|"
        r"Registrar|"
        r"Resident Auditor|"
        r"Principal Medical Officer|"
        r"Principal(?:\s*,\s*[A-Za-z &(),/\-]+)?|"
        r"Principal Laboratory Engineer|"
        r"Director General|"
        r"Director of [A-Za-z &(),/-]+|"
        r"Director|"
        r"Librarian|"
        r"IT Manager|"
        r"IT Managers|"
        r"Chairman|"
        r"Chairperson|"
        r"Co[- ]?Chairperson|"
        r"Dean Faculty of [A-Za-z &(),/\-]+(?=\s*$)|"
        r"Dean|"
        r"Treasurer|"
        r"Associate Professor|"
        r"Associate Professors|"
        r"Assistant Professors|"
        r"Assistant Professor|"
        r"Professor|"
        r"Professors|" 
        r"Lecturer|"
        r"Lecturers|"
        r"Incharge|"
        r"Manager"
        # r")\b",
        r")(?=\s|$)",
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
        "principal",
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

    # QUALIFICATION_START = re.compile(
    #     r"""
    #     ^
    #     (
    #         B\.?E\.?|
    #         B\.?Sc\.?|
    #         B\.?S\.?|
    #         B\.?Arch\.?|
    #         B\.?Com\.?|
    #         B\.?A\.?|
    #         MBBS|
    #         Pharm\.?D|
    #         LL\.?B|
    #         M\.?E\.?|
    #         M\.?Engg\.?|
    #         M\.?Sc\.?|
    #         M\.?S\.?|
    #         MCS|
    #         MEM|
    #         MBA|
    #         MPA|
    #         MHRM|
    #         M\.?Phil\.?|
    #         Ph\.?D\.?|
    #         Postdoc|
    #         C\.?Eng|
    #         FIMechE|
    #         MIEEE|
    #         MIEE|
    #         MCPS|
    #         FCPS
    #     )
    #     """,
    #     re.I | re.X,
    # )

    QUALIFICATION_START = re.compile(
        r"""
        ^
        (
            B\.?E\.?|
            B\.?S\.?|
            B\.?Sc\.?|
            B\.?A\.?|
            B\.?Com\.?|
            B\.?Arch\.?|
            B\.?Ed\.?|
            B\.?BA|
            B\.?S\.?\s*\(?[A-Za-z]{0,10}\)?|
            BBA|
            BSCS|
            BSIT|
            BCIT|
            BSSE|
            MBBS|
            BDS|
            Pharm\.?D|
            D\.?Pharm|
            LLB|
            LL\.?B|
            LLM|
            M\.?E\.?|
            M\.?Engg\.?|
            M\.?Sc\.?|
            M\.?S\.?|
            M\.?A\.?|
            M\.?Com\.?|
            M\.?Arch\.?|
            M\.?Ed\.?|
            M\.?Phil\.?|
            MCS|
            MCA|
            MBA|
            MPA|
            MHRM|
            MEM|
            MSCS|
            MSIT|
            MSSE|
            Ph\.?D\.?|
            DPhil|
            Postdoc|
            C\.?Eng\.?|
            PE|
            FIMechE|
            MIEEE|
            MIEE|
            MCPS|
            FCPS|
            FRCS|
            PMP|
            CFA|
            ACCA|
            CA|
            ICMA|
            BCS|
            B\.?Com
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )
 
    # Section/department headings in the reconstructed text look like
    # "2.2 Teaching Departments" or "2.2.1 Department of Civil
    # Engineering". Qualification/name lines never start this way once
    # normalized (they either have no leading number, or a bare
    # "N." list marker, which this pattern excludes since it requires
    # nested numbering "N.N" and a body of at least a few letters).
    HEADING_PATTERN = re.compile(
        r"^\d+(?:\.\d+)+\s+[A-Z][A-Za-z&,()'\- ]{2,90}$"
    )
 
    def extract(
        self,
        layout_document: dict,
        faculty_pages: set[int] | None = None,
    ) -> list[PersonRecord]:
        """
        Parameters
        ----------
        pages:
            Layout.json page entries already filtered down to the
            relevant range by the caller, each shaped like
            {"page_number": int, "reconstructed_text": str}.
        """
 
        records: list[PersonRecord] = []
 
        pages = (
            layout_document["pages"]
            if isinstance(layout_document, dict)
            else layout_document
        )
        current_department = None
        current_role = None

        for page in pages:

            page_number = page["page_number"]

            if faculty_pages is not None and page_number not in faculty_pages:
                current_department = None

 
            page_number = page["page_number"]
 
            text = page.get("reconstructed_text", "") or ""
 
            lines = text.splitlines()
 
            page_records, current_department, current_role = (
                self._extract_people(
                    lines=lines,
                    page_number=page_number,
                    current_department=current_department,
                    current_role=current_role,
                    allow_department=(
                        faculty_pages is None
                        or page_number in faculty_pages
                    ),
                )
            )

            records.extend(page_records)

        # for record in records:
        #     print(record)
 
        return self._deduplicate(records)

    def _get_page_lines(
        self,
        page: dict,
    ) -> list[str]:
        """
        Build reading-order lines from layout items.

        When a page has multiple columns, each column is processed
        independently from left to right. Pages without layout items
        fall back to reconstructed_text.
        """

        layout_items = page.get("layout_items") or []

        if not layout_items:
            text = page.get("reconstructed_text", "") or ""
            return text.splitlines()

        items = [
            item
            for item in layout_items
            if str(item.get("text", "")).strip()
        ]

        if not items:
            return []

        x_values = sorted(
            float(item.get("x", 0))
            for item in items
        )

        if len(x_values) < 4:
            columns = [items]
        else:
            gaps = [
                x_values[index + 1] - x_values[index]
                for index in range(len(x_values) - 1)
            ]

            largest_gap_index = max(
                range(len(gaps)),
                key=gaps.__getitem__,
            )

            largest_gap = gaps[largest_gap_index]
            x_range = x_values[-1] - x_values[0]

            # Detect a genuine column separation dynamically.
            if (
                x_range > 0
                and largest_gap > x_range * 0.20
            ):
                split_x = (
                    x_values[largest_gap_index]
                    + largest_gap / 2
                )

                left = [
                    item
                    for item in items
                    if float(item.get("x", 0)) < split_x
                ]

                right = [
                    item
                    for item in items
                    if float(item.get("x", 0)) >= split_x
                ]

                columns = [
                    column
                    for column in (left, right)
                    if column
                ]
            else:
                columns = [items]

        lines: list[str] = []

        for column in columns:
            column.sort(
                key=lambda item: (
                    float(item.get("top", item.get("y", 0))),
                    float(item.get("x", 0)),
                )
            )

            for item in column:
                lines.append(
                    str(item.get("text", "")).strip()
                )

        return lines
 
    def _deduplicate(
        self,
        records: list[PersonRecord],
    ) -> list[PersonRecord]:
 
        # merged: dict[str, PersonRecord] = {}
        merged: dict[tuple[str, str, str], PersonRecord] = {}
 
        for record in records:
 
            # key = re.sub(
            #     r"\s+",
            #     " ",
            #     record.name.lower(),
            # ).strip()
            normalized_name = re.sub(
                r"\s+",
                " ",
                record.name.lower(),
            ).strip()

            normalized_role = re.sub(
                r"\s+",
                " ",
                (record.role or "").lower(),
            ).strip()

            normalized_department = re.sub(
                r"\s+",
                " ",
                (record.department or "").lower(),
            ).strip()

            key = (
                normalized_name,
                normalized_role,
                normalized_department,
            )
 
            existing = merged.get(key)
 
            if existing is None:
                merged[key] = record
                continue
 
            if existing.role is None and record.role:
                existing.role = record.role
 
            if existing.department is None and record.department:
                existing.department = record.department
 
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
 
        text = re.sub(r"^\d+\.\s*", "", text)
        text = re.sub(r"^[ivxlcdmIVXLCDM]+\)\s*", "", text)
        text = re.sub(r"^[A-Za-z]\)\s*", "", text)
 
        text = re.sub(r"\s+", " ", text)
        text = text.strip(" ,;:-.")
 
        return text.strip()
 
    def _extract_department(
        self,
        heading: str,
    ) -> str | None:
        """
        Extract a department/faculty name from the current
        block heading (the nearest preceding numbered heading
        line, e.g. "2.2.1 Department of Civil Engineering").
        """
 
        heading = heading.strip()
 
        if not heading:
            return None
 
        keywords = (
            "department",
            "faculty",
            "school",
            "institute",
            "centre",
            "center",
        )
 
        if any(k in heading.lower() for k in keywords):
            return heading
 
        return None
 
    def _looks_like_qualification(
        self,
        line: str,
    ) -> bool:
 
        text = line.strip()
 
        if not text:
            return False

        if self.QUALIFICATION_START.match(text):
            return True
 
        if text.isdigit():
            return False
 
        if re.fullmatch(r"\d+(?:\.\d+)?", text):
            return False
 
        if self.TITLE_PATTERN.search(text):
            return False
 
        if self.ROLE_PATTERN.search(text):
            return False
 
        if len(text) > 120:
            return False
 
        if text.endswith(":"):
            return False
 
        if re.match(r"^\d+(\.\d+)*", text):
            return False
 
        score = 0
 
        if "," in text:
            score += 1
 
        if "(" in text or ")" in text:
            score += 1
 
        if any(ch.isdigit() for ch in text):
            score += 1
 
        if len(text.split()) <= 10:
            score += 1
 
        institution_words = (
            "university",
            "institute",
            "college",
            "school",
        )
 
        if any(word in text.lower() for word in institution_words):
            score += 2
 
        return score >= 3
 
    def _looks_like_person_name(
        self,
        text: str,
    ) -> bool:
 
        text = text.strip()
 
        if not text:
            return False
 
        if any(ch.isdigit() for ch in text):
            return False
 
        if len(text) > 80:
            return False
 
        if len(text.split()) > 8:
            return False
 
        if text.count(",") > 1:
            return False
 
        if ";" in text:
            return False
 
        letters = "".join(ch for ch in text if ch.isalpha())
 
        if letters and letters == letters.upper():
            return False
 
        if self._looks_like_qualification(text):
            return False
 
        if re.match(
            r"^(B\.?E\.?|B\.?S\.?|M\.?E\.?|M\.?S\.?|M\.?Engg\.?|MBA|M\.?Phil\.?|Ph\.?D)",
            text,
            re.IGNORECASE,
        ):
            return False
 
        institution_words = (
            "university",
            "institute",
            "college",
            "school",
            "faculty",
            "department",
        )
 
        if any(word in text.lower() for word in institution_words):
            return False
 
        if self.TITLE_PATTERN.search(text):
            return True
 
        return False
 
    def _is_non_person(
        self,
        text: str,
    ) -> bool:
 
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
 
        return any(word in text for word in blocked)
 
 
    def _extract_people(
        self,
        *,
        lines: list[str],
        page_number: int,
        current_department: str | None,
        current_role: str | None,
        allow_department: bool,
    ) -> tuple[
        list[PersonRecord],
        str | None,
        str | None,
    ]:
        

        records = []

        current_person = None
        pending_role = None

        for raw_line in lines:

            line = raw_line.strip()
            if (
                line.isdigit()
                or line.startswith("PROSPECTUS")
                or line == "OF ENGINEERING & TECHNOLOGY"
                or line.startswith("www.")
            ):
                continue

            normalized_line = self._normalize_person_name(line)


            if not line:
                continue

            # department_match = self.DEPARTMENT_PATTERN.match(line)
            # if department_match:

            #     current_department = department_match.group("department").strip()

            #     current_person = None
            #     continue

            if allow_department:
                department_match = self.DEPARTMENT_PATTERN.match(line)

                if department_match:
                    current_department = department_match.group("department").strip()

                    current_person = None
                    continue

            role_match = self.ROLE_PATTERN.match(line)

            if role_match:

                matched_role = role_match.group(0).strip()

                if line.startswith(self.FULL_LINE_ROLES):

                    current_role = line.strip()
                    pending_role = None
                    current_department = None

                else:

                    pending_role = matched_role

                current_person = None
                continue


            # person_match = self.PERSON_PATTERN.search(line)

            # role_match = self.ROLE_PATTERN.match(line)

            # if role_match:
            #     matched_role = role_match.group(0).strip()

            #     if line.startswith(self.FULL_LINE_ROLES):
            #         current_role = line[:role_match.end()].strip()
            #         pending_role = None
            #     else:
            #         pending_role = self.GROUP_ROLE_MAP.get(
            #             matched_role.lower(),
            #             matched_role,
            #         )

            #     current_person = None

            #     # Keep any person appearing after the role on the same line.
            #     remainder = line[role_match.end():].strip()
            #     remainder = re.sub(
            #         r"^\d+\.\s*",
            #         "",
            #         remainder,
            #     )
            
            #     if remainder:
            #         line = remainder
            #     else:
            #         continue

            person_match = self.PERSON_PATTERN.search(line)
            # person_matches = list(
            #     self.PERSON_PATTERN.finditer(line)
            # )

            # person_match = (
            #     person_matches[0]
            #     if person_matches
            #     else None
            # )
            if person_match:

                name = self._normalize_person_name(
                        person_match.group(0)
                    )
                # name = re.split(
                #     r"""
                #     \b(
                #         B\.?E\.?|
                #         B\.?Sc\.?|
                #         B\.?Arch\.?|
                #         M\.?E\.?|
                #         M\.?Engg\.?|
                #         M\.?Sc\.?|
                #         M\.?S\.?|
                #         MEM|
                #         MBA|
                #         MCS|
                #         M\.?Phil\.?|
                #         Ph\.?D\.?
                #     )\b
                #     """,
                #     name,
                #     maxsplit=1,
                #     flags=re.I | re.X,
                # )[0].strip()

                
                if pending_role:

                    current_role = self.GROUP_ROLE_MAP.get(
                        pending_role.lower(),
                        pending_role,
                    )

                    pending_role = None

                if current_role is None:
                    continue

                current_person = PersonRecord(
                    name=name,
                    role=current_role,
                    department=current_department,
                    qualifications=[],
                    source_page=page_number,
                )

                if not name.strip():
                    print(
                        "[PERSON DEBUG] EMPTY NAME",
                        {
                            "line": repr(line),
                            "person_match": (
                                person_match.group(0)
                                if person_match
                                else None
                            ),
                            "role": current_role,
                            "page": page_number,
                        },
                    )
                    continue

                records.append(current_person)
                continue

            if (
                current_person is not None
                and self.QUALIFICATION_START.match(line)
            ):

                current_person.qualifications.append(line)

                continue

            # if (
            #     current_person is not None
            #     and self._looks_like_qualification(line)
            # ):

            #     current_person.qualifications.append(line)


        return (
            records,
            current_department,
            current_role,
        )