import json
import os
import re
import uuid
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from llama_cloud import LlamaCloud
from qdrant_client import QdrantClient, models

from src.services.document_manager import DocumentManager


PROJECT_ROOT = Path(__file__).resolve().parents[3]

load_dotenv(
    PROJECT_ROOT / "backend" / ".env"
)


class RescueDocumentProcessingService:

    MODEL = (
        "sentence-transformers/"
        "all-minilm-l6-v2"
    )

    TARGET_CHARS = 1800
    OVERLAP_BLOCKS = 1
    BATCH_SIZE = 16


    def __init__(self) -> None:

        self.manager = DocumentManager()

        llama_api_key = os.getenv(
            "LLAMA_CLOUD_API_KEY"
        )

        if not llama_api_key:
            raise RuntimeError(
                "LLAMA_CLOUD_API_KEY is missing."
            )

        self.llama_client = LlamaCloud(
            api_key=llama_api_key
        )

        self.qdrant = QdrantClient(
            url=os.getenv("QDRANT_HOST"),
            api_key=os.getenv(
                "QDRANT_API_KEY"
            ),
            cloud_inference=True,
            timeout=180,
            check_compatibility=False,
        )


    def process(
        self,
        document_id: str,
    ) -> dict[str, Any]:

        pdf_path = (
            self.manager.get_upload_path(
                document_id
            )
        )

        collection_name = (
            "prospectus_"
            + re.sub(
                r"[^a-zA-Z0-9_]+",
                "_",
                document_id,
            ).strip("_").lower()
        )

        rescue_dir = (
            PROJECT_ROOT
            / "storage"
            / "rescue"
            / document_id
        )

        rescue_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        parse_path = (
            rescue_dir
            / "llamaparse.json"
        )

        chunks_path = (
            rescue_dir
            / "chunks.json"
        )

        self._set_status(
            document_id,
            "processing",
        )

        try:

            parsed_data = self._parse(
                pdf_path=pdf_path,
                output_path=parse_path,
            )

            chunks = self._build_chunks(
                parsed_data=parsed_data,
                document_name=pdf_path.name,
                output_path=chunks_path,
            )

            self._index(
                chunks=chunks,
                collection_name=collection_name,
            )

            self._mark_ready(
                document_id=document_id,
                collection_name=collection_name,
            )

            return {
                "document_id": document_id,
                "collection_name": collection_name,
                "chunks": len(chunks),
                "status": "ready",
            }

        except Exception:

            self._set_status(
                document_id,
                "failed",
            )

            raise


    def _parse(
        self,
        pdf_path: Path,
        output_path: Path,
    ) -> dict:

        with pdf_path.open("rb") as pdf_file:

            result = (
                self.llama_client.parsing.parse(
                    upload_file=pdf_file,
                    tier="agentic",
                    version="latest",
                    expand=[
                        "markdown",
                        "text",
                    ],
                    verbose=True,
                )
            )

        data = (
            result.model_dump()
            if hasattr(
                result,
                "model_dump",
            )
            else result
        )

        output_path.write_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )

        return data


    def _build_chunks(
        self,
        parsed_data: dict,
        document_name: str,
        output_path: Path,
    ) -> list[dict]:

        pages = (
            parsed_data
            .get("markdown", {})
            .get("pages", [])
        )

        all_chunks = []

        for page in pages:

            if not page.get(
                "success",
                True,
            ):
                continue

            page_number = int(
                page["page_number"]
            )

            markdown = (
                page.get(
                    "markdown",
                    ""
                )
                .replace(
                    "\x00",
                    " ",
                )
                .strip()
            )

            markdown = re.sub(
                r"\n{3,}",
                "\n\n",
                markdown,
            )

            if not markdown:
                continue

            heading = (
                self._extract_heading(
                    markdown,
                    page_number,
                )
            )

            blocks = [
                block.strip()
                for block in re.split(
                    r"\n\s*\n",
                    markdown,
                )
                if block.strip()
            ]

            current_blocks = []
            current_length = 0
            page_chunks = []

            def save_current():

                if not current_blocks:
                    return

                content = "\n\n".join(
                    current_blocks
                ).strip()

                if not content:
                    return

                chunk_index = len(
                    page_chunks
                )

                page_chunks.append(
                    {
                        "chunk_id": (
                            f"{document_name}_"
                            f"page_{page_number}_"
                            f"chunk_{chunk_index}"
                        ),
                        "document": (
                            document_name
                        ),
                        "page_number": (
                            page_number
                        ),
                        "heading": heading,
                        "content": content,
                        "is_complex_table": (
                            content.count(
                                "<table"
                            ) > 0
                            or content.count(
                                "<tr"
                            ) >= 8
                            or content.count(
                                "|"
                            ) >= 40
                        ),
                    }
                )

            for block in blocks:

                if (
                    current_blocks
                    and (
                        current_length
                        + len(block)
                        > self.TARGET_CHARS
                    )
                ):

                    save_current()

                    current_blocks = (
                        current_blocks[
                            -self.OVERLAP_BLOCKS:
                        ]
                    )

                    current_length = sum(
                        len(item)
                        for item
                        in current_blocks
                    )

                current_blocks.append(
                    block
                )

                current_length += len(
                    block
                )

            save_current()

            all_chunks.extend(
                page_chunks
            )

        output_path.write_text(
            json.dumps(
                {
                    "document": (
                        document_name
                    ),
                    "total_pages": len(
                        pages
                    ),
                    "total_chunks": len(
                        all_chunks
                    ),
                    "chunks": all_chunks,
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return all_chunks


    def _extract_heading(
        self,
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

        return (
            f"Prospectus page "
            f"{page_number}"
        )


    def _index(
        self,
        chunks: list[dict],
        collection_name: str,
    ) -> None:

        if self.qdrant.collection_exists(
            collection_name
        ):

            self.qdrant.delete_collection(
                collection_name=(
                    collection_name
                )
            )

        self.qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=(
                models.VectorParams(
                    size=384,
                    distance=(
                        models.Distance.COSINE
                    ),
                )
            ),
        )

        for start in range(
            0,
            len(chunks),
            self.BATCH_SIZE,
        ):

            batch = chunks[
                start:
                start + self.BATCH_SIZE
            ]

            points = []

            for chunk in batch:

                embedding_text = (
                    f"{chunk['heading']}\n\n"
                    f"{chunk['content'][:900]}"
                )

                point_id = str(
                    uuid.uuid5(
                        uuid.NAMESPACE_URL,
                        chunk["chunk_id"],
                    )
                )

                points.append(
                    models.PointStruct(
                        id=point_id,
                        vector=models.Document(
                            text=embedding_text,
                            model=self.MODEL,
                        ),
                        payload=chunk,
                    )
                )

            self.qdrant.upsert(
                collection_name=(
                    collection_name
                ),
                points=points,
                wait=True,
            )


    def _set_status(
        self,
        document_id: str,
        status: str,
    ) -> None:

        registry = (
            self.manager.load_registry()
        )

        for document in (
            registry["documents"]
        ):

            if (
                document["document_id"]
                == document_id
            ):

                document["status"] = (
                    status
                )

                break

        self.manager.save_registry(
            registry
        )


    def _mark_ready(
        self,
        document_id: str,
        collection_name: str,
    ) -> None:

        registry = (
            self.manager.load_registry()
        )

        found = False

        for document in (
            registry["documents"]
        ):

            if (
                document["document_id"]
                == document_id
            ):

                document["status"] = (
                    "ready"
                )

                document[
                    "collection_name"
                ] = collection_name

                found = True

                break

        if not found:

            raise ValueError(
                f"Unknown document: "
                f"{document_id}"
            )

        registry[
            "active_document_id"
        ] = document_id

        self.manager.save_registry(
            registry
        )

        self.manager.enforce_retention()
