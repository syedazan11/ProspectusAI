from copy import deepcopy
from pathlib import Path
import json
from copy import deepcopy
import re

from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

HEADERS = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
    ("####", "h4"),
]

header_splitter = MarkdownHeaderTextSplitter(
    headers_to_split_on=HEADERS,
    strip_headers=False,
)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1800,
    chunk_overlap=250,
    separators=[
        "\n#### ",
        "\n### ",
        "\n## ",
        "\n\n",
        "\n",
        ". ",
        " ",
    ],
)

# MARKDOWN_FILE = (
#     Path(__file__).resolve().parents[2]
#     / "storage"
#     / "experiments"
#     / "document.md"
# )


# def load_document() -> Document:

#     markdown = MARKDOWN_FILE.read_text(
#         encoding="utf-8",
#     )

#     return Document(
#         page_content=markdown,
#         metadata={
#             "document": MARKDOWN_FILE.stem,
#         },
#     )

def load_document(
    markdown_file: Path,
) -> Document:

    markdown = markdown_file.read_text(
        encoding="utf-8",
    )

    return Document(
        page_content=markdown,
        metadata={
            "document": markdown_file.stem,
        },
    )

def merge_metadata(
    parent: dict,
    child: dict,
) -> dict:

    metadata = deepcopy(parent)

    metadata.update(
        {
            key: value
            for key, value in child.items()
            if value not in ("", None)
        }
    )

    return metadata

def split_sections(
    pages: list[Document],
) -> list[Document]:

    sections = []
    last_h1 = None
    last_h2 = None
    last_h3 = None
    last_h4 = None
    section_counter = 0

    for page in pages:

        markdown_sections = header_splitter.split_text(
            page.page_content,
        )

        #
        # Page without headings
        #

        if not markdown_sections:

            metadata = deepcopy(page.metadata)

            if last_h1:
                metadata["h1"] = last_h1

            if last_h2:
                 metadata["h2"] = last_h2

            if last_h3:
                metadata["h3"] = last_h3

            if last_h4:
                metadata["h4"] = last_h4

            headings = []

            for level in ("h1", "h2", "h3", "h4"):

                if metadata.get(level):
                    headings.append(metadata[level])

            metadata["heading_path"] = " > ".join(headings)

            sections.append(
                Document(
                    page_content=page.page_content,
                    metadata=metadata,
                )
            )

            continue

        for section in markdown_sections:

            metadata = merge_metadata(
                page.metadata,
                section.metadata,
            )

            current_level = None

            if metadata.get("h4"):
                current_level = "h4"

            elif metadata.get("h3"):
                current_level = "h3"

            elif metadata.get("h2"):
                current_level = "h2"

            elif metadata.get("h1"):
                current_level = "h1"

            if current_level == "h1":

                last_h1 = metadata["h1"]

                last_h2 = None
                last_h3 = None
                last_h4 = None

            elif current_level == "h2":

                if metadata.get("h1"):
                    last_h1 = metadata["h1"]
                last_h2 = metadata.get("h2")
                last_h3 = None
                last_h4 = None

            elif current_level == "h3":

                if metadata.get("h1"):
                    last_h1 = metadata["h1"]
                if metadata.get("h2"):
                    last_h2 = metadata["h2"]
                last_h3 = metadata.get("h3")
                last_h4 = None

            elif current_level == "h4":

                if metadata.get("h1"):
                    last_h1 = metadata["h1"]
                if metadata.get("h2"):
                    last_h2 = metadata["h2"]
                if metadata.get("h3"):
                    last_h3 = metadata["h3"]
                last_h4 = metadata.get("h4")

            if current_level == "h4":

                if metadata.get("h3") is None:
                    metadata["h3"] = last_h3

                if metadata.get("h2") is None:
                    metadata["h2"] = last_h2

                if metadata.get("h1") is None:
                    metadata["h1"] = last_h1

            if current_level == "h3":

                if metadata.get("h2") is None:
                    metadata["h2"] = last_h2

                if metadata.get("h1") is None:
                    metadata["h1"] = last_h1

                if current_level == "h2":

                    if metadata.get("h1") is None:
                        metadata["h1"] = last_h1

            if current_level is not None:

                section_counter += 1


            #
            # Continuation page
            #

            if current_level is None:

                if last_h4:

                    metadata["h3"] = last_h3
                    metadata["h4"] = last_h4

                elif last_h3:

                    metadata["h2"] = last_h2
                    metadata["h3"] = last_h3

                elif last_h2:

                    metadata["h1"] = last_h1
                    metadata["h2"] = last_h2

                elif last_h1:

                    metadata["h1"] = last_h1

            #
            # Rebuild heading path
            #

            headings = []

            for level in ("h1", "h2", "h3", "h4"):

                if metadata.get(level):

                    headings.append(metadata[level])

            metadata["section_id"] = f"section_{section_counter}"

            metadata["heading_path"] = " > ".join(headings)

            sections.append(
                Document(
                    page_content=section.page_content,
                    metadata=metadata,
                )
            )

    return sections

def split_pages(
    markdown: str,
    document_name: str,
) -> list[Document]:
    
    pages = []

    pattern = r"<!--\s*PAGE\s+(\d+)\s*-->"

    matches = list(
        re.finditer(
            pattern,
            markdown,
            re.IGNORECASE,
        )
    )

    for i, match in enumerate(matches):

        page_number = int(match.group(1))

        start = match.end()

        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(markdown)

        page_text = markdown[start:end].strip()

        if not page_text:
            continue

        pages.append(
            Document(
                page_content=page_text,
                metadata={
                    "document": document_name, #MARKDOWN_FILE.stem,
                    "page": page_number,
                },
            )
        )

    return pages

def chunk_sections(
    sections: list[Document],
) -> list[Document]:

    chunks = []

    for section in sections:

        #
        # Preserve tables as one chunk
        #

        if "```table" in section.page_content:

            chunks.append(section)
            continue

        #
        # Split only if necessary
        #

        split_docs = text_splitter.create_documents(
            [section.page_content]
        )

        for split in split_docs:

            raw_text = split.page_content.strip()

            embedding_text = raw_text

            metadata = deepcopy(section.metadata)
            metadata["section_title"] = (
                metadata.get("h4")
                or metadata.get("h3")
                or metadata.get("h2")
                or metadata.get("h1")
                or ""
            )
            metadata["content_type"] = "text"

            if "|" in raw_text:
                metadata["content_type"] = "table"

            elif raw_text.startswith("-"):

                metadata["content_type"] = "list"

            elif raw_text.startswith("*"):

                metadata["content_type"] = "list"
            metadata["characters"] = len(raw_text)

            metadata["words"] = len(raw_text.split())

            #
            # Preserve heading hierarchy
            #

            heading_path = metadata.get(
                "heading_path",
                "",
            )

            if heading_path:

                context = heading_path.replace(
                    " > ",
                    "\n",
                )

                embedding_text = (
                    context
                    + "\n\n"
                    + raw_text
                )

            if (
                len(raw_text.split()) < 8
                and metadata.get("h4") is None
            ):
                continue

            metadata["raw_text"] = raw_text

            chunks.append(
                Document(
                    page_content=embedding_text,
                    metadata=metadata,
                )
            )

    return chunks

def save_chunks(
    chunks: list[Document],
    output_file: Path,
):

    output = []

    for index, chunk in enumerate(chunks, start=1):

        meta = chunk.metadata

        output.append(
            {
                "chunk_id": f"chunk_{index}",
                "section_id": meta.get("section_id"),
                #
                # Original text (for display)
                #
                "content": meta["raw_text"],

                #
                # Text to embed
                #
                "embedding_text": chunk.page_content,

                "metadata": {

                    "document": meta.get("document"),

                    "page": meta.get("page"),

                    "h1": meta.get("h1"),

                    "h2": meta.get("h2"),

                    "h3": meta.get("h3"),

                    "h4": meta.get("h4"),

                    "section_title": meta.get(
                        "section_title",
                    ),

                    "heading_path": meta.get(
                        "heading_path",
                    ),

                    "content_type": meta.get(
                        "content_type",
                    ),

                    "characters": meta.get(
                        "characters",
                    ),

                    "words": meta.get(
                        "words",
                    ),
                },
            }
        )

    # output_file = (
    #     Path(__file__).resolve().parents[2]
    #     / "storage"
    #     / "experiments"
    #     / "semantic_chunks.json"
    # )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with open(
        output_file,
        "w",
        encoding="utf-8",
    ) as f:

        json.dump(
            output,
            f,
            indent=4,
            ensure_ascii=False,
        )

    print(f"\nSaved -> {output_file}")

    return output_file

def create_semantic_chunks(
    markdown_file: Path,
) -> list[Document]:

    # global MARKDOWN_FILE

    # MARKDOWN_FILE = markdown_file

    # document = load_document()
    document = load_document(
        markdown_file,
    )

    pages = split_pages(
        document.page_content,
        markdown_file.stem,
    )

    sections = split_sections(
        pages,
    )

    chunks = chunk_sections(
        sections,
    )

    semantic_chunk_path = (
        markdown_file.parent
        / markdown_file.stem
        / "semantic_chunks.json"
    )

    save_chunks(
        chunks,
        semantic_chunk_path,
    )

    print(f"Pages    : {len(pages)}")
    print(f"Sections : {len(sections)}")
    print(f"Chunks   : {len(chunks)}")

    return chunks,  semantic_chunk_path

# def main():

#     document = load_document()

#     pages = split_pages(
#         document.page_content,
#     )

#     sections = split_sections(
#         pages,
#     )

#     chunks = chunk_sections(
#         sections,
#     )

#     save_chunks(
#         chunks,
#     )

#     print(f"Pages    : {len(pages)}")
#     print(f"Sections : {len(sections)}")
#     print(f"Chunks   : {len(chunks)}")


def main():
    raise RuntimeError(
        "Use create_semantic_chunks(markdown_file) "
        "from the document processing pipeline."
    )


if __name__ == "__main__":

    main()