from __future__ import annotations
 
import json
from pathlib import Path
import re
import statistics
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from enum import Enum
from src.processing.prospectus.section_detector import (
    ProspectusSectionDetector,
)
class StructureType(str, Enum):

    DOCUMENT_HEADING = "document_heading"

    LABEL = "label"

    LIST_ITEM = "list_item"

    PARAGRAPH = "paragraph"

    TABLE_ROW = "table_row"

    UNKNOWN = "unknown"

 
# ============================================================
# Shared data model
# ============================================================
 
@dataclass
class SemanticBlock:
 
    type: str        # "heading" | "list" | "paragraph"
    heading: str      # heading text, or the list's anchor label, or "" for paragraph
 
    text: str
 
    page: int
    depth: int = 0
 
    path: list = field(default_factory=list)   # ancestor heading titles, root -> parent
 
    rows: list = field(default_factory=list)
 
    top: float = 0
    bottom: float = 0
 
    left: float = 0
    right: float = 0
 
 
@dataclass
class HierarchyNode:
    """One node of the document tree. `block` is None only for the invisible root."""
    block: object = None
    children: list = field(default_factory=list)
 
 
class ReadingOrderReconstructor:
    """Phase 1 - unchanged, this part already works."""
 
    def reconstruct(
        self,
        layout_items,
        page_number,
        section=None,
    ):
 
        # body = self.strip_header_footer(layout_items)
 
        # columns = self.detect_columns(body)
 
        # rows = []
 
        # for column_index, column in enumerate(columns):
        #     rows.extend(
        #         self.cluster_rows(column
        #                           , page_number, column_index,)
        #     )
 
        # return rows
        body = self.strip_header_footer(layout_items)

        regions = self.segment_page(body,section,page_number)

        rows = []

        for region in regions:
            rows.extend(
                self.reconstruct_region(
                    region,
                    page_number,
                )
            )

        return rows
 
    # -------------------------------------------------
 
    def strip_header_footer(
        self,
        items,
    ):

        if not items:
            return items

        tops = sorted(item["top"] for item in items)
        bottoms = sorted(item["bottom"] for item in items)

        top_limit = tops[0]
        bottom_limit = bottoms[-1]

        filtered = []

        for item in items:

            text = item["text"].strip()

            if not text:
                continue

            if len(text) <= 2:
                filtered.append(item)
                continue

            # page header

            if item["bottom"] <= top_limit + 45:
                continue

            # footer

            if item["top"] >= bottom_limit - 45:
                continue
    
            filtered.append(item)

        return filtered
 
    # -------------------------------------------------
 
    def detect_columns(
        self,
        items,
    ):
 
        if len(items) < 10:
            return [items]

        body_items = []

        for item in items:

            text = item["text"].strip()

            if text.startswith("Department"):
                continue

            if re.match(r"^\d+\.\d+\.\d+", text):
                continue

            body_items.append(item)

        if len(body_items) >= 10:
            ordered = sorted(body_items, key=lambda x: x["x"])
        else:
            ordered = sorted(items, key=lambda x: x["x"])
 
        ordered = sorted(
            items,
            key=lambda x: x["x"],
        )
 
        centers = [
            item["x"]
            for item in ordered
        ]
 
        gaps = [
            centers[i + 1] - centers[i]
            for i in range(len(centers) - 1)
        ]
 
        if not gaps:
            return [items]
 
        median_gap = statistics.median(gaps)
 
        largest_gap = max(gaps)
 
        if largest_gap < median_gap * 2.5:
            return [items]
 
        split_index = gaps.index(largest_gap)
 
        split_x = (
            centers[split_index]
            + centers[split_index + 1]
        ) / 2
 
        left = []
        right = []
 
        for item in items:
 
            if item["x"] < split_x:
                left.append(item)
            else:
                right.append(item)
 
        if not left or not right:
            return [items]
 
        return [
            left,
            right,
        ]
 
    # -------------------------------------------------
 
    def cluster_rows(
        self,
        items,
        page_number,
        column,
    ):
 
        if not items:
            return []
 
        items = sorted(
            items,
            key=lambda x: (
                x["top"],
                x["x"],
            ),
        )
 
        median_height = statistics.median(
            max(
                1,
                x["bottom"] - x["top"],
            )
            for x in items
        )
 
        tolerance = max(
            median_height * 0.6,
            8,
        )
 
        rows = []
 
        for item in items:
 
            center = (
                item["top"] +
                item["bottom"]
            ) / 2
 
            if not rows:
 
                rows.append({
                    "center": center,
                    "items": [item],
                })
 
                continue
 
            if abs(
                center -
                rows[-1]["center"]
            ) <= tolerance:
 
                rows[-1]["items"].append(item)
 
                n = len(rows[-1]["items"])
 
                rows[-1]["center"] = (
                    rows[-1]["center"] * (n - 1)
                    + center
                ) / n
 
            else:
 
                rows.append({
                    "center": center,
                    "items": [item],
                })
 
        result = []
 
        for row in rows:
 
            items = sorted(
                row["items"],
                key=lambda x: x["x"],
            )
 
            result.append({
                "page": page_number,
                "column": column,
                "top": min(
                    item["top"]
                    for item in items
                ),
                "bottom": max(
                    item["bottom"]
                    for item in items
                ),
                "items": items,
                "text": " ".join(
                    item["text"].strip()
                    for item in items
                    if item["text"].strip()
                ),
                "marker": None,
                "row_type": None,
                "thread": None,
            })
 
        return result


    
    def segment_page(self, items, section, page_number):
        if (
            section is None
            or section.section_type != "academics"
        ):
            return [items]

        return self.segment_academics_page(items, page_number)

    # def _find_department_headings(
    #     self,
    #     items,
    #     page_number,
    # ):

    #     tokenizer = MarkerTokenizer()

    #     ordered = sorted(
    #         items,
    #         key=lambda x: (x["top"], x["x"]),
    #     )

    #     if not ordered:
    #         return []

    #     page_top = ordered[0]["top"]

    #     headings = []

    #     i = 0

    #     while i < len(ordered):

    #         item = ordered[i]

    #         if item["top"] < page_top + 150:
    #             i += 1
    #             continue

    #         candidate = item["text"].strip()

    #         matched_item = None

    #         for j in range(0, 3):

    #             if i + j >= len(ordered):
    #                 break

    #             if j > 0:
    #                 candidate += " " + ordered[i + j]["text"].strip()

    #             marker = tokenizer.tokenize(candidate)

    #             if (
    #                 marker
    #                 and marker["family"].startswith("decimal")
    #                 and marker["depth"] >= 3
    #             ):
    #                 matched_item = ordered[i + j]
    #                 break

    #         if matched_item:

    #             headings.append(matched_item)

    #             i += j + 1

    #         else:

    #             i += 1
    # def _find_department_headings(
    #     self,
    #     items,
    #     page_number,
    # ):

    #     ordered = sorted(
    #         items,
    #         key=lambda x: (x["top"], x["x"]),
    #     )

    #     if not ordered:
    #         return []

    #     page_top = ordered[0]["top"]

    #     headings = []

    #     i = 0

    #     while i < len(ordered):

    #         item = ordered[i]

    #         if item["top"] < page_top + 150:
    #             i += 1
    #             continue

    #         text = item["text"].strip()

    #     #
    #     # Case 1
    #     # 2.2.2 Department...
    #     #

    #         if re.match(r"^\d+\.\d+\.\d+", text):

    #             headings.append(item)
    #             i += 1
    #             continue

    #     #
    #     # Case 2
    #     # 2.2.2
    #     # Department...
    #     #

    #         if re.match(r"^\d+\.\d+\.\d+$", text):

    #             if i + 1 < len(ordered):

    #                 nxt = ordered[i + 1]

    #                 if "Department" in nxt["text"]:

    #                     headings.append(nxt)

    #                     i += 2
    #                     continue

    #     #
    #     # Case 3
    #     # Department...
    #     #

    #         if (
    #             text.startswith("Department ")
    #             or text.startswith("Department of ")
    #         ):

    #             headings.append(item)

    #         i += 1

    #     print(f"PAGE {page_number}: {len(headings)} headings")

    #     for h in headings:
    #         print(f"    {h['top']:.1f} {h['text']}")

    #     return headings

    def _find_department_headings(
        self,
        items,
        page_number,
    ):

        ordered = sorted(
            items,
            key=lambda x: (x["top"], x["x"]),
        )

        if not ordered:
            return []

        page_top = ordered[0]["top"]

        headings = []

        i = 0

        while i < len(ordered):

            item = ordered[i]

            if item["top"] < page_top + 150:
                i += 1
                continue

            text = item["text"].strip()

        # -------------------------------------------------------
        # Full heading already in one layout item
        # -------------------------------------------------------

            if re.match(r"^\d+\.\d+\.\d+.*Department", text):

                headings.append(item)
                i += 1
                continue

        # -------------------------------------------------------
        # Number and Department split across two items
        # 2.2.4
        # Department of Earthquake Engineering
        # -------------------------------------------------------

            if re.match(r"^\d+\.\d+\.\d+(?:\([^)]+\))?$", text):

                if i + 1 < len(ordered):

                    nxt = ordered[i + 1]

                    if nxt["text"].startswith("Department"):

                    #
                    # ONLY append the Department row.
                    # Never append both.
                    #

                        headings.append(nxt)

                        i += 2
                        continue

        # -------------------------------------------------------
        # Fallback
        # -------------------------------------------------------

            if text.startswith("Department"):

                headings.append(item)

            i += 1

        print(f"PAGE {page_number}: {len(headings)} headings")

        for h in headings:
            print(f"    {h['top']:.1f} {h['text']}")

        return headings

    def segment_academics_page(self, items, page_number):

        headings = self._find_department_headings(
            items,
            page_number,
        )
        print(
            f"PAGE {page_number}: {len(headings)} headings"
        )

        if not headings:
            return [items]

        headings.sort(key=lambda h: h["top"])

        split_points = [0.0]

        split_points.extend(
            h["top"]
            for h in headings
        )

        split_points.append(float("inf"))

        regions = []

        for start, end in zip(
            split_points[:-1],
            split_points[1:],
        ):

            region = [

                item

                for item in items

                if start <= item["top"] < end

            ]

            if region:
                regions.append(region)

        return regions

            
    
    def reconstruct_region(
        self,
        items,
        page_number,
    ):

        columns = self.detect_columns(items)

        rows = []

        for column_index, column in enumerate(columns):
            rows.extend(
                self.cluster_rows(
                    column,
                    page_number,
                    column_index,
                )
            )

        return rows
 
 
# ============================================================
# Shared marker tokenizer
#
# Both DocumentSurvey (Pass 0) and RowClassifier (Pass 1) need to parse
# "1.", "2.2.1", "(iv)", "(a)" the same way, so the parsing logic lives in
# one small, stateless class instead of being duplicated.
# ============================================================
 
class GapSplitter:
    """
    Same idiom ReadingOrderReconstructor.detect_columns already uses to find
    a column break: sort the values, and only split where the largest gap is
    disproportionately bigger than the *typical* gap (median), not merely
    the biggest of however many gaps happen to exist. With too few points to
    have a meaningful median, or a gap that isn't actually an outlier, no
    split happens - callers get everything back as "no outliers", the safe
    default. This means the returned "high" cluster is genuinely unusual for
    THIS document, not just whichever value happened to be largest.
    """
 
    RATIO = 2.5   # same constant already in use (and already approved) in detect_columns
 
    @classmethod
    def high_outliers(cls, values_by_key: dict) -> set:
 
        items = sorted(values_by_key.items(), key=lambda kv: kv[1])
        if len(items) < 2:
            return set()
 
        values = [v for _, v in items]
        gaps = [values[i + 1] - values[i] for i in range(len(values) - 1)]
 
        median_gap = statistics.median(gaps)
        largest_gap = max(gaps)
 
        if largest_gap == 0:
            return set()
 
        if median_gap > 0 and largest_gap < median_gap * cls.RATIO:
            return set()
 
        split_index = gaps.index(largest_gap)
        return {k for k, v in items[split_index + 1:]}
 
 
class MarkerTokenizer:
    """Purely syntactic marker parsing. No vocabulary, no keywords."""
 
    DECIMAL_RE = re.compile(r"^(\d+(?:\.\d+)*)\.?\s+(\S.*)$")
    ROMAN_DOT_RE = re.compile(
        r"^([IVXLCDM]{2,8})\.?\s+(\S.*)$",
        re.I,
    )
    ROMAN_RE = re.compile(r"^\(([ivxlcdm]{1,6})\)\s+(\S.*)$", re.I)
    ROMAN_PARENLESS_RE = re.compile(
        r"^([ivxlcdm]{1,8})\)\s+(\S.*)$",
        re.I,
    )
    LETTER_RE = re.compile(r"^\(?([a-hj-uw-z])\)\s+(\S.*)$", re.I)
 
    ROMAN_VALUES = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100, "d": 500, "m": 1000}
 
    # single-character markers that are simultaneously valid roman numerals
    # AND valid list letters (c, d, l, m, x - LETTER_RE already excludes the
    # unambiguous i/v). A lone "(c)" in an ordinary (a)(b)(c) list is far
    # more likely than a one-off roman numeral "100", so these only count as
    # roman once there's a second character removing the ambiguity (ii, iv,
    # xi, ...); a single one of these falls through to LETTER_RE instead.
    AMBIGUOUS_SINGLE_ROMAN = {"x", "l", "c", "d", "m"}
 
    def tokenize(self, text):
 
        text = text.strip()
 
        m = self.DECIMAL_RE.match(text)
        if m:
            parts = m.group(1).split(".")
            try:
                index = int(parts[-1])
            except ValueError:
                return None
            return {"family": f"decimal-d{len(parts)}", "index": index, "depth": len(parts)}

        m = self.ROMAN_DOT_RE.match(text)
        if m:
            token = m.group(1).lower()
            return {
                "family": "roman-dot",
                "index": self._roman_to_int(token),
                "depth": 1,
            }

        m = self.ROMAN_RE.match(text)
        if m:
            token = m.group(1).lower()
            if not (len(token) == 1 and token in self.AMBIGUOUS_SINGLE_ROMAN):
                return {"family": "roman-paren", "index": self._roman_to_int(token), "depth": 1}
            # else: ambiguous single letter - fall through and let LETTER_RE below decide

        m = self.ROMAN_PARENLESS_RE.match(text)
        if m:
            token = m.group(1).lower()
            if not (
                len(token) == 1
                and token in self.AMBIGUOUS_SINGLE_ROMAN
            ):
                return {
                    "family": "roman-parenless",
                    "index": self._roman_to_int(token),
                    "depth": 1,
                }
 
        m = self.LETTER_RE.match(text)
        if m:
            token = m.group(1).lower()
            return {"family": "letter-paren", "index": ord(token) - ord("a") + 1, "depth": 1}
 
        return None
 
    def _roman_to_int(self, s):
        s = s.lower()
        total, prev = 0, 0
        for ch in reversed(s):
            v = self.ROMAN_VALUES.get(ch, 0)
            total += -v if v < prev else v
            prev = max(prev, v)
        return total
 
 
# ============================================================
# Pass 0 - DocumentSurvey
# ============================================================
 
class DocumentSurvey:
    """
    Pass 0.
 
    Input  : the WHOLE document's row stream (list[dict], each with "text").
    Output : dict[family] -> "heading" | "list"
 
    No fixed thresholds. Two signals, both derived from THIS document only:
 
      1. Structural fact: a family that resets even once is, by definition,
         being reused across multiple contexts - that alone makes it a list
         marker (outline numbering never restarts mid-document).
 
      2. For families that happen to never reset (e.g. only one instance of
         that list exists anywhere in the doc, so there was nothing to reset
         against), fall back to comparing occurrence COUNT against every
         other family's count via the same largest-gap split used in
         detect_columns: sort the counts, find the one biggest jump, and
         call whatever sits above it an outlier -> list. Where that cutoff
         falls is whatever this specific document's own numbering implies,
         not a number picked in advance.
    """
 
    def __init__(self, tokenizer=None):
        self.tokenizer = tokenizer or MarkerTokenizer()
 
    def analyze(self, rows) -> dict:
 
        stats = defaultdict(lambda: {"count": 0, "resets": 0, "last": None})
 
        for row in rows:
            marker = self.tokenizer.tokenize(row["text"])
            if not marker:
                continue
            s = stats[marker["family"]]
            s["count"] += 1
            if s["last"] is not None and marker["index"] == 1 and s["last"] != 1:
                s["resets"] += 1
            s["last"] = marker["index"]
 
        if not stats:
            return {}
 
        counts = {fam: s["count"] for fam, s in stats.items()}
        count_outliers = GapSplitter.high_outliers(counts)
 
        families = {}
        for fam, s in stats.items():
            is_list = s["resets"] > 0 or fam in count_outliers
            families[fam] = "list" if is_list else "heading"
 
        return families

 
class RecordAggregator:

    def _is_marker(self, row):

        return MarkerTokenizer().tokenize(row["text"])


    def _is_short_line(self, row):

        text = row["text"].strip()

        return (
            text
            and len(text) <= 50
            and not text.endswith((".", ";", ","))
        )
    def _row_gap(self, previous, current):

        if previous["page"] != current["page"]:
            return 9999

        return current["top"] - previous["bottom"]

    def _is_role_title(self, row):

        text = row["text"].strip()

        words = text.split()

        if not words:
            return False

        if len(words) > 4:
            return False

        if text.endswith((".", ";", ",")):
            return False

        return all(
            word[:1].isupper()
            for word in words
        )

    def build(
        self,
        rows,
    ):

        tokenizer = MarkerTokenizer()

        records = []

        current = None

        previous = None

        for row in rows:
            text = row["text"].strip()

            if text.isdigit():
                previous = row
                continue

            # Matches: "PROSPECTUS 2026", "Prospectus 2025", etc.
            if re.fullmatch(r"(?i)\s*prospectus\s+\d{4}\s*", text):
                previous = row
                continue

            if "NED UNIVERSITY" in text.upper():
                previous = row
                continue
            if "OF ENGINEERING & TECHNOLOGY" in text.upper():
                            previous = row
                            continue
            if (
                previous
                and re.fullmatch(r"\d+\.\d+\.\d+", previous["text"].strip())
                and row["text"].startswith("Department")
            ):
                previous["text"] = (
                    previous["text"]
                    + " "
                    + row["text"]
                )
                continue

            marker = self._is_marker(row)

            if marker:

                current = LogicalRecord(
                    rows=[row],
                    marker=marker,
                    page=row["page"],
                    column=row["column"],
                    kind="numbered",
                )

                records.append(current)

                previous = row
                continue


            if current is None:

                current = LogicalRecord(
                    rows=[row],
                    page=row["page"],
                    column=row["column"],
                    kind="text",
                )

                records.append(current)

                previous = row
                continue
            same_page = row["page"] == previous["page"]

            vertical_gap = self._row_gap(previous, row)

            if (
                same_page
                and vertical_gap < 8
                and not self._is_role_title(row)
            ):

                current.rows.append(row)

            else:

                current = LogicalRecord(
                    rows=[row],
                    page=row["page"],
                    column=row["column"],
                    kind="text",
                )

                records.append(current)

            previous = row

        return records

class RecordHierarchyBuilder:
    ROLE_LABELS = {
        "Chairperson",
        "Co-Chairperson",
        "Professor",
        "Professors",
        "Associate Professor",
        "Associate Professors",
        "Assistant Professor",
        "Assistant Professors",
        "Lecturer",
        "Lecturers",
        "Lab Engineer",
        "Lab Engineers",
        "Principal Laboratory Engineer",
        "IT Manager",
        "IT Managers",
        "Lab Manager",}

    def _continues_thread(
        self,
        previous,
        current,
    ):

        if previous is None:
            return False

        if previous.marker is None:
            return False

        if current.marker is None:
            return False

        a = previous.marker
        b = current.marker

        if a["family"] != b["family"]:
            return False

        if b["index"] != a["index"] + 1:
            return False

    # same page is always a continuation
        if current.page == previous.page:
            return True

    # only immediate next page
        if current.page != previous.page + 1:
            return False

    # must stay in the same column
        if current.column != previous.column:
            return False

        return True

    def _is_label(self, record):

        if record.kind != "text":
            return False

        if len(record.rows) != 1:
            return False

        text = record.rows[0]["text"].strip()

        if not text:
            return False

        # labels are compact
        if len(text) > 60:
            return False

        # not sentence-like
        if text.endswith((".", ";", ",")):
            return False

    # no marker
        if record.marker:
            return False

        if self._is_person_record(record):
           return False

        return True

    def _is_person_record(self, record):

        if record.kind != "text":
            return False

        if len(record.rows) != 1:
            return False

        text = record.rows[0]["text"].strip()

        prefixes = (
            "Prof.",
            "Dr.",
            "Engr.",
            "Mr.",
            "Mrs.",
            "Ms.",
        )

        return text.startswith(prefixes)

    def _opens_role(self, record):

        return (
            self._is_label(record)
            and len(record.children) == 0
        )

    def _contains(self, root, target):

        if root is target:
            return True

        for child in root.children:
            if self._contains(child, target):
                return True

        return False

    def _safe_append(self, parent, child):

        if parent is child:

            raise RuntimeError(
                f"Self-cycle detected: {child.rows[0]['text']}"
            )

        if self._contains(child, parent):

            raise RuntimeError(
                f"Cycle detected:\n"
                f"Parent: {parent.rows[0]['text']}\n"
                f"Child : {child.rows[0]['text']}"
            )

        parent.children.append(child)

    def build(
        self,
        records,
    ):

        roots = []

        current_section = None
        current_label = None
        previous_numbered = None
        active_role = None

        #for record in records:
        for idx, record in enumerate(records):

            next_record = (
                records[idx + 1]
                if idx + 1 < len(records)
                else None
            )

            # idx = records.index(record)

            if idx + 1 < len(records):
                next_record = records[idx + 1]

            marker = record.marker


        # ----------------------------
        # Numbered section heading
        # ----------------------------

            if (
                marker
                and marker["family"].startswith("decimal")
                and marker["depth"] >= 2
            ):

                record.children = []

                roots.append(record)

                current_section = record
                current_label = None
                previous_numbered = None

                continue

        # ----------------------------
        # Standalone label
        # ----------------------------

            # if self._is_label(record):

                # if (
                #     next_record is None
                #     or next_record.marker is None
                # ):
                #     current_label = None

                #     if current_section:
                #         current_section.children.append(record)
                #     else:
                #         roots.append(record)

                #     continue

                # record.children = []

                # if current_section:

                #     current_section.children.append(record)
                
                # else:

                #     roots.append(record)

                # current_label = record

                # continue

            # ----------------------------
            # Standalone label
            # ----------------------------

            if self._is_label(record):

                record.children = []

                if current_section:

                    self._safe_append(current_section, record)

                else:

                    roots.append(record)

                current_label = record
                previous_numbered = None

                continue

        # ---------------------------------
        # Cross-page list continuation
        # ---------------------------------

            if (
                record.marker
                and previous_numbered
                and self._continues_thread(previous_numbered, record)
            ):

                if current_label:

                    self._safe_append(current_label, record)
                    # previous_numbered = record

                elif current_section:

                    self._safe_append(current_section, record)
                    # previous_numbered = record

                else:

                    roots.append(record)

                previous_numbered = record

                continue

        # ----------------------------
        # Everything else
        # ----------------------------

            # if current_label:

            #     if self._is_person_record(record):

            #         self._safe_append(current_label, record)

            #     elif record.marker:

            #         self._safe_append(current_label, record)

            #     else:

            #         current_label = None

            #         if current_section:
            #             self._safe_append(current_section, record)
            #         else:
            #             roots.append(record)

            #     previous_numbered = record
            #     continue

            # elif current_section:

            #     self._safe_append(current_section, record)

            # else:

            #     roots.append(record)

            # previous_numbered = record

            if current_label:

                self._safe_append(current_label, record)
                # if record.marker:
                #     previous_numbered = record

            elif current_section:

                self._safe_append(current_section, record)
                # if record.marker:
                #     previous_numbered = record

            else:

                roots.append(record)
            # if record.marker:
            #     previous_numbered = record
            previous_numbered = record

        # else:

        #     if current_label:
        #         current_label.children.append(record)
        #     elif current_section:
        #         current_section.children.append(record)
        #     else:
        #         roots.append(record)

        return roots

@dataclass
class LogicalRecord:

    rows: list = field(default_factory=list)

    marker: dict | None = None

    page: int = 0

    column: int = 0

    kind: str = "unknown"
    children: list = field(default_factory=list)


 
 
# ============================================================
# Pass 3 - HierarchyBuilder
# ============================================================
 
class HierarchyBuilder:
    """
    Pass 3.

    Input  : rows tagged by RowClassifier and repaired by ThreadRepair.
    Output : a HierarchyNode tree (the root node's .block is None).

    Headings nest by marker depth ("2.2" is a parent of "2.2.1"): a stack of
    currently-open headings is popped back to the first ancestor shallower
    than the new heading, then the new heading is pushed as that ancestor's
    child. A list block is anchored under whichever heading was open the
    moment its thread FIRST started (index == 1) - so if the list is
    interrupted and later repaired (Problem 3), the reattached items still
    land under the list's original heading, not wherever they physically
    appear in the row stream.
    """


    def build(self, rows) -> HierarchyNode:

        root = HierarchyNode(block=None)
        stack = [root]              # stack[-1] = currently open heading node
        thread_node = {}
        current_label_node = None            # id(thread) -> HierarchyNode holding that list
        open_block_node = None      # most recently opened list/paragraph node

        for row in rows:

            rtype = row["row_type"]

            if rtype == "heading":

                depth = row["marker"]["depth"]

                while len(stack) > 1 and stack[-1].block.depth >= depth:
                    stack.pop()

                block = SemanticBlock(
                    type="heading",
                    heading=row["text"],
                    text=row["text"],
                    page=row["page"],
                    depth=depth,
                    rows=[row],
                )
                node = HierarchyNode(block=block)
                stack[-1].children.append(node)
                stack.append(node)
                current_label_node = None
                open_block_node = None

            elif rtype == "list_item":

                thread = row["thread"]
                key = id(thread)

                if key not in thread_node:
                    parent_depth = stack[-1].block.depth if stack[-1].block else 0
                    block = SemanticBlock(
                        type="list",
                        heading=thread["anchor_label"],
                        text="",
                        page=row["page"],
                        depth=parent_depth + 1,
                        rows=[],
                    )
                    node = HierarchyNode(block=block)
                    if current_label_node is not None:
                        current_label_node.children.append(node)
                    else:
                        stack[-1].children.append(node)
                    thread_node[key] = node

                thread_node[key].block.rows.append(row)
                open_block_node = thread_node[key]

            elif rtype == "label":

                parent_depth = stack[-1].block.depth if stack[-1].block else 0

                block = SemanticBlock(
                    type="label",
                    heading=row["text"],
                    text=row["text"],
                    page=row["page"],
                    depth=parent_depth + 1,
                    rows=[row],
                )

                node = HierarchyNode(block=block)

                stack[-1].children.append(node)

                current_label_node = node
                open_block_node = node

            else:  # paragraph

                if open_block_node is not None and open_block_node.block.type == "list":
                    # a wrapped/continuation line right after a list item
                    open_block_node.block.rows.append(row)
                else:
                    if open_block_node is None or open_block_node.block.type != "paragraph":
                        parent_depth = stack[-1].block.depth if stack[-1].block else 0
                        block = SemanticBlock(
                            type="paragraph", heading="", text="", page=row["page"],
                            depth=parent_depth + 1, rows=[],
                        )
                        node = HierarchyNode(block=block)

                        if current_label_node is not None:
                            current_label_node.children.append(node)
                        else:
                            stack[-1].children.append(node)
                        current_label_node = node
                        open_block_node = node
                    open_block_node.block.rows.append(row)

        return root


# ============================================================
# Pass 4 - SemanticChunkBuilder
# ============================================================

@dataclass
class WritingBlock:

    page: int

    rows: list[dict] = field(default_factory=list)

    block_type: str = "unknown"

    @property
    def text(self):

        return "\n".join(
            row["text"]
            for row in self.rows
        )


class SemanticChunkBuilder:
    """
    Pass 4.

    Input  : the HierarchyNode tree from HierarchyBuilder.
    Output : a flat list[SemanticBlock], finalized (text/top/bottom/left/right
             computed from their rows) and each carrying .path - the titles
             of its ancestor headings, root to parent - so downstream code
             can chunk without re-walking the tree.
    """

    def build(self, root: HierarchyNode):
        blocks = []
        self._walk(root, path=[], blocks=blocks)
        return blocks

    def _walk(self, node: HierarchyNode, path, blocks):

        if node.block is not None:
            block = node.block
            self._finalize(block)
            block.path = list(path)
            blocks.append(block)
            if block.type == "heading":
                path = path + [block.heading]

        for child in node.children:
            self._walk(child, path, blocks)

    def _finalize(self, block: SemanticBlock):

        if not block.rows:
            return

        block.text = "\n".join(row["text"] for row in block.rows)

        block.top = min(row["top"] for row in block.rows)
        block.bottom = max(row["bottom"] for row in block.rows)

        block.left = min(min(item["x"] for item in row["items"]) for row in block.rows)
        block.right = max(max(item["x"] for item in row["items"]) for row in block.rows)


# ============================================================
# Orchestrator - just wires the five passes together in order.
# No pass-specific logic lives here.
# ============================================================

class SemanticPipeline:
    """
    Wires the five passes together in order. No pass-specific logic lives
    here - only sequencing and, optionally, writing each pass's own output
    to disk so a broken page can be traced to the exact pass that broke it
    instead of only ever looking at the final chunks.
    """

    def __init__(self):
        tokenizer = MarkerTokenizer()
        self.survey = DocumentSurvey(tokenizer=tokenizer)
        self.aggregator = RecordAggregator()
        self.hierarchy_builder = HierarchyBuilder()
        self.chunk_builder = SemanticChunkBuilder()
        self.record_hierarchy = RecordHierarchyBuilder()

    def run(self, rows, debug_dir: Path | None = None):

        if debug_dir:
            debug_dir.mkdir(parents=True, exist_ok=True)

        families = self.survey.analyze(rows)
        if debug_dir:
            self._dump(debug_dir / "pass0_survey.json", families)

        

        records = self.aggregator.build(rows)

        if debug_dir:
            self._dump(
                debug_dir / "pass1_records.json",
                [
                    [r["text"] for r in record.rows]
                    for record in records
                ],
            )

        records = self.record_hierarchy.build(records)
        

        return records
    
        # if debug_dir:
        #     self._dump(debug_dir / "pass3_tree.json", self._tree_debug(tree))

        # blocks = self.chunk_builder.build(tree)
        # if debug_dir:
        #     self._dump(debug_dir / "pass4_chunks.json", [asdict(b) for b in blocks])

        # return blocks

    # -------------------------------------------------
    # debug serialization - only ever reshapes data, no pipeline logic

    @staticmethod
    def _dump(path: Path, data):
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _rows_debug(rows):
        # open this file first if a row you expected to be a heading/list
        # item/label came out as something else - that tells you the bug
        # is in RowClassifier (or DocumentSurvey's family table it used).
        return [
            {
                "page": r["page"],
                "text": r["text"],
                "marker": r.get("marker"),
                "row_type": r.get("row_type"),
            }
            for r in rows
        ]

    @staticmethod
    def _threads_debug(rows, threads):
        # open this file if a row_type looked right in pass1 but ended up
        # merged into (or split from) the wrong list - that's ThreadRepair
        # attaching it to the wrong thread.
        members = defaultdict(list)
        for r in rows:
            if r.get("row_type") == "list_item" and "thread" in r:
                members[id(r["thread"])].append({"page": r["page"], "text": r["text"]})

        return [
            {
                "family": t["family"],
                "anchor_label": t["anchor_label"],
                "final_last_index": t["last_index"],
                "member_count": len(members.get(id(t), [])),
                "members": members.get(id(t), []),
            }
            for t in threads
        ]

    @staticmethod
    def _tree_debug(node: HierarchyNode):
        # open this file if threads looked right in pass2 but ended up
        # nested under the wrong heading - that's HierarchyBuilder.
        result = {}
        if node.block is not None:
            b = node.block
            result = {
                "type": b.type,
                "heading": b.heading,
                "depth": b.depth,
                "row_count": len(b.rows),
                "sample_text": [r["text"] for r in b.rows[:3]],
            }
        result["children"] = [SemanticPipeline._tree_debug(c) for c in node.children]
        return result
 
 
class LayoutReconstructionExperiment:
    """
    Phase 1 + Phase 2 (five-pass pipeline)
    Experimental reconstruction from layout_items only.
    """
 
    def __init__(
        self, 
        input_file: Path,
        output_dir: Path | None = None,
    ):
 
        self.project_root = Path(__file__).resolve().parents[2]
 
        # self.input_file = (
        #     self.project_root
        #     / "storage"
        #     / "parsed"
        #     / "UGProspectus2026.json"  # change if your filename differs
        # )

        self.input_file = input_file
 
        # self.output_dir = (
        #     self.project_root
        #     / "storage"
        #     / "experiments"
        # )
        self.output_dir = (
            output_dir
            if output_dir is not None
            else self.project_root
            / "storage"
            / "experiments"
        )
 
        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )
 
        self.reconstructor = ReadingOrderReconstructor()
        self.pipeline = SemanticPipeline()

    def _find_section(
        self,
        sections,
        page_number,
    ):
        for section in sections:

            if (
                section.start_page
                <= page_number
                <= section.end_page
            ):
                return section

        return None
 
    def run(self):
 
        if not self.input_file.exists():
            raise FileNotFoundError(self.input_file)
 
        with open(self.input_file, "r", encoding="utf-8") as f:
            document = json.load(f)
 
        pages = document.get("pages", [])
 
        print(f"\nLoaded: {self.input_file.name}")
        print(f"Total Pages: {len(pages)}\n")
 
        document_rows = []
        page_texts = {}
        sections = ProspectusSectionDetector().detect(pages)
 
        # --- Phase 1: reconstruct every page's rows first -------------
        for page in pages:
 
            page_number = page.get("page_number", 0)
            layout_items = page.get("layout_items") or []
            section = self._find_section(
                sections,
                page["page_number"],
            )

            if not layout_items:
                print(f"Page {page_number:03d} -> No layout items")
                continue
 
            print(f"Page {page_number:03d}")
 
            rows = self.reconstructor.reconstruct(layout_items, page_number, section)
            document_rows.extend(rows)
 
            reconstructed_text = "\n".join(row["text"] for row in rows)
            page_texts[page_number] = reconstructed_text
 
            (self.output_dir / f"page_{page_number:03d}_layout.txt").write_text(
                reconstructed_text, encoding="utf-8"
            )
 
        # --- Phase 2: run the five-pass pipeline ONCE, over the whole doc --
        # (Pass 0 needs full-document statistics; running it per-page would
        # starve early pages of evidence)
        # debug_dir gets one file per pass - inspect these, in order, to
        # find exactly which pass a broken page traces back to.
        debug_dir = self.output_dir / "debug"
        blocks = self.pipeline.run(document_rows, debug_dir=debug_dir)
 
        # write one blocks file for the whole document
        # blocks_path = self.output_dir / "document_blocks.txt"
        # with open(blocks_path, "w", encoding="utf-8") as f:
        #     for block in blocks:
        #         f.write("=" * 80 + "\n")
        #         f.write(f"TYPE    : {block.type}\n")
        #         f.write(f"HEADING : {block.heading}\n")
        #         f.write(f"PATH    : {' > '.join(block.path)}\n\n")
        #         for row in block.rows:
        #             f.write(row["text"] + "\n")
        #         f.write("\n")
        # records_path = self.output_dir / "document_records.txt"

        # with open(records_path, "w", encoding="utf-8") as f:

            # def dump(record, depth=0):

            #     indent = "    " * depth

            #     f.write(indent + "=" * 40 + "\n")

            #     f.write(indent + f"PAGE : {record.page}\n")

            #     if record.marker:
            #         f.write(indent + f"MARKER : {record.marker}\n")

            #     f.write("\n")

            #     for row in record.rows:
            #         f.write(indent + row["text"] + "\n")

            #     f.write("\n")

            #     for child in record.children:
            #         dump(child, depth + 1)

            # def dump(record, depth=0, visited=None):

            #     if visited is None:
            #         visited = set()

            #     if id(record) in visited:

            #         f.write(
            #             "    "*depth +
            #             "*** CYCLE DETECTED ***\n"
            #         )
            #         return

            #     visited.add(id(record))

            #     ...

            #     for child in record.children:
            #         dump(child, depth+1, visited)


            # for record in blocks:
            #     dump(record)

                # f.write("=" * 80 + "\n")
                # f.write(f"RECORD {i}\n")
                # f.write(f"PAGE : {record.page}\n")
                # f.write(f"KIND : {record.kind}\n")

                # if record.marker:
                #     f.write(f"MARKER : {record.marker}\n")

                # f.write("\n")

                # for row in record.rows:
                #     f.write(row["text"] + "\n")

                # f.write("\n")
 
        results = [
            {
                "page_number": page_number,
                "reconstructed_text": text,
            }
            for page_number, text in page_texts.items()
        ]
 
        json_path = self.output_dir / "layout_reconstruction.json"
        json_path.write_text(
            json.dumps(results, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
 
        # blocks_json_path = self.output_dir / "semantic_blocks.json"
        # blocks_json_path.write_text(
        #     json.dumps([asdict(b) for b in blocks], indent=2, ensure_ascii=False),
        #     encoding="utf-8",
        # )
        # records_path = self.output_dir / "document_records.txt"

        # with open(records_path, "w", encoding="utf-8") as f:

        #     for i, record in enumerate(blocks, start=1):

        #         f.write("=" * 80 + "\n")
        #         f.write(f"RECORD {i}\n")
        #         f.write(f"PAGE : {record.page}\n")

        #         if record.marker:
        #             f.write(f"MARKER : {record.marker}\n")

        #         f.write("\n")

        #         for row in record.rows:
        #             f.write(row["text"] + "\n")

        #         f.write("\n")
        records_path = self.output_dir / "document_records.txt"

        with open(records_path, "w", encoding="utf-8") as f:

            def dump(record, depth=0):

                indent = "    " * depth

                f.write(indent + "=" * 80 + "\n")
                f.write(indent + f"PAGE : {record.page}\n")
                f.write(indent + f"KIND : {record.kind}\n")

                if record.marker:
                    f.write(indent + f"MARKER : {record.marker}\n")

                f.write("\n")

                for row in record.rows:
                    f.write(indent + row["text"] + "\n")

                f.write("\n")

                for child in record.children:
                    dump(child, depth + 1)

            for record in blocks:
                dump(record)
 
 
if __name__ == "__main__":
    LayoutReconstructionExperiment().run()
 