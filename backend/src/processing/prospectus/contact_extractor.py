import re

from src.processing.prospectus.contact_record import (
    ContactRecord,
)


class ContactExtractor:

    EMAIL_PATTERN = re.compile(
        r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"
    )

    PHONE_PATTERN = re.compile(
        r"\+?\d[\d\s\-()]{6,}\d"
    )

    URL_PATTERN = re.compile(
        r"(?:https?://|www\.)[A-Za-z0-9./_-]+",
        re.IGNORECASE,
    )

    def extract(
        self,
        pages: list[dict],
    ) -> list[ContactRecord]:

        records: list[ContactRecord] = []

        for page in pages:

            page_number = page["page_number"]

            for section in page.get(
                "sections",
                [],
            ):

                heading = section.get(
                    "heading",
                    "",
                ).strip()

                for line in section.get(
                    "content",
                    [],
                ):

                    records.extend(
                        self._extract_contacts(
                            line=line,
                            heading=heading,
                            page_number=page_number,
                        )
                    )

        return records
    def _extract_contacts(
        self,
        *,
        line: str,
        heading: str,
        page_number: int,
    ) -> list[ContactRecord]:

        records: list[ContactRecord] = []

        for match in self.EMAIL_PATTERN.finditer(line):

            records.append(
                ContactRecord(
                    contact_type="email",
                    value=match.group(0),
                    department=None,
                    source_page=page_number,
                    source_heading=heading,
                    source_text=line,
                )
            )

        for match in self.PHONE_PATTERN.finditer(line):

            phone = match.group(0).strip()

                # Reject dates like 23-05-1923
            if re.fullmatch(
                r"\d{1,2}-\d{1,2}-\d{2,4}",
                phone,
            ):
                continue

            # Normalize whitespace
            phone = re.sub(
                r"\s+",
                " ",
                phone,
            ).strip()

            # Count digits
            digit_count = sum(
                c.isdigit()
                for c in phone
            )

            # Ignore short OCR garbage
            if digit_count < 8:
                continue

            # Reject values with more separators than digits
            separator_count = sum(
                c in "- ()"
                for c in phone
            )

            if separator_count > digit_count:
                continue


            records.append(
                ContactRecord(
                    contact_type="phone",
                    value=phone,
                    department=None,
                    source_page=page_number,
                    source_heading=heading,
                    source_text=line,
                )
            )

        for match in self.URL_PATTERN.finditer(line):

            records.append(
                ContactRecord(
                    contact_type="url",
                    value=match.group(0),
                    department=None,
                    source_page=page_number,
                    source_heading=heading,
                    source_text=line,
                )
            )

        return records