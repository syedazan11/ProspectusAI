from typing import Any

from src.schemas.table import ExtractedTable


class TableQualityValidator:
    """
    Generic quality gate for extracted tables.

    No page-specific rules.
    No university-specific rules.
    No fixed headers or dimensions.

    Validation layers:
    1. Structural quality
    2. OCR corruption quality
    3. Inferred column-type consistency
    """

    def validate(
        self,
        table: ExtractedTable,
    ) -> dict[str, Any]:

        errors: list[str] = []
        warnings: list[str] = []

        columns = [
            str(column).strip()
            for column in table.columns
        ]

        rows = table.rows

        if not columns:
            errors.append("Table has no columns.")

        if not rows:
            errors.append("Table has no rows.")

        empty_column_ratio = (
            sum(not column for column in columns)
            / len(columns)
            if columns
            else 1.0
        )

        meaningful_column_ratio = (
            sum(
                self._is_meaningful_text(column)
                for column in columns
            )
            / len(columns)
            if columns
            else 0.0
        )

        duplicate_column_ratio = (
            self._duplicate_ratio(columns)
        )

        corrupted_column_ratio = (
            self._corrupted_text_ratio(columns)
        )

        non_empty_row_ratio = (
            self._non_empty_row_ratio(rows)
        )

        row_consistency_ratio = (
            self._row_consistency_ratio(
                columns,
                rows,
            )
        )

        cell_values = [
            str(value).strip()
            for row in rows
            for value in row.values()
            if value not in (
                None,
                "",
                [],
                {},
            )
        ]

        corrupted_cell_ratio = (
            self._corrupted_text_ratio(
                cell_values
            )
        )

        suspicious_short_cell_ratio = (
            self._suspicious_short_cell_ratio(
                cell_values
            )
        )

        type_metrics = (
            self._analyze_column_types(
                columns=columns,
                rows=rows,
            )
        )

        inferred_numeric_column_count = (
            type_metrics[
                "inferred_numeric_column_count"
            ]
        )

        contaminated_numeric_column_count = (
            type_metrics[
                "contaminated_numeric_column_count"
            ]
        )

        numeric_contamination_ratio = (
            type_metrics[
                "numeric_contamination_ratio"
            ]
        )

        contaminated_numeric_columns = (
            type_metrics[
                "contaminated_numeric_columns"
            ]
        )

        if empty_column_ratio >= 0.5:
            errors.append(
                "Most table columns are empty."
            )

        if meaningful_column_ratio < 0.5:
            errors.append(
                "Too few meaningful column headers."
            )

        if duplicate_column_ratio >= 0.5:
            errors.append(
                "Too many duplicate column headers."
            )

        if corrupted_column_ratio >= 0.5:
            errors.append(
                "Most column headers appear corrupted."
            )

        if non_empty_row_ratio < 0.5:
            errors.append(
                "Most table rows are empty."
            )

        if corrupted_cell_ratio >= 0.35:
            errors.append(
                "Table cell content appears heavily corrupted."
            )

        if suspicious_short_cell_ratio >= 0.6:
            errors.append(
                "Most table cells contain suspicious OCR fragments."
            )

        if (
            suspicious_short_cell_ratio >= 0.5
            and corrupted_column_ratio >= 0.25
        ):
            errors.append(
                "Table contains combined header and cell OCR corruption."
            )

        if contaminated_numeric_column_count > 0:
            errors.append(
                "Inferred numeric columns contain "
                "non-numeric text contamination."
            )

        if row_consistency_ratio < 0.5:
            warnings.append(
                "Row structure is inconsistent with "
                "the declared columns."
            )

        if 0 < empty_column_ratio < 0.5:
            warnings.append(
                "Some table column headers are empty."
            )

        if 0 < duplicate_column_ratio < 0.5:
            warnings.append(
                "Some table column headers are duplicated."
            )

        status = (
            "invalid"
            if errors
            else (
                "valid_with_warnings"
                if warnings
                else "valid"
            )
        )

        return {
            "is_valid": not errors,
            "status": status,
            "errors": errors,
            "warnings": warnings,
            "metrics": {
                "column_count": len(columns),
                "row_count": len(rows),
                "cell_count": len(cell_values),
                "empty_column_ratio": round(
                    empty_column_ratio,
                    3,
                ),
                "meaningful_column_ratio": round(
                    meaningful_column_ratio,
                    3,
                ),
                "duplicate_column_ratio": round(
                    duplicate_column_ratio,
                    3,
                ),
                "corrupted_column_ratio": round(
                    corrupted_column_ratio,
                    3,
                ),
                "non_empty_row_ratio": round(
                    non_empty_row_ratio,
                    3,
                ),
                "row_consistency_ratio": round(
                    row_consistency_ratio,
                    3,
                ),
                "corrupted_cell_ratio": round(
                    corrupted_cell_ratio,
                    3,
                ),
                "suspicious_short_cell_ratio": round(
                    suspicious_short_cell_ratio,
                    3,
                ),
                "inferred_numeric_column_count": (
                    inferred_numeric_column_count
                ),
                "contaminated_numeric_column_count": (
                    contaminated_numeric_column_count
                ),
                "numeric_contamination_ratio": round(
                    numeric_contamination_ratio,
                    3,
                ),
                "contaminated_numeric_columns": (
                    contaminated_numeric_columns
                ),
            },
        }

    def _analyze_column_types(
        self,
        columns: list[str],
        rows: list[dict[str, Any]],
    ) -> dict[str, Any]:

        inferred_numeric_columns = []
        contaminated_numeric_columns = []

        for column in columns:

            if not column:
                continue

            values = [
                str(row[column]).strip()
                for row in rows
                if column in row
                and row[column] not in (
                    None,
                    "",
                    [],
                    {},
                )
            ]

            if len(values) < 3:
                continue

            numeric_count = sum(
                self._looks_like_number(value)
                for value in values
            )

            numeric_ratio = (
                numeric_count
                / len(values)
            )

            if numeric_ratio < 0.7:
                continue

            inferred_numeric_columns.append(
                column
            )

            non_numeric_values = [
                value
                for value in values
                if not self._looks_like_number(
                    value
                )
            ]

            if non_numeric_values:
                contaminated_numeric_columns.append(
                    {
                        "column": column,
                        "numeric_ratio": round(
                            numeric_ratio,
                            3,
                        ),
                        "non_numeric_values": (
                            non_numeric_values[:5]
                        ),
                    }
                )

        inferred_count = len(
            inferred_numeric_columns
        )

        contaminated_count = len(
            contaminated_numeric_columns
        )

        contamination_ratio = (
            contaminated_count
            / inferred_count
            if inferred_count
            else 0.0
        )

        return {
            "inferred_numeric_column_count": (
                inferred_count
            ),
            "contaminated_numeric_column_count": (
                contaminated_count
            ),
            "numeric_contamination_ratio": (
                contamination_ratio
            ),
            "contaminated_numeric_columns": (
                contaminated_numeric_columns
            ),
        }

    def _is_meaningful_text(
        self,
        value: str,
    ) -> bool:

        if not value:
            return False

        return any(
            character.isalnum()
            for character in value
        )

    def _duplicate_ratio(
        self,
        values: list[str],
    ) -> float:

        non_empty = [
            value.casefold()
            for value in values
            if value
        ]

        if not non_empty:
            return 1.0

        return (
            len(non_empty)
            - len(set(non_empty))
        ) / len(non_empty)

    def _corrupted_text_ratio(
        self,
        values: list[str],
    ) -> float:

        if not values:
            return 0.0

        corrupted = sum(
            self._looks_corrupted(value)
            for value in values
        )

        return corrupted / len(values)

    def _looks_corrupted(
        self,
        value: str,
    ) -> bool:

        if not value:
            return False

        alphanumeric = sum(
            character.isalnum()
            for character in value
        )

        symbols = sum(
            not character.isalnum()
            and not character.isspace()
            for character in value
        )

        if alphanumeric == 0:
            return True

        if symbols > alphanumeric:
            return True

        if len(value) >= 40:
            tokens = value.split()

            if tokens:
                one_char_tokens = sum(
                    len(token) == 1
                    for token in tokens
                )

                if (
                    one_char_tokens
                    / len(tokens)
                    >= 0.4
                ):
                    return True

        return False

    def _suspicious_short_cell_ratio(
        self,
        values: list[str],
    ) -> float:

        if not values:
            return 0.0

        suspicious = 0

        for value in values:

            if (
                len(value) <= 3
                and not self._looks_like_number(
                    value
                )
            ):
                suspicious += 1

        return suspicious / len(values)

    def _looks_like_number(
        self,
        value: str,
    ) -> bool:

        cleaned = (
            value
            .replace(",", "")
            .replace(".", "")
            .replace("-", "")
            .replace("%", "")
        )

        return (
            bool(cleaned)
            and cleaned.isdigit()
        )

    def _non_empty_row_ratio(
        self,
        rows: list[dict[str, Any]],
    ) -> float:

        if not rows:
            return 0.0

        non_empty = sum(
            any(
                value not in (
                    None,
                    "",
                    [],
                    {},
                )
                for value in row.values()
            )
            for row in rows
        )

        return non_empty / len(rows)

    def _row_consistency_ratio(
        self,
        columns: list[str],
        rows: list[dict[str, Any]],
    ) -> float:

        if not columns or not rows:
            return 0.0

        declared = {
            column
            for column in columns
            if column
        }

        if not declared:
            return 0.0

        consistent = 0

        for row in rows:

            overlap = (
                declared
                & set(row.keys())
            )

            if (
                len(overlap)
                / len(declared)
                >= 0.5
            ):
                consistent += 1

        return consistent / len(rows)
