from dataclasses import dataclass

@dataclass(slots=True)
class AdmissionCategoryRecord:
    code: str
    scheme: str | None
    description: str
    source_page: int
    source_heading: str
    source_text: str