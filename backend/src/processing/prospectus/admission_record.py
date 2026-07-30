# from dataclasses import dataclass


# @dataclass
# class AdmissionRecord:

#     title: str

#     category: str | None

#     details: dict[str, str]

#     source_page: int

#     source_heading: str

#     source_text: str
from dataclasses import asdict, dataclass


@dataclass(slots=True)
class AdmissionRecord:
    """
    Structured admission section.
    """

    number: str

    title: str

    content: list[dict]

    source_page: int

    source_heading: str

    source_text: str

    parent: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)