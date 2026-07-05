from pathlib import Path
import pypdfium2 as pdfium


PDF_PATH = Path(
    r"C:\Users\syyea\Projects\ProspectusAI\storage\uploads\testingnedprospect.pdf"
)

OUTPUT_PATH = Path(
    "experiments/table_extraction/page_2.png"
)


pdf = pdfium.PdfDocument(PDF_PATH)

# PDFium uses 0-based indexing:
# index 1 = actual PDF page 2
page = pdf[1]

# 3x scale ≈ 216 DPI
bitmap = page.render(scale=3)

image = bitmap.to_pil()
# Rotate the page so the table is horizontal
image = image.rotate(-90, expand=True)
image.save(OUTPUT_PATH)

print(f"Saved: {OUTPUT_PATH}")
print(f"Image size: {image.size}")