from __future__ import annotations

from typing import Iterable

import fitz
import numpy as np
from rapidocr import RapidOCR

from src.ingestion.extraction.models import (
    ExtractedPage,
)
from src.ingestion.extraction.text_quality import (
    TextQualityAnalyzer,
)


class OCRExtractor:
    """
    Performs local OCR only on pages that require it.

    RapidOCR uses the local ONNX Runtime engine.
    No cloud OCR service is called.
    """

    def __init__(
        self,
        render_scale: float = 2.0,
    ) -> None:
        self.engine = RapidOCR()
        self.quality_analyzer = TextQualityAnalyzer()
        self.render_scale = render_scale

    def extract_page(
        self,
        page: fitz.Page,
        page_number: int,
    ) -> ExtractedPage:
        matrix = fitz.Matrix(
            self.render_scale,
            self.render_scale,
        )

        pixmap = page.get_pixmap(
            matrix=matrix,
            alpha=False,
        )

        image = np.frombuffer(
            pixmap.samples,
            dtype=np.uint8,
        ).reshape(
            pixmap.height,
            pixmap.width,
            pixmap.n,
        )

        result = self.engine(image)

        text = self._result_to_text(result)
        quality = self.quality_analyzer.analyze(text)

        return ExtractedPage(
            page_number=page_number,
            text=text,
            extraction_method="ocr",
            quality=quality,
        )

    def extract_pages(
        self,
        pdf: fitz.Document,
        page_numbers: Iterable[int],
    ) -> list[ExtractedPage]:
        import time

        extracted_pages = []
        page_numbers = list(page_numbers)
        total = len(page_numbers)

        for index, page_number in enumerate(
            page_numbers,
            start=1,
        ):
            if not 1 <= page_number <= len(pdf):
                raise ValueError(
                    f"Invalid PDF page: {page_number}"
                )

            started = time.perf_counter()

            print(
                f"OCR page {index}/{total} "
                f"(PDF page {page_number})...",
                flush=True,
            )

            extracted_page = self.extract_page(
                page=pdf[page_number - 1],
                page_number=page_number,
            )

            extracted_pages.append(extracted_page)

            elapsed = time.perf_counter() - started

            print(
                f"  done in {elapsed:.2f}s "
                f"chars={len(extracted_page.text)} "
                f"usable={extracted_page.quality.is_usable}",
                flush=True,
            )

        return extracted_pages

    @staticmethod
    def _result_to_text(result) -> str:
        if result is None:
            return ""

        texts = getattr(result, "txts", None)

        if texts is not None:
            return "\n".join(
                str(text).strip()
                for text in texts
                if str(text).strip()
            )

        if isinstance(result, tuple):
            result = result[0]

        if not result:
            return ""

        lines = []

        for item in result:
            if (
                isinstance(item, (list, tuple))
                and len(item) >= 2
            ):
                text = item[1]

                if isinstance(text, (list, tuple)):
                    text = text[0]

                text = str(text).strip()

                if text:
                    lines.append(text)

        return "\n".join(lines)
