import json
from pathlib import Path

from src.processing.prospectus.section_detector import ProspectusSectionDetector

parsed = Path("../storage/parsed/UGProspectus2026.json")

with open(parsed, encoding="utf-8") as f:
    document = json.load(f)

sections = ProspectusSectionDetector().detect(
    document["pages"]
)

print("=" * 80)
print("DETECTED SECTIONS")
print("=" * 80)

for section in sections:
    print(
        f"{section.section_type:35}"
        f"{section.start_page:4}"
        f" -> "
        f"{section.end_page:<4}"
    )