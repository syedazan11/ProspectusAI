import json
from pathlib import Path

from src.services.table_processing_service import (
    TableProcessingService,
)


parsed_path = Path(
    "../storage/parsed/testingnedprospect.json"
)

data = json.loads(
    parsed_path.read_text(encoding="utf-8")
)

service = TableProcessingService()

complex_pages = [
    page
    for page in data["pages"]
    if page["metadata"]["route"]
    == "complex_table_page"
]

total_base_calls = 0

print("\n=== COMPLEX TABLE API PLAN ===")

for page in complex_pages:
    page_number = page["page_number"]

    page_path = Path(
        page["metadata"]["page_path"]
    )

    image_path = service._render_page(
        page_path=page_path,
        page_number=page_number,
    )

    layout = service.table_pipeline.analyze(
        image_path=image_path
    )

    strategy = (
        service.table_pipeline.choose_strategy(
            layout=layout
        )
    )

    if strategy == "single":
        base_calls = 1

    else:
        width = layout["width"]
        height = layout["height"]

        estimated_columns = max(
            layout["estimated_columns"],
            1,
        )

        column_based_count = (
            estimated_columns + 9
        ) // 10

        target_block_width = max(
            int(height * 0.40),
            1,
        )

        geometry_based_count = (
            width
            + target_block_width
            - 1
        ) // target_block_width

        base_calls = min(
            8,
            max(
                2,
                column_based_count,
                geometry_based_count,
            ),
        )

    total_base_calls += base_calls

    print(
        f"PAGE {page_number}"
        f" | COLUMNS: {layout['estimated_columns']}"
        f" | ROWS: {layout['estimated_rows']}"
        f" | STRATEGY: {strategy}"
        f" | BASE CALLS: {base_calls}"
    )

print(
    "\nTOTAL BASE VISION CALLS:",
    total_base_calls,
)

print(
    "NOTE: Recovery calls are not included."
)