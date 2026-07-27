from __future__ import annotations

import os
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
        # self.ocr_extractor = OCRExtractor(
        #     render_scale=1.0,
        # )
        render_scale = float(
            os.getenv(
                "OCR_RENDER_SCALE",
                "2.0",
            )
        )

        self.ocr_extractor = OCRExtractor(
            render_scale=render_scale,
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

            for ocr_page in ocr_pages:

                native_page = pages_by_number[
                    ocr_page.page_number
                ]

                if (
                    ocr_page.quality.word_count
                    >= native_page.quality.word_count
                ):
                    pages_by_number[
                        ocr_page.page_number
                    ] = ocr_page

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

        ocr_reason_summary = {}

        for page in pages:
            for reason in page.quality.reasons:
                ocr_reason_summary[reason] = (
                    ocr_reason_summary.get(reason, 0) + 1
                )

        usable_pages = sum(
            page.quality.is_usable
            for page in pages
        )

        print("\n========== Extraction Summary ==========")
        print(f"Total pages     : {len(pages)}")
        print(f"Native pages    : {native_pages}")
        print(f"OCR pages       : {ocr_pages}")
        print(f"Usable pages    : {usable_pages}")
        print(f"Needs attention : {failed_pages}")

        if ocr_reason_summary:
            print("\nFallback reasons:")

            for reason, count in sorted(
                ocr_reason_summary.items()
           ):
                print(f"  {reason}: {count}")

        print("========================================\n")

        return ExtractedDocument(
            source_file=native_result.source_file,
            total_pages=len(pages),
            native_pages=native_pages,
            ocr_pages=ocr_pages,
            pages_needing_ocr=failed_pages,
            pages=pages,
        )

