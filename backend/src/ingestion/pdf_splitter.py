from pathlib import Path

import fitz


class PDFSplitter:
    """
    Splits a PDF into individual page PDFs
    and stores them in storage/pages.
    """

    def split(self, pdf_path: Path) -> list[Path]:

        document = fitz.open(pdf_path)

        project_root = Path(__file__).resolve().parents[3]

        pages_dir = project_root / "storage" / "pages"

        pages_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        # Remove old pages
        for file in pages_dir.glob("page_*.pdf"):
            file.unlink()

        page_paths = []

        for page_number in range(len(document)):

            single_page = fitz.open()

            single_page.insert_pdf(
                document,
                from_page=page_number,
                to_page=page_number,
            )

            output_path = pages_dir / f"page_{page_number + 1}.pdf"

            single_page.save(output_path)

            single_page.close()

            page_paths.append(output_path)

        document.close()

        print(f"\nSaved {len(page_paths)} pages to:")
        print(pages_dir)

        return page_paths