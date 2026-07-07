from typing import Any

import pandas as pd


class TableQualityEvaluator:
    """
    Evaluates whether a table extracted locally
    by Docling is structurally usable.

    This evaluator does not call an LLM or API.

    Decision:
    - accept_local
    - escalate_to_vision
    """

    def evaluate(
        self,
        dataframe: pd.DataFrame,
    ) -> dict[str, Any]:

        row_count = len(dataframe)
        column_count = len(dataframe.columns)

        if row_count == 0 or column_count == 0:
            return self._result(
                usable=False,
                action="escalate_to_vision",
                reasons=["empty_table"],
                row_count=row_count,
                column_count=column_count,
            )

        normalized_headers = [
            str(column).strip()
            for column in dataframe.columns
        ]

        blank_header_count = sum(
            1
            for header in normalized_headers
            if not header
        )

        duplicate_header_count = (
            len(normalized_headers)
            - len(set(normalized_headers))
        )

        cell_lengths = []

        non_empty_cell_count = 0

        for value in dataframe.to_numpy().flatten():

            text = str(value).strip()

            if not text or text.lower() == "nan":
                continue

            non_empty_cell_count += 1
            cell_lengths.append(len(text))

        max_cell_length = (
            max(cell_lengths)
            if cell_lengths
            else 0
        )

        average_cell_length = (
            sum(cell_lengths) / len(cell_lengths)
            if cell_lengths
            else 0.0
        )

        reasons = []

        if non_empty_cell_count == 0:
            reasons.append("no_meaningful_cells")

        if (
            row_count <= 2
            and column_count >= 8
            and max_cell_length >= 300
        ):
            reasons.append(
                "suspicious_wide_low_row_table"
            )

        if max_cell_length >= 1500:
            reasons.append(
                "extreme_cell_content"
            )

        if (
            average_cell_length >= 250
            and column_count >= 8
        ):
            reasons.append(
                "abnormally_large_cells"
            )

        if (
            blank_header_count
            >= max(2, column_count // 3)
        ):
            reasons.append(
                "too_many_blank_headers"
            )

        if (
            duplicate_header_count
            >= max(2, column_count // 3)
        ):
            reasons.append(
                "too_many_duplicate_headers"
            )

        usable = len(reasons) == 0

        return self._result(
            usable=usable,
            action=(
                "accept_local"
                if usable
                else "escalate_to_vision"
            ),
            reasons=reasons,
            row_count=row_count,
            column_count=column_count,
            blank_header_count=blank_header_count,
            duplicate_header_count=(
                duplicate_header_count
            ),
            max_cell_length=max_cell_length,
            average_cell_length=round(
                average_cell_length,
                2,
            ),
            non_empty_cell_count=(
                non_empty_cell_count
            ),
        )

    def _result(
        self,
        usable: bool,
        action: str,
        reasons: list[str],
        row_count: int,
        column_count: int,
        **metrics: Any,
    ) -> dict[str, Any]:

        return {
            "usable": usable,
            "action": action,
            "reasons": reasons,
            "metrics": {
                "row_count": row_count,
                "column_count": column_count,
                **metrics,
            },
        }