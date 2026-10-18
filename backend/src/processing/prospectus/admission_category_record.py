from dataclasses import asdict, dataclass
@dataclass(slots=True)
class AdmissionCategoryRecord:
    code: str
    scheme: str | None
    description: str
    source_page: int

    def to_dict(self) -> dict:
        return asdict(self)