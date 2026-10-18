from dataclasses import dataclass, field
from typing import Any


@dataclass
class AnswerContext:

    question: str

    retrieval_query: str = ""

    chunks: list[dict[str, Any]] = field(default_factory=list)

    selected_chunks: list[dict[str, Any]] = field(default_factory=list)

    context: str = ""

    prompt: str = ""

    answer: str = ""

    has_complex_table: bool = False

    page_references: list[dict[str, Any]] = field(default_factory=list)

    status: str = "answered"