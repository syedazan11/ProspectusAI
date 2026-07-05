from pydantic import BaseModel, Field


class ParsedPage(BaseModel):
    page_number: int

    markdown: str = ""

    text: str = ""

    headings: list[str] = Field(default_factory=list)

    paragraphs: list[str] = Field(default_factory=list)

    lists: list[str] = Field(default_factory=list)

    has_tables: bool = False

    has_images: bool = False

    metadata: dict = Field(default_factory=dict)


class ParsedDocument(BaseModel):
    document_type: str

    total_pages: int

    pages: list[ParsedPage] = Field(default_factory=list)

    metadata: dict = Field(default_factory=dict)