import re
from collections import defaultdict
from src.processing.prospectus.admission_category_record import (
    AdmissionCategoryRecord,
)


class AdmissionCategoryExtractor:

    CATEGORY_PATTERN = re.compile(
        r"""
        ^
        (R|SF)              # Prefix
        \s*-?\s*            # Optional dash
        \d+                 # Main number
        (?:                 # Optional subcategory
            \s*
            [\(\[]?
            [a-z]
            [\)\].]?
        )?
        $
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    CODE_PATTERN = re.compile(
        r"""
        ^
        (?P<code>
            (?:R|SF)
            \s*-\s*
            \d+
            (?:\([a-z]\))?
        )
        \s+
        (?P<description>[A-Z].+)
        $
        """,
        re.I | re.X,
    )

    NOISE_PATTERNS = (

        re.compile(r"^PROSPECTUS", re.I),

        re.compile(r"^UNDERGRADUATE$", re.I),

        re.compile(r"^NED UNIVERSITY", re.I),

        re.compile(r"^OF ENGINEERING", re.I),

        re.compile(r"^KARACHI$", re.I),

        re.compile(r"^CARACHI$", re.I),

        re.compile(r"^www\.", re.I),

        re.compile(r"^NEDUETOfficial$", re.I),

        re.compile(
            r"^\d+\s*(?:_?\s*www\.neduet\.edu\.pk)?$",
            re.I,
        )
    )

    STOP_PATTERN = re.compile(
        r"""
        ^
        \d+\.\d+
        \s*
        \(
            [ivxIVX]+
        \)
        """,
        re.X,
    )


    def _extract_from_text(
        self,
        *,
        text: str,
        page_number: int,
    ) -> list[AdmissionCategoryRecord]:

        records = []

        current_code = None
        current_page = None
        description_parts = []

        def flush():

            nonlocal current_code
            nonlocal current_page
            nonlocal description_parts

            if current_code is None:
                return

            scheme = (
                "Regular"
                if current_code.startswith("R-")
                else "Self Finance"
            )

            records.append(
                AdmissionCategoryRecord(
                    code=current_code,
                    scheme=scheme,
                    description=" ".join(
                        description_parts
                    ).strip(),
                    source_page=current_page,
                )
            )

            current_code = None
            current_page = None
            description_parts = []

        for raw_line in text.splitlines():

            line = raw_line.strip()

            if not line:
                continue

            # Skip OCR/page noise
            if any(
                pattern.match(line)
                for pattern in self.NOISE_PATTERNS
            ):
                continue

            if self.STOP_PATTERN.match(line):

                flush()

                continue
            
            match = self.CODE_PATTERN.match(line)
            
            if match:
            
                flush()

            
                current_code = (
                    match.group("code")
                    .replace(" ", "")
                    .upper()
                )
            
                current_page = page_number
            
                description_parts = [
                    match.group("description").strip()
                ]
            
                continue
            
            if current_code is not None:
            
                description_parts.append(line)

        flush()

        return records
    
    def _repair_missing_codes(
        self,
        records: list[AdmissionCategoryRecord],
    ) -> list[AdmissionCategoryRecord]:

        repaired = []

        i = 0

        while i < len(records):

            current = records[i]

            if (
                i + 2 < len(records)
                and current.code is not None
                and records[i + 1].code is None
                and records[i + 2].code is not None
            ):

                next_record = records[i + 2]
            # Case 1:
            # Same numeric category, missing alphabetical code.
            # Example:
            # R-2(b) -> R-2(d)
            # becomes
            # R-2(b), R-2(c), R-2(d)
                m1 = re.match(
                    r"([A-Z]+)-(\d+)\(([a-z])\)",
                    current.code,
                    re.I,
                )

                m2 = re.match(
                    r"([A-Z]+)-(\d+)\(([a-z])\)",
                    next_record.code,
                    re.I,
                )

                if (
                    m1
                    and m2
                    and m1.group(1) == m2.group(1)
                    and m1.group(2) == m2.group(2)
                ):

                    expected = chr(ord(m1.group(3)) + 1)

                    if m2.group(3).lower() != chr(ord(expected) + 1):
                        repaired.append(current)
                        i += 1
                        continue
                    
                    repaired.append(current)

                    new_code = (
                        f"{m1.group(1)}-{m1.group(2)}({expected})"
                    )

                    repaired.append(
                        AdmissionCategoryRecord(
                            code=new_code,
                            scheme=(
                                "Regular"
                                if new_code.startswith("R-")
                                else "Self Finance"
                            ),
                            description=records[i + 1].description,
                            source_page=records[i + 1].source_page,
                        )
                    )

                    repaired.append(next_record)

                    i += 3
                    continue
            # Case 2:
            # Number increments and next starts at (b)
            # Example:
            # SF-8
            # placeholder
            # SF-9(b) becomes:
            # SF-8
            # SF-9(a)
            # SF-9(b)
        
                m3 = re.match(
                    r"([A-Z]+)-(\d+)$",
                    current.code,
                    re.I,
                )

                if (
                    m3
                    and m2
                    and m3.group(1) == m2.group(1)
                    and int(m2.group(2)) == int(m3.group(2)) + 1
                    and m2.group(3).lower() == "b"
                ):

                    repaired.append(current)

                    new_code = (
                        f"{m2.group(1)}-{m2.group(2)}(a)"
                    )

                    repaired.append(
                        AdmissionCategoryRecord(
                            code=new_code,
                            scheme=(
                                "Regular"
                                if new_code.startswith("R-")
                                else "Self Finance"
                            ),
                            description=records[i + 1].description,
                            source_page=records[i + 1].source_page,
                        )
                    )

                    repaired.append(next_record)

                    i += 3
                    continue

            repaired.append(current)
            i += 1

        return repaired
    
    def extract(
        self,
        *,
        layout_document: dict,
        pages: set[int],
    ) -> list[AdmissionCategoryRecord]:

        records: list[AdmissionCategoryRecord] = []

        for page in layout_document:

            if page["page_number"] not in pages:
                continue

            page_number = page["page_number"]

            text = page.get(
                "reconstructed_text",
                "",
            )

            records.extend(
                self._extract_from_text(
                    text=text,
                    page_number=page_number,
                )
            )

        # return self._repair_missing_codes(records)
        return records