from __future__ import annotations

from src.conversation.models import (
    ConversationRequest,
    ConversationResponse,
    RequestType,
)

from src.conversation.handlers import (
    GreetingHandler,
    GoodbyeHandler,
    SystemHandler,
    IrrelevantHandler,
    GibberishHandler,
    ClarificationHandler,
    ProspectusHandler,
    ConversationHandler,
)

from src.generation.answer_service import (
    RescueAnswerService,
)
from src.retrieval.curriculum_question_router import (
    CurriculumQuestionRouter,
)

class ConversationRouter:

    def __init__(
        self,
    ) -> None:
        self._handlers = {

            RequestType.GREETING:
                GreetingHandler(),

            RequestType.GOODBYE:
                GoodbyeHandler(),

            RequestType.SYSTEM:
                SystemHandler(),

            RequestType.IRRELEVANT:
                IrrelevantHandler(),

            RequestType.GIBBERISH:
                GibberishHandler(),

            RequestType.PROSPECTUS:
                ProspectusHandler(),

            RequestType.CONVERSATION:
                ConversationHandler(),
        
        }

        self._clarification_handler = (
            ClarificationHandler()
        )
        self._curriculum_router = (
            CurriculumQuestionRouter()
        )

    def route(
        self,
        request: ConversationRequest,
    ) -> ConversationResponse | dict:

        if request.request_type == RequestType.CONVERSATION:

            curriculum_route = (
                self._curriculum_router.route(
                    question=request.original_query,
                )
            )

            if curriculum_route is not None:

                request.request_type = (
                    RequestType.PROSPECTUS
                )

        if request.needs_clarification:

            return self._clarification_handler.handle(
                request,
            )

        handler = self._handlers.get(
            request.request_type,
        )

        if handler is None:

            return ConversationResponse(
                answer=(
                    "I couldn't process your request."
                ),
            )

        return handler.handle(
            request,
        )

