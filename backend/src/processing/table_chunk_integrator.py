# import json
# from pathlib import Path


# class TableChunkIntegrator:
#     """
#     Adds processed table-row chunks to the existing
#     document child-chunk artifact.
#     """

#     def integrate(
#         self,
#         chunks_path: Path,
#         tables_path: Path,
#     ) -> dict:

#         with open(
#             chunks_path,
#             "r",
#             encoding="utf-8",
#         ) as file:
#             chunks_document = json.load(file)

#         with open(
#             tables_path,
#             "r",
#             encoding="utf-8",
#         ) as file:
#             tables_document = json.load(file)

#         child_chunks = chunks_document[
#             "child_chunks"
#         ]

#         existing_table_chunks = {
#             chunk["chunk_id"]
#             for chunk in child_chunks
#             if chunk.get(
#                 "metadata",
#                 {},
#             ).get("content_type") == "table_row"
#         }

#         document_name = tables_document[
#             "document"
#         ]

#         added_count = 0

#         for page in tables_document["pages"]:

#             page_number = page["page_number"]

#             for table_index, table_entry in enumerate(
#                 page["tables"],
#                 start=1,
#             ):
#                 for row_index, table_chunk in enumerate(
#                     table_entry["chunks"],
#                     start=1,
#                 ):
#                     chunk_id = (
#                         f"table_p{page_number}"
#                         f"_t{table_index}"
#                         f"_r{row_index}"
#                     )

#                     if chunk_id in existing_table_chunks:
#                         continue

#                     table_title = (
#                         table_chunk["metadata"]
#                         ["table_title"]
#                     )

#                     child_chunks.append(
#                         {
#                             "chunk_id": chunk_id,
#                             "parent_chunk_id": chunk_id,
#                             "page_number": page_number,
#                             "heading": table_title,
#                             "content": table_chunk["text"],
#                             "metadata": {
#                                 "document": document_name,
#                                 "page": page_number,
#                                 "parent": chunk_id,
#                                 "content_type": "table_row",
#                                 "table_title": table_title,
#                             },
#                         }
#                     )

#                     existing_table_chunks.add(
#                         chunk_id
#                     )

#                     added_count += 1

#         with open(
#             chunks_path,
#             "w",
#             encoding="utf-8",
#         ) as file:
#             json.dump(
#                 chunks_document,
#                 file,
#                 indent=4,
#                 ensure_ascii=False,
#             )

#         return {
#             "added_table_chunks": added_count,
#             "total_child_chunks": len(
#                 child_chunks
#             ),
#         }

import json
from pathlib import Path


class TableChunkIntegrator:
    """
    Rebuilds table-row chunks inside the existing
    document child-chunk artifact.
    """

    def integrate(
        self,
        chunks_path: Path,
        tables_path: Path,
    ) -> dict:

        with open(
            chunks_path,
            "r",
            encoding="utf-8",
        ) as file:
            chunks_document = json.load(file)

        with open(
            tables_path,
            "r",
            encoding="utf-8",
        ) as file:
            tables_document = json.load(file)

        original_child_chunks = chunks_document[
            "child_chunks"
        ]

        # Remove old table chunks.
        # They may contain results from an older
        # table-extraction run.
        text_chunks = [
            chunk
            for chunk in original_child_chunks
            if chunk.get(
                "metadata",
                {},
            ).get("content_type") != "table_row"
        ]

        removed_table_chunks = (
            len(original_child_chunks)
            - len(text_chunks)
        )

        chunks_document["child_chunks"] = text_chunks

        child_chunks = chunks_document[
            "child_chunks"
        ]

        # Get document name safely.
        document_name = (
            chunks_document.get("document")
            or chunks_document.get(
                "metadata",
                {},
            ).get("document")
            or chunks_path.stem
        )

        added_count = 0

        for page in tables_document.get(
            "pages",
            [],
        ):

            page_number = page["page_number"]

            for table_index, table_entry in enumerate(
                page.get("tables", []),
                start=1,
            ):

                for row_index, table_chunk in enumerate(
                    table_entry.get("chunks", []),
                    start=1,
                ):

                    chunk_id = (
                        f"table_p{page_number}"
                        f"_t{table_index}"
                        f"_r{row_index}"
                    )

                    table_title = (
                        table_chunk.get(
                            "metadata",
                            {},
                        ).get(
                            "table_title",
                            f"Table on page {page_number}",
                        )
                    )

                    child_chunks.append(
                        {
                            "chunk_id": chunk_id,
                            "parent_chunk_id": chunk_id,
                            "page_number": page_number,
                            "heading": table_title,
                            "content": table_chunk["text"],
                            "metadata": {
                                "document": document_name,
                                "page": page_number,
                                "parent": chunk_id,
                                "content_type": "table_row",
                                "table_title": table_title,
                            },
                        }
                    )

                    added_count += 1

        with open(
            chunks_path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                chunks_document,
                file,
                indent=4,
                ensure_ascii=False,
            )

        return {
            "removed_old_table_chunks": (
                removed_table_chunks
            ),
            "added_table_chunks": added_count,
            "total_child_chunks": len(
                child_chunks
            ),
        }