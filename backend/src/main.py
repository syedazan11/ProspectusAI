from pathlib import Path

from fastapi import FastAPI


from src.api.chat import router as chat_router

app = FastAPI(title="ProspectusAI")
app.include_router(
    chat_router,
    prefix="/api/v1",
    tags=["Chat"],
)


@app.get("/")
def home():
    return {"message": "ProspectusAI API Running"}

@app.post("/parse")
def parse_document():
    from src.ingestion.loader import DocumentLoader
    from src.ingestion.document_classifier import DocumentClassifier
    from src.ingestion.parser import DocumentParser
    from src.processing.cleaner import DocumentCleaner
    from src.processing.chunker import DocumentChunker

    loader = DocumentLoader()
    classifier = DocumentClassifier()
    parser = DocumentParser()
    cleaner = DocumentCleaner()
    chunker = DocumentChunker()

    pdf_path = Path(
        r"C:\Users\syyea\Projects\ProspectusAI\storage\uploads\testingnedprospect.pdf"
    )

    pdf = loader.validate(pdf_path)

    classification = classifier.classify(pdf)

    parsed = parser.parse(
        pdf,
        classification["document_type"],
    )

    parsed_json = (
        Path(__file__).resolve().parents[2]
        / "storage"
        / "parsed"
        / f"{pdf.stem}.json"
)

    cleaned = cleaner.clean(parsed_json)
    cleaned_json = (
        Path(__file__).resolve().parents[2]
        / "storage"
        / "cleaned"
        / f"{pdf.stem}.json"
    )

    chunks = chunker.chunk(cleaned_json)

    return {
        "document_type": cleaned["document_type"],
        "pages": cleaned["total_pages"],
        "metadata": cleaned["metadata"],
        "parent_chunks": len(chunks["parent_chunks"]),
        "child_chunks": len(chunks["child_chunks"]),

    }