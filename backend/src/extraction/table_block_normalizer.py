from typing import Any


class TableBlockNormalizer:
    """
    Normalizes vision-extracted table blocks before merging.

    Responsibilities:
    - separate metadata fields from numeric table columns
    - make every row match its block's declared column count
    - pad missing cells with None
    - trim only obvious extra leading metadata placeholders

    Does not contain university-specific rules.
    """

    METADATA_COLUMNS = {
        "category",
        "description",
        "row",
        "row label",
        "label",
    }

    def normalize(
        self,
        blocks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

        normalized_blocks = []

        for block in blocks:

            normalized_block = dict(block)

            extracted_data = dict(
                block.get("extracted_data", {})
            )

            columns = list(
                extracted_data.get("columns", [])
            )

            rows = list(
                extracted_data.get("rows", [])
            )

            (
                normalized_columns,
                metadata_prefix_count,
            ) = self._normalize_columns(
                columns
            )

            normalized_rows = []

            for row in rows:

                normalized_rows.append(
                    self._normalize_row(
                        row=row,
                        expected_width=len(
                            normalized_columns
                        ),
                        metadata_prefix_count=(
                            metadata_prefix_count
                        ),
                    )
                )

            extracted_data["columns"] = (
                normalized_columns
            )

            extracted_data["rows"] = (
                normalized_rows
            )

            normalized_block[
                "extracted_data"
            ] = extracted_data

            normalized_blocks.append(
                normalized_block
            )

        return normalized_blocks

    def _normalize_columns(
        self,
        columns: list[Any],
    ) -> tuple[list[Any], int]:

        metadata_prefix_count = 0

        for column in columns:

            normalized_name = (
                str(column)
                .strip()
                .lower()
            )

            if (
                normalized_name
                in self.METADATA_COLUMNS
            ):
                metadata_prefix_count += 1
                continue

            break

        return (
            columns[metadata_prefix_count:],
            metadata_prefix_count,
        )

    def _normalize_row(
        self,
        row: dict[str, Any],
        expected_width: int,
        metadata_prefix_count: int,
    ) -> dict[str, Any]:

        normalized_row = {
            "category": row.get(
                "category",
                "",
            ),
            "description": row.get(
                "description",
                "",
            ),
            "values": list(
                row.get("values", [])
            ),
        }

        values = normalized_row["values"]

        values = self._remove_metadata_prefix(
            values=values,
            metadata_prefix_count=(
                metadata_prefix_count
            ),
        )

        if len(values) < expected_width:

            missing_count = (
                expected_width - len(values)
            )

            values.extend(
                [None] * missing_count
            )

        elif len(values) > expected_width:

            values = values[
                :expected_width
            ]

        normalized_row["values"] = values

        return normalized_row

    def _remove_metadata_prefix(
        self,
        values: list[Any],
        metadata_prefix_count: int,
    ) -> list[Any]:

        if metadata_prefix_count == 0:
            return values

        removable_count = 0

        for value in values[
            :metadata_prefix_count
        ]:

            if value in (
                None,
                "",
            ):
                removable_count += 1

            else:
                break

        return values[
            removable_count:
        ]