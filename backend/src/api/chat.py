from functools import lru_cache
import json


from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import StreamingResponse

from src.generation.answer_service import RescueAnswerService
from src.services.chat_history_service import ChatHistoryService
from src.services.document_manager import DocumentManager


router = APIRouter()

document_manager = DocumentManager()
chat_service = ChatHistoryService()


def get_chat_owner_id(
    x_chat_owner_id: str | None,
) -> str:

    owner_id = (
        x_chat_owner_id or ""
    ).strip()

    if not owner_id:
        raise HTTPException(
            status_code=400,
            detail="X-Chat-Owner-ID is required.",
        )

    if len(owner_id) > 100:
        raise HTTPException(
            status_code=400,
            detail="Invalid chat owner ID.",
        )

    return owner_id


@lru_cache(maxsize=2)
def get_answer_service(
    document_id: str,
    collection_name: str,
) -> RescueAnswerService:

    return RescueAnswerService(
        collection_name=collection_name,
    )


def load_answer_service() -> RescueAnswerService:

    active_document = (
        document_manager.get_active_document()
    )

    collection_name = active_document.get(
        "collection_name"
    )

    if not collection_name:
        raise HTTPException(
            status_code=503,
            detail=(
                "Active prospectus has no "
                "Qdrant collection configured."
            ),
        )

    return get_answer_service(
        active_document["document_id"],
        collection_name,
    )


@router.get("/chats")
def list_chats(
    x_chat_owner_id: str | None = Header(
        default=None
    ),
):

    owner_id = get_chat_owner_id(
        x_chat_owner_id
    )

    return {
        "chats": chat_service.list_chats(
            browser_id=owner_id,
        )
    }


@router.post("/chats")
def create_chat(
    x_chat_owner_id: str | None = Header(
        default=None
    ),
):

    owner_id = get_chat_owner_id(
        x_chat_owner_id
    )

    return chat_service.create_chat(
        browser_id=owner_id,
    )


@router.get("/chats/{chat_id}/messages")
def get_messages(
    chat_id: str,
    x_chat_owner_id: str | None = Header(
        default=None
    ),
):

    owner_id = get_chat_owner_id(
        x_chat_owner_id
    )

    chat = chat_service.get_chat(
        browser_id=owner_id,
        chat_id=chat_id,
    )

    if chat is None:
        raise HTTPException(
            status_code=404,
            detail="Chat not found.",
        )

    return {
        "messages": chat_service.get_messages(
            browser_id=owner_id,
            chat_id=chat_id,
        )
    }


@router.post("/chats/{chat_id}/messages/stream")
def send_message_stream(
    chat_id: str,
    payload: dict,
    x_chat_owner_id: str | None = Header(
        default=None
    ),
):

    owner_id = get_chat_owner_id(
        x_chat_owner_id
    )

    question = str(
        payload.get("question", "")
    ).strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    chat = chat_service.get_chat(
        browser_id=owner_id,
        chat_id=chat_id,
    )

    if chat is None:
        raise HTTPException(
            status_code=404,
            detail="Chat not found.",
        )

    conversation_history = (
        chat_service.get_messages(
            browser_id=owner_id,
            chat_id=chat_id,
        )
    )[-6:]

    chat_service.add_message(
        browser_id=owner_id,
        chat_id=chat_id,
        role="user",
        content=question,
    )

    if chat["title"] == "New Chat":
        chat_service.update_title(
            browser_id=owner_id,
            chat_id=chat_id,
            title=question,
        )

    answer_service = load_answer_service()

    def event_stream():

        try:
            for event in answer_service.stream_answer(
                question=question,
                top_k=8,
                conversation_history=(
                    conversation_history
                ),
            ):

                if event["type"] == "done":
                    result = event["result"]

                    assistant_message = (
                        chat_service.add_message(
                            browser_id=owner_id,
                            chat_id=chat_id,
                            role="assistant",
                            content=result["answer"],
                            sources=result.get(
                                "sources",
                                [],
                            ),
                            page_references=result.get(
                                "page_references",
                                [],
                            ),
                            curriculum_route=result.get(
                                "curriculum_route",
                                {},
                            ),
                        )
                    )

                    event = {
                        "type": "done",
                        "answer": result["answer"],
                        "status": result["status"],
                        "sources": result.get(
                            "sources",
                            [],
                        ),
                        "page_references": result.get(
                            "page_references",
                            [],
                        ),
                        "message": assistant_message,
                    }

                yield json.dumps(
                    event,
                    ensure_ascii=False,
                ) + "\n"

        except Exception as exc:
            yield json.dumps(
                {
                    "type": "error",
                    "message": str(exc),
                },
                ensure_ascii=False,
            ) + "\n"

    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/chats/{chat_id}/messages")
def send_message(
    chat_id: str,
    payload: dict,
    x_chat_owner_id: str | None = Header(
        default=None
    ),
):

    owner_id = get_chat_owner_id(
        x_chat_owner_id
    )

    question = str(
        payload.get("question", "")
    ).strip()

    if not question:
        raise HTTPException(
            status_code=400,
            detail="Question cannot be empty.",
        )

    chat = chat_service.get_chat(
        browser_id=owner_id,
        chat_id=chat_id,
    )

    if chat is None:
        raise HTTPException(
            status_code=404,
            detail="Chat not found.",
        )

    conversation_history = (
        chat_service.get_messages(
            browser_id=owner_id,
            chat_id=chat_id,
        )
    )[-6:]

    chat_service.add_message(
        browser_id=owner_id,
        chat_id=chat_id,
        role="user",
        content=question,
    )

    if chat["title"] == "New Chat":

        chat_service.update_title(
            browser_id=owner_id,
            chat_id=chat_id,
            title=question,
        )

    answer_service = load_answer_service()

    result = answer_service.answer(
        question=question,
        top_k=8,
        conversation_history=(
            conversation_history
        ),
    )

    assistant_message = (
        chat_service.add_message(
            browser_id=owner_id,
            chat_id=chat_id,
            role="assistant",
            content=result["answer"],
            sources=result.get(
                "sources",
                [],
            ),
            page_references=result.get(
                "page_references",
                [],
            ),
            curriculum_route=result.get(
                "curriculum_route",
                {},
            ),
        )
    )

    return {
        "answer": result["answer"],
        "status": result["status"],
        "sources": result.get(
            "sources",
            [],
        ),
        "page_references": result.get(
            "page_references",
            [],
        ),
        "message": assistant_message,
    }


@router.patch("/chats/{chat_id}")
def rename_chat(
    chat_id: str,
    payload: dict,
    x_chat_owner_id: str | None = Header(
        default=None
    ),
):

    owner_id = get_chat_owner_id(
        x_chat_owner_id
    )

    title = str(
        payload.get("title", "")
    ).strip()

    try:
        chat_service.update_title(
            browser_id=owner_id,
            chat_id=chat_id,
            title=title,
        )

    except PermissionError as error:
        raise HTTPException(
            status_code=404,
            detail="Chat not found.",
        ) from error

    return {"message": "Chat renamed."}


@router.delete("/chats/{chat_id}")
def delete_chat(
    chat_id: str,
    x_chat_owner_id: str | None = Header(
        default=None
    ),
):

    owner_id = get_chat_owner_id(
        x_chat_owner_id
    )

    deleted = chat_service.delete_chat(
        browser_id=owner_id,
        chat_id=chat_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Chat not found.",
        )

    return {"message": "Chat deleted."}

