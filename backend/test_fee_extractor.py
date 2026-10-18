
from src.processing.prospectus.fee_record_extractor import (
    FeeRecordExtractor,
)
import json
from pathlib import Path

def main() -> None:
    project_root = Path(__file__).resolve().parents[1]

    sections_path = (
        project_root
        / "storage"
        / "sections"
        / "UGProspectus2025.json"
    )

    layout_path = (
        project_root
        / "storage"
        / "experiments"
        / "layout_reconstruction.json"
    )

    with open(
        sections_path,
        "r",
        encoding="utf-8",
    ) as f:
        sections_document = json.load(f)

    with open(
        layout_path,
        "r",
        encoding="utf-8",
    ) as f:
        layout_document = json.load(f)

    sections = sections_document.get(
        "sections",
        [],
    )

    finance_sections = [
        section
        for section in sections
        if section.get("section_type") == "finance"
    ]

    if not finance_sections:
        print(
            "NO FINANCE SECTION FOUND"
        )
        return

    finance_page_numbers = set()

    for section in finance_sections:
        start_page = section.get(
            "start_page"
        )
        end_page = section.get(
            "end_page"
        )

        print(
            f"FINANCE SECTION: "
            f"{start_page}-{end_page}"
        )

        if (
            start_page is None
            or end_page is None
        ):
            continue

        finance_page_numbers.update(
            range(
                start_page,
                end_page + 1,
            )
        )

    layout_pages = (
        layout_document.get("pages", [])
        if isinstance(
            layout_document,
            dict,
        )
        else layout_document
    )

    fee_pages = [
        page
        for page in layout_pages
        if page.get("page_number")
        in finance_page_numbers
    ]

    print(
        f"FINANCE PAGE NUMBERS: "
        f"{sorted(finance_page_numbers)}"
    )

    print(
        f"LAYOUT FEE PAGES: "
        f"{len(fee_pages)}"
    )

    extractor = FeeRecordExtractor()

    records = extractor.extract(
        layout_document=layout_document,
        pages=fee_pages,
    )

    output_path = (
        Path(__file__).resolve().parent
        / "fee_extractor_test_output.txt"
    )

    with open(
        output_path,
        "w",
        encoding="utf-8",
    ) as f:
        f.write(
            f"TOTAL RECORDS: "
            f"{len(records)}\n\n"
        )

        for index, record in enumerate(
            records,
            start=1,
        ):
            f.write(
                f"========== RECORD "
                f"{index} ==========\n"
            )

            for key, value in (
                record.to_dict().items()
            ):
                f.write(
                    f"{key}: {value}\n"
                )

            f.write("\n")

    print(
        f"TOTAL RECORDS: "
        f"{len(records)}"
    )

    print(
        f"OUTPUT: {output_path}"
    )


if __name__ == "__main__":
    main()