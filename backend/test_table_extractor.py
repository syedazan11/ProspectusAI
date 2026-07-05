from src.processing.table_extractor import TableExtractor


extractor = TableExtractor()


# -----------------------------------------
# TEST 1: SEAT TABLE
# -----------------------------------------

seat_data = {
    "table_title": "Distribution of Seats",
    "columns": [
        "Category",
        "CS",
        "SE",
        "Total",
    ],
    "rows": [
        {
            "Category": "Open Merit",
            "CS": 100,
            "SE": 80,
            "Total": 180,
        }
    ],
}

seat_table = extractor.extract(
    table_data=seat_data,
    page_number=10,
)

print("\n========== SEAT TABLE ==========")
print(seat_table.model_dump())


# -----------------------------------------
# TEST 2: FEE TABLE
# -----------------------------------------

fee_data = {
    "table_title": "Fee Structure",
    "columns": [
        "Program",
        "Admission Fee",
        "Tuition Fee",
    ],
    "rows": [
        {
            "Program": "Computer Science",
            "Admission Fee": 50000,
            "Tuition Fee": 120000,
        },
        {
            "Program": "Software Engineering",
            "Admission Fee": 50000,

            # Intentionally missing Tuition Fee.
            # It should become None automatically.
        },
    ],
}

fee_table = extractor.extract(
    table_data=fee_data,
    page_number=25,
)

print("\n========== FEE TABLE ==========")
print(fee_table.model_dump())