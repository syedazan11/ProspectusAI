from dataclasses import dataclass
from typing import Literal


@dataclass(slots=True)
class PendingSectionReview:
    """
    Created when automatic section detection
    cannot confidently identify a section.
    """

    section_type: Literal["seat_distribution"]

    reason: str

    suggested_start_page: int | None = None
    suggested_end_page: int | None = None


@dataclass(slots=True)
class AdminSectionAnnotation:
    """
    Human-approved section boundaries.
    """

    section_type: str

    label: str

    start_page: int

    end_page: int