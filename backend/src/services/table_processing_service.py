import json
from pathlib import Path
from typing import Any

import fitz

from src.schemas.table import ExtractedTable
from src.processing.table_pipeline import TablePipeline
from src.validation.table_quality_validator import (
    TableQualityValidator,
)


class TableProcessingService:
    """
    Processes table pages with automatic quality control.

    Flow:
    extraction
        -> final quality validation
        -> alternate vision retry if invalid
        -> revalidation
        -> accept or quarantine

    Invalid tables are never stored as successful pages.
    """

    def __init__(self):
        self.table_pipeline = TablePipeline()
        self.quality_validator = TableQualityValidator()

        self.table_detector = None
    
    def _get_table_detector(self):

        if self.table_detector is not None:
            return self.table_detector

        from docling.datamodel.base_models import (
            InputFormat,
        )
        from docling.datamodel.pipeline_options import (
            PdfPipelineOptions,
        )
        from docling.document_converter import (
            DocumentConverter,
            PdfFormatOption,
        )

        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False
        pipeline_options.do_table_structure = True

        self.table_detector = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options
                )
            }
        )

        return self.table_detector

    def process(
        self,
        parsed_path: Path,
        output_path: Path,
    ) -> dict[str, Any]:

        parsed_document = json.loads(
            parsed_path.read_text(encoding="utf-8")
        )

        result = self._load_checkpoint(output_path)

        processed_page_numbers = set(
            result["metadata"].get(
                "processed_page_numbers",
                [],
            )
        )

        table_pages = [
            page
            for page in parsed_document["pages"]
            if page["metadata"]["route"]
            in {
                "local_table_page",
                "complex_table_page",
            }
        ]

        print("\n======= TABLE PROCESSING PLAN =======")
        print(f"Table pages: {len(table_pages)}")
        print(
            "Already processed:",
            len(processed_page_numbers),
        )
        print(
            "Pending:",
            sum(
                1
                for page in table_pages
                if page["page_number"]
                not in processed_page_numbers
            ),
        )
        print("=====================================\n")

        for page in table_pages:

            page_number = page["page_number"]

            if page_number in processed_page_numbers:
                print(
                    f"Skipping page {page_number} "
                    "(already processed)."
                )
                continue

            route = page["metadata"]["route"]

            print(
                f"Processing page {page_number} "
                f"via {route}..."
            )

            try:
                if route == "local_table_page":
                    page_result = self._process_local_page(
                        page
                    )

                elif route == "complex_table_page":
                    page_result = self._process_complex_page(
                        page
                    )

                else:
                    continue

                if page_result["status"] == "accepted":

                    result["pages"] = [
                        existing_page
                        for existing_page in result["pages"]
                        if existing_page["page_number"]
                        != page_number
                    ]

                    result["pages"].append(page_result)

                    processed_page_numbers.add(page_number)

                    result["metadata"][
                        "processed_page_numbers"
                    ] = sorted(processed_page_numbers)

                    result["metadata"][
                        "quarantined_pages"
                    ] = [
                        item
                        for item in result[
                            "metadata"
                        ].get(
                            "quarantined_pages",
                            [],
                        )
                        if item["page_number"]
                        != page_number
                    ]

                    print(
                        f"Accepted page {page_number}."
                    )

                else:
                    quarantine_entry = {
                        "page_number": page_number,
                        "route": route,
                        "reason": page_result.get(
                            "reason",
                            "Table failed quality validation.",
                        ),
                        "page_path": page.get(
                            "metadata",
                            {},
                        ).get(
                            "page_path",
                        ),
                        "document": parsed_path.stem,
                        "attempts": page_result.get(
                            "attempts",
                            [],
                        ),
                    }

                    quarantined = [
                        item
                        for item in result[
                            "metadata"
                        ].get(
                            "quarantined_pages",
                            [],
                        )
                        if item["page_number"]
                        != page_number
                    ]

                    quarantined.append(
                        quarantine_entry
                    )

                    result["metadata"][
                        "quarantined_pages"
                    ] = quarantined

                    processed_page_numbers.add(
                        page_number
                    )

                    result["metadata"][
                        "processed_page_numbers"
                    ] = sorted(
                        processed_page_numbers
                    )

                    print(
                        f"Quarantined page {page_number} "
                        "and marked processing complete."
                    )

                result["metadata"][
                    "failed_pages"
                ] = [
                    failure
                    for failure in result[
                        "metadata"
                    ].get(
                        "failed_pages",
                        [],
                    )
                    if failure["page_number"]
                    != page_number
                ]

                self._save_checkpoint(
                    result=result,
                    output_path=output_path,
                )

            except Exception as error:

                print(
                    f"Failed page {page_number}: {error}"
                )

                failures = [
                    failure
                    for failure in result[
                        "metadata"
                    ].get(
                        "failed_pages",
                        [],
                    )
                    if failure["page_number"]
                    != page_number
                ]

                failures.append(
                    {
                        "page_number": page_number,
                        "error": str(error),
                    }
                )

                result["metadata"][
                    "failed_pages"
                ] = failures

                self._save_checkpoint(
                    result=result,
                    output_path=output_path,
                )

        return result

    def _process_local_page(
        self,
        page: dict[str, Any],
    ) -> dict[str, Any]:

        page_number = page["page_number"]
        attempts = []
        accepted_tables = []

        for decision in page[
            "metadata"
        ].get(
            "table_decisions",
            [],
        ):
            if not decision.get("usable", False):
                continue

            table_data = decision.get(
                "local_table_data"
            )

            if not table_data:
                continue

            table_data = {
                "table_title": (
                    f"Table on page {page_number}"
                ),
                **table_data,
                "metadata": {
                    "source": "docling_local",
                    "table_index": decision[
                        "table_index"
                    ],
                },
            }

            candidate = self._build_candidate(
                table_data=table_data,
                page_number=page_number,
                source="docling_local",
            )

            attempts.append(
                self._attempt_summary(candidate)
            )

            if candidate["validation"]["is_valid"]:
                accepted_tables.append(
                    candidate["table_entry"]
                )

        if accepted_tables:
            return {
                "page_number": page_number,
                "route": "local_table_page",
                "status": "accepted",
                "attempts": attempts,
                "tables": accepted_tables,
            }

        print(
            f"Local extraction invalid on page "
            f"{page_number}; sending to page-review fallback."
        )

        return {
            "page_number": page_number,
            "route": "local_table_page",
            "status": "quarantined",
            "reason": (
                "Local table extraction failed quality validation. "
                "Use the original prospectus page for review."
            ),
            "attempts": attempts,
            "tables": [],
        }

    def _process_complex_page(
        self,
        page: dict[str, Any],
    ) -> dict[str, Any]:

        page_number = page["page_number"]

        print(
            f"Skipping expensive vision extraction "
            f"for complex page {page_number}; "
            f"sending to page-review fallback."
        )

        return {
            "page_number": page_number,
            "route": "complex_table_page",
            "status": "quarantined",
            "reason": (
                "Complex table extraction was skipped. "
                "Use the original prospectus page for review."
            ),
            "attempts": [],
            "tables": [],
        }

    def _retry_with_vision(
        self,
        page: dict[str, Any],
        attempts: list[dict[str, Any]],
        original_route: str,
    ) -> dict[str, Any]:

        page_number = page["page_number"]

        page_path = Path(
            page["metadata"]["page_path"]
        )

        image_path = self._render_table_crop(
            page_path=page_path,
            page_number=page_number,
        )

        layout = self.table_pipeline.analyze(
            image_path=image_path
        )

        selected_strategy = (
            self.table_pipeline.choose_strategy(
                layout=layout
            )
        )

        strategies = [
            selected_strategy,
            self._alternate_strategy(
                selected_strategy
            ),
        ]

        for strategy in strategies:

            print(
                f"Vision retry on page {page_number} "
                f"using {strategy}..."
            )

            candidate = self._run_vision_attempt(
                image_path=image_path,
                page_number=page_number,
                layout=layout,
                strategy=strategy,
            )

            attempts.append(
                self._attempt_summary(candidate)
            )

            if candidate[
                "validation"
            ]["is_valid"]:
                return {
                    "page_number": page_number,
                    "route": original_route,
                    "status": "accepted",
                    "image_path": str(image_path),
                    "layout": layout,
                    "strategy": strategy,
                    "attempts": attempts,
                    "tables": [
                        candidate["table_entry"]
                    ],
                }

        return {
            "page_number": page_number,
            "route": original_route,
            "status": "quarantined",
            "reason": (
                "Local extraction and all available "
                "vision strategies failed final "
                "quality validation."
            ),
            "attempts": attempts,
            "tables": [],
        }

    def _run_vision_attempt(
        self,
        image_path: Path,
        page_number: int,
        layout: dict[str, Any],
        strategy: str,
    ) -> dict[str, Any]:

        table_data = (
            self.table_pipeline.prepare_extraction(
                image_path=image_path,
                page_number=page_number,
                layout=layout,
                strategy=strategy,
            )
        )

        return self._build_candidate(
            table_data=table_data,
            page_number=page_number,
            source=strategy,
        )

    def _build_candidate(
        self,
        table_data: dict[str, Any],
        page_number: int,
        source: str,
    ) -> dict[str, Any]:

        extracted_table, chunks = (
            self.table_pipeline.process_extracted_data(
                table_data=table_data,
                page_number=page_number,
            )
        )

        validation = (
            self.quality_validator.validate(
                extracted_table
            )
        )

        return {
            "source": source,
            "validation": validation,
            "table_entry": {
                "table": extracted_table.model_dump(),
                "chunks": chunks,
                "quality_validation": validation,
            },
        }

    def _attempt_summary(
        self,
        candidate: dict[str, Any],
    ) -> dict[str, Any]:

        validation = candidate["validation"]

        return {
            "source": candidate["source"],
            "status": validation["status"],
            "is_valid": validation["is_valid"],
            "errors": validation["errors"],
            "warnings": validation["warnings"],
            "metrics": validation["metrics"],
        }

    def _alternate_strategy(
        self,
        strategy: str,
    ) -> str:

        if strategy == "adaptive_blocks":
            return "single"

        if strategy == "single":
            return "adaptive_blocks"

        raise ValueError(
            f"Unsupported extraction strategy: {strategy}"
        )

    def _render_table_crop(
        self,
        page_path: Path,
        page_number: int,
    ) -> Path:

        output_dir = (
            page_path.parent
            / "table_images"
            / "crops"
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        image_path = (
            output_dir
            / f"page_{page_number}_table.png"
        )

        if image_path.exists():
            return image_path

        result = self._get_table_detector().convert(
            page_path
        )

        document = result.document

        if not document.tables:
            raise ValueError(
                "Docling detected no table "
                "for table page."
            )

        table = document.tables[0]

        if not table.prov:
            raise ValueError(
                "Detected table has no bounding box."
            )

        bbox = table.prov[0].bbox

        pdf = fitz.open(page_path)

        try:
            pdf_page = pdf[0]
            page_height = pdf_page.rect.height

            clip = fitz.Rect(
                bbox.l,
                page_height - bbox.t,
                bbox.r,
                page_height - bbox.b,
            )

            padding = 8

            clip = fitz.Rect(
                max(
                    pdf_page.rect.x0,
                    clip.x0 - padding,
                ),
                max(
                    pdf_page.rect.y0,
                    clip.y0 - padding,
                ),
                min(
                    pdf_page.rect.x1,
                    clip.x1 + padding,
                ),
                min(
                    pdf_page.rect.y1,
                    clip.y1 + padding,
                ),
            )

            pixmap = pdf_page.get_pixmap(
                matrix=fitz.Matrix(3, 3),
                clip=clip,
                alpha=False,
            )

            pixmap.save(str(image_path))

        finally:
            pdf.close()

        return image_path

    def _load_checkpoint(
        self,
        output_path: Path,
    ) -> dict[str, Any]:

        if not output_path.exists():
            return {
                "pages": [],
                "metadata": {
                    "processed_page_numbers": [],
                    "failed_pages": [],
                    "quarantined_pages": [],
                },
            }

        checkpoint = json.loads(
            output_path.read_text(
                encoding="utf-8"
            )
        )

        checkpoint.setdefault("pages", [])

        metadata = checkpoint.setdefault(
            "metadata",
            {},
        )

        metadata.setdefault(
            "processed_page_numbers",
            [],
        )
        metadata.setdefault(
            "failed_pages",
            [],
        )
        metadata.setdefault(
            "quarantined_pages",
            [],
        )

        valid_pages = []
        valid_page_numbers = []
        invalid_page_numbers = []

        for page in checkpoint["pages"]:

            page_number = page.get("page_number")
            tables = page.get("tables", [])

            if not tables:
                invalid_page_numbers.append(
                    page_number
                )
                continue

            page_is_valid = True

            for entry in tables:

                try:
                    table = ExtractedTable.model_validate(
                        entry["table"]
                    )

                    validation = (
                        self.quality_validator.validate(
                            table
                        )
                    )

                    if (
                        validation.get("status")
                        == "invalid"
                    ):
                        page_is_valid = False
                        break

                except (
                    KeyError,
                    TypeError,
                    ValueError,
                ):
                    page_is_valid = False
                    break

            if page_is_valid:
                valid_pages.append(page)
                valid_page_numbers.append(
                    page_number
                )
            else:
                invalid_page_numbers.append(
                    page_number
                )

        checkpoint["pages"] = valid_pages

        metadata[
            "processed_page_numbers"
        ] = valid_page_numbers

        print(
            "Loaded table checkpoint:",
            len(valid_page_numbers),
            "valid pages retained.",
        )

        if invalid_page_numbers:
            print(
                "Invalid checkpoint pages "
                "returned to pending:",
                invalid_page_numbers,
            )

        return checkpoint

    def _save_checkpoint(
        self,
        result: dict[str, Any],
        output_path: Path,
    ) -> None:

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path.write_text(
            json.dumps(
                result,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
