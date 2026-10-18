import re

from src.processing.prospectus.student_life_record import (
    StudentLifeRecord,
)


MARKER_RE = re.compile(r"^\s*(\d+[.)]|[A-Za-z][.)])\s*")


class StudentLifeExtractor:
    """
    Builds StudentLifeRecords from the pages RecordProcessingService
    has already selected for this section. No relevance filtering
    and no title/keyword heuristics here — blocks are found the same
    way ReadingOrderReconstructor finds rows: from the structure of
    the content itself, not from a fixed vocabulary.
    """

    def extract(
        self,
        pages: list[dict],
    ) -> list[StudentLifeRecord]:

        records: list[StudentLifeRecord] = []

        for page in pages:

            page_number = page["page_number"]

            for section in page.get("sections", []):

                heading = section.get("heading", "").strip()

                records.extend(
                    self._extract_blocks(
                        section=section,
                        page_number=page_number,
                        heading=heading,
                    )
                )

        return records

    def _extract_blocks(
        self,
        *,
        section: dict,
        page_number: int,
        heading: str,
    ) -> list[StudentLifeRecord]:

        content = section.get("content", [])

        records = []

        for number, title, body_lines in self._split_into_blocks(content):

            records.append(
                StudentLifeRecord(
                    number=number,
                    title=title or "",
                    content=[
                        self._parse_line(line)
                        for line in body_lines
                    ],
                    source_page=page_number,
                    source_heading=heading,
                    source_text="\n".join(
                        ([title] if title else []) + body_lines
                    ),
                    parent=heading or None,
                )
            )

        return records

    def _split_into_blocks(self, content):

        blocks = []

        current_number = ""
        current_title = None
        current_body: list[str] = []

        for raw_line in content:

            line = raw_line.strip()

            if not line:
                continue

            match = MARKER_RE.match(line)

            if match:

                if current_title is not None or current_body:
                    blocks.append(
                        (current_number, current_title, current_body)
                    )

                current_number = match.group(1).rstrip(".)")
                current_title = line[match.end():].strip()
                current_body = []

                continue

            if current_title is None:
                current_title = line
                continue

            current_body.append(line)

        if current_title is not None or current_body:
            blocks.append((current_number, current_title, current_body))

        return blocks

    def _parse_line(self, line: str) -> dict:

        for separator in (":", " - ", "..."):

            if separator in line:

                key, value = line.split(separator, 1)

                return {
                    "key": key.strip().lower().replace(" ", "_"),
                    "value": value.strip(),
                }

        return {"text": line}