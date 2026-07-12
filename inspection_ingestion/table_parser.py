import re
from typing import Any


class TableParser:

    def is_table_corrupted(self, text: str) -> bool:

        # Lots of weird symbols
        symbols = re.findall(r"[^\w\s.,():/-]", text)

        # One-letter OCR lines
        short_lines = [
            line
            for line in text.splitlines()
            if len(line.strip()) <= 2
        ]

        # OCR garbage patterns
        garbage = re.findall(
            r"[A-Za-z]{1}\s+[A-Za-z]{1}\s+[A-Za-z]{1}",
            text,
        )

        if len(symbols) > 40:
            return True

        if len(short_lines) > 10:
            return True

        if len(garbage) > 5:
            return True

        return False

    def validate_row(
        self,
        values: list[int | None],
        expected_columns: int,
        printed_total: int | None = None,
    ) -> dict[str, Any]:

        errors = []

        if len(values) != expected_columns:
            errors.append(
                f"Expected {expected_columns} values, "
                f"got {len(values)}."
            )

        if any(value is None for value in values):
            errors.append(
                "Row contains unreadable values."
            )

        calculated_total = None

        if not any(value is None for value in values):
            calculated_total = sum(values)

        if (
            printed_total is not None
            and calculated_total is not None
            and calculated_total != printed_total
        ):
            errors.append(
                f"Calculated total {calculated_total} "
                f"does not match printed total "
                f"{printed_total}."
            )

        return {
            "is_valid": len(errors) == 0,
            "calculated_total": calculated_total,
            "printed_total": printed_total,
            "errors": errors,
        }

    def build_row_chunk(
        self,
        table_title: str,
        row: dict[str, Any],
        page_number: int,
    ) -> dict[str, Any]:

        if not row:
            raise ValueError(
                "Table row cannot be empty."
            )

        row_lines = []

        for column, value in row.items():

            if value is None:
                continue

            row_lines.append(
                f"{column}: {value}"
            )

        row_text = "\n".join(row_lines)

        text = (
            f"Table: {table_title}\n"
            f"{row_text}\n"
            f"Page: {page_number}"
        )

        return {
            "text": text,
            "metadata": {
                "content_type": "table_row",
                "table_title": table_title,
                "page_number": page_number,
            },
        }