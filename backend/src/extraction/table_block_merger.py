from typing import Any


class TableBlockMerger:
    """
    Merges overlapping table blocks extracted from
    left to right.

    Assumptions:
    - blocks preserve table row order
    - neighboring blocks overlap horizontally
    - column names and values may contain minor
      vision/OCR errors
    """

    def merge(
        self,
        blocks: list[dict[str, Any]],
    ) -> dict[str, Any]:

        if not blocks:
            raise ValueError(
                "No extracted blocks were provided."
            )

        ordered_blocks = sorted(
            blocks,
            key=lambda block: block["block_index"],
        )

        extracted_blocks = [
            block["extracted_data"]
            for block in ordered_blocks
        ]

        row_counts = [
            len(block.get("rows", []))
            for block in extracted_blocks
        ]

        if not row_counts:
            raise ValueError(
                "No table rows were extracted."
            )

        expected_row_count = max(row_counts)

        merged_columns = list(
            extracted_blocks[0].get(
                "columns",
                [],
            )
        )

        merged_rows = []

        first_rows = extracted_blocks[0].get(
            "rows",
            [],
        )

        for row_index in range(
            expected_row_count
        ):

            first_row = (
                first_rows[row_index]
                if row_index < len(first_rows)
                else {}
            )

            merged_rows.append(
                {
                    "category": first_row.get(
                        "category",
                        "",
                    ),
                    "description": first_row.get(
                        "description",
                        "",
                    ),
                    "values": list(
                        first_row.get(
                            "values",
                            []
                        )
                    ),
                }
            )

        merge_report = []

        for block_index in range(
            1,
            len(extracted_blocks),
        ):

            previous_block = (
                extracted_blocks[
                    block_index - 1
                ]
            )

            current_block = (
                extracted_blocks[
                    block_index
                ]
            )

            overlap_size = (
                self._detect_overlap_size(
                    previous_block=previous_block,
                    current_block=current_block,
                )
            )

            current_columns = (
                current_block.get(
                    "columns",
                    [],
                )
            )

            merged_columns.extend(
                current_columns[
                    overlap_size:
                ]
            )

            current_rows = (
                current_block.get(
                    "rows",
                    [],
                )
            )

            for row_index, merged_row in enumerate(
                merged_rows
            ):

                if row_index >= len(current_rows):

                    missing_width = (
                        len(current_columns)
                        - overlap_size
                    )

                    merged_row["values"].extend(
                        [None] * missing_width
                    )

                    continue

                current_row = (
                    current_rows[row_index]
                )

                current_values = list(
                    current_row.get(
                        "values",
                        []
                    )
                )

                merged_row["values"].extend(
                    current_values[
                        overlap_size:
                    ]
                )

                if not merged_row["category"]:
                    merged_row["category"] = (
                        current_row.get(
                            "category",
                            "",
                        )
                    )

                if not merged_row["description"]:
                    merged_row["description"] = (
                        current_row.get(
                            "description",
                            "",
                        )
                    )

            merge_report.append(
                {
                    "left_block": block_index,
                    "right_block": (
                        block_index + 1
                    ),
                    "overlap_size": overlap_size,
                }
            )

        return {
            "columns": merged_columns,
            "rows": merged_rows,
            "metadata": {
                "block_count": len(
                    extracted_blocks
                ),
                "row_counts": row_counts,
                "merge_report": merge_report,
            },
        }

    def _detect_overlap_size(
        self,
        previous_block: dict[str, Any],
        current_block: dict[str, Any],
    ) -> int:

        previous_columns = previous_block.get(
            "columns",
            [],
        )

        current_columns = current_block.get(
            "columns",
            [],
        )

        maximum_overlap = min(
            len(previous_columns),
            len(current_columns),
            8,
        )

        best_overlap = 0
        best_combined_score = 0.0
        best_value_score = 0.0
        best_header_score = 0.0

        for overlap_size in range(
            1,
            maximum_overlap + 1,
        ):

            value_score = (
                self._column_vector_overlap_score(
                    previous_block=previous_block,
                    current_block=current_block,
                    overlap_size=overlap_size,
                )
            )

            header_score = (
                self._column_overlap_score(
                    previous_columns[
                        -overlap_size:
                    ],
                    current_columns[
                        :overlap_size
                    ],
                )
            )

            combined_score = (
                value_score * 0.5
                + header_score * 0.5
            )

            if combined_score > best_combined_score:
                best_overlap = overlap_size
                best_combined_score = combined_score
                best_value_score = value_score
                best_header_score = header_score

        if (
            best_combined_score < 0.50
            and best_value_score < 0.65
            and best_header_score < 0.65
        ):
            return 0

        return best_overlap

    def _column_vector_overlap_score(
        self,
        previous_block: dict[str, Any],
        current_block: dict[str, Any],
        overlap_size: int,
    ) -> float:

        previous_rows = previous_block.get(
            "rows",
            [],
        )

        current_rows = current_block.get(
            "rows",
            [],
        )

        comparable_rows = min(
            len(previous_rows),
            len(current_rows),
        )

        matches = 0
        comparisons = 0

        for column_offset in range(
            overlap_size
        ):

            previous_index = (
                len(previous_block["columns"])
                - overlap_size
                + column_offset
            )

            current_index = column_offset

            for row_index in range(
                comparable_rows
            ):

                previous_values = (
                    previous_rows[row_index][
                        "values"
                    ]
                )

                current_values = (
                    current_rows[row_index][
                        "values"
                    ]
                )

                left_value = previous_values[
                    previous_index
                ]

                right_value = current_values[
                    current_index
                ]

                if (
                    left_value is None
                    or right_value is None
                ):
                    continue

                comparisons += 1

                if left_value == right_value:
                    matches += 1

        if comparisons == 0:
            return 0.0

        return matches / comparisons

    def _column_overlap_score(
        self,
        left_columns: list[Any],
        right_columns: list[Any],
    ) -> float:

        if not left_columns:
            return 0.0

        matches = 0

        for left, right in zip(
            left_columns,
            right_columns,
        ):

            left_normalized = (
                self._normalize_text(left)
            )

            right_normalized = (
                self._normalize_text(right)
            )

            if (
                left_normalized
                == right_normalized
            ):
                matches += 1

        return matches / len(left_columns)

    def _normalize_text(
        self,
        value: Any,
    ) -> str:

        return (
            str(value)
            .strip()
            .lower()
            .replace(" ", "")
            .replace(".", "")
        )