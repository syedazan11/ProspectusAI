import inspect
import json
from pathlib import Path

from src.processing.prospectus.section_detector import (
    ProspectusSectionDetector,
)
from src.processing.prospectus.fee_record_extractor import (
    FeeRecordExtractor,
)

print(inspect.getfile(FeeRecordExtractor))

JSON_PATH = Path("../storage/cleaned/UGProspectus2026.json")

print("Exists:", JSON_PATH.exists())
print("Resolved:", JSON_PATH.resolve())

with open(JSON_PATH, "r", encoding="utf-8") as f:
    document = json.load(f)

detector = ProspectusSectionDetector()

sections = detector.detect(document["pages"])

print("\n===== DETECTED SECTIONS =====")

for section in sections:
    print(
        section.section_type,
        section.start_page,
        section.end_page,
        section.heading,
    )

extractor = FeeRecordExtractor()

fee_pages = []

for section in sections:

    if section.section_type == "fee_structure":

        pages = [
            page
            for page in document["pages"]
            if (
                section.start_page
                <= page["page_number"]
                <= section.end_page
            )
        ]

        fee_pages.extend(pages)

        print(
            f"[TEST] fee_structure: "
            f"{section.start_page}-{section.end_page} "
            f"({len(pages)} pages)"
        )

seen = set()

fee_pages = [
    page
    for page in fee_pages
    if not (
        page["page_number"] in seen
        or seen.add(page["page_number"])
    )
]

print(f"\nFee pages passed: {len(fee_pages)}")

records = extractor.extract(fee_pages)

print("\n========================================")
print("TOTAL FEE RECORDS:", len(records))
print("========================================")

for record in records:

    print("=" * 80)
    print("CATEGORY :", record.category)
    print("AMOUNT   :", record.amount)
    print("CURRENCY :", record.currency)
   # print("COLUMN   :", record.column)
    print("SCHEME   :", record.scheme)
    print("PERIOD   :", record.payment_period)
    print("NOTES    :", record.notes)
    print("PAGE     :", record.source_page)
    print("HEADING  :", record.source_heading)
    print("SOURCE   :", record.source_text)

print("\n===== FIRST 20 RECORDS =====")

for record in records[:20]:
    print(record)