import json
from pathlib import Path

from src.processing.prospectus.layout_helper import LayoutHelper

JSON_PATH = Path("../storage/parsed/UGProspectus2026.json")

with open(JSON_PATH, "r", encoding="utf-8") as f:
    document = json.load(f)

page = next(
    p
    for p in document["pages"]
    if p["page_number"] == 97
)

items = page["layout_items"]

print("\nX POSITIONS")
print("=" * 80)

xs = sorted(
    round(item["x"])
    for item in items
)

for item in sorted(items, key=lambda i: (i["x"], i["top"])):

    print(
        f"x={item['x']:>6.1f} "
        f"w={item.get('width',0):>6.1f} "
        f"h={item.get('height',0):>6.1f} "
        f"text={item['text']}"
    )

print(f"Total layout items: {len(items)}")

left, right = LayoutHelper.split_columns(items)

print("\n")
print("=" * 80)
print("LEFT COLUMN")
print("=" * 80)

for item in left:
    print(
        f"{item['top']:>6.1f}   {item['x']:>6.1f}   {item['text']}"
    )

print("\n")
print("=" * 80)
print("RIGHT COLUMN")
print("=" * 80)

for item in right:
    print(
        f"{item['top']:>6.1f}   {item['x']:>6.1f}   {item['text']}"
    )