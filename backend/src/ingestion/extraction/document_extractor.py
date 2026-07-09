from __future__ import annotations

from pathlib import Path

import fitz

from src.ingestion.extraction.models import (
    ExtractedDocument,
)
from src.ingestion.extraction.ocr_extractor import (
    OCRExtractor,
)
from src.ingestion.extraction.pdf_extractor import (
    PDFExtractor,
)


class DocumentExtractor:
    """
    Complete PDF extraction pipeline.

    1. Try native text extraction.
    2. Keep usable native pages.
    3. OCR only pages that require fallback.
    """

    def __init__(self) -> None:
        self.native_extractor = PDFExtractor()
        self.ocr_extractor = OCRExtractor(
            render_scale=2.0,
        )

    def extract(
        self,
        file_path: str | Path,
    ) -> ExtractedDocument:
        native_result = (
            self.native_extractor.extract(file_path)
        )

        pages_by_number = {
            page.page_number: page
            for page in native_result.pages
        }

        ocr_page_numbers = [
            page.page_number
            for page in native_result.pages
            if page.extraction_method == "needs_ocr"
        ]

        if ocr_page_numbers:
            with fitz.open(file_path) as pdf:
                ocr_pages = (
                    self.ocr_extractor.extract_pages(
                        pdf=pdf,
                        page_numbers=ocr_page_numbers,
                    )
                )

            for page in ocr_pages:
                pages_by_number[page.page_number] = page

        pages = [
            pages_by_number[page_number]
            for page_number in sorted(pages_by_number)
        ]

        native_pages = sum(
            page.extraction_method == "native"
            for page in pages
        )

        ocr_pages = sum(
            page.extraction_method == "ocr"
            for page in pages
        )

        failed_pages = sum(
            not page.quality.is_usable
            for page in pages
        )

        return ExtractedDocument(
            source_file=native_result.source_file,
            total_pages=len(pages),
            native_pages=native_pages,
            ocr_pages=ocr_pages,
            pages_needing_ocr=failed_pages,
            pages=pages,
        )
