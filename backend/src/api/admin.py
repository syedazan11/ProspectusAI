from pathlib import Path
import shutil

from fastapi import (
    APIRouter,
    File,
    Form,
    HTTPException,
    UploadFile,
)

from src.services.document_manager import DocumentManager


router = APIRouter()

document_manager = DocumentManager()


@router.post("/documents/upload")
def upload_document(
    year: int = Form(...),
    file: UploadFile = File(...),
):

    filename = Path(
        file.filename or ""
    ).name

    if not filename:
        raise HTTPException(
            status_code=400,
            detail="A filename is required.",
        )

    if Path(filename).suffix.lower() != ".pdf":
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed.",
        )

    if year < 2000 or year > 2100:
        raise HTTPException(
            status_code=400,
            detail="Invalid prospectus year.",
        )

    uploads_dir = (
        document_manager.storage_dir
        / "uploads"
    )

    uploads_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    pdf_path = uploads_dir / filename

    try:
        with pdf_path.open("wb") as output:
            shutil.copyfileobj(
                file.file,
                output,
            )

        entry = (
            document_manager.register_document(
                pdf_path=pdf_path,
                year=year,
                status="uploaded",
            )
        )

    except Exception:
        if pdf_path.exists():
            pdf_path.unlink()

        raise

    finally:
        file.file.close()

    return {
        "message": "Prospectus uploaded successfully.",
        "document": entry,
    }


@router.post("/documents/{document_id}/process")
def process_document(
    document_id: str,
):

    from src.services.document_processing_service import (
        DocumentProcessingService,
    )

    processor = DocumentProcessingService()

    try:
        result = processor.process(
            document_id=document_id,
        )

    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail=str(error),
        ) from error

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error

    return {
        "message": "Prospectus processed successfully.",
        "result": result,
    }
