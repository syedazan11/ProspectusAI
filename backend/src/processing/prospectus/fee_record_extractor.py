import re

from src.processing.prospectus.fee_record import FeeRecord
from dataclasses import dataclass


@dataclass(slots=True)
class VisualLine:

    text: str

    items: list[dict]

    top: float

    left: float

    right: float

    height: float


@dataclass(slots=True)
class LogicalLine:

    text: str

    lines: list[VisualLine]

    left: float

    top: float

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
                
                layout_items = (
                    section.get("layout_items")
                    or []
                )
                if not layout_items:
                    continue

                visual_lines = (
                    self._build_visual_lines(
                        layout_items
                    )
                )

                columns = (
                    self._split_columns(
                        visual_lines
                    )
                )

                for column in columns:

                    normalized = (
                        self._normalize_fee_layout(
                            column
                        )
                    )

                    logical = (
                        self._merge_wrapped_rows(
                            normalized
                        )
                    )

                    records.extend(
                        self._parse_fee_rows(
                            logical_lines=logical,
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

    def _build_visual_lines(
        self,
        layout_items: list[dict],
    ) -> list[VisualLine]:

        buckets: dict[int, list[dict]] = {}

        for item in layout_items:

            text = item.get(
                "text",
                "",
            ).strip()
    
            if not text:
                continue
    
            top_bucket = round(
                item.get(
                    "top",
                    0,
                ) / 8
            )

            x_bucket = round(
                item.get(
                    "x",
                    0,
                ) / 250
            )

            key = (
                top_bucket,
                x_bucket,
            )

            buckets.setdefault(
                key,
                [],
            ).append(item)

        visual_lines: list[VisualLine] = []

        for key in sorted(buckets):

            row = sorted(
                buckets[key],
                key=lambda x: x.get(
                    "x",
                    0,
                ),
            )

            text = " ".join(
                cell["text"].strip()
                for cell in row
            ).strip()

            if not text:
                continue

            left = min(
                cell.get(
                    "x",
                    0,
                )
                for cell in row
            )

            right = max(
                cell.get(
                    "x",
                    0,
                )
                for cell in row
            )

            top = sum(
                cell.get(
                    "top",
                    0,
                )
                for cell in row
            ) / len(row)

            height = max(
                cell.get(
                    "height",
                    0,
                )
                for cell in row
            )

            visual_lines.append(
                VisualLine(
                    text=text,
                    items=row,
                    left=left,
                    right=right,
                    top=top,
                    height=height,
                )
            )

        return visual_lines

    def _split_columns(
        self,
        lines: list[VisualLine],
    ) -> list[list[VisualLine]]:
        """
        Split a page into reading columns.

        Returns one or two columns ordered
        from left to right.
        """

        if not lines:
            return []

        # Use only reasonably narrow lines to detect column layout.
        column_candidates = [
            line
            for line in lines
            if (line.right - line.left) < 350
        ]

        # Fall back if there aren't enough candidates.
        if len(column_candidates) < 6:
            column_candidates = lines

        xs = sorted(
            (line.left + line.right) / 2
            for line in column_candidates
        )

        if len(xs) < 6:
            return [sorted(
                lines,
                key=lambda x: x.top,
            )]

        gaps = []

        for i in range(len(xs) - 1):

            gap = xs[i + 1] - xs[i]

            gaps.append(
                (
                    gap,
                    i,
                )
            )

        largest_gap, index = max(gaps)

        print(f"[COLUMN DEBUG] largest_gap={largest_gap:.1f}")

        print("[COLUMN DEBUG] centres:")
        for line in sorted(lines, key=lambda l: (l.left + l.right) / 2):
            centre = (line.left + line.right) / 2
            print(
                f"left={line.left:.1f} "
                f"right={line.right:.1f} "
                f"centre={centre:.1f} "
                f"text={line.text[:60]}"
            )

        # No meaningful split.
        if largest_gap < 120:

            return [
                sorted(
                    lines,
                    key=lambda x: x.top,
                )
            ]

        boundary = (
            xs[index]
            + xs[index + 1]
        ) / 2

        left = []
        right = []

        for line in lines:

            center = (
                line.left + line.right
            ) / 2

            if center < boundary:
                left.append(line)
            else:
                right.append(line)

        columns = []

        if left:
            columns.append(
                sorted(
                    left,
                    key=lambda x: x.top,
                )
            )

        if right:
            columns.append(
                sorted(
                    right,
                    key=lambda x: x.top,
                )
            )

        return columns

    def _normalize_fee_layout(
        self,
        lines: list[VisualLine],
    ) -> list[VisualLine]:
        """
        Repair layout artefacts before parsing.
        This stage only modifies visual structure.
        It must never classify fee records.
        """
        if not lines:
            return []

        normalized: list[VisualLine] = []
        i = 0

        while i < len(lines):

            current = lines[i]

            if i + 1 >= len(lines):

                normalized.append(current)
                break
            nxt = lines[i + 1]
            vertical_gap = abs(
                nxt.top - current.top
            )
            same_indent = abs(
                nxt.left - current.left
            ) <= 30

            current_has_amount = bool(
                self.AMOUNT_PATTERN.search(
                    current.text
                )
            )
            next_has_amount = bool(
                self.AMOUNT_PATTERN.search(
                    nxt.text
                )
            )
            should_merge = (
                vertical_gap <= 18
                and same_indent
                and not current_has_amount
                and not next_has_amount
            )

            if should_merge:

                merged = VisualLine(
                    text=f"{current.text} {nxt.text}",
                    items=current.items + nxt.items,
                    top=current.top,
                    left=min(current.left, nxt.left),
                    right=max(current.right, nxt.right),
                    height=max(current.height, nxt.height),
                )

                normalized.append(merged)

                i += 2

                continue

            normalized.append(current)

            i += 1

        return normalized

    def _merge_wrapped_rows(
        self,
        lines: list[VisualLine],
    ) -> list[LogicalLine]:

        logical: list[LogicalLine] = []

        for line in lines:
            if not logical:

                logical.append(
                    LogicalLine(
                        text=line.text,
                        lines=[line],
                        left=line.left,
                        top=line.top,
                    )
                )
                continue
            previous = logical[-1]
            previous_line = previous.lines[-1]
            vertical_gap = (
                line.top
                - previous_line.top
            )
            indent_gap = abs(
                line.left
                - previous_line.left
            )
            same_indent = indent_gap <= 25
            current_has_amount = bool(
                self.AMOUNT_PATTERN.search(
                    line.text
                )
            )
            previous_has_amount = bool(
                self.AMOUNT_PATTERN.search(
                    previous.text
                )
            )

            previous_text = previous.text.strip()
            current_text = line.text.strip()

            previous_ends_open = (
                previous_text.endswith("&")
                or previous_text.endswith("(")
                or previous_text.endswith("/")
                or previous_text.endswith("-")
                or not previous_text.endswith((".", ":", ";"))
            )

            current_starts_new = bool(
                re.match(
                    r"""
                    ^
                    (
                        \d+(?:\.\d+)*\.?
                        |
                        [A-Za-z]\)
                        |
                        [ivxlcdmIVXLCDM]+\)
                    )
                    """,
                    current_text,
                    re.VERBOSE,
                )
            )

            continuation = (
                vertical_gap <= 20
                and same_indent
                and previous_ends_open
                and not current_starts_new
                and not current_has_amount
                and not previous_has_amount
            )

            if continuation:
                previous.text += (
                    " "
                    + line.text
                )
                previous.lines.append(
                    line
                )
            else:
                logical.append(
                    LogicalLine(
                        text=line.text,
                        lines=[line],
                        left=line.left,
                        top=line.top,
                    )
                )

        return logical


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
    
    def _parse_fee_rows(
        self,
        *,
        logical_lines: list[LogicalLine],
        page_number: int,
        heading: str,
    ) -> list[FeeRecord]:

        records: list[FeeRecord] = []

        current_category: str | None = None
        current_context: str | None = None
        pending_category: str | None = None

        for logical in logical_lines:

            line = logical.text.strip()

            if not line:
                continue


            matches = list(
                self.AMOUNT_PATTERN.finditer(line)
            )

            if not matches:

                cleaned = self._normalize_category(
                    line
                )

                if pending_category and cleaned:

                    combined = (
                        pending_category
                        + " "
                        + cleaned
                    )

                    if self._category_is_complete(
                        combined
                    ):

                        current_category = combined
                        pending_category = None
                    else:
                        pending_category = combined

                    continue

                if cleaned:

                    line_type = self._classify_line(
                        cleaned
                    )
                    if (
                        line_type == "category"
                        and self._is_valid_category(cleaned)
                    ):

                        if self._category_is_complete(
                            cleaned
                        ):

                            current_category = cleaned
                        else:
                            pending_category = cleaned

                    elif line_type == "context":

                        current_context = cleaned

                continue

            if pending_category is not None:

                current_category = pending_category
                pending_category = None

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

