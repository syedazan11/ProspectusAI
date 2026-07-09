from dataclasses import asdict, dataclass


@dataclass(slots=True)
class ProspectusChunk:
    chunk_id: str
    page_number: int
    text: str
    section_heading: str | None
    character_count: int

    def to_dict(self) -> dict:
        return asdict(self)
