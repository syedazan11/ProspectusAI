import json
from collections import Counter
from pathlib import Path

from src.processing.prospectus.curriculum_record_extractor import (
    CurriculumRecordExtractor,
)


PROJECT_ROOT = Path(__file__).resolve().parents[4]

INPUT_PATH = (
    PROJECT_ROOT
    / "storage"
    / "processed"
    / "UGProspectus2025"
    / "curriculum_llamaparse_v1.json"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "storage"
    / "processed"
    / "UGProspectus2025"
    / "curriculum_records_v2.json"
)


def test_real_llamaparse_curriculum_extraction():
    data = json.loads(
        INPUT_PATH.read_text(
            encoding="utf-8-sig"
        )
    )

    pages = (
        data.get("markdown", {})
        .get("pages", [])
    )

    records = CurriculumRecordExtractor().extract(
        pages,
        first_source_page=38,
    )

    output = {
        "source": "curriculum_llamaparse_v1.json",
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

    programmes = Counter(
        record.programme
        for record in records
    )

    semesters = Counter(
        record.semester
        for record in records
    )

    civil_second_year = [
        record
        for record in records
        if (
            record.programme
            == "Civil Engineering"
            and record.study_year
            == "SECOND YEAR"
            and record.course_code
            in {"CE-224", "CE-228"}
        )
    ]

    print()
    print("Total records:", len(records))
    print("Programmes:", len(programmes))
    print("Semesters:", dict(semesters))
    print(
        "Civil checks:",
        [
            (
                r.course_code,
                r.course_title,
                r.semester,
            )
            for r in civil_second_year
        ],
    )
    print("Output:", OUTPUT_PATH)

    assert len(records) > 500
    assert len(programmes) > 10

    assert any(
        record.course_code == "CE-224"
        and record.semester == "Fall"
        and record.course_title
        == "Engineering Surveying-II"
        for record in records
    )

    assert any(
        record.course_code == "CE-228"
        and record.semester == "Spring"
        and record.course_title
        == "Engineering Drawing-II"
        for record in records
    )
