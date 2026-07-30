import re

from src.processing.prospectus.admission_record import (
    AdmissionRecord,
)
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

class AdmissionExtractor:
    """
    Extract structured admission information.
    """

    SUBSECTION_PATTERN = re.compile(
        r"""
        ^
        (?P<number>
            \d+
            (?:\.\d+)*
            \.?
            (?:\s*\([a-z]\))?
        )
        \s+
        (?P<title>.+?)
        \s*$
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
                ) / 6
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
    
    def _is_number_fragment(
        self,
        text: str,
    ) -> bool:

        return bool(
            re.fullmatch(
                r"""
                ^
                \d+
                (?:\.\d+)*
                \.?
                (?:
                    \([a-z]\)
                    |
                    \.[a-z]
                )?
                $
                """,
                text.strip(),
                re.IGNORECASE | re.VERBOSE,
            )
        )

    def _is_list_marker(
        self,
        text: str,
    ) -> bool:

        return bool(
            re.fullmatch(
                r"""
                (
                    \(?[a-z]\)?
                    |
                    [ivxlcdm]+\.
                    |
                    [ivxlcdm]+\)
                    |
                    •
                    |
                    -
                )
                """,
                text.strip(),
                re.IGNORECASE | re.VERBOSE,
            )
        )

    def _normalize_column_layout(
        self,
        lines: list[VisualLine],
    ) -> list[VisualLine]:
        """
        Merge OCR fragments that belong to the same visual line.

        This operates after column detection, so all lines are
        already in reading order.
        """

        if not lines:
            return []

        # -------------------------------------------------
        # First pass:
        # Correct obvious OCR ordering inversions.
        # -------------------------------------------------

        normalized = list(lines)

        print("\n[NORMALIZE BEFORE]")
        for idx, line in enumerate(normalized):
            print(
                f"{idx:02d} "
                f"top={line.top:.1f} "
                f"left={line.left:.1f} "
                f"text={line.text}"
            )

        i = 1

        while i < len(normalized):

            previous = normalized[i - 1]
            current = normalized[i]

            nxt = (
                normalized[i + 1]
                if i + 1 < len(normalized)
                else None
            )

            print(
                "\n[WINDOW]",
                f"i={i}",
            )

            print(
                "PREV:",
                previous.left,
                previous.top,
                previous.text,
            )

            print(
                "CURR:",
                current.left,
                current.top,
                current.text,
            )

            if nxt:
                print(
                    "NEXT:",
                    nxt.left,
                    nxt.top,
                    nxt.text,
                )

            previous_is_number = self._is_number_fragment(previous.text)
            current_is_number = self._is_number_fragment(current.text)

            previous_is_marker = self._is_list_marker(previous.text)
            current_is_marker = self._is_list_marker(current.text)

            # Pattern 1:
            # TEXT
            # NUMBER
            #   ->
            # NUMBER
            # TEXT

            if (
                i >= 1
                and not previous_is_number
                and not previous_is_marker
                and (current_is_number or current_is_marker)
            ):

                vertical_gap = abs(current.top - previous.top)

                if (
                    vertical_gap < 20
                    and current.left < previous.left
                    and (previous.left - current.left) < 220
                ):
                    print(
                        "[SWAP]",
                        previous.text,
                        "<->",
                        current.text,
                    )

                    normalized[i - 1], normalized[i] = (
                        normalized[i],
                        normalized[i - 1],
                    )

                    previous = normalized[i - 1]
                    current = normalized[i]

            # Pattern 2:
            # TEXT
            # NUMBER
            # TEXT
            #   ->
            # NUMBER
            # TEXT
            # TEXT

            if i < len(normalized) - 1:

                nxt = normalized[i + 1]

                if (
                    not previous_is_number
                    and not previous_is_marker
                    and current_is_number
                    and not self._is_number_fragment(nxt.text)
                    and not self._is_list_marker(nxt.text)
                ):

                    if (
                        abs(previous.top - current.top) <= 25
                        and abs(nxt.top - current.top) <= 25
                        and current.left < previous.left
                        and (previous.left - current.left) < 320
                    ):

                        normalized[i - 1], normalized[i] = (
                            normalized[i],
                            normalized[i - 1],
                        )

            i += 1

        merged = []
        i = 0

        while i < len(normalized):

            current = normalized[i]
    # Merge standalone list marker with next line
    # c)
    # HSC Marks Sheet -> c) HSC Marks Sheet
            if (
                self._is_list_marker(current.text)
                and i + 1 < len(normalized)
            ):

                nxt = normalized[i + 1]

                if (
                    abs(current.top - nxt.top) <= 30
                    and nxt.left > current.left
                ):

                    merged.append(
                        VisualLine(
                            text=f"{current.text} {nxt.text}",
                            items=current.items + nxt.items,
                            top=current.top,
                            left=current.left,
                            right=max(current.right, nxt.right),
                            height=max(current.height, nxt.height),
                        )
                    )

                    i += 2
                    continue

            merged.append(current)
            i += 1
        # merged = []
        # i = 0

        # while i < len(normalized):

        #     current = normalized[i]

        #     if (
        #         self._is_list_marker(current.text)
        #         and i + 1 < len(normalized)
        #     ):

        #         previous = (
        #             normalized[i - 1]
        #             if i > 0
        #             else None
        #         )

        #         nxt = normalized[i + 1]

        #         # --------------------------------------------------
        #         # Decide whether this marker belongs to
        #         # the previous paragraph or the next line.
        #         # --------------------------------------------------

        #         attach_to_previous = False

        #         if previous is not None:

        #             previous_is_text = (
        #                 not self._is_list_marker(previous.text)
        #                 and not self._is_number_fragment(previous.text)
        #                 and self._match_subsection(previous.text) is None
        #             )

        #             next_is_text = (
        #                 not self._is_list_marker(nxt.text)
        #                 and not self._is_number_fragment(nxt.text)
        #                 and self._match_subsection(nxt.text) is None
        #             )

        #             if (
        #                 previous_is_text
        #                 and next_is_text
        #                 and abs(previous.left - nxt.left) <= 35
        #                 and current.left < previous.left
        #                 and abs(current.top - previous.top) <= 30
        #             ):
        #                 attach_to_previous = True

        #         # -------------------------
        #         # Merge with PREVIOUS
        #         # -------------------------

        #         if attach_to_previous:

        #             merged[-1] = VisualLine(
        #                 text=f"{current.text} {previous.text}",
        #                 items=current.items + previous.items,
        #                 top=current.top,
        #                 left=current.left,
        #                 right=max(current.right, previous.right),
        #                 height=max(current.height, previous.height),
        #             )

        #             i += 1
        #             continue

        #         # -------------------------
        #         # Merge with NEXT
        #         # -------------------------

        #         if (
        #             abs(current.top - nxt.top) <= 30
        #             and nxt.left > current.left
        #         ):

        #             merged.append(
        #                 VisualLine(
        #                     text=f"{current.text} {nxt.text}",
        #                     items=current.items + nxt.items,
        #                     top=current.top,
        #                     left=current.left,
        #                     right=max(current.right, nxt.right),
        #                     height=max(current.height, nxt.height),
        #                 )
        #             )

        #             i += 2
        #             continue

            # normalized = merged

            # merged.append(current)
            # i += 1

        normalized = merged

        merged = []
        i = 0

        while i < len(normalized):

            current = normalized[i]

    # Pattern:
    # Text
    # d)
    # Continuation -> d) Text
    # Continuation
            if (
                i + 1 < len(normalized)
                and not self._is_list_marker(current.text)
                and self._is_list_marker(normalized[i + 1].text)
            ):

                marker = normalized[i + 1]

                if (
                    abs(marker.top - current.top) <= 30
                    and marker.left < current.left
                ):

                    merged.append(
                        VisualLine(
                            text=f"{marker.text} {current.text}",
                            items=marker.items + current.items,
                            top=marker.top,
                            left=marker.left,
                            right=max(marker.right, current.right),
                            height=max(marker.height, current.height),
                        )
                    )

                    i += 2
                    continue

            merged.append(current)
            i += 1

        normalized = merged
        print("\n[AFTER MARKER MERGE]")
        for idx, line in enumerate(normalized):
            print(
                f"{idx:02d} "
                f"top={line.top:.1f} "
                f"left={line.left:.1f} "
                f"text={line.text}"
            )

        merged: list[VisualLine] = []

        i = 0

        while i < len(normalized):

            current = normalized[i]

            if i == len(normalized) - 1:
                merged.append(current)
                break

            nxt = normalized[i + 1]

            current_text = current.text.strip()
            next_text = nxt.text.strip()

            vertical_gap = (
                nxt.top
                - current.top
            )

            current_is_number = self._is_number_fragment(
                current_text
            )

            next_is_number = self._is_number_fragment(
                next_text
            )

            if (
                current_is_number
                and not next_is_number
                and vertical_gap < 20
            ):

                merged.append(
                    VisualLine(
                        text=current_text + " " + next_text,
                        items=current.items + nxt.items,
                        top=current.top,
                        left=min(
                            current.left,
                            nxt.left,
                    ),
                        right=max(
                            current.right,
                            nxt.right,
                        ),
                        height=max(
                            current.height,
                            nxt.height,
                        ),
                    )
                )

                i += 2
                continue

            merged.append(current)

            i += 1

        return merged

    def _merge_wrapped_lines(
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

            marker_match = re.match(
                r"^(\(?[a-z]\)|[ivxlcdm]+\)|[ivxlcdm]+\.)\s+(.+)$",
                line.text,
                re.IGNORECASE,
            )

            original_line_text = line.text

            previous_has_marker = bool(
                re.match(
                    r"^(\(?[a-z]\)|[ivxlcdm]+\)|[ivxlcdm]+\.)\s+",
                    previous.text,
                    re.IGNORECASE,
                )
            )

            # if (
            #     marker_match
            #     and not previous_has_marker
            # ):

            #     continuation = marker_match.group(2)

            #     if (
            #         continuation
            #         and continuation[0].islower()
            #         and (line.top - previous_line.top) < 22
            #     ):

            #         previous.text = (
            #             f"{marker_match.group(1)} "
            #             f"{previous.text}"
            #         )

            #         line.text = continuation

            vertical_gap = (
                line.top
                - previous_line.top
            )

            # indent_gap = abs(
            #     line.left
            #     - previous_line.left
            # )

            indent_gap = abs(line.left - previous_line.left)

            allowed_indent = max(
                40,
                previous_line.height * 3,
            )

            same_indent = indent_gap <= allowed_indent

            marker_continuation = False

            previous_ends_sentence = previous.text.rstrip().endswith(
               (
                    ".",
                    ":",
                    ";",
                    "?",
                    "!",
                )
            )

            if marker_match:

                continuation_text = marker_match.group(2)

                # previous_ends_sentence = previous.text.rstrip().endswith(
                #     (
                #         ".",
                #         ":",
                #         ";",
                #         "?",
                #         "!",
                #     )
                # )


                if (
                    not previous_has_marker
                    and len(previous.lines) == 1
                    and continuation_text
                    and vertical_gap < 22
                    and not previous_ends_sentence
                    and not re.match(
                        r"^\s*(?:\d+(?:\.\d+)*|[a-z]\)|[ivxlcdm]+[\.)]|•|-)",
                        continuation_text,
                        re.IGNORECASE,
                    )
                ):
                    marker_continuation = True

                    previous.text = (
                        f"{marker_match.group(1)} "
                        f"{previous.text}"
                    )

                    line.text = continuation_text

            # starts_new_block = (
            #     self._match_subsection(line.text) is not None
            #     or bool(
            #         re.match(
            #             r"""
            #             ^
            #             (
            #                 \(?[a-z]\)
            #                 |
            #                 [ivxlcdm]+\)
            #                 |
            #                 •
            #                 |
            #                 -
            #             )
            #             """,
            #             line.text,
            #             re.IGNORECASE | re.VERBOSE,
            #         )
            #     )
            # )

            starts_new_block = (
                self._match_subsection(original_line_text) is not None
                or (
                    bool(
                        re.match(
                            r"""
                            ^
                            (
                                \(?[a-z]\)
                                |
                                [ivxlcdm]+\)
                                |
                                [ivxlcdm]+\.
                                |
                                •
                                |
                                -
                            )
                            """,
                            original_line_text,
                            re.IGNORECASE | re.VERBOSE,
                        )
                    )
                    and not marker_continuation
                )
            )

            # continuation = (
            #     not starts_new_block
            #     # and vertical_gap < 18
            #     and vertical_gap < 30
            #     # and indent_gap < 35
            # )
            continuation = (
                not starts_new_block
                and (
                    vertical_gap < 30
                    or (
                        not previous_ends_sentence
                        and vertical_gap < 45
                    )
                )
            )

            # previous_ends_sentence = previous.text.rstrip().endswith(
            #     (
            #         ".",
            #         ":",
            #         ";",
            #         "?",
            #         "!",
            #     )
            # )

            # # current_starts_lower = (
            # #     line.text
            # #     and line.text[0].islower()
            # # )

            # continuation = (
            #     not starts_new_block
            #     and (
            #         (
            #             vertical_gap < 18
            #             and not previous_ends_sentence
            #         )
            #         or
            #         (
            #             vertical_gap < 28
            #             and current_starts_lower
            #         )
            #     )
            # )

            print(
                "\n[CONTINUATION CHECK]"
            )

            print(
                "PREVIOUS:",
                repr(previous.text)
            )

            print(
                "CURRENT :",
                repr(line.text)
            )

            print(
                {
                    "vertical_gap": vertical_gap,
                    "indent_gap": indent_gap,
                    "same_indent": same_indent,
                    "starts_new_block": starts_new_block,
                    "marker_continuation": marker_continuation,
                    "previous_ends_sentence": previous_ends_sentence,
                    "continuation": continuation,
                }
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
        print("\n===== LOGICAL LINES =====")

        for i, item in enumerate(logical):
            print(
                f"{i:02d}",
                repr(item.text)
            )

        return logical
    
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
    
    def _match_subsection(
        self,
        text: str,
    ) -> re.Match | None:

        return self.SUBSECTION_PATTERN.match(
            text.strip()
        )

    def _clean_text(
        self,
        text: str,
    ) -> str:

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        text = text.replace(
            "•",
            ""
        )

        text = text.strip()

        return text

    def _parse_content(
        self,
        lines: list[str],
    ) -> list[dict]:

        parsed = []

        for line in lines:

            match = re.match(
                r"^([a-z]\)|[ivxlcdm]+[\.)]|•|-)\s*(.+)$",
                line,
                re.IGNORECASE,
            )

            if match:

                parsed.append(
                    {
                        "marker": match.group(1),
                        "text": match.group(2).strip(),
                    }
                )

            else:

                parsed.append(
                    {
                        "marker": None,
                        "text": line,
                    }
                )

        return parsed
    
    def _extract_logical_lines(
        self,
        *,
        logical_lines: list[LogicalLine],
        page_number: int,
        heading: str,
    ) -> list[AdmissionRecord]:

        print("ENTERED _extract_logical_lines")

        records: list[AdmissionRecord] = []

        current_title: str | None = None
        current_number: str | None = None
        current_parent: str | None = None

        current_lines: list[str] = []
        intro_lines: list[str] = []

        def flush():

            nonlocal current_title
            nonlocal current_number
            nonlocal current_lines
            nonlocal current_parent

            if not current_title:
                return

            body = "\n".join(
                current_lines
            ).strip()

            source_text = current_title

            if body:
                source_text += (
                    "\n"
                    + body
                )

            records.append(
                AdmissionRecord(
                    number=current_number or "",
                    parent=current_parent,
                    title=current_title,
                    content=self._parse_content(
                        current_lines
                    ),
                    source_page=page_number,
                    source_heading=heading,
                    source_text=source_text,
                )
            )

            current_title = None
            current_number = None
            current_parent = None
            current_lines = []

        for logical in logical_lines:

            text = self._clean_text(
                logical.text
            )
            # print(repr(text))
            print(text.encode("unicode_escape").decode())

            if len(text) < 3:
                continue

            if text.lower() in {
                "chapter",
                "contents",
                "prospectus",
            }:
                continue

            if not text:
                continue

            match = self._match_subsection(text)

            if match:
                flush()
                # current_number = match.group(
                #     "number"
                # )
                current_number = match.group("number").strip()

                parts = re.findall(r"\d+", current_number)

                if len(parts) <= 1:
                    current_parent = None
                else:
                    current_parent = ".".join(parts[:-1])

                current_title = self._clean_text(
                    match.group("title")
                )

                current_lines = []

                if intro_lines:

                    current_lines.extend(
                        intro_lines
                    )

                    intro_lines.clear()

                continue

            if current_title is None:

                intro_lines.append(
                    text
                )
                continue

            current_lines.append(text)

        flush()

        return records

    def _deduplicate(
        self,
        records: list[AdmissionRecord],
    ) -> list[AdmissionRecord]:

        merged: dict[str, AdmissionRecord] = {}

        for record in records:

            key = (
                f"{record.number}|"
                f"{record.title.lower().strip()}"
            )

            existing = merged.get(key)

            if existing is None:
                merged[key] = record
                continue

            if (
                len(record.content)
                >
                len(existing.content)
            ):
                existing.content = (
                    record.content
                )

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

    def extract(
        self,
        pages: list[dict],
    ) -> list[AdmissionRecord]:

        print(f"extract() received {len(pages)} pages")

        records: list[AdmissionRecord] = []

        for page in pages:

            print(
                f"Page {page['page_number']} "
                f"sections={len(page.get('sections', []))}"
            )

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

                layout_items = (
                    section.get(
                        "layout_items"
                    )
                    or []
                )

                # # Fallback for older documents.
                # if not layout_items:

                #     records.extend(
                #         self._extract_section(
                #             section=section,
                #             page_number=page_number,
                #             heading=heading,
                #         )
                #     )

                #     continue

                if not layout_items:
                    print(f"Skipping page {page_number}, heading '{heading}' (no layout_items)")
                    continue

                print(
                    f"Page {page_number} | Heading: {heading} | layout_items={len(layout_items)}"
                )

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

                print(f"Columns: {len(columns)}")

                for column in columns:

                    print(f"Column lines: {len(column)}")

                    column = self._normalize_column_layout(
                        column
                    )

                    logical_lines = (
                        self._merge_wrapped_lines(
                            column
                        )
                    )

                    records.extend(
                        self._extract_logical_lines(
                            logical_lines=logical_lines,
                            page_number=page_number,
                            heading=heading,
                        )
                    )

        return self._deduplicate(
            records
        )
    
#     def extract(
#         self,
#         pages: list[dict],
#     ) -> list[AdmissionRecord]:

#         records: list[AdmissionRecord] = []

#         for page in pages:

#             page_number = page["page_number"]

#             for section in page.get(
#                 "sections",
#                 [],
#             ):

#                 heading = section.get(
#                     "heading",
#                     "",
#                 ).strip()

#                 records.extend(
#                     self._extract_section(
#                         section=section,
#                         page_number=page_number,
#                         heading=heading,
#                     )
#                 )

#         return records

#     def _extract_section(
#         self,
#         *,
#         section: dict,
#         page_number: int,
#         heading: str,
#     ) -> list[AdmissionRecord]:

#         records: list[AdmissionRecord] = []

#         current_title: str | None = None
#         current_details: dict[str, str] = {}
#         current_block: list[str] = []

#         content = section.get(
#             "content",
#             [],
#         )

#         for index, line in enumerate(
#             content
#         ):

#             line = line.strip()

#             if not line:
#                 continue

#             if len(line) < 3:
#                 continue

#             if line.count("|") >= 2:
#                 continue

#             if line.count("...") >= 2:
#                 continue

#             if (
#                 not self._looks_like_attribute(line)
#                 and self._looks_like_title(line)
#             ):
                
#                 if self._is_non_admission_title(
#                     line
#                 ):
#                     continue

#                 if (
#                     current_title is not None
#                     and index + 1 < len(content)
#                 ):

#                     next_line = (
#                         content[index + 1]
#                         .strip()
#                     )

#                     if self._should_merge_title(
#                         current_title,
#                         next_line,
#                     ):

#                         current_title += (
#                             " " + next_line
#                         )

#                         current_block.append(
#                             next_line
#                         )

#                         continue

#                 if current_title is not None:

#                     records.append(
#                         AdmissionRecord(
#                             title=current_title,
#                             category=heading,
#                             details=current_details,
#                             source_page=page_number,
#                             source_heading=heading,
#                             source_text="\n".join(
#                                 current_block
#                             ),
#                         )
#                     )

#                 current_title = line
#                 current_details = {}
#                 current_block = [line]

#                 continue

#             if (
#                 current_title
#                 and self._looks_like_attribute(
#                     line
#                 )
#             ):

#                 key, value = self._parse_attribute(
#                     line
#                 )

#                 if key:

#                     current_details[key] = value

#                 current_block.append(
#                     line
#                 )

#         if current_title is not None:

#             records.append(
#                 AdmissionRecord(
#                     title=current_title,
#                     category=heading,
#                     details=current_details,
#                     source_page=page_number,
#                     source_heading=heading,
#                     source_text="\n".join(
#                         current_block
#                     ),
#                 )
#             )

#         return records
    
#     def _should_merge_title(
#         self,
#         current: str,
#         nxt: str,
#     ) -> bool:
#         """
#         Decide whether the next OCR line
#         is a continuation of the current title.
#         """

#         current = current.strip()
#         nxt = nxt.strip()

#         if not current or not nxt:
#             return False

#         # Don't merge attributes.
#         if self._looks_like_attribute(
#             nxt
#         ):
#             return False

#         # Don't merge document headings.
#         if self._is_non_admission_title(
#             nxt
#         ):
#             return False

#         # Don't merge URLs.
#         if (
#             "www." in nxt.lower()
#             or "http" in nxt.lower()
#         ):
#             return False

#         # Continuation lines are usually short.
#         if len(nxt.split()) > 4:
#             return False

#         # Lowercase continuation.
#         if nxt[0].islower():
#             return True

#         # One or two trailing words.
#         if len(nxt.split()) <= 2:
#             return True

#         return False
    
#     def _looks_like_title(
#         self,
#         line: str,
#     ) -> bool:

#         text = line.strip()

#         if not text:
#             return False

#         # Pure section numbers are not titles.
#         if re.fullmatch(
#             r"\d+(?:\.\d+)+",
#             text,
#         ):
#             return False
        
#         if (
#                 "www." in text.lower()
#                 or "http" in text.lower()
#                 or ".pk" in text.lower()
#                 or ".com" in text.lower()
#             ):
#                 return False


#         if ":" in text:
#             return False

#         if len(text) < 5:
#             return False

#         if len(text) > 80:
#             return False
        
#         words = text.split()

#         # Headings are concise.
#         if len(words) > 8:
#             return False
        
#         # Reject sentence-like titles.
#         common_starts = {
#             "the",
#             "a",
#             "an",
#             "all",
#             "any",
#             "every",
#             "each",
#             "candidate",
#             "candidates",
#             "applicant",
#             "applicants",
#             "students",
#             "student",
#             "he",
#             "she",
#             "they",
#             "you",
#         }

#         if words[0].lower() in common_starts:
#             return False

#         if len(text.split()) > 10:
#             return False

#         if text.endswith(
#             (
#                 ".",
#                 ";",
#                 "?",
#                 "!",
#             )
#         ):
#             return False

#         # Mostly numeric.
#         letters = sum(
#             c.isalpha()
#             for c in text
#         )

#         digits = sum(
#             c.isdigit()
#             for c in text
#         )

#         if digits > letters:
#             return False

#         if letters < 5:
#             return False

#         # Starts with lowercase -> probably prose.
#         if words[0][0].islower():
#             return False
        
#         verbs = (
#             "shall",
#             "should",
#             "must",
#             "may",
#             "will",
#             "required",
#             "advised",
#         )

#         if any(
#             verb in text.lower()
#             for verb in verbs
#         ):
#             return False
#         bad_endings = (
#             "and",
#             "or",
#             "of",
#             "to",
#             "for",
#             "with",
#             "in",
#         )

#         if words[-1].lower() in bad_endings:
#             return False

#         return True
    
#     def _is_non_admission_title(
#         self,
#         text: str,
#     ) -> bool:

#         lower = text.lower()

#         blocked = {
#             "chapter",
#             "contents",
#             "prospectus",
#             "admission",
#             "eligibility",
#             "general guidance",
#             "required documents",
#             "document required",
#             "notes",
#             "note",
#             "prospectus",
#             "technology",
#             "engineering",
#             "official",
#             "website",
#             "facebook",
#             "youtube",
#             "instagram",
#             "twitter",
#             "linkedin",
#             "neduetofficial",
#             "nepoid",
#             "nepidl",

#         }

#         if lower in blocked:
#             return True

#         # OCR garbage.
#         letters = sum(
#             c.isalpha()
#             for c in text
#         )

#         if letters < 5:
#             return True

#         return False
    
#     def _looks_like_attribute(
#         self,
#         line: str,
#     ) -> bool:
#         """
#         Detect generic key/value style
#         admission attributes.
#         """

#         text = line.strip()

#         if not text:
#             return False
        
#         if len(text) > 120:
#             return False

#         if re.fullmatch(
#             r"\d+(?:\.\d+)+",
#             text,
#         ):
#             return False

#         if ":" in text:
#             return True

#         if " - " in text:
#             return True

#         if "..." in text:
#             return True

#         words = text.split()

#         if (
#             2 <= len(words) <= 8
#             and any(
#                 ch.isdigit()
#                 for ch in text
#             )
#         ):
#             return True

#         return False
    
#     def _parse_attribute(
#         self,
#         line: str,
#     ) -> tuple[str | None, str]:

#         text = line.strip()

#         separators = (
#             ":",
#             " - ",
#             "...",
#         )

#         for separator in separators:

#             if separator in text:

#                 key, value = text.split(
#                     separator,
#                     1,
#                 )

#                 key = (
#                     key.strip()
#                     .lower()
#                     .replace(
#                         " ",
#                         "_",
#                     )
#                 )

#                 return (
#                     key,
#                     value.strip(),
#                 )

#         words = text.split()

#         if len(words) >= 2:

#             split_index = None

#             for i, word in enumerate(words):

#                 if any(
#                     ch.isdigit()
#                     for ch in word
#                 ):
#                     split_index = i
#                     break

#             if split_index is None:
#                 split_index = len(words) - 1

#             if split_index > 0:

#                 key = "_".join(
#                     words[:split_index]
#                 ).lower()

#                 value = " ".join(
#                     words[split_index:]
#                 )

#                 return (
#                     key,
#                     value,
#                 )

#         return (
#             None,
#             "",
#         )