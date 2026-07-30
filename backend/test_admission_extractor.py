import json
from pathlib import Path
from src.processing.prospectus.section_detector import ProspectusSectionDetector
from src.processing.prospectus.admission_extractor import AdmissionExtractor
import inspect

print(inspect.getfile(AdmissionExtractor))

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

print(document["pages"][0].keys())

print("Sections on first page:", len(document["pages"][0]["sections"]))

for page in document["pages"]:
    if page["sections"]:
        print("First page with sections:", page["page_number"])
        print("Sections:", len(page["sections"]))
        print(page["sections"][0]["heading"])
        break

print(type(document))
print(document.keys())

print("Pages:", len(document.get("pages", [])))

if document.get("pages"):
    print(document["pages"][0].keys())

print("Pages passed:", len(document["pages"]))

extractor = AdmissionExtractor()
admission_pages = []

for section in sections:
    if section.section_type in (
        "eligibility",
        "admission_process",
    ):
        pages = [
            page
            for page in document["pages"]
            if (
                section.start_page
                <= page["page_number"]
                <= section.end_page
            )
        ]

        admission_pages.extend(pages)

        print(
            f"[TEST] {section.section_type}: "
            f"{section.start_page}-{section.end_page} "
            f"({len(pages)} pages)"
        )

# Remove duplicate pages while preserving order
seen = set()
admission_pages = [
    page
    for page in admission_pages
    if not (
        page["page_number"] in seen
        or seen.add(page["page_number"])
    )
]

print(f"Admission pages passed: {len(admission_pages)}")

records = extractor.extract(admission_pages)

print("\n========================================")
print("Total records:", len(records))
print("========================================")

for record in records:
    print("=" * 80)
    print("NUMBER :", record.number)
    print("PARENT :", record.parent)
    print("TITLE  :", record.title)
    print("CONTENT:")
    for item in record.content:
        print("   ", item)

for record in records:
    print(record)