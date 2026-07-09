from pathlib import Path
import shutil

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from fastapi.security import (
    HTTPBasic,
    HTTPBasicCredentials,
)
from pydantic import BaseModel

from src.services.admin_auth_service import (
    AdminAuthService,
)
from src.services.document_manager import (
    DocumentManager,
)


router = APIRouter()

document_manager = DocumentManager()
admin_auth_service = AdminAuthService()

security = HTTPBasic()


class CreateAdminRequest(BaseModel):
    username: str
    password: str


def require_admin(
    credentials: HTTPBasicCredentials = Depends(
        security
    ),
) -> dict:

    admin = admin_auth_service.authenticate(
        username=credentials.username,
        password=credentials.password,
    )

    if admin is None:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail="Invalid admin credentials.",
            headers={
                "WWW-Authenticate": "Basic"
            },
        )

    return admin


@router.get("/me")
def get_current_admin(
    admin: dict = Depends(require_admin),
):
    return admin


@router.post("/admins")
def create_admin(
    request: CreateAdminRequest,
    current_admin: dict = Depends(
        require_admin
    ),
):

    try:
        admin = admin_auth_service.create_admin(
            username=request.username,
            password=request.password,
        )

    except ValueError as error:
        message = str(error)

        status_code = (
            409
            if (
                "Maximum of 2 admins"
                in message
                or "already exists"
                in message
            )
            else 400
        )

        raise HTTPException(
            status_code=status_code,
            detail=message,
        ) from error

    return {
        "message": "Admin created successfully.",
        "admin": admin,
        "created_by": current_admin["username"],
    }


@router.delete("/admins/{admin_id}")
def delete_admin(
    admin_id: str,
    current_admin: dict = Depends(
        require_admin
    ),
):

    if admin_id == current_admin["id"]:
        raise HTTPException(
            status_code=400,
            detail=(
                "You cannot delete your own "
                "admin account."
            ),
        )

    try:
        deleted = (
            admin_auth_service.delete_admin(
                admin_id=admin_id
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Admin not found.",
        )

    return {
        "message": "Admin deleted successfully.",
    }


@router.post("/documents/upload")
def upload_document(
    year: int = Form(...),
    official_url: str = Form(...),
    file: UploadFile = File(...),
    admin: dict = Depends(require_admin),
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

    official_url = official_url.strip()

    if not official_url.startswith(
        ("https://", "http://")
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "A valid official prospectus URL "
                "is required."
            ),
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
                official_url=official_url,
                status="uploaded",
            )
        )

        from src.services.document_processing_service import (
            DocumentProcessingService,
        )

        processor = DocumentProcessingService()

        result = processor.process(
            document_id=entry["document_id"],
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        ) from error

    finally:
        file.file.close()

    return {
        "message": (
            "Prospectus uploaded and processed "
            "successfully."
        ),
        "uploaded_by": admin["username"],
        "document": entry,
        "result": result,
    }


@router.post("/documents/{document_id}/process")
def process_document(
    document_id: str,
    admin: dict = Depends(require_admin),
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
        "message": (
            "Prospectus processed successfully."
        ),
        "processed_by": admin["username"],
        "result": result,
    }
