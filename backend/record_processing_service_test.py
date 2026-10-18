import json
from pathlib import Path

from src.processing.prospectus.record_processing_service import (
    RecordProcessingService,
)
from src.processing.prospectus.section_detector import (
   ProspectusSectionDetector
)


ROOT = Path(__file__).resolve().parents[1]

cleaned_document_path = (
    ROOT
    / "storage"
    / "cleaned"
    / "UGProspectus2026.json"
)

with open(
    cleaned_document_path,
    "r",
    encoding="utf-8",
) as f:
    cleaned_document = json.load(f)


detector = ProspectusSectionDetector()

detected_sections = detector.detect(
    pages=cleaned_document["pages"]
)

print("\n========== DETECTED SECTIONS ==========\n")

for section in detected_sections:
    print(section)

print(
    f"\nTOTAL SECTIONS: {len(detected_sections)}"
)


print("\n========== RECORD PROCESSING ==========\n")

service = RecordProcessingService()

records = service.process(
    cleaned_document=cleaned_document,
    detected_sections=detected_sections,
)

print("\n========== SUMMARY ==========\n")

for name, value in records.items():
    print(f"{name}: {len(value)}")