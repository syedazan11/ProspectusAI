from __future__ import annotations

from typing import Iterable

import fitz
import numpy as np
from rapidocr import RapidOCR

from src.ingestion.extraction.models import (
    ExtractedPage,
    LayoutItem,
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

        layout_items = self._result_to_layout_items(result)

        text = self._result_to_text(result)
        quality = self.quality_analyzer.analyze(text)

        return ExtractedPage(
            page_number=page_number,
            text=text,
            extraction_method="ocr",
            quality=quality,
            layout_items=layout_items,
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
        boxes = getattr(result, "boxes", None)

        # Preferred path: use OCR geometry to reconstruct reading order
        if texts is not None and boxes is not None:
            return OCRExtractor._reconstruct_reading_order(
                texts=texts,
                boxes=boxes,
            )

        # Fallback if boxes are unavailable
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
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                text = item[1]

                if isinstance(text, (list, tuple)):
                    text = text[0]

                text = str(text).strip()

                if text:
                    lines.append(text)

        return "\n".join(lines)
    
    @staticmethod
    def _result_to_layout_items(result) -> list[LayoutItem]:
        if result is None:
            return []

        texts = getattr(result, "txts", None)
        boxes = getattr(result, "boxes", None)

        if texts is None or boxes is None:
            return []

        if len(texts) != len(boxes):
            return []

        items = []

        for text, box in zip(texts, boxes):
            text = str(text).strip()

            if not text:
                continue

            xs = [float(p[0]) for p in box]
            ys = [float(p[1]) for p in box]

            items.append(
                LayoutItem(
                    text=text,
                    x=sum(xs) / len(xs),
                    y=sum(ys) / len(ys),
                    top=min(ys),
                    bottom=max(ys),
                    height=max(ys) - min(ys),
                )
            )

        return items
    
    @staticmethod
    def _reconstruct_reading_order(texts, boxes) -> str:
        """
        Reconstruct OCR reading order from bounding boxes.

        Strategy:
        1. Compute the center of every OCR box.
        2. Sort primarily by Y.
        3. Group nearby lines into horizontal bands.
        4. Within each band, read left-to-right.
        """

        if texts is None or boxes is None:
            return ""

        if len(texts) == 0 or len(boxes) == 0:
            return ""

        if len(texts) != len(boxes):
            return "\n".join(
                str(t).strip()
                for t in texts
                if str(t).strip()
            )

        items = []

        for text, box in zip(texts, boxes):
            text = str(text).strip()

            if not text:
                continue

            xs = [float(p[0]) for p in box]
            ys = [float(p[1]) for p in box]

            items.append({
                "text": text,
                "x": sum(xs) / len(xs),
                "y": sum(ys) / len(ys),
                "top": min(ys),
                "bottom": max(ys),
                "height": max(ys) - min(ys),
            })

        if not items:
            return ""

        # Average text height
        avg_height = sum(i["height"] for i in items) / len(items)

        # Lines whose centers are within this distance belong to the same row.
        y_threshold = max(avg_height * 0.75, 12)

        # Global top-to-bottom ordering
        items.sort(key=lambda i: i["y"])

        rows = []
        current = []

        for item in items:

            if not current:
                current.append(item)
                continue

            current_y = sum(r["y"] for r in current) / len(current)

            if abs(item["y"] - current_y) <= y_threshold:
                current.append(item)
            else:
                rows.append(current)
                current = [item]

        if current:
            rows.append(current)

        ordered = []

        for row in rows:
            row.sort(key=lambda r: r["x"])
            ordered.extend(row)

        return "\n".join(
            item["text"]
            for item in ordered
        )
