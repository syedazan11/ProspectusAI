from dataclasses import asdict, dataclass


@dataclass(slots=True)
class FeeRecord:
    """
    Structured fee information extracted from a prospectus.

    The record keeps both the fee itself and the contextual
    information needed to determine who/what the fee applies to.
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

    # Additional contextual information.
    #
    # These fields are intentionally generic. They do not contain
    # programme-specific or page-specific rules.
    fee_type: str | None = None

    applicability: str | None = None

    programme_scope: str | None = None

    # Physical campus/location to which the fee applies.
    campus: str | None = None

    # Student type, e.g. local or foreign.
    student_type: str | None = None


    section_number: str | None = None

    section_heading: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)