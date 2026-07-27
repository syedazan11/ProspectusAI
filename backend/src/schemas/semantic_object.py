from pydantic import BaseModel, Field


class SemanticObject(BaseModel):
    """
    Generic semantic object extracted from any university prospectus.
    """

    object_id: str

    object_type: str

    page_number: int

    source_id: str

    heading: str = ""

    title: str = ""

    text: str

    metadata: dict = Field(default_factory=dict)

    relationships: dict[str, list[str]] = Field(
        default_factory=dict
    )