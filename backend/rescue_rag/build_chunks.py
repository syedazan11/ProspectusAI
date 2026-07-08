import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

INPUT_PATH = (
    PROJECT_ROOT
    / "storage"
    / "rescue"
    / "UGProspectus2025_llamaparse.json"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "storage"
    / "rescue"
    / "UGProspectus2025_chunks.json"
)

DOCUMENT = "UGProspectus2025.pdf"

TARGET_CHARS = 1800
OVERLAP_BLOCKS = 1


def clean_markdown(text: str) -> str:

    text = text.replace("\x00", " ")

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


def extract_heading(
    text: str,
    page_number: int,
) -> str:

    for line in text.splitlines():

        line = line.strip()

        if line.startswith("#"):

            heading = re.sub(
                r"^#+\s*",
                "",
                line,
            ).strip()

            if heading:
                return heading[:300]

    return f"Prospectus page {page_number}"


def split_blocks(text: str) -> list[str]:

    blocks = re.split(
        r"\n\s*\n",
        text,
    )

    return [
        block.strip()
        for block in blocks
        if block.strip()
    ]


def build_page_chunks(
    page: dict,
) -> list[dict]:

    page_number = int(
        page["page_number"]
    )

    markdown = clean_markdown(
        page.get("markdown", "")
    )

    if not markdown:
        return []

    heading = extract_heading(
        markdown,
        page_number,
    )

    blocks = split_blocks(markdown)

    chunks = []
    current_blocks = []
    current_length = 0

    def save_current():

        if not current_blocks:
            return

        content = "\n\n".join(
            current_blocks
        ).strip()

        if not content:
            return

        chunk_index = len(chunks)

        chunks.append(
            {
                "chunk_id": (
                    f"page_{page_number}_"
                    f"chunk_{chunk_index}"
                ),
                "document": DOCUMENT,
                "page_number": page_number,
                "heading": heading,
                "content": content,
                "is_complex_table": (
                    content.count("<table") > 0
                    or content.count("<tr") >= 8
                    or content.count("|") >= 40
                ),
            }
        )

    for block in blocks:

        block_length = len(block)

        if (
            current_blocks
            and current_length + block_length
            > TARGET_CHARS
        ):

            save_current()

            current_blocks = (
                current_blocks[
                    -OVERLAP_BLOCKS:
                ]
            )

            current_length = sum(
                len(item)
                for item in current_blocks
            )

        current_blocks.append(block)

        current_length += block_length

    save_current()

    return chunks


data = json.loads(
    INPUT_PATH.read_text(
        encoding="utf-8"
    )
)

pages = data["markdown"]["pages"]

all_chunks = []

failed_pages = []

for page in pages:

    if not page.get("success", True):

        failed_pages.append(
            page.get("page_number")
        )

        continue

    all_chunks.extend(
        build_page_chunks(page)
    )


result = {
    "document": DOCUMENT,
    "total_pages": len(pages),
    "total_chunks": len(all_chunks),
    "failed_pages": failed_pages,
    "chunks": all_chunks,
}


OUTPUT_PATH.write_text(
    json.dumps(
        result,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)


print("\n=== RESCUE CHUNKING COMPLETE ===")
print("PAGES:", len(pages))
print("CHUNKS:", len(all_chunks))
print("FAILED PAGES:", failed_pages)
print(
    "COMPLEX TABLE CHUNKS:",
    sum(
        1
        for chunk in all_chunks
        if chunk["is_complex_table"]
    ),
)
print("SAVED:", OUTPUT_PATH)


print("\n=== PAGE 77 CHECK ===")

for chunk in all_chunks:

    if chunk["page_number"] == 77:

        print(
            chunk["chunk_id"],
            "|",
            chunk["heading"],
            "|",
            len(chunk["content"]),
            "chars",
        )

        print(
            chunk["content"][:500]
        )

        print("---")
