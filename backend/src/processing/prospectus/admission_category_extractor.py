import re
from collections import defaultdict
from src.processing.prospectus.admission_category_record import (
    AdmissionCategoryRecord,
)
from dataclasses import dataclass


@dataclass(slots=True)
class CategoryBlock:
    items: list[dict]

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

    # def _ordered_lines_from_layout(
    #     self,
    #     layout_items,
    # ) -> list[str]:
    #     """
    #     Reconstruct reading order from OCR layout.

    #     Items are grouped into horizontal rows using their
    #     vertical position. Each row is then read left-to-right.
    #     """

    #     if not layout_items:
    #         return []

    #     items = [
    #         item
    #         for item in layout_items
    #         if item.get("text", "").strip()
    #     ]

    #     if not items:
    #         return []

    #     ROW_THRESHOLD = 12

    #     row_anchors: list[float] = []
    #     rows: dict[float, list[dict]] = defaultdict(list)
    # # Group nearby TOP coordinates into one logical row.
    
    #     for item in sorted(items, key=lambda i: i["top"]):

    #         top = item["top"]

    #         matched = False

    #         for anchor in row_anchors:

    #             if abs(anchor - top) <= ROW_THRESHOLD:
    #                 rows[anchor].append(item)
    #                 matched = True
    #                 break

    #         if not matched:
    #             row_anchors.append(top)
    #             rows[top].append(item)

    #     ordered_lines: list[str] = []
    # # Read rows from top to bottom.
    # # Within each row read left to right.
    #     for anchor in sorted(row_anchors):

    #         row = sorted(
    #             rows[anchor],
    #             key=lambda item: item["x"],
    #         )

    #         for item in row:

    #             text = item["text"].strip()

    #             if text:
    #                 ordered_lines.append(text)

    #     return ordered_lines
    def _category_items(
        self,
        layout_items,
    ) -> list[dict]:
        """
        Return all OCR layout items that represent
        admission category codes (R-1(a), SF-2, etc.).
        """
        codes = []

        for item in layout_items:

            text = (
                item.get("text", "")
                .replace(" ", "")
                .replace("—", "-")
                .replace("–", "-")
                .replace("−", "-")
                .strip()
            )

            text = re.sub(
                r"[,:;]$",
                "",
                text,
            )

            match = self.CATEGORY_PATTERN.fullmatch(text)

            if match:
                item = dict(item)
                item["text"] = text
                codes.append(item)

        return sorted(
            codes,
            key=lambda item: (
                item["top"],
                item["x"],
            ),
        )
    
    def _split_columns(
        self,
        layout_items: list[dict],
    ) -> tuple[list[dict], list[dict]]:

        left = []
        right = []

        for item in layout_items:

            if item["x"] < 400:
                left.append(item)
            else:
                right.append(item)

        left.sort(
            key=lambda item: (
                item["top"],
                item["x"],
            )
        )

        right.sort(
            key=lambda item: (
                item["top"],
                item["x"],
            )
        )

        return left, right
    
    def _build_category_blocks(
        self,
        column_items: list[dict],
    ) -> list[CategoryBlock]:

        blocks: list[CategoryBlock] = []

        current: list[dict] = []

        previous_bottom = None
        previous_height = None

        category_items = self._category_items(column_items)

        category_keys = {
            (
                item["top"],
                item["x"],
            )

            for item in category_items
        }

        for item in column_items:

            is_category = (
                item["top"],
                item["x"],
            ) in category_keys

            top = item.get("top")
            bottom = item.get("bottom")
            height = item.get("height")

            split = False
    # Rule 1: large visual gap
            if (
                previous_bottom is not None
                and top is not None
                and previous_height is not None
            ):

                gap = top - previous_bottom

                if gap > previous_height * 1.5:
                    split = True
    # Rule 2: new category code
            if is_category and current:
                split = True

            if split:

                blocks.append(
                    CategoryBlock(
                        items=current,
                    )
                )

                current = []

            current.append(item)

            previous_bottom = bottom
            previous_height = height

        if current:

            blocks.append(
                CategoryBlock(
                    items=current,
                )
            )

        return blocks

    def _extract_column_records(
        self,
        *,
        column_items: list[dict],
        page_number: int,
        heading: str,
    ) -> list[AdmissionCategoryRecord]:

        records: list[AdmissionCategoryRecord] = []

        blocks = self._build_category_blocks(
            column_items,
        )

        for block in blocks:

            code = None

            source_lines: list[str] = []
            description_lines: list[str] = []

            for item in block.items:

                text = item.get(
                    "text",
                    "",
                ).strip()

                if not text:
                    continue

                normalized = (
                    text.replace(" ", "")
                        .replace("—", "-")
                        .replace("–", "-")
                        .replace("−", "-")
                        .strip()
                )

                normalized = re.sub(
                    r"[,.;:]$",
                    "",
                    normalized,
                )

                if (
                    code in (None, "__PLACEHOLDER__")
                    and self.CATEGORY_PATTERN.match(normalized)
                ):
                    code = normalized
                    source_lines.append(text)
                    continue

                # Missing category marker:
                # OCR sometimes drops R-1(f), R-2(c), etc.
                # If a new paragraph begins after a completed sentence,
                # finish the previous record and start a placeholder record.
                m = re.match(
                    r"(R|SF)-(\d+)\(([a-z])\)",
                    code or "",
                    re.I,
                )

                allow_placeholder = (
                    m is not None
                    and m.group(3).lower() in {"b", "e", "h"}
                )
                if (
                    allow_placeholder
                    and description_lines
                    and description_lines[-1].rstrip().endswith(".")
                    and text.startswith("Candidates")
                ):

                    records.append(
                        AdmissionCategoryRecord(
                            code=code,
                            scheme=None,
                            description=" ".join(description_lines).strip(),
                            source_page=page_number,
                            source_heading=heading,
                            source_text="\n".join(source_lines),
                        )
                    )


                    # Keep collecting the placeholder record.

                    code = "__PLACEHOLDER__"

                    source_lines = [text]
                    description_lines = [text]

                    continue

                source_lines.append(text)
                description_lines.append(text)

            if code is None:
                continue

            if code == "__PLACEHOLDER__":
                records.append(
                    AdmissionCategoryRecord(
                        code=None,
                        scheme=None,
                        description=" ".join(description_lines).strip(),
                        source_page=page_number,
                        source_heading=heading,
                        source_text="\n".join(source_lines),
                    )
                )
                continue

            records.append(
                AdmissionCategoryRecord(
                    code=code,
                    scheme=None,
                    description=" ".join(
                        description_lines
                    ).strip(),
                    source_page=page_number,
                    source_heading=heading,
                    source_text="\n".join(
                        source_lines
                    ),
                )
            )

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

                    repaired.append(
                        AdmissionCategoryRecord(
                            code=f"{m1.group(1)}-{m1.group(2)}({expected})",
                            scheme=None,
                            description=records[i + 1].description,
                            source_page=records[i + 1].source_page,
                            source_heading=records[i + 1].source_heading,
                            source_text=records[i + 1].source_text,
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

                    repaired.append(
                        AdmissionCategoryRecord(
                            code=f"{m2.group(1)}-{m2.group(2)}(a)",
                            scheme=None,
                            description=records[i + 1].description,
                            source_page=records[i + 1].source_page,
                            source_heading=records[i + 1].source_heading,
                            source_text=records[i + 1].source_text,
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
        pages: list[dict],
    ) -> list[AdmissionCategoryRecord]:

        records: list[AdmissionCategoryRecord] = []

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
                    ).strip()
                )

                records.extend(
                    self._extract_section(
                        section=section,
                        page_number=page_number,
                        heading=heading,
                    )
                )

        return self._repair_missing_codes(records)
    
    def _extract_section(
        self,
        *,
        section: dict,
        page_number: int,
        heading: str,
    ) -> list[AdmissionCategoryRecord]:

        records: list[AdmissionCategoryRecord] = []

        current_code: str | None = None
        current_description: list[str] = []
        current_source: list[str] = []

        layout_items = section.get(
            "layout_items",
            [],
        )

        if layout_items:

            print(
                f"\nPAGE {page_number}"
            )
            print(
                f"SECTION: {heading}"
            )
        print(
            "layout items:",
            len(layout_items),
        )

        left_items, right_items = self._split_columns(
            layout_items,
        )

        records.extend(
            self._extract_column_records(
                column_items=left_items,
                page_number=page_number,
                heading=heading,
            )
        )

        records.extend(
            self._extract_column_records(
                column_items=right_items,
                page_number=page_number,
                heading=heading,
            )
        )

        return records