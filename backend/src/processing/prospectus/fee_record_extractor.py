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

    def extract(
        self,
        pages: list[dict],
    ) -> list[FeeRecord]:

        records: list[FeeRecord] = []

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

                if not self._is_fee_section(
                    section
                ):
                    continue
                
                records.extend(
                    self._extract_fee_records(
                        section=section,
                        page_number=page_number,
                        heading=heading,
                    )
                )

        return records
    
    AMOUNT_PATTERN = re.compile(
        r"""
        Rs\.?\s*
        (?P<amount>
            \d[\d,]*(?:\.\d+)?
        )
        """,
        re.IGNORECASE | re.VERBOSE,
    )

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

        Removes common numbering prefixes while
        preserving the actual category text.
        """

        text = line.strip()

        if not text:
            return ""

        # Remove numbering prefixes such as:
        # 8.4
        # 8.4.1
        # 1)
        # a)
        # ii)
        text = re.sub(
            r"""
            ^
            (
                \d+(?:\.\d+)*\.?      # 8 / 8.1 / 8.1.1
                |
                \d+\)                # 1)
                |
                [A-Za-z]\)           # a)
                |
                [ivxlcdmIVXLCDM]+\)   # ii)
            )
            \s*
            """,
            "",
            text,
            flags=re.VERBOSE,
        )

        # Collapse repeated whitespace.
        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()
    
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

        if self.AMOUNT_PATTERN.search(
            line
        ):
            return "amount"

        if self._is_sentence(
            line
        ):
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

        if "per semester" in lower:
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
    
    def _extract_scheme_context(
        self,
        *,
        heading: str,
        category: str | None,
        line: str,
    ) -> str | None:
        """
        Extract the fee scheme exactly as it
        appears in the prospectus.

        This is intentionally generic and
        avoids university-specific mappings.
        """

        candidates = [
            heading,
            category,
            line,
        ]

        for candidate in candidates:

            if not candidate:
                continue

            text = candidate.strip()

            lower = text.lower()

            # "For Foreigners"
            if lower.startswith("for "):
                return text

            # Headings containing common scheme indicators.
            if any(
                keyword in lower
                for keyword in (
                    "self-finance",
                    "self finance",
                    "regular",
                    "hostel",
                    "foreign",
                    "international",
                    "local",
                    "resident",
                    "non-resident",
                    "morning",
                    "evening",
                    "weekend",
                )
            ):
                return text

        return None
    
    def _extract_fee_records(
        self,
        *,
        section: dict,
        page_number: int,
        heading: str,
    ) -> list[FeeRecord]:

        records: list[FeeRecord] = []

        content = section.get(
            "content",
            [],
        )

        current_category: str | None = None
        current_context: str | None = None

        for raw_line in content:

            line = raw_line.strip()

            if not line:
                continue


            matches = list(
                self.AMOUNT_PATTERN.finditer(line)
            )

            if not matches:

                cleaned = self._normalize_category(
                    line
                )

                if cleaned:

                    line_type = self._classify_line(
                        cleaned
                    )

                    if line_type == "category":
                        current_category = cleaned

                    elif line_type == "context":
                        current_context = cleaned

                continue

            for match in matches:

                amount = (
                    match.group("amount")
                    .replace(",", "")
                )

                try:
                    value = float(amount)
                except ValueError:
                    continue

                records.append(
                    FeeRecord(
                        category=current_category,
                        amount=value,
                        currency="PKR",
                        payment_period=self._extract_payment_period(line),
                        scheme=self._extract_scheme_context(heading=heading, category=current_category, line=line,),
                        notes=current_context,
                        source_page=page_number,
                        source_heading=heading,
                        source_text=line,
                    )
                )
                current_context = None

        return records

