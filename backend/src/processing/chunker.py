import json
import re
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.schemas.chunk import (
    ParentChunk,
    ChildChunk,
)
from src.processing.structured_chunk_builder import (
    StructuredChunkBuilder,
)


class DocumentChunker:
    """
    Creates parent and child chunks from the cleaned document.
    """

    def chunk(
        self,
        cleaned_json: Path,
        *,
        exclude_pages: set[int] | None = None,
        structured_records: dict | None = None,
    ):

        exclude_pages = exclude_pages or set()

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

            if page["page_number"] in exclude_pages:
                continue

            valid_sections = []

            for section in page.get("sections", []):

                heading = section.get(
                    "heading",
                    "",
                ).strip()

                content = "\n".join(
                    section.get("content", [])
                ).strip()

                letters = len(
                    re.findall(
                        r"[A-Za-z]",
                        heading,
                    )
                )

                if (
                    len(heading.split()) < 2
                    or "??" in heading
                    or letters < 8
                    or len(content.split()) < 20
                    or len(content) < 30
                ):
                    continue

                valid_sections.append(
                    {
                        "heading": heading,
                        "heading_number": section.get(
                            "heading_number",
                            "",
                        ),
                        "heading_level": section.get(
                            "heading_level",
                            0,
                        ),
                        "heading_title": section.get(
                            "heading_title",
                            heading,
                        ),
                        "content": content,
                        "metadata": dict(
                            section.get(
                                "metadata",
                                {},
                            )
                            or {}
                        ),
                    }
                )

            if not valid_sections:

                fallback_text = page.get(
                    "text",
                    "",
                ).strip()

                if len(fallback_text.split()) >= 20:
                    valid_sections.append(
                        {
                            "heading": (
                                f"Page {page['page_number']}"
                            ),
                            "content": fallback_text,
                        }
                    )

            for section in valid_sections:

                heading = section["heading"]
                content = section["content"]

                parent_id = f"parent_{chunk_counter}"

                parent_chunks.append(
                    ParentChunk(
                        chunk_id=parent_id,
                        heading=heading,
                        heading_number=section.get(
                            "heading_number",
                            "",
                        ),
                        heading_level=section.get(
                            "heading_level",
                            0,
                        ),
                        heading_title=section.get(
                            "heading_title",
                            heading,
                        ),
                        page_number=page["page_number"],
                        content=content,
                       metadata={
                           "document": (
                               document["metadata"]["filename"]
                           ),
                           "page": (
                               page["page_number"]
                           ),
                           **section.get(
                               "metadata",
                               {},
                           ),
                       },
                    )
                )

                full_text = f"{heading}\n\n{content}"

                split_chunks = (
                    text_splitter.split_text(
                        full_text
                    )
                )

                filtered_chunks = []

                for chunk in split_chunks:

                    if len(chunk.split()) < 15:
                        continue

                    filtered_chunks.append(chunk)

                for i, chunk_text in enumerate(
                    filtered_chunks,
                    start=1,
                ):

                    child_chunks.append(
                        ChildChunk(
                            chunk_id=(
                                f"{parent_id}_child_{i}"
                            ),
                            parent_chunk_id=parent_id,
                            page_number=(
                                page["page_number"]
                            ),
                            heading=heading,
                            heading_number=section.get(
                                "heading_number",
                                "",
                            ),
                            heading_level=section.get(
                                "heading_level",
                                0,
                            ),
                            heading_title=section.get(
                                "heading_title",
                                heading,
                            ),
                            content=chunk_text,
                            metadata={
                                "document": (
                                    document["metadata"]["filename"]
                                ),
                                "page": (
                                    page["page_number"]
                                ),
                                "parent": parent_id,
                                **section.get(
                                    "metadata",
                                    {},
                                ),
                            },
                        )
                    )

                chunk_counter += 1
        
        if structured_records:

            structured = (
                StructuredChunkBuilder().build(
                    record_results=structured_records,
                )
            )

            parent_chunks.extend(
                structured["parent_chunks"]
            )

            child_chunks.extend(
                structured["child_chunks"]
            )

            print(
                "[STRUCTURED CHUNKS] "
                f"Parent={len(structured['parent_chunks'])} "
                f"Child={len(structured['child_chunks'])}"
            )

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