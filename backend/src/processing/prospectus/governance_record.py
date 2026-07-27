from dataclasses import dataclass


@dataclass
class GovernanceRecord:

    title: str

    category: str | None

    attributes: dict[str, str]

    source_page: int

    source_heading: str

    source_text: str