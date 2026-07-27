from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

@dataclass(slots=True)
class PendingSectionReview:
    review_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    section_type: Literal["seat_distribution"] = (
        "seat_distribution"
    )

    reason: str = ""

    status: Literal[
        "pending",
        "resolved",
    ] = "pending"

    start_page: int | None = None

    end_page: int | None = None

    suggested_label: str | None = None

    created_at: str = field(
        default_factory=lambda:
            datetime.now(timezone.utc).isoformat()
    )

    resolved_at: str | None = None

@dataclass(slots=True)
class AdminSectionAnnotation:
    section_type: str

    label: str

    start_page: int

    end_page: int