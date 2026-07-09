from src.ingestion.extraction.models import (
    ExtractedDocument,
)


def make_document(
    native_pages: int,
    ocr_pages: int,
) -> ExtractedDocument:
    return ExtractedDocument(
        source_file="test.pdf",
        total_pages=native_pages + ocr_pages,
        native_pages=native_pages,
        ocr_pages=ocr_pages,
        pages_needing_ocr=0,
        pages=[],
    )


def test_digital_document_type():
    result = make_document(
        native_pages=10,
        ocr_pages=0,
    )

    assert result.document_type == "digital"


def test_scanned_document_type():
    result = make_document(
        native_pages=0,
        ocr_pages=10,
    )

    assert result.document_type == "scanned"


def test_mixed_document_type():
    result = make_document(
        native_pages=7,
        ocr_pages=3,
    )

    assert result.document_type == "mixed"
