import json
from pathlib import Path

from src.ingestion.extraction.document_extractor import (
    DocumentExtractor,
)


PROJECT_ROOT = Path(__file__).resolve().parents[4]

PDF_PATH = (
    PROJECT_ROOT
    / "storage"
    / "uploads"
    / "UGProspectus2025.pdf"
)


def test_full_real_prospectus_extraction():
    result = DocumentExtractor().extract(PDF_PATH)

    assert result.total_pages == 122
    assert result.ocr_pages == 122

    output_dir = (
        PROJECT_ROOT
        / "storage"
        / "processed"
        / "UGProspectus2025"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path = (
        output_dir
        / "extracted_document.json"
    )

    output_path.write_text(
        json.dumps(
            result.to_dict(),
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    unusable_pages = [
        page.page_number
        for page in result.pages
        if not page.quality.is_usable
    ]

    print()
    print(f"Total pages: {result.total_pages}")
    print(f"Native pages: {result.native_pages}")
    print(f"OCR pages: {result.ocr_pages}")
    print(f"Unusable pages: {unusable_pages}")
    print(f"Output: {output_path}")

    assert len(unusable_pages) <= 5
