import json
import re
from typing import Any

from src.indexing.curriculum_indexer import (
    CurriculumIndexer,
)
from src.indexing.indexer import Indexer
from src.ingestion.document_classifier import (
    DocumentClassifier,
)
from src.ingestion.loader import DocumentLoader
from src.ingestion.parser import DocumentParser
from src.processing.prospectus.curriculum_parse_service import (
    CurriculumParseService,
)
from src.processing.prospectus.curriculum_record_extractor import (
    CurriculumRecordExtractor,
)
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

            curriculum_result = {
                "detected": False,
                "records": 0,
                "start_page": None,
                "end_page": None,
            }

            curriculum_section = next(
                (
                    section
                    for section in sections
                    if section.section_type
                    == "curriculum"
                ),
                None,
            )

            if curriculum_section is not None:
                import fitz

                curriculum_result[
                    "detected"
                ] = True

                curriculum_start = (
                    curriculum_section.start_page
                )
                curriculum_end = (
                    curriculum_section.end_page
                )

                curriculum_result[
                    "start_page"
                ] = curriculum_start

                curriculum_result[
                    "end_page"
                ] = curriculum_end

                processed_dir = (
                    pdf_path.parent.parent
                    / "processed"
                    / document_id
                )

                processed_dir.mkdir(
                    parents=True,
                    exist_ok=True,
                )

                curriculum_pdf_path = (
                    processed_dir
                    / "curriculum_pages.pdf"
                )

                curriculum_parse_path = (
                    processed_dir
                    / "curriculum_llamaparse_v1.json"
                )

                curriculum_records_path = (
                    processed_dir
                    / "curriculum_records_v2.json"
                )

                source_pdf = fitz.open(pdf_path)

                try:
                    curriculum_pdf = fitz.open()

                    curriculum_pdf.insert_pdf(
                        source_pdf,
                        from_page=curriculum_start - 1,
                        to_page=curriculum_end - 1,
                    )

                    curriculum_pdf.save(
                        curriculum_pdf_path
                    )

                    curriculum_pdf.close()

                finally:
                    source_pdf.close()

                print(
                    "\n=== CURRICULUM ROUTE ==="
                )
                print(
                    f"Pages {curriculum_start}-"
                    f"{curriculum_end}"
                )

                curriculum_parse_data = (
                    CurriculumParseService().parse(
                        input_path=curriculum_pdf_path,
                        output_json_path=(
                            curriculum_parse_path
                        ),
                        force=True,
                    )
                )

                markdown_pages = (
                    curriculum_parse_data.get(
                        "markdown",
                        []
                    )
                )

                if not isinstance(
                    markdown_pages,
                    list,
                ):
                    raise ValueError(
                        "Curriculum parser did not "
                        "return a markdown page list."
                    )

                curriculum_records = (
                    CurriculumRecordExtractor().extract(
                        markdown_pages,
                        first_source_page=(
                            curriculum_start
                        ),
                    )
                )

                curriculum_records_path.write_text(
                    json.dumps(
                        {
                            "document_id": document_id,
                            "source_start_page": (
                                curriculum_start
                            ),
                            "source_end_page": (
                                curriculum_end
                            ),
                            "records": [
                                record.to_dict()
                                for record
                                in curriculum_records
                            ],
                        },
                        indent=2,
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )

                curriculum_result[
                    "records"
                ] = len(curriculum_records)

                if not curriculum_records:
                    raise ValueError(
                        "Curriculum section was "
                        "detected but produced "
                        "zero curriculum records."
                    )

                CurriculumIndexer().index(
                    curriculum_records_path,
                    document_id=document_id,
                )

                print(
                    f"CURRICULUM RECORDS: "
                    f"{len(curriculum_records)}"
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
                "curriculum": curriculum_result,
                "collection_name": collection_name,
                "status": "ready",
            }

        except Exception:
            self.document_manager.update_document(
                document_id,
                status="failed",
            )

            raise
