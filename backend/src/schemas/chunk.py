from pydantic import BaseModel, Field


class ParentChunk(BaseModel):
    chunk_id: str
    heading: str
    heading_number: str = ""
    heading_level: int = 0
    heading_title: str = ""
    page_number: int
    content: str
    metadata: dict = Field(default_factory=dict)


class ChildChunk(BaseModel):
    chunk_id: str
    parent_chunk_id: str
    page_number: int
    heading: str
    heading_number: str = ""
    heading_level: int = 0
    heading_title: str = ""
    content: str
    metadata: dict = Field(default_factory=dict)