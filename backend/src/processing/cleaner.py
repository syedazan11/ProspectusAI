import unicodedata
import json
import re
from pathlib import Path
from src.processing.table_parser import TableParser
from src.processing.reading_order import ReadingOrderRepairService

class DocumentCleaner:
    """
    Cleans the raw parsed document produced by the parser.
    """

    def __init__(
        self,
        debug_dir: Path | None = None,
    ) -> None:
        self.debug_dir = debug_dir

    # def clean(self, parsed_json: Path) -> dict:
    def clean(
        self,
        parsed_json: Path,
        output_path: Path | None = None,
    ) -> dict:

        with open(parsed_json, "r", encoding="utf-8") as f:
            document = json.load(f)

        cleaned_pages = []
        table_parser = TableParser()
        # reading_order = ReadingOrderRepairService()
        reading_order = ReadingOrderRepairService(
            debug_dir=self.debug_dir,
        )

        for page in document["pages"]:

            cleaned_text = self._clean_text(page["markdown"])
            lines = cleaned_text.splitlines()

            analysis = reading_order.analyze_page(lines)
            
            if analysis["suspicious"]:
                reading_order.save_debug_report(
                    page["page_number"],
                    analysis,
                )

            cleaning_stats = self._validate_cleaning(
                page["markdown"],
                cleaned_text,
            )

            layout_lookup: dict[str, list] = {}

            for item in page.get("layout_items") or []:

                cleaned = self._clean_layout_line(
                    item["text"] if isinstance(item, dict) else item.text
                )

                if not cleaned:
                    continue

                layout_lookup.setdefault(
                    cleaned,
                    [],
                ).append(item)

            headings = []
            paragraphs = []
            lists = []
            sections = []
            current_heading = None
            current_content = []
            current_layout_items = []

            for line in cleaned_text.splitlines():

                line = line.strip()

                if not line:
                    continue

                # Heading detection
                if self._is_heading(line):

                    headings.append(line)

                    if current_heading is not None:
                        metadata = self._heading_metadata(current_heading)

                        sections.append(
                            {
                                "heading": current_heading,
                                "heading_number": metadata["heading_number"],
                                "heading_level": metadata["heading_level"],
                                "heading_title": metadata["heading_title"],
                                "content": current_content,
                                "layout_items": current_layout_items,
                                "metadata": {
                                    "heading_number": metadata["heading_number"],
                                    "heading_level": metadata["heading_level"],
                                    "heading_title": metadata["heading_title"],
                                },
                            }
                        )

                    current_heading = line
                    current_content = []
                    current_layout_items = []


                # List detection
                elif (
                    line.startswith("-")
                    or line.startswith("•")
                    or line.startswith("*")
                ):

                    lists.append(line)

                    if current_heading is not None:
                        current_content.append(line)
                        current_layout_items.extend(
                            layout_lookup.pop(line, [])
                        )

                # Paragraph
                else:

                    paragraphs.append(line)

                    if current_heading is not None:
                        current_content.append(line)
                        current_layout_items.extend(
                            layout_lookup.pop(line, [])
                        )

            # Finalize the last section
            if current_heading is not None:

                metadata = self._heading_metadata(current_heading)

                sections.append(
                    {
                        "heading": current_heading,
                        "heading_number": metadata["heading_number"],
                        "heading_level": metadata["heading_level"],
                        "heading_title": metadata["heading_title"],
                        "content": current_content,
                        "layout_items": current_layout_items,
                        "metadata": {
                            "heading_number": metadata["heading_number"],
                            "heading_level": metadata["heading_level"],
                            "heading_title": metadata["heading_title"],
                        },
                    }
                )

            table_corrupted = False

            if page["has_tables"]:
                table_corrupted = table_parser.is_table_corrupted(
                    cleaned_text
                )

            cleaned_pages.append(
                {
                    "page_number": page["page_number"],
                    "text": cleaned_text,
                    "layout_items": page.get("layout_items"),
                    "headings": headings,
                    "paragraphs": paragraphs,
                    "lists": lists,
                    "sections": sections,
                    "has_tables": page["has_tables"],
                    "table_corrupted": table_corrupted,
                    "has_images": page["has_images"],
                    "cleaning_statistics": cleaning_stats,
                }
            )

        cleaned_document = {
            "document_type": document["document_type"],
            "total_pages": document["total_pages"],
            "pages": cleaned_pages,
            "metadata": document["metadata"],
        }

        # output_path = (
        #     Path(__file__).resolve()
        #     .parents[3]
        #     / "storage"
        #     / "cleaned"
        #     / f"{parsed_json.stem}.json"
        # )
        if output_path is None:
            output_path = (
                Path(__file__).resolve().parents[3]
                / "storage"
                / "cleaned"
                / f"{parsed_json.stem}.json"
            )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                cleaned_document,
                f,
                indent=4,
                ensure_ascii=False,
            )

        print(f"\nSaved cleaned file -> {output_path}")

        return cleaned_document

    def _clean_text(self, text: str) -> str:

        text = unicodedata.normalize(
            "NFKC",
            text,
        )

        # Repair words split across line breaks:
        # Electro-\nMechanical -> ElectroMechanical
        text = re.sub(
            r"([A-Za-z])-\n([A-Za-z])",
            r"\1\2",
            text,
        )

        # Remove repeated spaces
        text = re.sub(r"[ \t]+", " ", text)

        # Remove excessive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)

        text = self._reconstruct_lines(text)

        cleaned_lines = []

        for line in text.splitlines():

            line = line.strip()

            if not line:
                continue

            # Remove decorative symbols
            line = re.sub(r"[©¢»«•●◆■□★☆]+", "", line)

            # Remove leading/trailing non-alphanumeric symbols
            line = re.sub(r"^[^\w]+", "", line)
            line = re.sub(r"[^\w]+$", "", line)

            # Remove repeated punctuation
            line = re.sub(r"[&@]{2,}", "", line)

            # Normalize spaces again
            line = re.sub(r"\s+", " ", line).strip()

            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)
    
    def _clean_layout_line(
        self,
        text: str,
    ) -> str:
        """
        Apply the same normalization used by _clean_text(),
        but to a single OCR line.
        """

        text = unicodedata.normalize(
            "NFKC",
            text,
        )

        text = text.strip()

        text = re.sub(
            r"[©¢»«•●◆■□★☆]+",
            "",
            text,
        )

        text = re.sub(
            r"^[^\w]+",
            "",
            text,
        )

        text = re.sub(
            r"[^\w]+$",
            "",
            text,
        )

        text = re.sub(
            r"[&@]{2,}",
            "",
            text,
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        ).strip()

        return text

    def _is_heading(self, line: str) -> bool:
        """
        Returns True if a line is likely a document heading.

        Supports:
        - Traditional uppercase headings
        - Numbered headings (4.2 Eligibility Conditions)
        - Multi-level numbered headings (8.1.1 For Main Campus)
        """

        line = line.strip()

        if not line:
            return False

        # Ignore URLs
        if "www." in line.lower():
            return False

        # Length sanity checks
        if len(line) < 4 or len(line) > 120:
            return False

        # Must contain enough letters
        letters = sum(c.isalpha() for c in line)

        if letters < 5:
            return False

        # Reject lines dominated by digits
        digits = sum(c.isdigit() for c in line)

        if digits > len(line) * 0.35:
            return False

        words = line.split()

        # -------------------------
        # Existing uppercase headings
        # -------------------------

        if line.isupper():

            if len(words) < 2:
                return False

            # Reject page headers like:
            # OF ENGINEERING & TECHNOLOGY
            # PROSPECTUS 2026
            if len(words) <= 4 and not any(
                c.isdigit() for c in line
            ):
                return False

            return True

        # -------------------------
        # Generic numbered headings
        # -------------------------

        match = re.match(
            r"^(?P<number>\d+(?:\.\d+)*)\.?\s+(?P<title>.+)$",
            line,
        )

        if match:

            number = match.group("number")
            title = match.group("title").strip()

            # Single-number headings like:
            # 1. Hostel
            # 2. International Hostel
            # are usually list items, not document sections.
            if "." not in number:
                return False

            if len(title.split()) < 2:
                return False

            title_letters = sum(
                c.isalpha()
                for c in title
            )

            if title_letters < 5:
                return False

            return True

        return False
    
    def _heading_metadata(self, heading: str) -> dict:
        """
        Extract generic metadata from a heading.

        Examples:
            8.1 Fee Structure
            8.1.1 Main Campus
            CHAPTER 4
        """

        match = re.match(
            r"^(?P<number>\d+(?:\.\d+)*)\.?\s*(?P<title>.*)$",
            heading.strip(),
        )

        if match:
            number = match.group("number")
            title = match.group("title").strip()

            return {
                "heading_number": number,
                "heading_level": number.count(".") + 1,
                "heading_title": title,
            }

        return {
            "heading_number": "",
            "heading_level": 1,
            "heading_title": heading.strip(),
        }
    
    def _reconstruct_lines(self, text: str) -> str:
        """
        Preserve OCR line structure.

        Multi-column prospectuses cannot be reconstructed safely without
        layout coordinates. Aggressively joining lines destroys curriculum
        tables, faculty lists, fee schedules, and eligibility clauses.

        Keep one OCR line per output line and let downstream parsers decide
        how to interpret the structure.
        """

        cleaned_lines = [
            line.rstrip()
            for line in text.splitlines()
        ]

        return "\n".join(cleaned_lines)
    
    def _is_structural_label(self, line: str) -> bool:
        """
        Returns True if a line is likely a structural label that should
        remain on its own line.
        """

        line = line.strip()

        if not line:
            return False

        # Ends with colon
        if line.endswith(":"):
            return True

        # Very short title-like labels
        words = line.split()

        if (
            1 <= len(words) <= 4
            and all(
                word[:1].isupper()
                for word in words
                if word
            )
        ):
            return True

        return False
    
    def _validate_cleaning(
        self,
        original_text: str,
        cleaned_text: str,
    ) -> dict:
        """
        Generate cleaning statistics for validation.
        """

        original_characters = len(original_text)
        cleaned_characters = len(cleaned_text)

        original_lines = len(original_text.splitlines())
        cleaned_lines = len(cleaned_text.splitlines())

        original_blank_lines = sum(
            1 for line in original_text.splitlines()
            if not line.strip()
        )

        cleaned_blank_lines = sum(
            1 for line in cleaned_text.splitlines()
            if not line.strip()
        )

        return {
            "original_characters": original_characters,
            "cleaned_characters": cleaned_characters,
            "character_delta": original_characters - cleaned_characters,
            "original_lines": original_lines,
            "cleaned_lines": cleaned_lines,
            "line_delta": original_lines - cleaned_lines,
            "blank_lines_removed": (
                original_blank_lines - cleaned_blank_lines
            ),
        "changed": original_text != cleaned_text,
        }
        