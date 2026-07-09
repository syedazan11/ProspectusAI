import json
from pathlib import Path

import fitz

from src.ingestion.extraction.ocr_extractor import (
    OCRExtractor,
)


PROJECT_ROOT = Path(__file__).resolve().parents[4]

PDF_PATH = (
    PROJECT_ROOT
    / "storage"
    / "uploads"
    / "UGProspectus2025.pdf"
)

TEST_PAGES = [1, 20, 100]


def test_ocr_real_ug_prospectus_pages():
    assert PDF_PATH.exists()

    extractor = OCRExtractor(
        render_scale=2.0,
    )

    with fitz.open(PDF_PATH) as pdf:
        pages = extractor.extract_pages(
            pdf=pdf,
            page_numbers=TEST_PAGES,
        )

    assert len(pages) == 3

    report = []

    for page in pages:
        assert page.extraction_method == "ocr"

        report.append(
            {
                "page_number": page.page_number,
                "character_count": (
                    page.quality.character_count
                ),
                "word_count": (
                    page.quality.word_count
                ),
                "is_usable": (
                    page.quality.is_usable
                ),
                "reasons": page.quality.reasons,
                "text": page.text,
            }
        )

        print(
            f"\nPAGE {page.page_number}"
            f"\nCharacters: "
            f"{page.quality.character_count}"
            f"\nWords: {page.quality.word_count}"
            f"\nUsable: {page.quality.is_usable}"
            f"\nPreview:\n{page.text[:500]}"
        )

    report_path = (
        PROJECT_ROOT
        / "oldinfo"
        / "16_ocr_three_page_report.json"
    )

    report_path.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
