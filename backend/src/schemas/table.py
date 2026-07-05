from typing import Any

from pydantic import BaseModel, Field


class ExtractedTable(BaseModel):
    """
    Generic structured table extracted from any document.
    """

    table_title: str
    page_number: int
    columns: list[str]

    rows: list[dict[str, Any]]

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )