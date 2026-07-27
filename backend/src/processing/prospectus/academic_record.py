from dataclasses import asdict, dataclass


@dataclass(slots=True)
class AcademicRecord:
    """
    Structured academic program information.
    """

    title: str

    department: str | None

    attributes: dict[str, str]

    source_page: int

    source_heading: str

    source_text: str

    def to_dict(self) -> dict:
        return asdict(self)