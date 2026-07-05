from typing import Any


class TableRecoveryPlanner:
    """
    Creates a targeted recovery plan from table
    validation failures.

    It does not perform extraction itself.
    """

    def create_plan(
        self,
        table: dict[str, Any],
        validation: dict[str, Any],
        blocks: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:

        rows = table.get("rows", [])

        failed_categories = set()

        for check in validation.get(
            "total_checks",
            [],
        ):
            if check.get("status") in {
                "invalid",
                "needs_review",
            }:
                failed_categories.add(
                    check.get("category")
                )

        for item in validation.get(
            "missing_cells",
            [],
        ):
            failed_categories.add(
                item.get("category")
            )

        recovery_rows = []

        for row_index, row in enumerate(rows):

            category = (
                row.get("category")
                or f"row_{row_index + 1}"
            )

            if category not in failed_categories:
                continue

            reasons = []

            total_check = self._find_total_check(
                category=category,
                validation=validation,
            )

            if total_check:

                status = total_check.get("status")

                if status == "invalid":
                    reasons.append(
                        "total_mismatch"
                    )

                elif status == "needs_review":
                    reasons.append(
                        "total_needs_review"
                    )

            missing_info = (
                self._find_missing_cells(
                    category=category,
                    validation=validation,
                )
            )

            missing_columns = []

            if missing_info:

                missing_columns = (
                    missing_info.get(
                        "columns",
                        [],
                    )
                )

                reasons.append(
                    "missing_cells"
                )

            recovery_scope = (
                "full_row"
                if "total_mismatch" in reasons
                else "missing_columns"
            )

            recovery_rows.append(
                {
                    "row_index": row_index,
                    "category": category,
                    "reasons": reasons,
                    "recovery_scope": recovery_scope,
                    "missing_columns": missing_columns,
                }
            )

        row_bands = self._group_contiguous_rows(
            recovery_rows
        )
        column_ranges = self._build_column_ranges(
            columns=table.get("columns", []),
            recovery_rows=recovery_rows,
        )
        recovery_blocks = []

        if blocks:
            recovery_blocks = (
                self._map_recoveries_to_blocks(
                    recovery_rows=recovery_rows,
                    blocks=blocks,
                )
            )

        return {
            "requires_recovery": bool(
                recovery_rows
            ),
            "failed_row_count": len(
                recovery_rows
            ),
            "recovery_rows": recovery_rows,
            "row_bands": row_bands,
            "column_ranges": column_ranges,
            "recovery_blocks": recovery_blocks,
            "full_row_recoveries": [
                row
                for row in recovery_rows
                if row["recovery_scope"] == "full_row"
            ],
            "missing_cell_recoveries": [
                row
                for row in recovery_rows
                if row["recovery_scope"] == "missing_columns"
            ],
        }

    def _find_total_check(
        self,
        category: str,
        validation: dict[str, Any],
    ) -> dict[str, Any] | None:

        for check in validation.get(
            "total_checks",
            [],
        ):
            if (
                check.get("category")
                == category
            ):
                return check

        return None

    def _find_missing_cells(
        self,
        category: str,
        validation: dict[str, Any],
    ) -> dict[str, Any] | None:

        for item in validation.get(
            "missing_cells",
            [],
        ):
            if (
                item.get("category")
                == category
            ):
                return item

        return None

    def _group_contiguous_rows(
        self,
        recovery_rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

        if not recovery_rows:
            return []

        row_indexes = sorted(
            row["row_index"]
            for row in recovery_rows
        )

        groups = []
        current_group = [
            row_indexes[0]
        ]

        for row_index in row_indexes[1:]:

            if (
                row_index
                == current_group[-1] + 1
            ):
                current_group.append(
                    row_index
                )

            else:
                groups.append(
                    current_group
                )

                current_group = [
                    row_index
                ]

        groups.append(
            current_group
        )

        return [
            {
                "start_row_index": group[0],
                "end_row_index": group[-1],
                "row_count": len(group),
            }
            for group in groups
        ]

    def _build_column_ranges(
        self,
        columns: list[Any],
        recovery_rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

        affected_indexes = set()

        for row in recovery_rows:

            for column_name in row.get(
                "missing_columns",
                [],
            ):

                if column_name in columns:
                    affected_indexes.add(
                        columns.index(column_name)
                    )

        if not affected_indexes:
            return []

        sorted_indexes = sorted(
            affected_indexes
        )

        groups = []
        current_group = [
            sorted_indexes[0]
        ]

        for column_index in sorted_indexes[1:]:

            if (
                column_index
                == current_group[-1] + 1
            ):
                current_group.append(
                    column_index
                )

            else:
                groups.append(
                    current_group
                )

                current_group = [
                    column_index
                ]

        groups.append(
            current_group
        )

        return [
            {
                "start_column_index": group[0],
                "end_column_index": group[-1],
                "column_count": len(group),
                "columns": [
                    columns[index]
                    for index in group
                ],
            }
            for group in groups
        ]

    def _map_recoveries_to_blocks(
        self,
        recovery_rows: list[dict[str, Any]],
        blocks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

        recovery_blocks = []

        for block in blocks:

            block_index = block.get(
                "block_index"
            )

            extracted_data = block.get(
                "extracted_data",
                {},
            )

            block_columns = extracted_data.get(
                "columns",
                [],
            )

            affected_rows = []

            for recovery_row in recovery_rows:

                scope = recovery_row.get(
                    "recovery_scope"
                )

                if scope == "full_row":

                    affected_rows.append(
                        recovery_row["row_index"]
                    )

                    continue

                missing_columns = set(
                    recovery_row.get(
                        "missing_columns",
                        [],
                    )
                )

                if missing_columns.intersection(
                    block_columns
                ):
                    affected_rows.append(
                        recovery_row["row_index"]
                    )

            if not affected_rows:
                continue

            recovery_blocks.append(
                {
                    "block_index": block_index,
                    "row_indexes": sorted(
                        set(affected_rows)
                    ),
                    "coordinates": {
                        "left": block.get("left"),
                        "top": block.get("top"),
                        "right": block.get("right"),
                        "bottom": block.get("bottom"),
                    },
                }
            )

        return recovery_blocks

    def apply_recovery(
        self,
        table: dict[str, Any],
        recovery_results: list[dict[str, Any]],
        recovery_plan: dict[str, Any],
    ) -> dict[str, Any]:

        columns = table.get("columns", [])
        rows = table.get("rows", [])

        patched_cells = 0
        ignored_cells = 0
        rejected_candidates = 0

        recovery_rows = {
            item["row_index"]: item
            for item in recovery_plan.get(
                "recovery_rows",
                [],
            )
        }

        for block_result in recovery_results:

            for recovered_row in block_result.get(
                "rows",
                [],
            ):

                row_index = recovered_row.get(
                    "row_index"
                )

                category = recovered_row.get(
                    "category"
                )

                if (
                    not isinstance(row_index, int)
                    or row_index < 0
                    or row_index >= len(rows)
                ):
                    continue

                target_row = rows[row_index]

                if target_row.get("category") != category:
                    continue

                instruction = recovery_rows.get(
                    row_index
                )

                if not instruction:
                    continue

                scope = instruction.get(
                    "recovery_scope"
                )

                missing_columns = set(
                    instruction.get(
                        "missing_columns",
                        [],
                    )
                )

                valid_cells = {}

                for column_name, value in (
                    recovered_row.get(
                        "cells",
                        {},
                    ).items()
                ):

                    if column_name not in columns:
                        ignored_cells += 1
                        continue

                    if (
                        scope == "missing_columns"
                        and column_name not in missing_columns
                    ):
                        ignored_cells += 1
                        continue

                    if value is None:
                        continue

                    if isinstance(value, str):

                        cleaned = value.strip()

                        if not cleaned.lstrip(
                            "-"
                        ).isdigit():
                            ignored_cells += 1
                            continue

                        value = int(cleaned)

                    elif not isinstance(
                        value,
                        (int, float),
                    ):
                        ignored_cells += 1
                        continue

                    valid_cells[column_name] = value

                if not valid_cells:
                    continue

                printed_total = target_row.get(
                    "printed_total"
                )

                if printed_total is None:
                    printed_total = target_row.get(
                        "total"
                    )

                if not isinstance(
                    printed_total,
                    (int, float),
                ):
                    rejected_candidates += 1
                    continue

                current_values = list(
                    target_row.get(
                        "values",
                        [],
                    )
                )

                candidate_values = list(
                    current_values
                )

                for column_name, value in (
                    valid_cells.items()
                ):

                    column_index = columns.index(
                        column_name
                    )

                    candidate_values[
                        column_index
                    ] = value

                if any(
                    value is None
                    for value in current_values
                ):
                    current_error = float("inf")

                elif all(
                    isinstance(value, (int, float))
                    for value in current_values
                ):
                    current_error = abs(
                        sum(current_values)
                        - printed_total
                    )

                else:
                    current_error = float("inf")

                if any(
                    value is None
                    for value in candidate_values
                ):
                    candidate_error = float("inf")

                elif all(
                    isinstance(value, (int, float))
                    for value in candidate_values
                ):
                    candidate_error = abs(
                        sum(candidate_values)
                        - printed_total
                    )

                else:
                    candidate_error = float("inf")

                if candidate_error >= current_error:
                    rejected_candidates += 1
                    continue

                for column_name, value in (
                    valid_cells.items()
                ):

                    column_index = columns.index(
                        column_name
                    )

                    target_row["values"][
                        column_index
                    ] = value

                    patched_cells += 1

        table.setdefault(
            "metadata",
            {},
        )["recovery_report"] = {
            "patched_cells": patched_cells,
            "ignored_cells": ignored_cells,
            "rejected_candidates": (
                rejected_candidates
            ),
        }

        return table