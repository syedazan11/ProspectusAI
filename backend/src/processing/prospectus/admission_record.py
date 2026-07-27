from dataclasses import dataclass


@dataclass
class AdmissionRecord:

    title: str

    category: str | None

    details: dict[str, str]

    source_page: int

    source_heading: str

    source_text: str