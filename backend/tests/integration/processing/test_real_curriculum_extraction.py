import json
from pathlib import Path

from src.processing.prospectus.curriculum_parser import (
    CurriculumParser,
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
    / "storage"
    / "processed"
    / "UGProspectus2025"
    / "curriculum_records_v1.json"
)


def test_real_curriculum_extraction():
    data = json.loads(
        INPUT_PATH.read_text(encoding="utf-8-sig")
    )

    records = CurriculumParser().parse_pages(
        pages=data["pages"],
        source_file=data["source_file"],
    )

    output = {
        "source_file": data["source_file"],
        "total_records": len(records),
        "records": [
            record.to_dict()
            for record in records
        ],
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    civil_codes = {
        record.course_code
        for record in records
        if record.page_number in {38, 39}
    }

    print()
    print(f"Total curriculum records: {len(records)}")
    print(
        "Records with programme: "
        f"{sum(bool(r.programme) for r in records)}"
    )
    print(
        "Records with study year: "
        f"{sum(bool(r.study_year) for r in records)}"
    )
    print(
        "Civil page codes found: "
        f"{sorted(civil_codes)[:20]}"
    )
    print(f"Output: {OUTPUT_PATH}")

    assert len(records) > 200
    assert "CE-224" in civil_codes
    assert "CE-228" in civil_codes
    assert "CE-225" in civil_codes
