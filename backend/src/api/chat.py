from fastapi import APIRouter

from src.schemas.chat import ChatRequest, ChatResponse
from src.retrieval.retriever import Retriever
from src.retrieval.context_builder import ContextBuilder
from src.llm.llm_service import LLMService


router = APIRouter()

retriever = Retriever()
context_builder = ContextBuilder()
llm_service = LLMService()


@router.post(
    "/chat",
    response_model=ChatResponse,
)
def chat(request: ChatRequest):

    chunks = retriever.retrieve(
        query=request.question,
        top_k=5,
    )

    context = context_builder.build(chunks)

    answer = llm_service.generate_answer(
        question=request.question,
        context=context,
    )

    return ChatResponse(
        answer=answer,
    )