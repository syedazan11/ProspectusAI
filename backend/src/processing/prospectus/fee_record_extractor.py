import re

from src.processing.prospectus.fee_record import FeeRecord

class FeeRecordExtractor:
    """
    Extracts structured fee records from
    cleaned prospectus sections.
    """

    FEE_HEADING_PATTERN = re.compile(
        r"\b("
        r"fee|fees|"
        r"charge|charges|"
        r"deposit|deposits|"
        r"refund|refunds|"
        r"scholarship|scholarships"
        r")\b",
        re.IGNORECASE,
    )

    AMOUNT_PATTERN = re.compile(
        r"""
        Rs\.?\s*
        (?P<amount>
            \d[\d,]*(?:\.\d+)?
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )

    # @staticmethod
    # def _build_fee_page_streams(
    #     page: dict,
    # ) -> list[str]:
    #     """
    #     Reconstruct the major page columns while preserving
    #     horizontally aligned label/amount pairs.

    #     The page coordinate system is used directly. Items are
    #     first divided into major left/right regions, then grouped
    #     into horizontal rows inside each region.
    #     """

    #     layout_items = page.get(
    #         "layout_items",
    #         [],
    #     )

    #     items = [
    #         item
    #         for item in layout_items
    #         if (
    #             isinstance(item, dict)
    #             and str(item.get("text", "")).strip()
    #             and isinstance(item.get("x"), (int, float))
    #             and isinstance(item.get("top"), (int, float))
    #             and isinstance(item.get("bottom"), (int, float))
    #         )
    #     ]

    #     if not items:
    #         text = str(
    #             page.get(
    #                 "reconstructed_text",
    #                 page.get("text", ""),
    #             )
    #             or ""
    #         ).strip()

    #         return [text] if text else []

    #     # The rendered OCR coordinate space is approximately
    #     # twice the original PDF width. The two major content
    #     # regions are separated around the page midpoint.
    #     page_width = 1224.0

    #     boundary = page_width / 2.0

    #     left = [
    #         item
    #         for item in items
    #         if float(item["x"]) < boundary
    #     ]

    #     right = [
    #         item
    #         for item in items
    #         if float(item["x"]) >= boundary
    #     ]

    #     def build_rows(
    #         column: list[dict],
    #     ) -> str:

    #         if not column:
    #             return ""

    #         column = sorted(
    #             column,
    #             key=lambda item: (
    #                 float(item["top"]),
    #                 float(item["x"]),
    #             ),
    #         )

    #         rows: list[list[dict]] = []

    #         for item in column:

    #             top = float(item["top"])
    #             bottom = float(item["bottom"])
    #             height = max(
    #                 bottom - top,
    #                 1.0,
    #             )

    #             best_row = None
    #             best_distance = None

    #         for item in column:

    #             top = float(item["top"])
    #             bottom = float(item["bottom"])
    #             height = max(
    #                 bottom - top,
    #                 1.0,
    #             )

    #             best_row = None
    #             best_distance = None

    #             for row in rows:

    #                 row_top = min(
    #                     float(existing["top"])
    #                     for existing in row
    #                 )

    #                 row_bottom = max(
    #                     float(existing["bottom"])
    #                     for existing in row
    #                 )

    #                 row_height = max(
    #                     row_bottom - row_top,
    #                     1.0,
    #                 )

    #                 center = (
    #                     top + bottom
    #                 ) / 2.0

    #                 row_center = sum(
    #                     (
    #                         float(existing["top"])
    #                         + float(existing["bottom"])
    #                     ) / 2.0
    #                     for existing in row
    #                 ) / len(row)

    #                 tolerance = max(
    #                     7.0,
    #                     min(
    #                         height,
    #                         row_height,
    #                     ) * 0.30,
    #                 )

    #                 center_distance = abs(
    #                     center - row_center
    #                 )

    #                 if center_distance <= tolerance:

    #                     if (
    #                         best_distance is None
    #                         or center_distance < best_distance
    #                     ):
    #                         best_row = row
    #                         best_distance = center_distance

    #             if best_row is None:
    #                 rows.append([item])
    #             else:
    #                 best_row.append(item)

    #         output = []

    #         for row in rows:

    #             row.sort(
    #                 key=lambda item: float(item["x"])
    #             )

    #             parts = [
    #                 str(item["text"]).strip()
    #                 for item in row
    #                 if str(item["text"]).strip()
    #             ]

    #             if parts:
    #                 output.append(
    #                     " ".join(parts)
    #                 )

    #         return "\n".join(output).strip()

    #     streams = []

    #     left_text = build_rows(left)
    #     right_text = build_rows(right)

    #     if left_text:
    #         streams.append(left_text)

    #     if right_text:
    #         streams.append(right_text)

    #     return streams

    @staticmethod
    def _build_fee_page_streams(
        page: dict,
    ) -> list[str]:
        """
        Reconstruct the two major page regions while preserving
        horizontally aligned label/amount pairs.

        The OCR coordinate space is used directly. Items are
        assigned to the left or right half of the page, then
        grouped into horizontal rows using vertical center
        alignment.
        """

        layout_items = page.get(
            "layout_items",
            [],
        ) or []

        items = [
            item
            for item in layout_items
            if (
                isinstance(item, dict)
                and str(item.get("text", "")).strip()
                and isinstance(
                    item.get("x"),
                    (int, float),
                )
                and isinstance(
                    item.get("top"),
                    (int, float),
                )
                and isinstance(
                    item.get("bottom"),
                    (int, float),
                )
            )
        ]

        if not items:
            text = str(
                page.get(
                    "reconstructed_text",
                    page.get("text", ""),
                )
                or ""
            ).strip()

            return [text] if text else []

        # RapidOCR renders the A4 page at approximately
        # 1224 x 1584 when render_scale=2.0.
        #
        # The actual two major page regions are separated
        # around the horizontal midpoint.
        page_width = max(
            float(item["x"])
            for item in items
        )

        boundary = page_width / 2.0

        left = []
        right = []

        for item in items:

            if float(item["x"]) < boundary:
                left.append(item)
            else:
                right.append(item)

        def build_rows(
            column: list[dict],
        ) -> str:

            if not column:
                return ""

            ordered = sorted(
                column,
                key=lambda item: (
                    (
                        float(item["top"])
                        + float(item["bottom"])
                    ) / 2.0,
                    float(item["x"]),
                ),
            )

            rows: list[list[dict]] = []

            for item in ordered:

                center = (
                    float(item["top"])
                    + float(item["bottom"])
                ) / 2.0

                height = max(
                    float(item["bottom"])
                    - float(item["top"]),
                    1.0,
                )

                best_row = None
                best_distance = None

                for row in rows:

                    row_center = sum(
                        (
                            float(existing["top"])
                            + float(existing["bottom"])
                        ) / 2.0
                        for existing in row
                    ) / len(row)

                    row_height = max(
                        max(
                            float(existing["bottom"])
                            for existing in row
                        )
                        -
                        min(
                            float(existing["top"])
                            for existing in row
                        ),
                        1.0,
                    )

                    tolerance = max(
                        6.0,
                        min(
                            height,
                            row_height,
                        ) * 0.35,
                    )

                    distance = abs(
                        center - row_center
                    )

                    if distance <= tolerance:

                        if (
                            best_distance is None
                            or distance < best_distance
                        ):
                            best_row = row
                            best_distance = distance

                if best_row is None:
                    rows.append([item])
                else:
                    best_row.append(item)

            output = []

            for row in rows:

                row.sort(
                    key=lambda item: float(
                        item["x"]
                    )
                )

                parts = [
                    str(item["text"]).strip()
                    for item in row
                    if str(item["text"]).strip()
                ]

                if parts:
                    output.append(
                        " ".join(parts)
                    )

            return "\n".join(output).strip()

        streams = []

        left_text = build_rows(left)
        right_text = build_rows(right)

        if left_text:
            streams.append(left_text)

        if right_text:
            streams.append(right_text)

        return streams

    def extract(
        self,
        layout_document: dict | list,
        pages: list[dict],
    ) -> list[FeeRecord]:

        records: list[FeeRecord] = []

        layout_pages = self._get_layout_pages(
            layout_document,
            pages,
        )

        if not layout_pages:
            return records

        for page in layout_pages:

            page_number = page.get(
                "page_number"
            )

            # reconstructed_text = str(
            #     page.get(
            #         "reconstructed_text",
            #         page.get("text", ""),
            #     )
            #     or ""
            # ).strip()

            # if not reconstructed_text:
            #     continue

            # page_streams = [
            #     reconstructed_text
            # ]

            page_streams = (
                self._build_fee_page_streams(
                    page
                )
            )

            # if not page_streams:
            #     continue

            for reconstructed_text in page_streams:

                if not reconstructed_text:
                    continue

                sections = (
                    self._extract_fee_sections(
                        reconstructed_text
                    )
                )

                for section in sections:

                    heading = section.get(
                        "heading",
                        "",
                    )

                    content_lines = section.get(
                        "content",
                        [],
                    )

                    if not content_lines:
                        continue

                    logical_lines = (
                        self._merge_fee_continuation_lines(
                            content_lines
                        )
                    )

                    section_records = (
                        self._parse_fee_rows(
                            logical_lines=logical_lines,
                            page_number=page_number,
                            heading=heading,
                            heading_number=section.get(
                                "heading_number"
                            ),
                            section_heading=heading,
                        )
                    )

                    records.extend(
                        section_records
                    )

        return records

    # def extract(
    #     self,
    #     layout_document: dict | list,
    #     pages: list[dict],
    # ) -> list[FeeRecord]:

    #     records: list[FeeRecord] = []

    #     layout_pages = self._get_layout_pages(
    #         layout_document,
    #         pages,
    #     )

    #     if not layout_pages:
    #         return records

    #     for page in layout_pages:

    #         page_number = page.get(
    #             "page_number"
    #         )

    #         # reconstructed_text = str(
    #         #     page.get(
    #         #         "reconstructed_text",
    #         #         page.get("text", ""),
    #         #         # "",
    #         #     )
    #         #     or ""
    #         # ).strip()
    #         reconstructed_text = (
    #             self._build_fee_page_text(page)
    #         )

    #         if not reconstructed_text:
    #             continue

    #         sections = self._extract_fee_sections(
    #             reconstructed_text
    #         )

    #         for section in sections:

    #             heading = section.get(
    #                 "heading",
    #                 "",
    #             )

    #             content_lines = section.get(
    #                 "content",
    #                 [],
    #             )

    #             if not content_lines:
    #                 continue

    #             logical_lines = (
    #                 self._merge_fee_continuation_lines(
    #                     content_lines
    #                 )
    #             )

    #             section_records = self._parse_fee_rows(
    #                 logical_lines=logical_lines,
    #                 page_number=page_number,
    #                 heading=heading,
    #                 heading_number=section.get(
    #                     "heading_number"
    #                 ),
    #                 section_heading=heading,
    #             )

    #             records.extend(
    #                 section_records
    #             )

    #     return records
#bhbhb
    # @staticmethod
    # def _get_layout_pages(
    #     layout_document: dict | list,
    #     pages: list[dict],
    # ) -> list[dict]:
    #     """
    #     Return layout-reconstruction pages corresponding only to
    #     the dynamically selected fee pages.

    #     No page numbers are hardcoded here.
    #     """

    #     if isinstance(layout_document, dict):
    #         layout_pages = layout_document.get(
    #             "pages",
    #             [],
    #         )
    #     elif isinstance(layout_document, list):
    #         layout_pages = layout_document
    #     else:
    #         return []

    #     if not isinstance(layout_pages, list):
    #         return []

    #     selected_page_numbers = {
    #         page.get("page_number")
    #         for page in pages
    #         if page.get("page_number") is not None
    #     }

    #     if not selected_page_numbers:
    #         return []

    #     return [
    #         page
    #         for page in layout_pages
    #         if page.get("page_number")
    #         in selected_page_numbers
    #     ]
    
    # AMOUNT_PATTERN = re.compile(
    #     r"""
    #     Rs\.?\s*
    #     (?P<amount>
    #         \d[\d,]*(?:\.\d+)?
    #     )
    #     """,
    #     re.IGNORECASE | re.VERBOSE,
    # )

    @staticmethod
    def _get_layout_pages(
        layout_document: dict | list,
        pages: list[dict],
    ) -> list[dict]:
        """
        Return the dynamically selected fee pages.

        Prefer the selected cleaned pages because they retain
        layout_items needed for spatial fee-page reconstruction.
        Fall back to the layout document for compatibility.
        """

        selected_pages = [
            page
            for page in pages
            if page.get("page_number") is not None
        ]

        if selected_pages:
            return selected_pages

        if isinstance(layout_document, dict):
            layout_pages = layout_document.get("pages", [])
        elif isinstance(layout_document, list):
            layout_pages = layout_document
        else:
            return []

        if not isinstance(layout_pages, list):
            return []

        return layout_pages


    def _is_fee_section(
        self,
        section: dict,
    ) -> bool:

        heading = (
            section.get(
                "heading",
                "",
            )
            .strip()
        )

        content = "\n".join(
            section.get(
                "content",
                [],
            )
        )

        text = (
            heading
            + "\n"
            + content
        )

        if not heading:
            return False

        # Reject OCR paragraphs accidentally treated as headings.
        if len(heading) > 120:
            return False

    # Real headings are usually short.
        if len(heading.split()) > 12:
            return False

        return bool(
            self.FEE_HEADING_PATTERN.search(
                text
            )
        )
    
    def _is_category_line(
        self,
        line: str,
    ) -> bool:
        """
        Decide whether a line is likely
        to be a fee category/item.
        """

        text = line.strip()

        if not text:
            return False

# Amounts are handled separately.
        if self.AMOUNT_PATTERN.search(text):
            return False

# Extremely long labels are unlikely.
        if len(text) > 60:
            return False

        # Categories are usually concise.
        if len(text.split()) > 8:
            return False

        return True
    
    def _normalize_category(
        self,
        line: str,
    ) -> str:
        """
        Normalize a potential fee category.
        Removes numbering, bullets and OCR artefacts while
        preserving genuine category text.
        """
        text = line.strip()

        if not text:
            return ""
        text = re.sub(
            r"""
            ^
            (
                \d+(?:\.\d+)*\.?
                |
                \d+\)
                |
                [A-Za-z]\)
                |
                [ivxlcdmIVXLCDM]+\)
                |
                [•*▪◦●]
                |
                [ò]
            )
            \s*
            """,
            "",
            text,
            flags=re.VERBOSE,
        )
        text = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()
    
        if not text:
            return ""
        # Ignore isolated numbering remnants.
        if re.fullmatch(
            r"[ivxlcdm]+",
            text,
            re.IGNORECASE,
        ):
            return ""
        # Ignore very short OCR fragments.
        if len(text) <= 2:
            return ""
        # Ignore obvious note markers.
        if text.upper() in {
            "NB",
            "NB:",
            "NOTE",
            "NOTE:",
        }:
            return ""
        return text

    def _is_valid_category(
        self,
        text: str,
    ) -> bool:

        """
        Decide whether a normalized label is suitable
        to become the current fee category.
        """

        text = re.sub(
            r"""
            ^
            (
                \d+(?:\.\d+)*\.?
                |
                [A-Za-z]\)
                |
                [ivxlcdmIVXLCDM]+\)
            )
            \s*
            """,
            "",
            text,
            flags=re.VERBOSE,
        ).strip()

        if not text:
            return False

        if len(text) < 3:
            return False

        if len(text.split()) > 8:
            return False

        if text.endswith(","):
            return False

        if text.endswith("&"):
            return False

        if text.endswith("("):
            return False

        if re.fullmatch(
            r"[ivxlcdm]+",
            text,
            re.IGNORECASE,
        ):
            return False

        if re.fullmatch(
            r"[A-Za-z]\)",
            text,
        ):
            return False

        alpha_chars = sum(
            ch.isalpha()
            for ch in text
        )

        if alpha_chars > 0:

            unique_alpha = len(
                {
                    ch.lower()
                    for ch in text
                    if ch.isalpha()
                }
            )

            if unique_alpha <= 2 and alpha_chars >= 6:
                return False

            words = re.findall(
                r"[A-Za-z]+",
                text,
            )

        if words:

            single_letter_words = sum(
                len(word) == 1
                for word in words
            )
            if (
                len(words) >= 3
                and single_letter_words / len(words) > 0.4
            ):
                return False
            average_word_length = (
                sum(len(word) for word in words)
                / len(words)
            )
            if average_word_length < 2.5:
                return False

        lowered = text.lower()

        if lowered.startswith(
            (
                "and ",
                "or ",
                "of ",
                "from ",
                "to ",
                "with ",
                "against ",
                "subject ",
                "under ",
                "after ",
                "before ",
                "once ",
            )
        ):
            return False

        if self._is_sentence(text):
           return False

        return True

    def _category_is_complete(
        self,
        text: str,
    ) -> bool:

        text = text.rstrip()

        if not text:
            return False

        if text.endswith("&"):
            return False

        if text.endswith(","):
            return False

        if text.endswith("("):
            return False

        return True
    
    def _is_sentence(
        self,
        text: str,
    ) -> bool:
        """
        Returns True if a line reads like
        explanatory prose rather than a label.
        """

        text = text.strip()

        if not text:
            return False

        lower = f" {text.lower()} "

        sentence_markers = (
            " is ",
            " are ",
            " was ",
            " were ",
            " shall ",
            " should ",
            " may ",
            " can ",
            " must ",
            " under ",
            " after ",
            " before ",
            " eligible ",
            " applicable ",
            " included ",
            " recommended ",
            " subject to ",
        )

        if any(
            marker in lower
            for marker in sentence_markers
        ):
            return True

        if "," in text:
            return True

        if text.endswith("."):
            return True

        if len(text.split()) > 10:
            return True

        return False
    
    def _classify_line(
        self,
        line: str,
    ) -> str:
        """
        Classify a cleaned line into a generic
        document role.
        """

        if not line:
            return "empty"

        if self.AMOUNT_PATTERN.search(line):
            return "amount"

        if self._is_sentence(line):
            return "context"

        word_count = len(line.split())

        if word_count > 8:
            return "context"

        if line.endswith("."):
            return "context"

        if "," in line:
            return "context"

        return "category"
    
    def _extract_payment_period(
        self,
        text: str,
    ) -> str | None:
        """
        Extract payment frequency from a fee line.
        """

        lower = text.lower()

        if "per month" in lower:
            return "per_month"

        if (
            "per semester" in lower
            or "each semester" in lower
        ):
            return "per_semester"

        if "per year" in lower:
            return "per_year"

        if "annually" in lower:
            return "annual"

        if (
            "once" in lower
            or "one time" in lower
            or "one-time" in lower
        ):
            return "one_time"

        return None

    def _extract_fee_sections(
        self,
        text: str,
    ) -> list[dict]:
        """
        Split reconstructed fee-page text into logical sections.

        Heading detection is based on the structure of the
        reconstructed document, not on hardcoded page numbers,
        fee amounts, programmes, or prospectus years.
        """

        if not text:
            return []

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        sections: list[dict] = []

        current_heading: str | None = None
        current_heading_number: str | None = None
        current_content: list[str] = []

        heading_pattern = re.compile(
           r"""
           ^
           (?P<number>
               \d+(?:\.\d+)+
           )
           \.?
           \s+
           (?P<title>.+?)
           $
           """,
            re.VERBOSE,
        )

        def flush_section() -> None:

            nonlocal current_heading
            nonlocal current_heading_number
            nonlocal current_content

            if (
                current_heading is None
                and not current_content
            ):
                return

            sections.append(
                {
                    "heading": current_heading or "",
                    "heading_number": (
                        current_heading_number
                    ),
                    "content": current_content.copy(),
                }
            )

            current_heading = None
            current_heading_number = None
            current_content = []

        for line in lines:

            match = heading_pattern.match(line)

            if match:

                flush_section()

                current_heading_number = (
                    match.group("number")
                )

                current_heading = (
                    match.group("title").strip()
                )

                continue

# Join a continuation line when the detected heading
# clearly ends mid-phrase.
            if (
                current_heading
                and current_heading.rstrip().lower().endswith(
                    (
                        " and",
                        " of",
                        " for",
                        " to",
                        " in",
                        " under",
                        " with",
                    )
                )
                and not re.match(
                    r"^(?:[a-z]\)|[ivxlcdm]+\)|\d+\.)\s+",
                    line,
                    flags=re.IGNORECASE,
                )
            ):
                current_heading = (
                    f"{current_heading} {line}".strip()
                )
                continue

            current_content.append(line)

        flush_section()

        return sections
    
    def _is_new_fee_item_context(
        self,
        line: str,
    ) -> bool:
        """
        Determine whether a line starts a new fee item
        rather than continuing the context of the current
        fee item.

        Detection is structural and does not depend on
        specific fee names, programmes, pages, or amounts.
        """

        raw_text = str(line).strip()

        if not raw_text:
            return False

        # Detect structural enumeration BEFORE removing it.
        structural_item = re.match(
            r"^(?:"
            r"[a-z]\)"
            r"|[ivxlcdm]+\)"
            r"|\(\s*[a-z]\s*\)"
            r"|\(\s*[ivxlcdm]+\s*\)"
            r"|\d+\."
            r")\s+",
            raw_text,
            flags=re.IGNORECASE,
        )

        text = FeeRecordExtractor._clean_structural_prefix(
            raw_text
        ).strip()

        if not text:
            return False

        lower = text.casefold()

        # Applicability/context lines do not start a new
        # fee item, even when they have a structural marker.
        if re.match(
            r"^(?:for|all|except|including|excluding)\b",
            text,
            flags=re.IGNORECASE,
        ):
            return False

        if lower.startswith(
            (
                "note",
                "nb",
                "subject to",
                "provided that",
                "in case",
                "which ",
                "this ",
                "these ",
                "those ",
                "once ",
                "against ",
                "during ",
                "after ",
                "before ",
            )
        ):
            return False

        # Programme/category descriptions are contextual
        # information.
        if (
            "programme" in lower
            or "programmes" in lower
            or "category" in lower
            or "categories" in lower
        ):
            return False

        # A sentence is normally explanatory/contextual prose.
        if self._is_sentence(text):
            return False

        # A structural marker is strong evidence of a new
        # logical row.
        if structural_item:
            return True

        # Non-enumerated labels still need to satisfy the
        # generic fee-label rules.
        return self._looks_like_fee_label(
            text
        )

    @staticmethod
    def _should_keep_fee_context(
        line: str,
    ) -> bool:
        """
        Determine whether an amount-bearing line contains
        useful context that should remain available for the
        next logical fee line.

        This is structural and does not depend on specific
        prospectus pages, programmes, or fee amounts.
        """

        text = str(line).strip()

        if not text:
            return False

        cleaned = FeeRecordExtractor._clean_structural_prefix(
            text
        )

        if not cleaned:
            return False

        lower = cleaned.casefold()

        if re.match(
            r"^(?:for|all|except|including|excluding)\b",
            cleaned,
            flags=re.IGNORECASE,
        ):
            return True

        if (
            "programme" in lower
            or "programmes" in lower
        ):
            return True

        if (
            "scheme" in lower
            or "category" in lower
            or "categories" in lower
        ):
            return True

        if (
            "tax" in lower
            or "subject to revision" in lower
            or "if applicable" in lower
        ):
            return True

        return False

    @staticmethod
    def _is_applicability_continuation(
        line: str,
    ) -> bool:
        """
        Determine whether a line modifies the applicability
        of the current fee item rather than starting a new fee.
        """

        text = FeeRecordExtractor._clean_structural_prefix(
            str(line)
        )

        if not text:
            return False

        return re.match(
            r"^(?:for|all|except|including|excluding)\b",
            text,
            flags=re.IGNORECASE,
        ) is not None

    @staticmethod
    def _merge_fee_continuation_lines(
        lines: list[str],
    ) -> list[str]:
        """
        Merge fee-label lines that are clearly wrapped across
        reconstructed layout lines.

        Only explicit structural continuation signals are merged.
        """

        merged: list[str] = []

        for line in lines:
            text = str(line).strip()

            if not text:
                continue

            should_merge = False

            if merged:
                previous = merged[-1].rstrip()

                if previous.endswith("&"):
                    should_merge = True

                elif (
                    previous.count("(")
                    > previous.count(")")
                ):
                    should_merge = True

            if should_merge:
                merged[-1] = (
                    merged[-1].rstrip()
                    + " "
                    + text
                )
            else:
                merged.append(text)

        return merged
    @staticmethod
    def _is_self_finance_category_line(
        line: str,
    ) -> bool:
        """
        Determine whether a line explicitly identifies a
        self-finance fee category.
        """

        text = str(line).strip()

        if not text:
            return False

        cleaned = FeeRecordExtractor._clean_structural_prefix(
            text
        )

        return re.search(
            r"\bCategories\s+SF-\d+\s+to\s+SF-\d+\b",
            cleaned,
            flags=re.IGNORECASE,
        ) is not None
    
    # def _parse_fee_rows(
    #     self,
    #     logical_lines: list[str],
    #     page_number: int,
    #     heading: str,
    #     heading_number: str | None,
    #     section_heading: str | None = None,
    # ) -> list[FeeRecord]:

    #     records: list[FeeRecord] = []

    #     if not logical_lines:
    #         return records

    #     current_context: list[str] = []

    #     active_category: str | None = None
    #     active_scheme: str | None = None
    #     active_applicability: str | None = None
    #     active_campus = None
        
    #     if section_heading:
    #         current_context.append(section_heading)

    #     if heading and heading != section_heading:
    #         current_context.append(heading)

    #     heading_applicability = self._extract_applicability(
    #         heading or section_heading
    #     )

    #     if heading_applicability:
    #         active_applicability = heading_applicability

    #         active_campus = self._extract_campus(
    #             heading_applicability
    #         )

    #     for raw_line in logical_lines:

    #         line = str(raw_line).strip()

    #         if not line:
    #             continue

    #         amount_matches = list(
    #             self.AMOUNT_PATTERN.finditer(
    #                 line
    #             )
    #         )

    #         if self._is_self_finance_category_line(
    #             line
    #         ):
    #             current_context = []

    #             active_category = None
    #             active_scheme = "Self-Finance"
    #             active_applicability = None

    #         if not amount_matches:

    #             if FeeRecordExtractor._is_applicability_continuation(
    #                 line
    #             ):
    #                 current_context.append(
    #                     line
    #                 )

    #             elif re.match(
    #                 r"^\d+(?:\.\d+)+\.?\s+For\b",
    #                 line.strip(),
    #                 flags=re.IGNORECASE,
    #             ):
    #                 current_context = [line]

    #                 active_category = None
    #                 active_scheme = None
    #                 active_applicability = None
    #                 active_campus = None

    #             elif self._is_new_fee_item_context(
    #                 line
    #             ):
    #                 current_context = [
    #                     line
    #                 ]

    #                 active_category = None
    #                 active_scheme = None
    #                 # active_applicability = None

    #             else:
    #                 current_context.append(
    #                     line
    #                 )

    #             continue

    #         for match in amount_matches:

    #             amount = self._parse_amount(
    #                 match.group("amount")
    #             )

    #             if amount is None:
    #                 continue

    #             before_amount = (
    #                 line[:match.start()]
    #                 .strip()
    #             )
    #             label_detection_text = re.sub(
    #                 r"Rs\.?\s*[\d,]+(?:\.\d+)?\s*/?-?",
    #                 "",
    #                 before_amount,
    #                 flags=re.IGNORECASE,
    #             ).strip()

                

    #             before_amount_cleaned = (
    #                 FeeRecordExtractor
    #                 ._clean_structural_prefix(
    #                     label_detection_text
    #                 )
    #             ).strip()

    #             after_amount = (
    #                 line[match.end():]
    #                 .strip()
    #             )

    #             structural_item_match = re.match(
    #                 r"^(?:"
    #                 r"[a-z]\)"
    #                 r"|[ivxlcdm]+\)"
    #                 r"|\(\s*[a-z]\s*\)"
    #                 r"|\(\s*[ivxlcdm]+\s*\)"
    #                 r"|\d+\."
    #                 r")\s+",
    #                 before_amount,
    #                 flags=re.IGNORECASE,
    #             )

    #             if structural_item_match:
    #                 current_context = []
    #                 active_category = None
    #                 active_scheme = None
    #                 # active_applicability = None

    #             current_row_has_item_marker = bool(
    #                 re.match(
    #                     r"^(?:"
    #                     r"[a-z]\)"
    #                     r"|[ivxlcdm]+\)"
    #                     r"|\(\s*[a-z]\s*\)"
    #                     r"|\(\s*[ivxlcdm]+\s*\)"
    #                     r"|\d+\."
    #                     r")\s+",
    #                     before_amount,
    #                     flags=re.IGNORECASE,
    #                 )
    #             )

    #             context_lines = list(
    #                 current_context
    #             )

    #             if before_amount:
    #                 context_lines.append(
    #                     before_amount
    #                 )

    #             context_text = "\n".join(
    #                 context_lines
    #             ).strip()

    #             detected_label = (
    #                 self._extract_fee_label(
    #                     context_text
    #                 )
    #             )

    #             detected_applicability = (
    #                 self._extract_applicability(
    #                     context_text
    #                 )
    #             )

    #             detected_scheme = (
    #                 self._extract_scheme_context(
    #                     context_text
    #                 )
    #             )

                

    #             current_row_is_applicability = (
    #                 FeeRecordExtractor
    #                 ._is_applicability_continuation(
    #                     before_amount_cleaned
    #                 )
    #                 if before_amount_cleaned
    #                 else False
    #             )

    #             # Determine category strictly: require an explicit label or
    #             # structural continuity. Exclude pure applicability scopes
    #             # and non-fee prose fragments from becoming categories.
    #             is_pure_applicability = (
    #                 FeeRecordExtractor._is_applicability_continuation(
    #                     before_amount_cleaned
    #                 )
    #                 or re.match(
    #                     r"^(?:for|all|except|including|excluding)\b",
    #                     before_amount_cleaned,
    #                     flags=re.IGNORECASE,
    #                 ) is not None
    #             )

    #             is_prose_fragment = (
    #                 re.match(
    #                     r"^(?:outlay|about|additional|cost|expense|expenses|expenditure|payment|price|value)\b",
    #                     before_amount_cleaned,
    #                     flags=re.IGNORECASE,
    #                 ) is not None
    #                 or self._is_sentence(
    #                     before_amount_cleaned
    #                 )
    #             )

    #             if current_row_has_item_marker or detected_label:
    #                 candidate = (
    #                     detected_label
    #                     or before_amount_cleaned
    #                 )

    #                 if (
    #                     candidate
    #                     and not is_pure_applicability
    #                     and not is_prose_fragment
    #                 ):
    #                     current_category = candidate
    #                     active_category = current_category
    #                 else:
    #                     current_category = (
    #                         candidate
    #                         if (
    #                             candidate
    #                             and not is_pure_applicability
    #                         )
    #                         else None
    #                     )

    #             else:
    #                 if (
    #                     before_amount_cleaned
    #                     and not is_pure_applicability
    #                     and not is_prose_fragment
    #                 ):
    #                     current_category = (
    #                         before_amount_cleaned
    #                     )
    #                     active_category = (
    #                         current_category
    #                     )
    #                 else:
    #                     current_category = (
    #                         active_category
    #                         if not before_amount_cleaned
    #                         else None
    #                     )

    #             if detected_scheme:
    #                 active_scheme = (
    #                     detected_scheme
    #                 )

    #             if detected_applicability:
    #                 detected_campus = self._extract_campus(
    #                     detected_applicability,
    #                 )

    #                 if detected_campus and active_campus is None:
    #                     active_campus = detected_campus

                

    #             category = (
    #                 current_category
    #                 or active_category
    #             )

    #             if category is None:
    #                 contextual_label = (
    #                     self._extract_fee_label(
    #                         context_text
    #                     )
    #                 )

    #                 if contextual_label:
    #                     category = contextual_label
    #                 elif active_category:
    #                     category = active_category
    #                 else:
    #                     continue

    #             payment_period = (
    #                 self._extract_payment_period(
    #                     context_text
    #                 )
    #                 or self._extract_payment_period(
    #                     after_amount
    #                 )
    #             )

    #             scheme = (
    #                 detected_scheme
    #                 or active_scheme
    #             )

    #             notes = (
    #                 self._extract_notes(
    #                     context_text,
    #                     after_amount,
    #                 )
    #             )

    #             source_text_parts: list[str] = []

    #             if context_text:
    #                 source_text_parts.append(
    #                     context_text
    #                 )

    #             source_text_parts.append(
    #                 line
    #             )

    #             if after_amount:
    #                 source_text_parts.append(
    #                     after_amount
    #                 )

    #             source_text = " ".join(
    #                 source_text_parts
    #             )

    #             applicability = (
    #                 active_applicability
    #             )

    #             records.append(
    #                 FeeRecord(
    #                     category=category,
    #                     amount=amount,
    #                     currency="PKR",
    #                     payment_period=payment_period,
    #                     scheme=scheme,
    #                     applicability=applicability,
    #                     campus=active_campus,
    #                     notes=notes,
    #                     fee_type=self._clean_fee_type(
    #                         detected_label or category
    #                     ),
    #                     source_page=page_number,
    #                     source_heading=heading,
    #                     source_text=source_text,
    #                     section_number=heading_number,
    #                     section_heading=section_heading,
    #                 )
    #             )

    #     return records

    def _parse_fee_rows(
        self,
        logical_lines: list[str],
        page_number: int,
        heading: str,
        heading_number: str | None,
        section_heading: str | None = None,
    ) -> list[FeeRecord]:

        records: list[FeeRecord] = []

        if not logical_lines:
            return records

        current_context: list[str] = []
        payment_period_context: list[str] = []

        active_category: str | None = None
        active_scheme: str | None = None
        active_applicability: str | None = None
        active_campus = None
        
        if section_heading:
            current_context.append(section_heading)

        if heading and heading != section_heading:
            current_context.append(heading)

        heading_applicability = self._extract_applicability(
            heading or section_heading
        )

        if heading_applicability:
            active_applicability = heading_applicability

            active_campus = self._extract_campus(
                heading_applicability
            )

        for raw_line in logical_lines:

            line = str(raw_line).strip()

            if not line:
                continue

            amount_matches = list(
                self.AMOUNT_PATTERN.finditer(
                    line
                )
            )

            if self._is_self_finance_category_line(
                line
            ):
                current_context = []

                active_category = None
                active_scheme = "Self-Finance"
                active_applicability = None

            if not amount_matches:

                if FeeRecordExtractor._is_applicability_continuation(
                    line
                ):
                    current_context.append(
                        line
                    )

                elif re.match(
                    r"^\d+(?:\.\d+)+\.?\s+For\b",
                    line.strip(),
                    flags=re.IGNORECASE,
                ):
                    current_context = [line]

                    active_category = None
                    active_scheme = None
                    active_applicability = None
                    active_campus = None

                elif self._is_new_fee_item_context(
                    line
                ):
                    current_context = [
                        line
                    ]

                    active_category = None
                    active_scheme = None
                    # active_applicability = None

                else:
                    current_context.append(
                        line
                    )

                    if self._extract_payment_period(line):
                        payment_period_context.append(line)

                continue

            for match in amount_matches:

                amount = self._parse_amount(
                    match.group("amount")
                )

                if amount is None:
                    continue

                before_amount = (
                    line[:match.start()]
                    .strip()
                )
                label_detection_text = re.sub(
                    r"Rs\.?\s*[\d,]+(?:\.\d+)?\s*/?-?",
                    "",
                    before_amount,
                    flags=re.IGNORECASE,
                ).strip()

                

                before_amount_cleaned = (
                    FeeRecordExtractor
                    ._clean_structural_prefix(
                        label_detection_text
                    )
                ).strip()

                after_amount = (
                    line[match.end():]
                    .strip()
                )

                structural_item_match = re.match(
                    r"^(?:"
                    r"[a-z]\)"
                    r"|[ivxlcdm]+\)"
                    r"|\(\s*[a-z]\s*\)"
                    r"|\(\s*[ivxlcdm]+\s*\)"
                    r"|\d+\."
                    r")\s+",
                    before_amount,
                    flags=re.IGNORECASE,
                )

                if structural_item_match:
                    current_context = []
                    active_category = None
                    active_scheme = None
                    # active_applicability = None

                current_row_has_item_marker = bool(
                    re.match(
                        r"^(?:"
                        r"[a-z]\)"
                        r"|[ivxlcdm]+\)"
                        r"|\(\s*[a-z]\s*\)"
                        r"|\(\s*[ivxlcdm]+\s*\)"
                        r"|\d+\."
                        r")\s+",
                        before_amount,
                        flags=re.IGNORECASE,
                    )
                )

                context_lines = list(
                    current_context
                )

                if before_amount:
                    context_lines.append(
                        before_amount
                    )

                context_text = "\n".join(
                    context_lines
                ).strip()

                detected_label = (
                    self._extract_fee_label(
                        context_text
                    )
                )

                detected_applicability = (
                    self._extract_applicability(
                        context_text
                    )
                )

                detected_scheme = (
                    self._extract_scheme_context(
                        context_text
                    )
                )

                

                current_row_is_applicability = (
                    FeeRecordExtractor
                    ._is_applicability_continuation(
                        before_amount_cleaned
                    )
                    if before_amount_cleaned
                    else False
                )

                # Determine category strictly: require an explicit label or
                # structural continuity. Exclude pure applicability scopes
                # and non-fee prose fragments from becoming categories.
                is_pure_applicability = (
                    FeeRecordExtractor._is_applicability_continuation(
                        before_amount_cleaned
                    )
                    or re.match(
                        r"^(?:for|all|except|including|excluding)\b",
                        before_amount_cleaned,
                        flags=re.IGNORECASE,
                    ) is not None
                )

                is_prose_fragment = (
                    re.match(
                        r"^(?:outlay|about|additional|cost|expense|expenses|expenditure|payment|price|value)\b",
                        before_amount_cleaned,
                        flags=re.IGNORECASE,
                    ) is not None
                    or self._is_sentence(
                        before_amount_cleaned
                    )
                )

                if current_row_has_item_marker or detected_label:
                    candidate = (
                        detected_label
                        or before_amount_cleaned
                    )

                    if (
                        candidate
                        and not is_pure_applicability
                        and not is_prose_fragment
                    ):
                        current_category = candidate
                        active_category = current_category
                    else:
                        current_category = (
                            candidate
                            if (
                                candidate
                                and not is_pure_applicability
                            )
                            else None
                        )

                else:
                    if (
                        before_amount_cleaned
                        and not is_pure_applicability
                        and not is_prose_fragment
                    ):
                        current_category = (
                            before_amount_cleaned
                        )
                        active_category = (
                            current_category
                        )
                    else:
                        current_category = (
                            active_category
                            if not before_amount_cleaned
                            else None
                        )

                if detected_scheme:
                    active_scheme = (
                        detected_scheme
                    )

                if detected_applicability:
                    detected_campus = self._extract_campus(
                        detected_applicability,
                    )

                    if detected_campus and active_campus is None:
                        active_campus = detected_campus

                

                category = (
                    current_category
                    or active_category
                )

                if category is None:
                    contextual_label = (
                        self._extract_fee_label(
                            context_text
                        )
                    )

                    if contextual_label:
                        category = contextual_label
                    elif active_category:
                        category = active_category
                    else:
                        continue

                payment_period = (
                    self._extract_payment_period(
                        context_text
                    )
                    or self._extract_payment_period(
                        after_amount
                    )
                    or self._extract_payment_period(
                        "\n".join(payment_period_context)
                    )
                )

                scheme = (
                    detected_scheme
                    or active_scheme
                )

                notes = (
                    self._extract_notes(
                        context_text,
                        after_amount,
                    )
                )

                source_text_parts: list[str] = []

                if context_text:
                    source_text_parts.append(
                        context_text
                    )

                source_text_parts.append(
                    line
                )

                if after_amount:
                    source_text_parts.append(
                        after_amount
                    )

                source_text = " ".join(
                    source_text_parts
                )

                applicability = (
                    active_applicability
                )

                student_type = None

                student_match = re.search(
                    r"\bFor\s+(Locals?|Foreigners?)\b",
                    before_amount,
                    flags=re.IGNORECASE,
                )

                if student_match:
                    value = student_match.group(1).lower()

                    if value.startswith("local"):
                        student_type = "Local"
                    else:
                        student_type = "Foreign"

                records.append(
                    FeeRecord(
                        category=category,
                        amount=amount,
                        currency="PKR",
                        payment_period=payment_period,
                        scheme=scheme,
                        applicability=applicability,
                        campus=active_campus,
                        notes=notes,
                        fee_type=self._clean_fee_type(
                            detected_label or category
                        ),
                        # programme_scope=programme_scope,
                        student_type=student_type,
                        source_page=page_number,
                        source_heading=heading,
                        source_text=source_text,
                        section_number=heading_number,
                        section_heading=section_heading,
                    )
                )

        return records    

    @staticmethod
    def _extract_campus(
        applicability: str | None,
        heading: str | None = None,
    ) -> str | None:
        values = []

        if applicability:
            values.append(applicability)

        if heading:
            values.append(heading)

        text = " ".join(values)

        text = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        if not text:
            return None

        match = re.search(
            r"\bFor\s+(.+?)(?=\s+For\s+|\s+All\s+|\s*$)",
            text,
            flags=re.IGNORECASE,
        )

        if match is None:
            return None

        candidate = match.group(1).strip(
            " :-,.;"
        )

        if not candidate:
            return None

        # if not re.search(
        #     r"\bcampus\b",
        #     candidate,
        #     flags=re.IGNORECASE,
        # ):
        #     return None

        return candidate

    @staticmethod
    def _clean_fee_type(
        value: str | None,
    ) -> str | None:
        if not value:
            return None

        value = " ".join(
            value.split()
        ).strip()

    # Keep the actual fee label and remove
    # trailing explanatory wording.
        value = re.sub(
            r"\s+to\s+be\s+paid(?:\s+once)?"
            r"(?:\s+at\s+the\s+time\s+of\s+admission)?\s*$",
            "",
            value,
            flags=re.IGNORECASE,
        )

        value = re.sub(
            r"\s+of\s*$",
            "",
            value,
            flags=re.IGNORECASE,
        )

        value = value.strip(
            " :-*()"
        )

        return value or None
    
    @staticmethod
    def _parse_amount(
        amount_text: str,
    ) -> float | None:

        if not amount_text:
            return None

        cleaned = (
            amount_text
            .replace(",", "")
            .strip()
        )

        try:
            return float(cleaned)
        except ValueError:
          return None

    @staticmethod
    def _clean_structural_prefix(
        line: str,
    ) -> str:
        """
        Remove structural numbering and bullet prefixes from
        reconstructed prospectus lines.

        This does not alter the actual semantic content of
        the line.
        """

        text = str(line).strip()

        if not text:
            return ""

        text = re.sub(
            r"^[•\-–—*▪◦●]+\s*",
            "",
            text,
        ).strip()

        text = re.sub(
            r"^(?:[a-z])\)\s*",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()

        text = re.sub(
            r"^(?:i{1,3}|iv|v|vi|vii|viii)\)\s*",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip()

        text = re.sub(
            r"^\d+(?:\.\d+)*\.?\s*",
            "",
            text,
        ).strip()

        text = re.sub(
            r"\*+",
            "",
            text,
        ).strip()

        return text

    
    def _extract_fee_label(
        self,
        context: str,
    ) -> str | None:
        """
        Extract the most likely explicit fee-item label from
        nearby reconstructed layout text.

        Label detection is based on individual logical lines.
        Structural continuation of wrapped labels is handled
        earlier by _merge_fee_continuation_lines().
        """

        if not context:
            return None

        lines = [
            re.sub(
                r"\s+",
                " ",
                line,
            ).strip()
            for line in context.splitlines()
            if line.strip()
        ]

        if not lines:
            return None

        candidates: list[str] = []

        for line in lines:

            has_structural_marker = re.match(
                r"^(?:"
                r"[a-z]\)"
                r"|[ivxlcdm]+\)"
                r"|\(\s*[a-z]\s*\)"
                r"|\(\s*[ivxlcdm]+\s*\)"
                r"|\d+\."
                r")\s+",
                line,
                flags=re.IGNORECASE,
            ) is not None

            cleaned = (
                FeeRecordExtractor
                ._clean_structural_prefix(line)
            )

            cleaned = cleaned.rstrip(":").strip()

            if not cleaned:
                continue

            if not self._looks_like_fee_label(
                cleaned,
                has_structural_marker=has_structural_marker,
            ):
                continue

            candidates.append(cleaned)

        

        if not candidates:
            return None

        return candidates[-1]

    def _looks_like_fee_label(
        self,
        text: str,
        has_structural_marker: bool = False,
    ) -> bool:
        """
        Determine whether a line structurally resembles
        a fee item rather than applicability text or prose.
        """

        if not text:
            return False

        if len(text) > 80:
            return False

        if len(text.split()) > 16:
            return False

        lower = text.casefold().strip()

        if re.match(
            r"^(?:for|all|except|including|excluding)\b",
            text,
            flags=re.IGNORECASE,
        ):
            return False

        if lower.startswith(
            (
                "note",
                "nb",
                "subject to",
                "provided that",
                "in case",
                "which ",
                "this ",
                "these ",
                "those ",
                "once ",
                "against ",
                "during ",
                "after ",
                "before ",
            )
        ):
            return False

        if "," in text:
            return False

        if text.endswith(
            (
                "&",
                "(",
            )
        ):
            return False


        if self._is_sentence(text):
            if not (
                has_structural_marker
                and re.search(
                    r"\b(?:fee|fees|charge|charges|deposit|rent)\b",
                    text,
                    flags=re.IGNORECASE,
                )
            ):
                return False
            
        core_text = re.sub(
            r"\s*\([^)]*\)\s*$",
            "",
            text,
        ).strip()

        if re.search(
            r"\b(?:fee|fees|charge|charges|deposit|rent)\b\s*$",
            core_text,
            flags=re.IGNORECASE,
        ):
            return True

        

        # A genuine fee label normally ends with, or clearly
        # contains, a fee/charge/deposit noun.
        if re.search(
            r"\b(?:fee|fees|charge|charges|deposit|rent)\b\s*$",
            text,
            flags=re.IGNORECASE,
        ):
            return True


        # Preserve known standalone document/service fee labels.
        if re.match(
            r"^(?:mark certificate|transcript|degree|"
            r"duplicate degree|provisional certificate|"
            r"re-totaling of answer)$",
            text,
            flags=re.IGNORECASE,
        ):
            return True

        # Programme/application labels may contain fee terminology,
        # but they should still look like a label rather than prose.
        if re.search(
            r"\b(?:fee|fees|charge|charges|deposit|rent)\b",
            text,
            flags=re.IGNORECASE,
        ):
            return True

        return False
    
    def _extract_category(
        self,
        context: str,
    ) -> str | None:

        if not context:
            return None

        lines = [
            re.sub(
                r"\s+",
                " ",
                line,
            ).strip()
            for line in context.splitlines()
            if line.strip()
        ]

        if not lines:
            return None

        candidates: list[str] = []

        for line in lines:

            cleaned = self._clean_structural_prefix(
                line
            )

            if not cleaned:
                continue

            if not self._is_category_candidate(
                cleaned
            ):
                continue

            candidates.append(
                cleaned
            )

        if not candidates:
            return None

        # Prefer explicit fee-like labels.
        for candidate in candidates:

            lower = candidate.casefold()

            if re.search(
                r"\b(fee|fees|charge|charges|"
                r"rent|deposit|certificate|"
                r"transcript|degree)\b",
                lower,
            ):
                return candidate

        # Otherwise use the first structurally valid
        # candidate rather than a later applicability line.
        return candidates[0]

    def _is_category_candidate(
        self,
        text: str,
    ) -> bool:

        text = text.strip()

        if not text:
            return False

        if len(text) < 3:
            return False

        if len(text.split()) > 10:
            return False

        if text.endswith(
            (
                ",",
                "&",
                "(",
            )
        ):
            return False

        lower = text.casefold()

        # Common prose fragments that can appear immediately
        # before an amount in explanatory sections.
        if re.match(
            r"^(?:outlay|amount|cost|expense|expenses|"
            r"expenditure|payment|price|value)\b",
            text,
            flags=re.IGNORECASE,
        ):
            return False

        # Applicability / qualification statements.
        if re.match(
            r"^(?:for|all|except|including|excluding)\b",
            text,
            flags=re.IGNORECASE,
        ):
            return False

        # Prose fragments beginning with common grammatical
        # connectors should never become fee categories.
        if re.match(
            r"^(?:of|in|on|at|to|from|with|by|and|or|but|as|"
            r"that|which|who|whose|where|when|while|because)\b",
            text,
            flags=re.IGNORECASE,
        ):
            return False

        # Scheme/category selectors are context,
        # not the fee itself.
        if re.match(
            r"^scheme\b",
            text,
            flags=re.IGNORECASE,
        ):
            return False

        if re.match(
            r"^categories?\s+SF-\d+\s+to\s+SF-\d+\b",
            text,
            flags=re.IGNORECASE,
        ):
            return True

        # Explanatory prose.
        if lower.startswith(
            (
                "note",
                "nb",
                "subject to",
                "provided that",
                "in case",
                "which",
                "this ",
                "these ",
                "those ",
                "the student",
                "students ",
                "he ",
                "she ",
                "they ",
                "it ",
            )
        ):
            return False

        if self._is_sentence(
            text
        ):
            return False

        # Standalone generic words are normally OCR/prose
        # fragments rather than fee categories.
        words = re.findall(
            r"[A-Za-z]+",
            text,
        )

        if len(words) == 1:
            explicit_category_words = {
                "certificate",
                "transcript",
                "degree",
                "deposit",
                "rent",
                "tuition",
                "admission",
                "application",
                "registration",
                "examination",
                "fee",
                "fees",
                "charge",
                "charges",
            }

            if lower not in explicit_category_words:
                return False

        # Very long natural-language fragments are not
        # structured categories.
        if len(words) >= 6:
            return False

        # A standalone programme applicability line
        # should not become a fee category.
        if (
            "programme" in lower
            or "programmes" in lower
        ):
            return False

        return True

    @staticmethod
    def _extract_applicability(
        context: str,
    ) -> str | None:
        """
        Extract the most relevant applicability statement
        from the nearby fee context.

        This remains generic and does not depend on specific
        programmes, categories, pages, or fee amounts.
        """

        if not context:
            return None

        lines = [
            re.sub(
                r"\s+",
                " ",
                line,
            ).strip()
            for line in context.splitlines()
            if line.strip()
        ]

        candidates: list[str] = []

        for line in lines:

            cleaned = FeeRecordExtractor._clean_structural_prefix(
                line
            )

            cleaned = cleaned.rstrip(
                ":"
            ).strip()

            if not cleaned:
                continue

            if re.match(
                r"^(?:for|all|except|including|excluding)\b",
                cleaned,
                flags=re.IGNORECASE,
            ):
                candidates.append(
                    cleaned
                )

        if not candidates:
            return None

        return " ".join(
            candidates
        )
    
    @staticmethod
    def _extract_scheme_context(
        context: str,
    ) -> str | None:
        """
        Extract explicit scheme information from nearby
        fee context.

        Scheme information is kept separate from ordinary
        applicability such as "For locals" or "For Foreigners".

        Detection is structural and does not depend on
        prospectus years, page numbers, programme names,
        or specific category numbers.
        """

        if not context:
            return None

        lines = [
            re.sub(
                r"\s+",
                " ",
                line,
            ).strip()
            for line in context.splitlines()
            if line.strip()
        ]

        if not lines:
            return None

        scheme_lines: list[str] = []

        collecting = False

        for line in lines:

            cleaned = FeeRecordExtractor._clean_structural_prefix(
                line
            )

            cleaned = cleaned.rstrip(
                ":"
            ).strip()

            if not cleaned:
                continue

            lower = cleaned.casefold()

            explicit_scheme = (
                "self-finance" in lower
                or "self finance" in lower
                or re.search(
                    r"\bscheme\b",
                    lower,
                ) is not None
            )

            category_range = re.search(
                r"\bcategories?\s+"
                r"[A-Za-z0-9]+"
                r"(?:\s*(?:to|-)\s*"
                r"[A-Za-z0-9]+)*",
                cleaned,
                flags=re.IGNORECASE,
            )

            if explicit_scheme:
                collecting = True
                scheme_lines.append(
                    cleaned
                )
                continue

            if category_range:
                collecting = True
                scheme_lines.append(
                    cleaned
                )
                continue

            if not collecting:
                continue

            if (
                lower.startswith(
                    (
                        "categories ",
                        "category ",
                    )
                )
            ):
                scheme_lines.append(
                    cleaned
                )
                continue

            if (
                "self-finance" in lower
                or "self finance" in lower
            ):
                scheme_lines.append(
                    cleaned
                )
                continue

            break

        if not scheme_lines:
            return None

        result = " ".join(
            scheme_lines
        )

        result = re.sub(
            r"\s+",
            " ",
            result,
        ).strip()

        return result or None

    @staticmethod
    def _extract_notes(
        context: str,
        after_amount: str = "",
    ) -> str | None:

        parts: list[str] = []

        if context:
            parts.append(
                str(context).strip()
            )

        if after_amount:
            parts.append(
                str(after_amount).strip()
            )

        text = " ".join(
            part
            for part in parts
            if part
        )

        if not text:
            return None

        text = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        notes: list[str] = []

        note_patterns = (
            r"\+\s*\d+(?:\.\d+)?\s*%\s*tax\b",
            r"subject\s+to\s+revision\b",
            r"\bnote\s*:",
            r"\bnb\s*:",
            r"availability\s+of\s+funds",
            r"merit[\s-]*based\s+scholarship",
            r"need[\s-]*based\s+scholarship",
            r"scholarship",
            r"refundable",
            r"non[\s-]*refundable",
            r"will\s+be\s+refunded",
            r"shall\s+be\s+refunded",
            r"may\s+be\s+considered",
            r"\bif\s+applicable\b",
        )

        for pattern in note_patterns:

            matches = re.finditer(
                pattern,
                text,
                flags=re.IGNORECASE,
            )

            for match in matches:

                note = match.group(0).strip()

                if note:
                    notes.append(note)

        if not notes:
            return None

        unique_notes = list(
            dict.fromkeys(
                notes
            )
        )

        return "; ".join(
            unique_notes
        )