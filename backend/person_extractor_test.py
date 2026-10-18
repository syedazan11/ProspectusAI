# import json
# from pathlib import Path

# from src.processing.prospectus.person_extractor import (
#     PersonExtractor,
# )

# layout_path = (
#     Path(__file__).resolve().parents[1]
#     / "storage"
#     / "experiments"
#     / "layout_reconstruction.json"
# )

# with open(layout_path, "r", encoding="utf-8") as f:
#     layout_document = json.load(f)

# extractor = PersonExtractor()

# records = extractor.extract(layout_document)

# print(f"\nTOTAL RECORDS: {len(records)}")
import json
from pathlib import Path

from src.processing.prospectus.person_extractor import PersonExtractor


layout_path = (
    Path(__file__).resolve().parents[1]
    / "storage"
    / "experiments"
    / "layout_reconstruction.json"
)

with open(layout_path, "r", encoding="utf-8") as f:
    layout_document = json.load(f)

extractor = PersonExtractor()
records = extractor.extract(layout_document)

print(f"\nTOTAL RECORDS: {len(records)}\n")
print("=" * 100)

output_path = Path("person_records_output.txt")

with output_path.open("w", encoding="utf-8") as f:
    f.write(f"TOTAL RECORDS: {len(records)}\n")
    f.write("=" * 100 + "\n")

    for index, record in enumerate(records, start=1):
        f.write(f"\nRECORD {index}\n")
        f.write(f"Name:         {record.name}\n")
        f.write(f"Role:         {record.role}\n")
        f.write(f"Department:   {record.department}\n")
        f.write(f"Page:         {record.source_page}\n")
        f.write("Qualifications:\n")

        if record.qualifications:
            for qualification in record.qualifications:
                f.write(f"  - {qualification}\n")
        else:
            f.write("  - None\n")

        f.write("-" * 100 + "\n")

print(f"\nSaved records to: {output_path.resolve()}")