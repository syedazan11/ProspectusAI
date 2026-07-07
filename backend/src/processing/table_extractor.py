from typing import Any

from src.schemas.table import ExtractedTable


class TableExtractor:
    """
    Coordinates structured table extraction.

    This class does not assume:
    - a specific university
    - a fixed number of columns
    - a fixed page orientation
    - a specific table type
    """

    def extract(
        self,
        table_data: dict[str, Any],
        page_number: int,
    ) -> ExtractedTable:

        table_title = table_data.get(
            "table_title",
            "Untitled Table",
        )

        columns = table_data.get("columns", [])
        rows = table_data.get("rows", [])

        if not columns:
            raise ValueError(
                "Extracted table has no columns."
            )

        if not rows:
            raise ValueError(
                "Extracted table has no rows."
            )

        normalized_rows = []

        for row in rows:

            # Adaptive-table format:
            # {
            #   "category": "...",
            #   "description": "...",
            #   "values": [...]
            # }
            if "values" in row:

                values = list(
                    row.get("values", [])
                )

                normalized_row = {
                    "Category": row.get(
                        "category",
                        "",
                    ),
                    "Description": row.get(
                        "description",
                        "",
                    ),
                }

                for index, value in enumerate(
                    values
                ):
                    column_name = (
                        columns[index]
                        if index < len(columns)
                        and str(columns[index]).strip()
                        else f"Value_{index + 1}"
                    )

                    normalized_row[
                        str(column_name)
                    ] = value

            # Normal dictionary-table format.
            else:

                normalized_row = {
                    column: row.get(column)
                    for column in columns
                }

            normalized_rows.append(
                normalized_row
            )

        return ExtractedTable(
            table_title=table_title,
            page_number=page_number,
            columns=columns,
            rows=normalized_rows,
            metadata=table_data.get(
                "metadata",
                {},
            ),
        )