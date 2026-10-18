from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.database.database import SessionLocal, engine
from sqlalchemy import text
from src.api.chat import router as chat_router
from src.api.admin import router as admin_router
from contextlib import asynccontextmanager

from src.api.chat import get_answer_service
from src.services.document_manager import DocumentManager

@asynccontextmanager
async def lifespan(app: FastAPI):

    print("[WARMUP] Warming database connection pool...")

    try:
        connections = []

        for _ in range(5):
            connection = engine.connect()
            connection.execute(text("SELECT 1"))
            connections.append(connection)

        for connection in connections:
            connection.close()

        print("[WARMUP] Database connection pool ready.")

    except Exception as exc:
        print(
            f"[WARMUP] Database connection pool warmup failed: "
            f"{exc}"
        )

    document_manager = DocumentManager()

    try:
        active_document = (
            document_manager.get_active_document()
        )

        if active_document:
            document_id = active_document.get(
                "document_id"
            )

            collection_name = active_document.get(
                "collection_name"
            )

            if document_id and collection_name:

                print(
                    "[WARMUP] Building BM25 cache..."
                )

                answer_service = (
                    get_answer_service(
                        document_id,
                        collection_name,
                    )
                )

                answer_service.retriever._build_bm25_index()

                print(
                    "[WARMUP] BM25 cache ready."
                )

    except Exception as exc:

        print(
            f"[WARMUP] Failed: {exc}"
        )

    yield


app = FastAPI(
    title="ProspectusAI",
    lifespan=lifespan,
)

# app = FastAPI(title="ProspectusAI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(
    chat_router,
    prefix="/api/v1",
    tags=["Chat"],
)

app.include_router(
    admin_router,
    prefix="/api/v1/admin",
    tags=["Admin"],
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

    from src.services.document_manager import DocumentManager

    document_manager = DocumentManager()

    document_id = (
        document_manager.get_active_document_id()
    )

    pdf_path = (
        document_manager.get_upload_path(
            document_id
        )
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