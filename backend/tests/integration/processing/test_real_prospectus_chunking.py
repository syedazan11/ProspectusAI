import json
from pathlib import Path

from src.processing.prospectus.chunker import (
    ProspectusChunker,
)


PROJECT_ROOT = Path(__file__).resolve().parents[4]

INPUT_PATH = (
    PROJECT_ROOT
    / "storage"
    / "processed"
    / "UGProspectus2025"
    / "extracted_document.json"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "storage"
    / "processed"
    / "UGProspectus2025"
    / "chunks_v1.json"
)


def test_chunk_real_ug_prospectus():
    data = json.loads(
        INPUT_PATH.read_text(
            encoding="utf-8-sig"
        )
    )

    chunks = ProspectusChunker().chunk_document(
        data["pages"]
    )

    lengths = [
        chunk.character_count
        for chunk in chunks
    ]

    oversized = [
        chunk
        for chunk in chunks
        if chunk.character_count > 2000
    ]

    empty = [
        chunk
        for chunk in chunks
        if not chunk.text.strip()
    ]

    output = {
        "source_file": data["source_file"],
        "total_chunks": len(chunks),
        "chunks": [
            chunk.to_dict()
            for chunk in chunks
        ],
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    print()
    print(f"Total chunks: {len(chunks)}")
    print(f"Minimum size: {min(lengths)}")
    print(f"Maximum size: {max(lengths)}")
    print(
        f"Average size: "
        f"{sum(lengths) // len(lengths)}"
    )
    print(f"Oversized chunks: {len(oversized)}")
    print(f"Empty chunks: {len(empty)}")
    print(f"Output: {OUTPUT_PATH}")

    assert len(chunks) > 200
    assert not oversized
    assert not empty
    assert len(set(
        chunk.chunk_id
        for chunk in chunks
    )) == len(chunks)
