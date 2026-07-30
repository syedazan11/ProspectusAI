import json
from pathlib import Path

from src.processing.prospectus.student_life_extractor import (
    StudentLifeExtractor,
)
from src.processing.prospectus.governance_extractor import (
    GovernanceExtractor,
)
from src.processing.prospectus.research_extractor import (
    ResearchExtractor,
)

JSON_PATH = Path("../storage/cleaned/UGProspectus2026.json")

with open(JSON_PATH, "r", encoding="utf-8") as f:
    document = json.load(f)

pages = document["pages"]

tests = [
    ("STUDENT LIFE", StudentLifeExtractor()),
    ("GOVERNANCE", GovernanceExtractor()),
    ("RESEARCH", ResearchExtractor()),
]

for name, extractor in tests:

    print("\n")
    print("=" * 100)
    print(name)
    print("=" * 100)

    records = extractor.extract(pages)

    print(f"TOTAL RECORDS: {len(records)}")

    pages_found = sorted(
        {
            record.source_page
            for record in records
        }
    )

    print(f"PAGES: {pages_found}")

    for record in records:

        print("-" * 100)
        print(f"TITLE      : {record.title}")
        print(f"CATEGORY   : {record.category}")
        print(f"PAGE       : {record.source_page}")
        print(f"HEADING    : {record.source_heading}")

        if record.attributes:
            print("ATTRIBUTES :")
            for key, value in record.attributes.items():
                print(f"    {key}: {value}")

        print("SOURCE TEXT:")
        print(record.source_text)