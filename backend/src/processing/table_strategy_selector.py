from typing import Any


class TableStrategySelector:
    """
    Chooses how a table should be extracted.

    Current strategies:
    - single: extract the table in one vision request
    - adaptive_blocks: split dense/wide tables into blocks
    """

    def select(
        self,
        layout: dict[str, Any],
    ) -> str:

        if layout.get("requires_splitting", False):
            return "adaptive_blocks"

        return "single"