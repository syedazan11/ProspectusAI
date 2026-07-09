from pathlib import Path

import fitz

from src.ingestion.extraction.models import (
    ExtractedDocument,
    ExtractedPage,
)
from src.ingestion.extraction.text_quality import (
    TextQualityAnalyzer,
)
from src.ingestion.loader import DocumentLoader


class PDFExtractor:
    """
    Extracts native PDF text page by page.

    OCR is not performed here yet. Pages whose
    native text is unusable are marked needs_ocr
    for the fallback stage.
    """

    def __init__(self) -> None:
        self.loader = DocumentLoader()
        self.quality_analyzer = TextQualityAnalyzer()

    def extract(
        self,
        file_path: str | Path,
    ) -> ExtractedDocument:
        path = self.loader.validate(file_path)

        pages: list[ExtractedPage] = []

        with fitz.open(path) as pdf:
            for page_index, page in enumerate(
                pdf,
                start=1,
            ):
                text = page.get_text(
                    "text",
                    sort=True,
                ).strip()

                quality = (
                    self.quality_analyzer.analyze(
                        text
                    )
                )

                extraction_method = (
                    "native"
                    if quality.is_usable
                    else "needs_ocr"
                )

                pages.append(
                    ExtractedPage(
                        page_number=page_index,
                        text=text,
                        extraction_method=(
                            extraction_method
                        ),
                        quality=quality,
                    )
                )

        native_pages = sum(
            page.extraction_method == "native"
            for page in pages
        )

        pages_needing_ocr = sum(
            page.extraction_method == "needs_ocr"
            for page in pages
        )

        return ExtractedDocument(
            source_file=path.name,
            total_pages=len(pages),
            native_pages=native_pages,
            ocr_pages=0,
            pages_needing_ocr=pages_needing_ocr,
            pages=pages,
        )
