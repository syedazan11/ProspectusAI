from dataclasses import asdict, dataclass


@dataclass(slots=True)
class ContactRecord:
    """
    Structured contact information
    extracted from a prospectus.
    """

    contact_type: str

    value: str

    department: str | None

    source_page: int

    source_heading: str

    source_text: str

    def to_dict(self) -> dict:
        return asdict(self)