from src.processing.table_parser import TableParser


parser = TableParser()

columns = [
    "CE", "CE (UE)", "PE", "CE (CN)", "ME",
    "TE", "IM", "ME (AU)", "EE", "TC",
    "CS", "EL", "CH", "MY", "MM",
    "PP", "FD", "BM", "SE", "CT",
    "PH", "IC", "CF", "DS", "TS",
    "MG", "B. Arch", "EG", "EC", "TCT",
    "TCE",
]


# -----------------------------------------
# TEST 1: VALID ROW
# R-1(a) calculated total = 1464
# -----------------------------------------

valid_values = [
    105, 49, 25, 22, 135,
    47, 72, 28, 127, 56,
    77, 94, 46, 28, 35,
    36, 28, 30, 46, 60,
    49, 49, 64, 2, 48,
    34, 16, 6, 45, 3,
    2,
]

valid_result = parser.validate_row(
    values=valid_values,
    expected_columns=len(columns),
    printed_total=1464,
)

print("\n========== VALID ROW ==========")
print(valid_result)


# -----------------------------------------
# TEST 2: INVALID ROW
# R-1(d) extracted sum = 11
# printed total = 14
# -----------------------------------------

invalid_values = [
    0, 0, 0, 0, 0,
    0, 0, 0, 0, 0,
    0, 0, 0, 0, 0,
    0, 0, 0, 0, 0,
    2, 0, 3, 0, 3,
    0, 0, 3, 0, 0,
    0,
]

invalid_result = parser.validate_row(
    values=invalid_values,
    expected_columns=len(columns),
    printed_total=14,
)

print("\n========== INVALID ROW ==========")
print(invalid_result)


# -----------------------------------------
# TEST 3: BUILD GENERIC RAG CHUNK
# -----------------------------------------

row = {
    "Category": "R-1(a)",
    "Description": (
        "HSC (Pre-Engineering/Computer Science) "
        "from Board of Intermediate Education, Karachi."
    ),
}

for column, value in zip(columns, valid_values):
    row[column] = value

row["Total"] = 1464

chunk = parser.build_row_chunk(
    table_title="Distribution of Seats",
    row=row,
    page_number=73,
)

print("\n========== GENERIC RAG CHUNK ==========")
print(chunk["text"])

print("\n========== METADATA ==========")
print(chunk["metadata"])