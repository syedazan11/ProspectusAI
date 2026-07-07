import json
from typing import Any

from src.graph.graph_builder import GraphBuilder
from src.indexing.indexer import Indexer
from src.ingestion.document_classifier import (
    DocumentClassifier,
)
from src.ingestion.loader import DocumentLoader
from src.ingestion.parser import DocumentParser
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

        graph_path = (
            self.document_manager.get_graph_path(
                document_id
            )
        )

        print(
            f"\n=== PROCESSING {document_id} ==="
        )

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

        indexer = Indexer()
        indexer.index(chunks_path)

        parent_chunks = chunks.get(
            "parent_chunks",
            [],
        )

        graph_builder = GraphBuilder()

        graph = graph_builder.build(
            chunks=parent_chunks,
            checkpoint_path=graph_path,
        )

        graph_builder.save(
            graph=graph,
            output_path=graph_path,
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
            "parent_chunks": len(parent_chunks),
            "child_chunks": len(
                chunks.get("child_chunks", [])
            ),
            "table_pages": len(
                table_result.get("pages", [])
            ),
            "graph_entities": len(
                graph.get("entities", [])
            ),
            "graph_relationships": len(
                graph.get("relationships", [])
            ),
            "status": "ready",
        }
