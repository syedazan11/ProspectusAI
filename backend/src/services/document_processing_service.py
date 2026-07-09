import json
import re
from typing import Any

from src.indexing.indexer import Indexer
from src.ingestion.document_classifier import (
    DocumentClassifier,
)
from src.ingestion.loader import DocumentLoader
from src.ingestion.parser import DocumentParser
from src.processing.prospectus.section_detector import (
    ProspectusSectionDetector,
)
from src.processing.chunker import DocumentChunker
from src.processing.cleaner import DocumentCleaner
from src.services.document_manager import DocumentManager
from src.services.table_processing_service import (
    TableProcessingService,
)


class DocumentProcessingService:
    """
    Runs the complete processing pipeline for one
    registered prospectus.

    The document becomes ready only after the full
    pipeline succeeds.
    """

    def __init__(self) -> None:
        self.document_manager = DocumentManager()

    def process(
        self,
        document_id: str,
    ) -> dict[str, Any]:

        pdf_path = (
            self.document_manager.get_upload_path(
                document_id
            )
        )

        parsed_path = (
            self.document_manager.get_parsed_path(
                document_id
            )
        )

        sections_path = (
            self.document_manager.get_sections_path(
                document_id
            )
        )

        cleaned_path = (
            self.document_manager.get_cleaned_path(
                document_id
            )
        )

        chunks_path = (
            self.document_manager.get_chunks_path(
                document_id
            )
        )

        tables_path = (
            self.document_manager.get_tables_path(
                document_id
            )
        )

        collection_suffix = re.sub(
            r"[^a-zA-Z0-9_-]+",
            "_",
            document_id,
        ).strip("_").lower()

        if not collection_suffix:
            raise ValueError(
                "Document ID cannot produce a valid "
                "Qdrant collection name."
            )

        collection_name = (
            f"prospectus_{collection_suffix}"
        )

        self.document_manager.update_document(
            document_id,
            status="processing",
        )

        print(
            f"\n=== PROCESSING {document_id} ==="
        )

        try:
            loader = DocumentLoader()
            classifier = DocumentClassifier()
            parser = DocumentParser()
            cleaner = DocumentCleaner()
            chunker = DocumentChunker()

            pdf = loader.validate(pdf_path)

            classification = classifier.classify(pdf)

            parser.parse(
                pdf,
                classification["document_type"],
            )

            if not parsed_path.exists():
                raise FileNotFoundError(
                    f"Parsed output not found: {parsed_path}"
                )

            parsed_data = json.loads(
                parsed_path.read_text(
                    encoding="utf-8-sig"
                )
            )

            sections = (
                ProspectusSectionDetector().detect(
                    parsed_data.get("pages", [])
                )
            )

            sections_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            sections_path.write_text(
                json.dumps(
                    {
                        "document_id": document_id,
                        "sections": [
                            section.to_dict()
                            for section in sections
                        ],
                    },
                    indent=4,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            cleaner.clean(parsed_path)

            if not cleaned_path.exists():
                raise FileNotFoundError(
                    f"Cleaned output not found: {cleaned_path}"
                )

            chunks = chunker.chunk(cleaned_path)

            if not chunks_path.exists():
                raise FileNotFoundError(
                    f"Chunks output not found: {chunks_path}"
                )

            table_service = TableProcessingService()

            table_result = table_service.process(
                parsed_path=parsed_path,
                output_path=tables_path,
            )

            indexer = Indexer(
                collection_name=collection_name,
            )

            indexer.index(
                chunks_json=chunks_path,
                document_id=document_id,
            )

            self.document_manager.update_document(
                document_id,
                collection_name=collection_name,
            )

            self.document_manager.mark_ready(
                document_id
            )

            print(
                f"\n=== {document_id} READY ==="
            )

            return {
                "document_id": document_id,
                "document_type": (
                    classification["document_type"]
                ),
                "parent_chunks": len(
                    chunks.get("parent_chunks", [])
                ),
                "child_chunks": len(
                    chunks.get("child_chunks", [])
                ),
                "table_pages": len(
                    table_result.get("pages", [])
                ),
                "collection_name": collection_name,
                "status": "ready",
            }

        except Exception:
            self.document_manager.update_document(
                document_id,
                status="failed",
            )

            raise
