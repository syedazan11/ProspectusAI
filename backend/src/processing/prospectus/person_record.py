from dataclasses import asdict, dataclass


@dataclass(slots=True)
class PersonRecord:

    name: str

    role: str | None

    department: str | None

    qualifications: list[str]

    source_page: int

    def to_dict(self) -> dict:
        return asdict(self)