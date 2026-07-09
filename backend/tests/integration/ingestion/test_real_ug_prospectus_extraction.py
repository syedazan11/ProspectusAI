import json
from pathlib import Path

from src.ingestion.extraction.pdf_extractor import PDFExtractor


PROJECT_ROOT = Path(__file__).resolve().parents[4]
PDF_PATH = (
    PROJECT_ROOT
    / "storage"
    / "uploads"
    / "UGProspectus2025.pdf"
)


def test_real_ug_prospectus_extraction():
    assert PDF_PATH.exists()

    result = PDFExtractor().extract(PDF_PATH)

    assert result.total_pages > 100
    assert result.native_pages == 0
    assert result.pages_needing_ocr == 122
    assert result.document_type == "scanned"

    report = {
        "source_file": result.source_file,
        "total_pages": result.total_pages,
        "document_type": result.document_type,
        "native_pages": result.native_pages,
        "pages_needing_ocr": result.pages_needing_ocr,
        "ocr_candidates": [
            {
                "page": page.page_number,
                "characters": page.quality.character_count,
                "words": page.quality.word_count,
                "ratio": page.quality.alphanumeric_ratio,
                "reasons": page.quality.reasons,
                "preview": page.text[:200],
            }
            for page in result.pages
            if page.extraction_method == "needs_ocr"
        ],
    }

    report_path = (
        PROJECT_ROOT
        / "oldinfo"
        / "14_native_extraction_report.json"
    )

    report_path.write_text(
        json.dumps(report, indent=2),
        encoding="utf-8",
    )

    print(f"\nTotal pages: {result.total_pages}")
    print(f"Document type: {result.document_type}")
    print(f"Native pages: {result.native_pages}")
    print(
        f"Pages needing OCR: "
        f"{result.pages_needing_ocr}"
    )

    for item in report["ocr_candidates"]:
        print(
            f"OCR candidate: page {item['page']} | "
            f"chars={item['characters']} | "
            f"reasons={item['reasons']}"
        )

