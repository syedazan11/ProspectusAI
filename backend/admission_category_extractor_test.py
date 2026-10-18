import json
from pathlib import Path

from src.processing.prospectus.admission_category_extractor import (
    AdmissionCategoryExtractor,
)


layout_path = (
    Path(__file__).resolve().parents[1]
    / "storage"
    / "experiments"
    / "layout_reconstruction.json"
)

with open(layout_path, "r", encoding="utf-8") as f:
    layout_document = json.load(f)


# Adjust these pages to whatever your section detector found.
# Example for UG Prospectus 2026:
pages = {
    87,
    88,
    89,
    92,
    93,
}

extractor = AdmissionCategoryExtractor()

records = extractor.extract(
    layout_document=layout_document,
    pages=pages,
)

print("\n========== ADMISSION CATEGORIES ==========\n")

for record in records:
    print(record)

print(f"\nTOTAL RECORDS: {len(records)}")