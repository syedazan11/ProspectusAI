import json
import re
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.schemas.chunk import (
    ParentChunk,
    ChildChunk,
)


class DocumentChunker:
    """
    Creates parent and child chunks from the cleaned document.
    """

    def chunk(self, cleaned_json: Path):

        with open(cleaned_json, "r", encoding="utf-8") as f:
            document = json.load(f)

        parent_chunks: list[ParentChunk] = []
        child_chunks: list[ChildChunk] = []

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=150,
            separators=[
                "\n\n",
                "\n",
                ". ",
                " ",
                "",
            ],
        )

        chunk_counter = 1

        for page in document["pages"]:

            # Skip pages with corrupted tables
            if page.get("table_corrupted", False):
                continue

            for section in page["sections"]:

                heading = section["heading"]

                # Reject noisy OCR headings
                letters = len(re.findall(r"[A-Za-z]", heading))

                if (
                    len(heading.split()) < 2
                    or "¥" in heading
                    or letters < 8
                ):
                    continue

                content = "\n".join(section["content"]).strip()

                # Reject very small chunks
                words = content.split()

                if len(words) < 20:
                    continue

                if len(content) < 30:
                    continue

                parent_id = f"parent_{chunk_counter}"

                parent_chunks.append(
                    ParentChunk(
                        chunk_id=parent_id,
                        heading=heading,
                        page_number=page["page_number"],
                        content=content,
                        metadata={
                                "document": document["metadata"]["filename"],
                                "page": page["page_number"],
                            },
                    )
                )

                # Generate child chunks
                full_text = f"{heading}\n\n{content}"
                split_chunks = text_splitter.split_text(full_text)

                filtered_chunks = []

                for chunk in split_chunks:

                    if len(chunk.split()) < 15:
                        continue

                    filtered_chunks.append(chunk)

                for i, chunk_text in enumerate(filtered_chunks, start=1):

                    child_chunks.append(
                        ChildChunk(
                            chunk_id=f"{parent_id}_child_{i}",
                            parent_chunk_id=parent_id,
                            page_number=page["page_number"],
                            heading=heading,
                            content=chunk_text,
                            metadata={
                                    "document": document["metadata"]["filename"],
                                    "page": page["page_number"],
                                    "parent": parent_id,
                                },
                        )
                    )

                chunk_counter += 1

        output = {
            "parent_chunks": [
                chunk.model_dump()
                for chunk in parent_chunks
            ],
            "child_chunks": [
                chunk.model_dump()
                for chunk in child_chunks
            ],
        }

        output_path = (
            Path(__file__).resolve().parents[3]
            / "storage"
            / "chunks"
            / f"{cleaned_json.stem}.json"
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                output,
                f,
                indent=4,
                ensure_ascii=False,
            )

        print(f"Saved chunks -> {output_path}")
        print(f"Parent Chunks: {len(parent_chunks)}")
        print(f"Child Chunks: {len(child_chunks)}")
        return output