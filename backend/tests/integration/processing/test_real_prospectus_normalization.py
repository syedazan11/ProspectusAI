import json
from pathlib import Path

from src.processing.prospectus.text_normalizer import (
    ProspectusTextNormalizer,
)


PROJECT_ROOT = Path(__file__).resolve().parents[4]

INPUT_PATH = (
    PROJECT_ROOT
    / "storage"
    / "processed"
    / "UGProspectus2025"
    / "extracted_document.json"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "oldinfo"
    / "19_normalization_report.json"
)


def test_real_prospectus_normalization():
    data = json.loads(
        INPUT_PATH.read_text(
            encoding="utf-8-sig"
        )
    )

    normalizer = ProspectusTextNormalizer()

    total_raw_lines = 0
    total_clean_lines = 0
    headings = []
    table_signals = []

    for page in data["pages"]:
        raw_lines = page["text"].splitlines()

        clean_lines = (
            normalizer.normalize_page(
                page["text"]
            )
        )

        total_raw_lines += len(raw_lines)
        total_clean_lines += len(clean_lines)

        for line in clean_lines:
            if normalizer.is_heading(line):
                headings.append({
                    "page": page["page_number"],
                    "text": line,
                })

            if normalizer.is_table_signal(line):
                table_signals.append({
                    "page": page["page_number"],
                    "text": line,
                })

    report = {
        "total_pages": len(data["pages"]),
        "total_raw_lines": total_raw_lines,
        "total_clean_lines": total_clean_lines,
        "heading_count": len(headings),
        "table_signal_count": len(table_signals),
        "heading_samples": headings[:100],
        "table_signal_samples": (
            table_signals[:100]
        ),
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print(
        f"Raw lines: {total_raw_lines}"
    )
    print(
        f"Clean lines: {total_clean_lines}"
    )
    print(
        f"Headings detected: {len(headings)}"
    )
    print(
        "Table signals detected: "
        f"{len(table_signals)}"
    )

    assert len(data["pages"]) == 122
    assert total_clean_lines > 0
    assert len(headings) > 20
    assert len(table_signals) > 20
