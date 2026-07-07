import json
from pathlib import Path

from pydantic import TypeAdapter

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import (
    DocumentConverter,
    PdfFormatOption,
)

from src.ingestion.pdf_splitter import PDFSplitter
from src.schemas.document import (
    ParsedDocument,
    ParsedPage,
)
from src.processing.table_quality_evaluator import (
    TableQualityEvaluator,
)


class DocumentParser:
    """
    Parses every PDF page exactly once with Docling.

    The same parsing pass provides:
    - page text
    - table detection
    - image detection
    - routing metadata

    Table extraction itself happens later.
    """

    def __init__(self):

        pipeline_options = PdfPipelineOptions()

        pipeline_options.do_ocr = True
        pipeline_options.do_table_structure = True

        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options
                )
            }
        )

        self.splitter = PDFSplitter()
        self.table_quality_evaluator = (
            TableQualityEvaluator()
        )

    def parse(
        self,
        pdf_path: Path,
        document_type: str,
    ) -> ParsedDocument:

        page_paths = self.splitter.split(pdf_path)

        output_path = (
            Path(__file__).resolve()
            .parents[3]
            / "storage"
            / "parsed"
            / f"{pdf_path.stem}.json"
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        adapter = TypeAdapter(ParsedDocument)

        if output_path.exists():
            parsed = adapter.validate_json(
                output_path.read_text(
                    encoding="utf-8"
                )
            )

            print(
                f"Resuming from checkpoint: "
                f"{len(parsed.pages)} pages completed."
            )
        else:
            parsed = ParsedDocument(
                document_type=document_type,
                total_pages=len(page_paths),
            )

            parsed.metadata["filename"] = pdf_path.name

        completed_pages = {
            page.page_number
            for page in parsed.pages
        }

        for page_number, page_path in enumerate(
            page_paths,
            start=1,
        ):
            if page_number in completed_pages:
                print(
                    f"Skipping page {page_number} "
                    "(checkpointed)."
                )
                continue

            print(
                f"Parsing page "
                f"{page_number}/{len(page_paths)}..."
            )

            result = self.converter.convert(
                page_path
            )

            document = result.document

            raw_text = "\n".join(
                item.text
                for item in document.texts
                if (
                    hasattr(item, "text")
                    and item.text.strip()
                )
            )

            table_count = len(document.tables)
            picture_count = len(document.pictures)

            table_decisions = []

            for table_index, table in enumerate(
                document.tables,
                start=1,
            ):
                try:
                    dataframe = table.export_to_dataframe(
                        doc=document
                    )

                    local_table_data = {
                        "columns": [
                            str(column)
                            for column in dataframe.columns
                        ],
                        "rows": dataframe.where(
                            dataframe.notna(),
                            None,
                        ).to_dict(
                            orient="records"
                        ),
                    }

                    quality = (
                        self.table_quality_evaluator.evaluate(
                            dataframe
                        )
                    )

                    decision = {
                        "table_index": table_index,
                        "action": quality["action"],
                        "usable": quality["usable"],
                        "reasons": quality["reasons"],
                        "metrics": quality["metrics"],
                    }

                    if quality["usable"]:
                        decision["local_table_data"] = (
                            local_table_data
                        )

                    table_decisions.append(decision)

                except Exception as error:
                    table_decisions.append(
                        {
                            "table_index": table_index,
                            "action": "escalate_to_vision",
                            "usable": False,
                            "reasons": [
                                "local_export_failed"
                            ],
                            "error": str(error),
                        }
                    )

            if table_count == 0:
                route = "text_page"

            elif any(
                decision["action"]
                == "escalate_to_vision"
                for decision in table_decisions
            ):
                route = "complex_table_page"

            else:
                route = "local_table_page"

            page = ParsedPage(
                page_number=page_number,
                markdown=raw_text,
                text=raw_text,
                has_tables=table_count > 0,
                has_images=picture_count > 0,
                metadata={
                    "page_path": str(page_path),
                    "table_count": table_count,
                    "picture_count": picture_count,
                    "route": route,
                    "table_decisions": table_decisions,
                },
            )

            parsed.pages.append(page)

            output_path.write_text(
                json.dumps(
                    adapter.dump_python(
                        parsed,
                        mode="json",
                    ),
                    indent=4,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            print(
                f"  route={route}"
                f" tables={table_count}"
                f" pictures={picture_count}"
                f" chars={len(raw_text)}"
            )

        output_path = (
            Path(__file__).resolve()
            .parents[3]
            / "storage"
            / "parsed"
            / f"{pdf_path.stem}.json"
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        adapter = TypeAdapter(ParsedDocument)

        with open(
            output_path,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                adapter.dump_python(
                    parsed,
                    mode="json",
                ),
                file,
                indent=4,
                ensure_ascii=False,
            )

        print("\n========== Parsing Summary ==========")
        print(f"Pages: {parsed.total_pages}")
        print(
            "Table pages:",
            sum(
                1
                for page in parsed.pages
                if page.has_tables
            ),
        )
        print(
            "Text-only pages:",
            sum(
                1
                for page in parsed.pages
                if not page.has_tables
            ),
        )
        print(f"Saved: {output_path}")
        print("=====================================\n")

        return parsed