from dataclasses import asdict, dataclass


@dataclass(slots=True)
class PersonRecord:

    name: str

    role: str | None

    department: str | None

    qualifications: list[str]

    source_page: int

    source_heading: str

    source_text: str

    def to_dict(self) -> dict:
        return asdict(self)