from typing import Any


class TableValidator:
    """
    Validates a merged extracted table.

    Checks:
    - row width matches column width
    - missing cells are reported
    - numeric totals are validated when a
      Total column exists
    """

    def validate(
        self,
        table: dict[str, Any],
    ) -> dict[str, Any]:

        columns = table.get("columns", [])
        rows = table.get("rows", [])

        expected_width = len(columns)

        structure_errors = []
        missing_cells = []
        total_checks = []

        total_index = self._find_total_index(
            columns
        )

        for row_index, row in enumerate(
            rows
        ):

            category = (
                row.get("category")
                or f"row_{row_index + 1}"
            )

            values = row.get(
                "values",
                [],
            )

            if len(values) != expected_width:

                structure_errors.append(
                    {
                        "category": category,
                        "expected": expected_width,
                        "actual": len(values),
                    }
                )

                continue

            missing_indexes = [
                index
                for index, value in enumerate(values)
                if value is None
            ]

            if missing_indexes:

                missing_cells.append(
                    {
                        "category": category,
                        "columns": [
                            columns[index]
                            for index in missing_indexes
                        ],
                    }
                )

            if total_index is not None:

                total_check = (
                    self._validate_total(
                        category=category,
                        values=values,
                        total_index=total_index,
                    )
                )

                total_checks.append(
                    total_check
                )

        invalid_totals = [
            check
            for check in total_checks
            if check["status"] == "invalid"
        ]

        review_totals = [
            check
            for check in total_checks
            if check["status"] == "needs_review"
        ]

        is_structurally_valid = (
            len(structure_errors) == 0
        )

        is_fully_valid = (
            is_structurally_valid
            and len(invalid_totals) == 0
            and len(review_totals) == 0
            and len(missing_cells) == 0
        )

        return {
            "is_structurally_valid": (
                is_structurally_valid
            ),
            "is_fully_valid": is_fully_valid,
            "expected_width": expected_width,
            "row_count": len(rows),
            "structure_errors": structure_errors,
            "missing_cells": missing_cells,
            "total_checks": total_checks,
            "invalid_total_count": len(
                invalid_totals
            ),
            "needs_review_count": len(
                review_totals
            ),
        }

    def _find_total_index(
        self,
        columns: list[Any],
    ) -> int | None:

        for index, column in enumerate(
            columns
        ):

            normalized = (
                str(column)
                .strip()
                .lower()
            )

            if normalized in {
                "total",
                "grand total",
            }:
                return index

        return None

    def _validate_total(
        self,
        category: str,
        values: list[Any],
        total_index: int,
    ) -> dict[str, Any]:

        printed_total = values[
            total_index
        ]

        data_values = values[
            :total_index
        ]

        if printed_total is None:

            return {
                "category": category,
                "status": "needs_review",
                "reason": "Total is missing.",
            }

        if any(
            value is None
            for value in data_values
        ):

            return {
                "category": category,
                "status": "needs_review",
                "reason": (
                    "One or more data cells "
                    "are missing."
                ),
                "printed_total": printed_total,
            }

        numeric_values = []

        for value in data_values:

            if isinstance(
                value,
                (int, float),
            ):
                numeric_values.append(value)

            else:
                return {
                    "category": category,
                    "status": "needs_review",
                    "reason": (
                        "One or more data cells "
                        "are not numeric."
                    ),
                    "printed_total": printed_total,
                }

        if not isinstance(
            printed_total,
            (int, float),
        ):

            return {
                "category": category,
                "status": "needs_review",
                "reason": (
                    "Printed total is not numeric."
                ),
            }

        calculated_total = sum(
            numeric_values
        )

        status = (
            "valid"
            if calculated_total == printed_total
            else "invalid"
        )

        return {
            "category": category,
            "status": status,
            "calculated_total": (
                calculated_total
            ),
            "printed_total": printed_total,
        }