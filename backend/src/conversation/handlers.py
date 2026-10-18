from __future__ import annotations

from src.conversation.models import (
    ConversationRequest,
    ConversationResponse,
)

from src.llm.llm_service import (
    LLMService,
)




class BaseHandler:
    """
    Common interface for all conversation handlers.

    Every handler receives a ConversationRequest
    and returns a ConversationResponse.
    """

    def handle(
        self,
        request: ConversationRequest,
    ) -> ConversationResponse:

        raise NotImplementedError(
            f"{self.__class__.__name__} must implement handle()."
        )


class GreetingHandler(
    BaseHandler,
):

    RESPONSE = (

        "HI! I'm NED ProspectusAI, your assistant for the university undergraduate prospectus.\n"
        "I can help you with: "
        "Admissions, "
        "Eligibility criteria, "
        "Departments and programmes, "
        "Curriculum, "
        "Fees, "
        "Seat distribution, "
        "Scholarships, "
        "Hostel information \n\n"
        "What would you like to know?"
    )

    def handle(
        self,
        request: ConversationRequest,
    ) -> ConversationResponse:

        return ConversationResponse(
            answer=self.RESPONSE,
        )


class GoodbyeHandler(
    BaseHandler,
):

    RESPONSE = (
        "You're welcome! 😊\n\n"
        "I hope I was able to help.\n\n"
        "If you have any more questions about the university "
        "undergraduate prospectus, feel free to ask anytime.\n\n"
        "Take care. Allah Hafiz! 👋"
    )

    def handle(
        self,
        request: ConversationRequest,
    ) -> ConversationResponse:

        return ConversationResponse(
            answer=self.RESPONSE,
        )


class SystemHandler(
    BaseHandler,
):

    RESPONSE = (
        "I'm NED ProspectusAI, an AI assistant designed to help you "
        "navigate the NED University's undergraduate prospectus.\n\n"

        "I can help you with:\n"
        "Admissions, "
        "Eligibility criteria, "
        "Departments and programmes, "
        "Curriculum, "
        "Fees, "
        "Seat distribution, "
        "Scholarships, "
        "Hostel information, "
        "Academic rules and regulations\n\n"

        "Simply ask your question naturally, and I'll do my best "
        "to find the relevant information from the prospectus."
    )

    def handle(
        self,
        request: ConversationRequest,
    ) -> ConversationResponse:

        return ConversationResponse(
            answer=self.RESPONSE,
        )


class IrrelevantHandler(
    BaseHandler,
):

    RESPONSE = (
        "I can only help with questions related to the university "
        "undergraduate prospectus.\n\n"

        "For example, you can ask me about:\n"
        "Admissions, "
        "Eligibility criteria, "
        "Departments and programmes, "
        "Curriculum, "
        "Fees, "
        "Seat distribution, "
        "Scholarships, "
        "Hostel information \n\n"

        "Please ask a question related to the undergraduate prospectus."
    )

    def handle(
        self,
        request: ConversationRequest,
    ) -> ConversationResponse:

        return ConversationResponse(
            answer=self.RESPONSE,
        )


class GibberishHandler(
    BaseHandler,
):

    DEFAULT_RESPONSE = (
        "I'm sorry, but I couldn't understand your question.\n\n"
        "Could you please rephrase it or provide a little more detail?"
    )

    def handle(
        self,
        request: ConversationRequest,
    ) -> ConversationResponse:

        response = (
            request.clarification_question
            or self.DEFAULT_RESPONSE
        )

        return ConversationResponse(
            answer=response,
        )

class ClarificationHandler(
    BaseHandler,
):

    DEFAULT_RESPONSE = (
        "Could you please clarify your question?"
    )

    def handle(
        self,
        request: ConversationRequest,
    ) -> ConversationResponse:

        return ConversationResponse(
            answer=(
                request.clarification_question
                or self.DEFAULT_RESPONSE
            ),
        )


class ProspectusHandler(
    BaseHandler,
):

    def __init__(
        self,
    ) -> None:

        pass

    def handle(
        self,
        request: ConversationRequest,
    ):

        return request


class ConversationHandler(
    BaseHandler,
):
    """
    Handles requests classified as CONVERSATION.

    Conversation context comes entirely from the current
    ConversationSession. The latest 20 messages are passed
    to the conversation LLM.

    No factual extraction or hardcoded personal-information
    handling is performed here.
    """

    def __init__(
        self,
    ) -> None:


        self._llm = LLMService()

    def handle(
        self,
        request: ConversationRequest,
    ) -> ConversationResponse:

        session = request.session

        if session is None:

            return ConversationResponse(
                answer=(
                    "I don't have any conversation history "
                    "available for this chat."
                ),
            )

        messages = session.get_messages()

        answer = self._llm.generate_conversation(
            messages=messages,
        )

        return ConversationResponse(
            answer=answer.strip(),
        )