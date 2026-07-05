import json
from pathlib import Path

from src.extraction.table_block_merger import (
    TableBlockMerger,
)
from src.extraction.table_block_normalizer import (
    TableBlockNormalizer,
)
from src.extraction.table_validator import (
    TableValidator,
)
from src.extraction.table_recovery_planner import (
    TableRecoveryPlanner,
)
from src.extraction.vision_table_extractor import (
    VisionTableExtractor,
)

input_path = Path(
    "experiments/table_extraction/"
    "adaptive_blocks/page_2/"
    "extraction_result.json"
)

with open(
    input_path,
    "r",
    encoding="utf-8",
) as file:
    extraction_result = json.load(file)


merger = TableBlockMerger()

normalizer = TableBlockNormalizer()

normalized_blocks = normalizer.normalize(
    extraction_result["blocks"]
)

print(
    "\n========== NORMALIZED BLOCKS =========="
)

for block in normalized_blocks:

    data = block["extracted_data"]

    row_lengths = [
        len(row["values"])
        for row in data["rows"]
    ]

    print(
        f"Block {block['block_index']}: "
        f"{len(data['columns'])} columns, "
        f"row lengths = "
        f"{sorted(set(row_lengths))}"
    )


merged = merger.merge(
    normalized_blocks
)

validator = TableValidator()

validation = validator.validate(
    merged
)

recovery_planner = TableRecoveryPlanner()

recovery_plan = recovery_planner.create_plan(
    table=merged,
    validation=validation,
    blocks=normalized_blocks,
)

print(
    "\n========== MERGE REPORT =========="
)

for item in merged["metadata"]["merge_report"]:
    print(item)


print(
    "\n========== MERGED STRUCTURE =========="
)

print(
    "Columns:",
    len(merged["columns"]),
)

print(
    "Rows:",
    len(merged["rows"]),
)

for row in merged["rows"]:
    print(
        row["category"],
        "->",
        len(row["values"]),
        "values",
    )


output_path = Path(
    "experiments/table_extraction/"
    "adaptive_blocks/page_2/"
    "merged_result.json"
)

with open(
    output_path,
    "w",
    encoding="utf-8",
) as file:
    json.dump(
        merged,
        file,
        indent=4,
        ensure_ascii=False,
    )

print(
    f"\nSaved: {output_path}"
)

print(
    "\n========== VALIDATION =========="
)

print(
    "Structurally valid:",
    validation["is_structurally_valid"],
)

print(
    "Fully valid:",
    validation["is_fully_valid"],
)

print(
    "Invalid totals:",
    validation["invalid_total_count"],
)

print(
    "Needs review:",
    validation["needs_review_count"],
)

print(
    "Rows with missing cells:",
    len(validation["missing_cells"]),
)

for check in validation["total_checks"]:
    print(check)

print(
    "\n========== RECOVERY PLAN =========="
)

print(
    "Requires recovery:",
    recovery_plan["requires_recovery"],
)

print(
    "Failed rows:",
    recovery_plan["failed_row_count"],
)

print("\nRow bands:")

for band in recovery_plan["row_bands"]:
    print(band)

print("\nRows:")

for row in recovery_plan["recovery_rows"]:
    print(row)

print("\nColumn ranges:")

for column_range in recovery_plan[
    "column_ranges"
]:
    print(column_range)

print(
    "\nFull-row recoveries:",
    len(recovery_plan["full_row_recoveries"]),
)

print(
    "Missing-cell recoveries:",
    len(recovery_plan["missing_cell_recoveries"]),
)

print("\nRecovery blocks:")

for block in recovery_plan[
    "recovery_blocks"
]:
    print(block)

recovery_cache_path = Path(
    "experiments/table_extraction/"
    "adaptive_blocks/page_2/"
    "recovery_result.json"
)

if recovery_cache_path.exists():

    print(
        "\nUsing cached recovery result."
    )

    with open(
        recovery_cache_path,
        "r",
        encoding="utf-8",
    ) as file:
        recovery_results = json.load(file)

else:

    print(
        "\nRunning targeted recovery..."
    )

    vision_extractor = VisionTableExtractor()

    recovery_results = (
        vision_extractor.recover_rows(
            recovery_blocks=recovery_plan[
                "recovery_blocks"
            ],
            source_blocks=normalized_blocks,
            recovery_rows=recovery_plan[
                "recovery_rows"
            ],
        )
    )

    with open(
        recovery_cache_path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            recovery_results,
            file,
            indent=4,
            ensure_ascii=False,
        )

    print(
        f"Saved recovery result: "
        f"{recovery_cache_path}"
    )

print(
    "\n========== RECOVERY RESULTS =========="
)

for result in recovery_results:

    print(
        f"Block {result['block_index']}: "
        f"{len(result['rows'])} rows recovered"
    )

recovered_table = recovery_planner.apply_recovery(
    table=merged,
    recovery_results=recovery_results,
    recovery_plan=recovery_plan,
)

revalidation = validator.validate(
    recovered_table
)

print(
    "\n========== POST-RECOVERY VALIDATION =========="
)

print(
    "Recovery report:",
    recovered_table["metadata"][
        "recovery_report"
    ],
)

print(
    "Fully valid:",
    revalidation["is_fully_valid"],
)

print(
    "Invalid totals:",
    revalidation["invalid_total_count"],
)

print(
    "Needs review:",
    revalidation["needs_review_count"],
)

for check in revalidation["total_checks"]:
    print(check)    