from dataclasses import asdict, dataclass
from typing import Literal


BlockType = Literal[
    "heading",
    "paragraph",
    "list_item",
    "table_signal",
]


@dataclass(slots=True)
class DocumentBlock:
    block_id: str
    page_number: int
    block_type: BlockType
    text: str
    heading_level: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)
