from __future__ import annotations

from src.annotations.models import PendingSectionReview
from src.processing.prospectus.section_detector import (
    ProspectusSection,
)


class ReviewService:
    """
    Determines whether manual review
    is required after automatic detection.
    """

    def check(
        self,
        pages: list[dict],
        detected_sections: list[ProspectusSection],
    ) -> list[PendingSectionReview]:

        reviews: list[PendingSectionReview] = []

        detected_types = {
            section.section_type
            for section in detected_sections
        }

        regular_found = (
            "seat_distribution_regular"
            in detected_types
        )

        self_finance_found = (
            "seat_distribution_self_finance"
            in detected_types
        )

        if not regular_found and not self_finance_found:
            reviews.append(
                PendingSectionReview(
                    section_type="seat_distribution",
                    reason=(
                        "Automatic seat distribution "
                        "detection failed."
                    ),
                )
            )

        return reviews