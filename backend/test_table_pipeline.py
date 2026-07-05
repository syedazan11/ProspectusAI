import json
from pathlib import Path

from src.processing.table_pipeline import TablePipeline


pipeline = TablePipeline()

image_path = Path(
    "experiments/table_extraction/page_2.png"
)

layout = pipeline.analyze(
    image_path=image_path,
)

strategy = pipeline.choose_strategy(
    layout=layout,
)

print("\n========== TABLE LAYOUT ==========")

for key, value in layout.items():
    print(f"{key}: {value}")

print("\n========== SELECTED STRATEGY ==========")
print(strategy)


plan = pipeline.prepare_extraction(
    image_path=image_path,
    page_number=2,
    layout=layout,
    strategy=strategy,
)

output_path = Path(
    "experiments/table_extraction/"
    "adaptive_blocks/page_2/"
    "extraction_result.json"
)

with open(
    output_path,
    "w",
    encoding="utf-8",
) as file:
    json.dump(
        plan,
        file,
        indent=4,
        ensure_ascii=False,
    )

print(
    f"\nSaved extraction result: "
    f"{output_path}"
)

print("\n========== EXTRACTION PLAN ==========")
print(plan["metadata"])

for block in plan.get("blocks", []):
    print(block)