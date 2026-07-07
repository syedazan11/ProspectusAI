from typing import Any

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str


class PageReference(BaseModel):
    document: str
    page_number: int
    page_path: str | None = None
    page_url: str | None = None
    reason: str | None = None


class ChatResponse(BaseModel):
    answer: str
    status: str = "answered"

    sources: list[dict[str, Any]] = Field(
        default_factory=list
    )

    page_references: list[PageReference] = Field(
        default_factory=list
    )
