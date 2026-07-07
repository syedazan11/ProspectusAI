from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from src.schemas.chat import ChatRequest, ChatResponse
from src.generation.answer_generator import AnswerGenerator
from src.services.document_manager import DocumentManager


router = APIRouter()

document_manager = DocumentManager()

_answer_generator = None
_loaded_document_id = None


def get_answer_generator() -> AnswerGenerator:
    """
    Return an AnswerGenerator for the active prospectus.

    The generator is rebuilt automatically whenever
    the active document changes.
    """

    global _answer_generator
    global _loaded_document_id

    document_id = (
        document_manager.get_active_document_id()
    )

    if (
        _answer_generator is None
        or _loaded_document_id != document_id
    ):
        _answer_generator = AnswerGenerator(
            graph_path=(
                document_manager.get_graph_path(
                    document_id
                )
            ),
        )

        _loaded_document_id = document_id

    return _answer_generator


@router.post(
    "/chat",
    response_model=ChatResponse,
)
def chat(request: ChatRequest):

    answer_generator = get_answer_generator()

    result = answer_generator.answer(
        question=request.question,
        vector_top_k=5,
        graph_top_k=5,
    )

    return ChatResponse(
        answer=result["answer"],
        status=result["status"],
        sources=result["sources"],
        page_references=result["page_references"],
    )



@router.get("/pages/{document}/{page_number}")
def get_page(
    document: str,
    page_number: int,
):

    if not document.replace(
        "_",
        "",
    ).replace(
        "-",
        "",
    ).isalnum():
        raise HTTPException(
            status_code=400,
            detail="Invalid document name.",
        )

    if page_number < 1:
        raise HTTPException(
            status_code=400,
            detail="Invalid page number.",
        )

    page_path = (
        document_manager.get_pages_dir(document)
        / f"page_{page_number}.pdf"
    )

    if not page_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Page not found.",
        )

    return FileResponse(
        path=page_path,
        media_type="application/pdf",
        filename=(
            f"{document}_page_{page_number}.pdf"
        ),
    )
