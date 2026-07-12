import json
import re
from pathlib import Path
from src.processing.table_parser import TableParser


class DocumentCleaner:
    """
    Cleans the raw parsed document produced by the parser.
    """

    def clean(self, parsed_json: Path) -> dict:

        with open(parsed_json, "r", encoding="utf-8") as f:
            document = json.load(f)

        cleaned_pages = []
        table_parser = TableParser()

        for page in document["pages"]:

            cleaned_text = self._clean_text(page["markdown"])

            if page["page_number"] == 104:
                print("\n" + "=" * 80)
                print("RAW PAGE 104")
                print("=" * 80)
                print(page["markdown"])

                print("\n" + "=" * 80)
                print("CLEANED PAGE 104")
                print("=" * 80)
                print(cleaned_text)

            headings = []
            paragraphs = []
            lists = []
            sections = []
            current_heading = None
            current_content = []

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
                            }
                        )

                    current_heading = line
                    current_content = []

                # List detection
                elif (
                    line.startswith("-")
                    or line.startswith("•")
                    or line.startswith("*")
                ):

                    lists.append(line)

                    if current_heading is not None:
                        current_content.append(line)

                # Paragraph
                else:

                    paragraphs.append(line)

                    if current_heading is not None:
                        current_content.append(line)

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
                    "headings": headings,
                    "paragraphs": paragraphs,
                    "lists": lists,
                    "sections": sections,
                    "has_tables": page["has_tables"],
                    "table_corrupted": table_corrupted,
                    "has_images": page["has_images"],
                }
            )

        cleaned_document = {
            "document_type": document["document_type"],
            "total_pages": document["total_pages"],
            "pages": cleaned_pages,
            "metadata": document["metadata"],
        }

        output_path = (
            Path(__file__).resolve()
            .parents[3]
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

        # Remove repeated spaces
        text = re.sub(r"[ \t]+", " ", text)

        # Remove excessive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)

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

            return True

        # -------------------------
        # Generic numbered headings
        # -------------------------

        match = re.match(
            r"^\d+(?:\.\d+)*\.?\s+(.+)$",
            line,
        )

        if match:

            title = match.group(1).strip()

            if len(title.split()) < 2:
                return False

            # Title shouldn't be mostly numbers
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