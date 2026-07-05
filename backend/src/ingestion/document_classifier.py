from pathlib import Path

import fitz

from src.core.config import settings


class DocumentClassifier:
    """
    Classifies a PDF as:
    - digital
    - scanned
    - mixed
    """

    def classify(self, pdf_path: Path) -> dict:
        """
        Analyze every page in the document.

        Args:
            pdf_path: Validated PDF path

        Returns:
            Dictionary containing document statistics.
        """

        document = fitz.open(pdf_path)

        total_pages = len(document)
        digital_pages = 0
        scanned_pages = 0

        for page in document:

            text = page.get_text().strip()

            if len(text) >= settings.TEXT_THRESHOLD:
                digital_pages += 1
            else:
                scanned_pages += 1

        document.close()

        # Determine overall document type
        if scanned_pages == 0:
            document_type = "digital"

        elif digital_pages == 0:
            document_type = "scanned"

        else:
            document_type = "mixed"

        return {
            "document_type": document_type,
            "total_pages": total_pages,
            "digital_pages": digital_pages,
            "scanned_pages": scanned_pages,
        }