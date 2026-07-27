from dataclasses import asdict, dataclass


@dataclass(slots=True)
class FeeRecord:
    """
    Structured fee information extracted from a prospectus.
    """

    category: str | None

    amount: float | None

    currency: str | None

    payment_period: str | None

    scheme: str | None

    notes: str | None

    source_page: int

    source_heading: str

    source_text: str

    def to_dict(self) -> dict:
        return asdict(self)