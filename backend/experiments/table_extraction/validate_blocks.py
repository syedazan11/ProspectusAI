import json
from pathlib import Path


BASE_DIR = Path("experiments/table_extraction")

HEADERS_PATH = (
    BASE_DIR / "header_test" / "all_headers.json"
)

BLOCKS_PATH = (
    BASE_DIR / "column_test" / "all_blocks.json"
)


def load_json(path: Path):
    return json.loads(
        path.read_text(encoding="utf-8")
    )


def find_overlap(left: list, right: list) -> int:
    """
    Returns the largest overlap where the end of
    'left' matches the beginning of 'right'.
    """

    max_size = min(len(left), len(right))

    for size in range(max_size, 0, -1):

        if left[-size:] == right[:size]:
            return size

    return 0


def merge_overlapping_lists(blocks: list[list]) -> list:

    merged = blocks[0].copy()

    for block in blocks[1:]:

        overlap = find_overlap(
            merged,
            block,
        )

        print(
            f"Overlap found: {overlap} items"
        )

        if overlap == 0:
            raise ValueError(
                "No overlap found between blocks."
            )

        merged.extend(block[overlap:])

    return merged


headers_data = load_json(HEADERS_PATH)
blocks_data = load_json(BLOCKS_PATH)


# -----------------------------------------
# 1. MERGE HEADERS
# -----------------------------------------

header_blocks = [
    block["columns"]
    for block in headers_data
]

print("\n========== HEADER VALIDATION ==========")

merged_headers = merge_overlapping_lists(
    header_blocks
)

print(f"\nMerged header count: {len(merged_headers)}")
print(merged_headers)


# -----------------------------------------
# 2. VALIDATE NUMERIC BLOCK OVERLAPS
# -----------------------------------------

print("\n========== NUMERIC BLOCK VALIDATION ==========")

numeric_headers = [
    block["visible_columns"]
    for block in blocks_data
]

for index in range(len(numeric_headers) - 1):

    left = numeric_headers[index]
    right = numeric_headers[index + 1]

    overlap = find_overlap(left, right)

    print(
        f"Block {index + 1} → Block {index + 2}: "
        f"{overlap} matching values"
    )


# -----------------------------------------
# 3. BASIC STRUCTURE CHECK
# -----------------------------------------

print("\n========== STRUCTURE CHECK ==========")

for index, block in enumerate(
    blocks_data,
    start=1,
):

    expected = len(block["visible_columns"])

    print(
        f"\nBlock {index}: "
        f"{expected} expected values per row"
    )

    for row_number, row in enumerate(
        block["rows"],
        start=1,
    ):

        actual = len(row["values"])

        status = (
            "OK"
            if actual == expected
            else "FAIL"
        )

        print(
            f"Row {row_number}: "
            f"{actual} values → {status}"
        )

# -----------------------------------------
# 4. MERGE NUMERIC ROWS
# -----------------------------------------

print("\n========== MERGED ROWS ==========")

row_count = len(blocks_data[0]["rows"])

merged_rows = []

for row_index in range(row_count):

    row_blocks = [
        block["rows"][row_index]["values"]
        for block in blocks_data
    ]

    merged_values = row_blocks[0].copy()

    for next_block in row_blocks[1:]:
        merged_values.extend(next_block[3:])

    category = blocks_data[0]["rows"][row_index].get(
        "category"
    )

    merged_rows.append(
        {
            "category": category,
            "values": merged_values,
        }
    )

    print(
        f"{category}: "
        f"{len(merged_values)} merged values"
    )


# -----------------------------------------
# 5. SAVE MERGED TEST RESULT
# -----------------------------------------

OUTPUT_PATH = (
    BASE_DIR
    / "column_test"
    / "merged_test_rows.json"
)

OUTPUT_PATH.write_text(
    json.dumps(
        {
            "columns": merged_headers,
            "rows": merged_rows,
        },
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

print(f"\nSaved: {OUTPUT_PATH}")

# -----------------------------------------
# 6. CHECK ROW SUMS
# -----------------------------------------

print("\n========== ROW SUM VALIDATION ==========")

for row in merged_rows:

    category = row["category"]
    values = row["values"]

    calculated_sum = sum(
        value
        for value in values
        if isinstance(value, int)
    )

    print(
        f"{category}: "
        f"calculated sum = {calculated_sum}"
    )