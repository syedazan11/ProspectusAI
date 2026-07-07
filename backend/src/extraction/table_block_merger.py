from typing import Any


class TableBlockMerger:
    """
    Merges overlapping table blocks extracted from
    a 2D adaptive grid.

    Process:
    1. Group blocks by vertical row band.
    2. Merge blocks inside each band horizontally.
    3. Stack merged row bands vertically.
    4. Remove duplicate rows caused by vertical overlap.
    """

    def merge(
        self,
        blocks: list[dict[str, Any]],
    ) -> dict[str, Any]:

        if not blocks:
            raise ValueError(
                "No extracted blocks were provided."
            )

        # Group blocks by vertical row band.
        row_bands: dict[
            int,
            list[dict[str, Any]],
        ] = {}

        for block in blocks:

            row_band_index = block.get(
                "row_band_index",
                0,
            )

            row_bands.setdefault(
                row_band_index,
                [],
            ).append(block)

        merged_bands = []
        full_merge_report = []

        # Merge each row band horizontally.
        for row_band_index in sorted(row_bands):

            band_blocks = sorted(
                row_bands[row_band_index],
                key=lambda block: block.get(
                    "column_band_index",
                    block["block_index"],
                ),
            )

            extracted_blocks = [
                block["extracted_data"]
                for block in band_blocks
            ]

            row_counts = [
                len(block.get("rows", []))
                for block in extracted_blocks
            ]

            expected_row_count = max(
                row_counts,
                default=0,
            )

            if expected_row_count == 0:
                continue

            first_block = extracted_blocks[0]

            merged_columns = list(
                first_block.get(
                    "columns",
                    [],
                )
            )

            first_rows = first_block.get(
                "rows",
                [],
            )

            merged_rows = []

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
                                [],
                            )
                        ),
                    }
                )

            # Merge remaining column blocks
            # inside this row band.
            for local_index in range(
                1,
                len(extracted_blocks),
            ):

                previous_block = (
                    extracted_blocks[
                        local_index - 1
                    ]
                )

                current_block = (
                    extracted_blocks[
                        local_index
                    ]
                )

                overlap_size = (
                    self._detect_overlap_size(
                        previous_block=previous_block,
                        current_block=current_block,
                    )
                )

                current_columns = list(
                    current_block.get(
                        "columns",
                        [],
                    )
                )

                added_columns = (
                    current_columns[
                        overlap_size:
                    ]
                )

                merged_columns.extend(
                    added_columns
                )

                current_rows = (
                    current_block.get(
                        "rows",
                        [],
                    )
                )

                for (
                    row_index,
                    merged_row,
                ) in enumerate(merged_rows):

                    if row_index >= len(
                        current_rows
                    ):

                        merged_row[
                            "values"
                        ].extend(
                            [None]
                            * len(added_columns)
                        )

                        continue

                    current_row = (
                        current_rows[
                            row_index
                        ]
                    )

                    current_values = list(
                        current_row.get(
                            "values",
                            [],
                        )
                    )

                    merged_row[
                        "values"
                    ].extend(
                        current_values[
                            overlap_size:
                        ]
                    )

                    if not merged_row[
                        "category"
                    ]:

                        merged_row[
                            "category"
                        ] = current_row.get(
                            "category",
                            "",
                        )

                    if not merged_row[
                        "description"
                    ]:

                        merged_row[
                            "description"
                        ] = current_row.get(
                            "description",
                            "",
                        )

                full_merge_report.append(
                    {
                        "row_band_index": (
                            row_band_index
                        ),
                        "left_block": (
                            band_blocks[
                                local_index - 1
                            ]["block_index"]
                        ),
                        "right_block": (
                            band_blocks[
                                local_index
                            ]["block_index"]
                        ),
                        "overlap_size": (
                            overlap_size
                        ),
                    }
                )

            merged_bands.append(
                {
                    "row_band_index": (
                        row_band_index
                    ),
                    "columns": merged_columns,
                    "rows": merged_rows,
                    "row_counts": row_counts,
                }
            )

        if not merged_bands:
            raise ValueError(
                "No table rows were extracted."
            )

        # Use the widest merged row band
        # as the final column structure.
        widest_band = max(
            merged_bands,
            key=lambda band: len(
                band["columns"]
            ),
        )

        final_columns = list(
            widest_band["columns"]
        )

        final_rows = []

        # Stack row bands vertically.
        for band in merged_bands:

            for row in band["rows"]:

                values = list(
                    row.get(
                        "values",
                        [],
                    )
                )

                if len(values) < len(
                    final_columns
                ):

                    values.extend(
                        [None]
                        * (
                            len(final_columns)
                            - len(values)
                        )
                    )

                elif len(values) > len(
                    final_columns
                ):

                    values = values[
                        :len(final_columns)
                    ]

                normalized_row = {
                    "category": row.get(
                        "category",
                        "",
                    ),
                    "description": row.get(
                        "description",
                        "",
                    ),
                    "values": values,
                }

                category = str(
                    normalized_row.get(
                        "category",
                        "",
                    )
                ).strip().lower()

                description = str(
                    normalized_row.get(
                        "description",
                        "",
                    )
                ).strip().lower()

                is_duplicate = False

                # Check only nearby rows because
                # duplicates can occur at vertical
                # band boundaries.
                for existing_row in final_rows[-5:]:

                    existing_category = str(
                        existing_row.get(
                            "category",
                            "",
                        )
                    ).strip().lower()

                    existing_description = str(
                        existing_row.get(
                            "description",
                            "",
                        )
                    ).strip().lower()

                    if (
                        category
                        and category
                        == existing_category
                    ):
                        is_duplicate = True
                        break

                    if (
                        not category
                        and description
                        and description
                        == existing_description
                    ):
                        is_duplicate = True
                        break

                if not is_duplicate:
                    final_rows.append(
                        normalized_row
                    )

        return {
            "columns": final_columns,
            "rows": final_rows,
            "metadata": {
                "block_count": len(blocks),
                "row_band_count": len(
                    merged_bands
                ),
                "band_row_counts": [
                    {
                        "row_band_index": (
                            band[
                                "row_band_index"
                            ]
                        ),
                        "source_row_counts": (
                            band[
                                "row_counts"
                            ]
                        ),
                        "merged_row_count": len(
                            band["rows"]
                        ),
                    }
                    for band in merged_bands
                ],
                "merge_report": (
                    full_merge_report
                ),
            },
        }
    
    def _get_anchor_rows(
        self,
        band_blocks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Uses the leftmost block as the authoritative
        row structure for a horizontal row band.
        """

        if not band_blocks:
            return []

        anchor_block = band_blocks[0]
        anchor_data = anchor_block.get(
            "extracted_data",
            {},
        )

        anchor_rows = []

        for row in anchor_data.get("rows", []):

            category = str(
                row.get("category") or ""
            ).strip()

            description = str(
                row.get("description") or ""
            ).strip()

            if not category and not description:
                continue

            anchor_rows.append(
                {
                    "category": category,
                    "description": description,
                    "values": list(
                        row.get("values", [])
                    ),
                }
            )

        return anchor_rows

    

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

            if (
                combined_score
                > best_combined_score
            ):
                best_overlap = overlap_size
                best_combined_score = (
                    combined_score
                )
                best_value_score = value_score
                best_header_score = (
                    header_score
                )

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
                len(
                    previous_block[
                        "columns"
                    ]
                )
                - overlap_size
                + column_offset
            )

            current_index = column_offset

            for row_index in range(
                comparable_rows
            ):

                previous_values = (
                    previous_rows[
                        row_index
                    ].get(
                        "values",
                        [],
                    )
                )

                current_values = (
                    current_rows[
                        row_index
                    ].get(
                        "values",
                        [],
                    )
                )

                if (
                    previous_index
                    >= len(previous_values)
                    or current_index
                    >= len(current_values)
                ):
                    continue

                left_value = (
                    previous_values[
                        previous_index
                    ]
                )

                right_value = (
                    current_values[
                        current_index
                    ]
                )

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