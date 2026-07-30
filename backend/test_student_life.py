import json
from pathlib import Path

from src.processing.prospectus.section_detector import ProspectusSectionDetector
from src.processing.prospectus.student_life_extractor import StudentLifeExtractor

JSON_PATH = Path("../storage/cleaned/UGProspectus2026.json")

with open(JSON_PATH, "r", encoding="utf-8") as f:
    document = json.load(f)

detector = ProspectusSectionDetector()
sections = detector.detect(document["pages"])

extractor = StudentLifeExtractor()

student_life_pages = []

print("\n===== STUDENT LIFE SECTIONS =====")

for section in sections:

    print(
        section.section_type,
        section.start_page,
        section.end_page,
        section.heading,
    )

    if section.section_type in (
        "student_life",
        "hostel",
        "library",
        "sports",
        "transport",
        "scholarship",
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

        student_life_pages.extend(pages)

        print(
            f"[TEST] {section.section_type}: "
            f"{section.start_page}-{section.end_page} "
            f"({len(pages)} pages)"
        )

# Remove duplicate pages
seen = set()

student_life_pages = [
    page
    for page in student_life_pages
    if not (
        page["page_number"] in seen
        or seen.add(page["page_number"])
    )
]

print(f"\nStudent Life pages passed: {len(student_life_pages)}")

# ---------------------------------------------------------
# DEBUG: Dump every PROSPECTUS 2026 section after page 85
# ---------------------------------------------------------

with open(
    "prospectus_sections_debug.txt",
    "w",
    encoding="utf-8",
) as out:

    count = 0

    for page in document["pages"]:

        if page["page_number"] < 85:
            continue

        for section in page.get("sections", []):

            if section.get("heading") != "PROSPECTUS 2026":
                continue

            count += 1

            out.write("=" * 120 + "\n")
            out.write(f"SECTION #{count}\n")
            out.write(f"PAGE: {page['page_number']}\n")
            out.write(f"HEADING: {section.get('heading')}\n")
            out.write("\nCONTENT:\n\n")

            for i, line in enumerate(section.get("content", []), 1):
                out.write(f"{i:02d}. {line}\n")

            out.write("\n")

    out.write("=" * 120 + "\n")
    out.write(f"TOTAL PROSPECTUS SECTIONS: {count}\n")

print("Debug written to prospectus_sections_debug.txt")

# ---------------------------------------------------------
# Run extractor
# ---------------------------------------------------------

records = extractor.extract(document["pages"])

print("\n========================================")
print(f"Total records: {len(records)}")
print("========================================")

for record in records:
    print("=" * 80)
    print(record)