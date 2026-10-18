from dataclasses import dataclass, field
# @dataclass
# class StudentLifeRecord:

#     title: str

#     category: str | None

#     attributes: dict[str, str]

#     source_page: int

#     source_heading: str

#     source_text: str
@dataclass(slots=True)
class StudentLifeRecord:

    number: str

    title: str

    content: list[dict]

    source_page: int

    source_heading: str

    source_text: str

    parent: str | None = None

