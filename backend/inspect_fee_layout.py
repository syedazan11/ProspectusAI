import json

path = "../storage/experiments/layout_reconstruction.json"

with open(path, "r", encoding="utf-8") as f:
    document = json.load(f)

if isinstance(document, dict):
    pages = document.get("pages", [])
else:
    pages = document

with open("fee_layout_inspection.txt", "w", encoding="utf-8") as out:

    for page in pages:

        if page.get("page_number") not in {103, 104, 105}:
            continue

        out.write(
            f"\n===== PAGE {page.get('page_number')} =====\n"
        )

        out.write(
            page.get("reconstructed_text", "")
        )

        items = page.get("layout_items", [])

        out.write(
            f"\n\nLAYOUT ITEMS: {len(items)}\n"
        )

        for item in items:
            out.write(
                f"{item}\n"
            )
