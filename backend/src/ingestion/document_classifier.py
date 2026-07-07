from pathlib import Path
from typing import Any

import fitz

from src.core.config import settings


class DocumentClassifier:
    """
    Classifies a PDF at both document
    and individual page level.

    Document types:
    - digital
    - scanned
    - mixed

    Page types:
    - digital
    - scanned
    """

    def classify(
        self,
        pdf_path: Path,
    ) -> dict[str, Any]:

        document = fitz.open(pdf_path)

        digital_pages = 0
        scanned_pages = 0
        page_classifications = []

        try:
            for page_index, page in enumerate(
                document,
                start=1,
            ):
                text = page.get_text().strip()
                text_length = len(text)

                if (
                    text_length
                    >= settings.TEXT_THRESHOLD
                ):
                    page_type = "digital"
                    digital_pages += 1

                else:
                    page_type = "scanned"
                    scanned_pages += 1

                page_classifications.append(
                    {
                        "page_number": page_index,
                        "page_type": page_type,
                        "text_length": text_length,
                    }
                )

            total_pages = len(document)

        finally:
            document.close()

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
            "pages": page_classifications,
        }