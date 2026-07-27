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
from src.processing.prospectus.record_processing_service import (
    RecordProcessingService,
)
from src.schemas.seat_distribution import (
    SeatDistributionDocument,
    SeatDistributionSection,
)
from src.processing.seat_distribution_processor import (
    SeatDistributionProcessor,
)
from src.annotations.review_service import ReviewService
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
                force_pages=None,
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

            print("\n=== DETECTED SECTIONS ===")

            for section in sections:
                print(
                    section.section_type,
                    section.start_page,
                    section.end_page,
                )

            seat_processor = SeatDistributionProcessor()

            seat_processing_results = []

            for section in sections:

                if not section.section_type.startswith(
                    "seat_distribution"
                ):
                    continue

                result = seat_processor.process(
                    section=section,
                    parsed_pages=parsed_data.get(
                        "pages",
                        [],
                    ),
                )

                seat_processing_results.append(result)

            print("\n=== SEAT PROCESSOR ===")

            for result in seat_processing_results:
                print(
                    f"{result['section'].section_type} "
                    f"-> extractable={result['extractable']}"
                )

            review_service = ReviewService()

            pending_reviews = review_service.check(
                pages=parsed_data.get("pages", []),
                detected_sections=sections,
            )

            self.document_manager.save_pending_reviews(
                document_id=document_id,
                reviews=pending_reviews,
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

            seat_distribution_path = (
                self.document_manager.get_seat_distribution_path(
                    document_id
                )
            )

            seat_distribution_path.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            seat_distribution = SeatDistributionDocument(
                document_id=document_id,
            )

            for section in sections:

                if (
                    section.section_type
                    == "seat_distribution_regular"
                ):
                    seat_distribution.sections.append(
                        SeatDistributionSection.from_page_range(
                            scheme="Regular",
                            start_page=section.start_page,
                            end_page=section.end_page,
                        )
                    )

                elif (
                    section.section_type
                    == "seat_distribution_self_finance"
                ):
                    seat_distribution.sections.append(
                        SeatDistributionSection.from_page_range(
                            scheme="Self Finance",
                            start_page=section.start_page,
                            end_page=section.end_page,
                        )
                    )

            seat_distribution_path.write_text(
                seat_distribution.model_dump_json(
                    indent=4,
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
                        force=False,
                    )
                )

                markdown_data = (
                    curriculum_parse_data.get(
                        "markdown",
                        {}
                    )
                )

                if isinstance(markdown_data, dict):
                    markdown_pages = (
                        markdown_data.get(
                            "pages",
                            []
                        )
                    )
                else:
                    markdown_pages = markdown_data

                if not isinstance(
                    markdown_pages,
                    list,
                ):
                    raise ValueError(
                        "Curriculum parser did not "
                        "return a markdown page list."
                    )

                extractor = CurriculumRecordExtractor()

                curriculum_records = extractor.extract(
                    markdown_pages,
                    first_source_page=curriculum_start,
                )

                curriculum_metadata = (
                    extractor.get_curriculum_metadata()
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
                            "curriculum_metadata": (
                                curriculum_metadata
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

                CurriculumIndexer(
                    collection_name=collection_name,
                ).index(
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
            
            with open(
                cleaned_path,
                "r",
                encoding="utf-8",
            ) as f:
                cleaned_document = json.load(f)

            record_results = (
                RecordProcessingService().process(
                    cleaned_document=cleaned_document,
                    detected_sections=sections,
                )
            )

            chunks = chunker.chunk(
                cleaned_path,
                structured_records=record_results,
            )

            if not chunks_path.exists():
                raise FileNotFoundError(
                    f"Chunks output not found: {chunks_path}"
                )

            table_service = TableProcessingService()

            table_result = table_service.process(
                parsed_path=parsed_path,
                output_path=tables_path,
            )

            # --------------------------------------
            # Route-aware ingestion quality gate
            # --------------------------------------

            parsed_pages = parsed_data.get(
                "pages",
                [],
            )

            total_pages = len(parsed_pages)

            if total_pages == 0:
                raise ValueError(
                    "Ingestion quality gate failed: "
                    "no parsed pages."
                )

            usable_text_pages = 0

            for page in parsed_pages:
                page_text = (
                    page.get("text")
                    or page.get("markdown")
                    or ""
                ).strip()

                if len(page_text.split()) >= 20:
                    usable_text_pages += 1

            parent_chunks = chunks.get(
                "parent_chunks",
                [],
            )

            child_chunks = chunks.get(
                "child_chunks",
                [],
            )

            detected_section_types = {
                section.section_type
                for section in sections
            }

            curriculum_detected = (
                "curriculum"
                in detected_section_types
            )

            seat_sections_detected = {
                section_type
                for section_type
                in detected_section_types
                if section_type.startswith(
                    "seat_distribution_"
                )
            }

            minimum_usable_text_pages = max(
                5,
                total_pages // 5,
            )

            minimum_parent_chunks = max(
                5,
                total_pages // 20,
            )

            minimum_child_chunks = max(
                10,
                total_pages // 10,
            )

            quality_errors = []

            if (
                usable_text_pages
                < minimum_usable_text_pages
            ):
                quality_errors.append(
                    "usable text coverage too low: "
                    f"{usable_text_pages}/"
                    f"{total_pages} pages"
                )

            if (
                len(parent_chunks)
                < minimum_parent_chunks
            ):
                quality_errors.append(
                    "parent chunk coverage too low: "
                    f"{len(parent_chunks)} "
                    f"(minimum "
                    f"{minimum_parent_chunks})"
                )

            if (
                len(child_chunks)
                < minimum_child_chunks
            ):
                quality_errors.append(
                    "child chunk coverage too low: "
                    f"{len(child_chunks)} "
                    f"(minimum "
                    f"{minimum_child_chunks})"
                )

            if (
                curriculum_detected
                and curriculum_result.get(
                    "records",
                    0,
                ) <= 0
            ):
                quality_errors.append(
                    "curriculum was detected but "
                    "no curriculum records were produced"
                )

            print(
                "\n=== INGESTION QUALITY GATE ==="
            )
            print(
                f"Parsed pages: {total_pages}"
            )
            print(
                "Usable text pages: "
                f"{usable_text_pages}"
            )
            print(
                "Parent chunks: "
                f"{len(parent_chunks)}"
            )
            print(
                "Child chunks: "
                f"{len(child_chunks)}"
            )
            print(
                "Detected sections: "
                f"{sorted(detected_section_types)}"
            )
            print(
                "Seat routes: "
                f"{sorted(seat_sections_detected)}"
            )
            print(
                "Curriculum records: "
                f"{curriculum_result.get('records', 0)}"
            )

            if quality_errors:
                raise ValueError(
                    "Ingestion quality gate failed: "
                    + "; ".join(quality_errors)
                )

            print("QUALITY GATE: PASS")

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
