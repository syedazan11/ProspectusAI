from dataclasses import asdict, dataclass
from typing import Literal


ExtractionMethod = Literal["native", "needs_ocr", "ocr"]


@dataclass(slots=True)
class TextQuality:
    character_count: int
    word_count: int
    alphanumeric_ratio: float
    replacement_character_count: int
    is_usable: bool
    reasons: list[str]
    warnings: list[str]

    def to_dict(self) -> dict:
        return asdict(self)
    
@dataclass(slots=True)
class LayoutItem:
    text: str
    x: float
    y: float
    top: float
    bottom: float
    height: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(slots=True)
class ExtractedPage:
    page_number: int
    text: str
    extraction_method: ExtractionMethod
    quality: TextQuality
    layout_items: list[LayoutItem] | None = None

    def to_dict(self) -> dict:
        return {
            "page_number": self.page_number,
            "text": self.text,
            "extraction_method": self.extraction_method,
            "quality": self.quality.to_dict(),
            "layout_items": (
                [item.to_dict() for item in self.layout_items]
                if self.layout_items is not None
                else None
            ),
        }


@dataclass(slots=True)
class ExtractedDocument:
    source_file: str
    total_pages: int
    native_pages: int
    ocr_pages: int
    pages_needing_ocr: int
    pages: list[ExtractedPage]

    @property
    def document_type(self) -> str:
        if self.ocr_pages == 0:
            return "digital"

        if self.native_pages == 0:
            return "scanned"

        return "mixed"

    def to_dict(self) -> dict:
        return {
            "source_file": self.source_file,
            "total_pages": self.total_pages,
            "document_type": self.document_type,
            "native_pages": self.native_pages,
            "ocr_pages": self.ocr_pages,
            "pages_needing_ocr": self.pages_needing_ocr,
            "pages": [
                page.to_dict()
                for page in self.pages
            ],
        }

