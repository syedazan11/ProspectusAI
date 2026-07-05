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


class DocumentParser:

    def __init__(self):

        pipeline_options = PdfPipelineOptions()

        # OCR is only needed for scanned PDFs
        pipeline_options.do_ocr = False

        # Enable table detection
        pipeline_options.do_table_structure = True

        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(
                    pipeline_options=pipeline_options
                )
            }
        )

        self.splitter = PDFSplitter()

    def parse(
        self,
        pdf_path: Path,
        document_type: str,
    ) -> ParsedDocument:

        page_paths = self.splitter.split(pdf_path)

        parsed = ParsedDocument(
            document_type=document_type,
            total_pages=len(page_paths),
        )

        parsed.metadata["filename"] = pdf_path.name

        for page_number, page_path in enumerate(page_paths, start=1):

            print(f"Parsing Page {page_number}/{len(page_paths)}")

            result = self.converter.convert(page_path)

            document = result.document
            print("\n===== PAGE", page_number, "=====")
            print("Texts:", len(document.texts))
            print("Pictures:", len(document.pictures))
            print("Tables:", len(document.tables))

            for text in document.texts:
                print(text.text)

            raw_text = "\n".join(
                item.text
                for item in document.texts
                if hasattr(item, "text") and item.text.strip()
            )

            page = ParsedPage(
                page_number=page_number,
                markdown=raw_text,
                has_tables=len(document.tables) > 0,
                has_images=len(document.pictures) > 0,
            )

            parsed.pages.append(page)

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
        ) as f:

            json.dump(
                adapter.dump_python(
                    parsed,
                    mode="json",
                ),
                f,
                indent=4,
                ensure_ascii=False,
            )

        print("\n========== Parsing Summary ==========")
        print(f"Pages : {parsed.total_pages}")
        print(f"Saved : {output_path}")
        print("=====================================\n")

        return parsed