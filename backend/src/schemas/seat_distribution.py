from pydantic import BaseModel, Field


class SeatDistributionPage(BaseModel):
    page: int
    confidence: float = 1.0
    admin_verified: bool = False


class SeatDistributionSection(BaseModel):
    scheme: str
    extractable: bool
    pages: list[SeatDistributionPage] = (
        Field(default_factory=list)
    )

    @classmethod
    def from_page_range(
        cls,
        scheme: str,
        start_page: int,
        end_page: int,
        extractable: bool = False,
    ):
        return cls(
            scheme=scheme,
            extractable=extractable,
            pages=[
                SeatDistributionPage(page=page)
                for page in range(
                    start_page,
                    end_page + 1,
                )
            ],
        )


class SeatDistributionDocument(BaseModel):
    document_id: str
    sections: list[SeatDistributionSection] = (
        Field(default_factory=list)
    )