from __future__ import annotations

from requests import request

from src.conversation.models import (
    ConversationRequest,
    ConversationResponse,
    ConversationState,
    RequestType,
)
from src.conversation.session import (
    ConversationSession,
    ConversationTopic,
)

from src.conversation.classifier import (
    Classifier,
)

from src.conversation.query_interpreter import (
    QueryInterpreter,
)

from src.conversation.router import (
    ConversationRouter,
)

from src.conversation.person_matcher import PersonMatcher
from src.retrieval.planner import RetrievalPlanner
from src.retrieval.models import RetrievalIntent

class ConversationManager:

    def __init__(
        self,
    ) -> None:

        self._people_records = []

        self._classifier = (
            Classifier()
        )

        self._interpreter = (
            QueryInterpreter()
        )

        self._router = (
            ConversationRouter()
        )

    def set_people_records(
        self,
        people_records: list[dict],
    ) -> None:

        self._people_records = people_records

    def commit_prospectus_context(
        self,
        request: ConversationRequest,
        session: ConversationSession,
    ) -> None:

        self._interpreter.commit_pending_context(
            request,
            session,
        )

    def process(
        self,
        query: str,
        state: ConversationState,
        session: ConversationSession,
    ) -> ConversationResponse | dict:

        # --------------------------------------------------------
        # Store the user's message in this chat's in-memory
        # conversation history.
        #
        # ConversationSession keeps only the latest 20 messages.
        # --------------------------------------------------------

        # session.add_message(
        #     role="user",
        #     content=query,
        # )

        # --------------------------------------------------------
        # FIRST PASS
        #
        # Cheap deterministic classification.
        #
        # Known simple request types continue through the existing
        # handlers without involving the LLM.
        # --------------------------------------------------------

        request_type = (
            self._classifier.classify(
                query,
            )
        )
        print(
            f"[MANAGER] query={query!r} "
            f"classified={request_type}"
        )

        person_status = "none"
        person_matches = []

        # if request_type == RequestType.UNKNOWN:
        #     person_status, person_matches = (
        #         PersonMatcher.match_status(
        #             query,
        #             self._people_records,
        #         )
        #     )
        if request_type == RequestType.UNKNOWN:
            if PersonMatcher.is_person_query(query):
                person_status, person_matches = (
                    PersonMatcher.match_status(
                        query,
                        self._people_records,
                    )
                )
            else:
                person_status, person_matches = (
                    PersonMatcher.partial_name_status(
                        query,
                        self._people_records,
                    )
                )
        retrieval_plan = None

        if (
            request_type == RequestType.UNKNOWN
            and person_status == "none"
        ):
            retrieval_plan = RetrievalPlanner.plan(query)

        request = ConversationRequest(
            original_query=query,
            rewritten_query=query,
            request_type=request_type,
            state=state,
            session=session,
        )

        if person_status == "unique":
            request.request_type = RequestType.PROSPECTUS
            request.rewritten_query = person_matches[0].name

            session.context.update(
                topic=ConversationTopic.PEOPLE,
                person_name=person_matches[0].name,
            )

        elif person_status == "ambiguous":
            names = [
                match.name
                for match in person_matches[:5]
            ]

        if (
            request_type == RequestType.UNKNOWN
            and person_status == "none"
        ):
            if retrieval_plan is None:
                retrieval_plan = RetrievalPlanner.plan(query)

            requested_name = PersonMatcher.extract_requested_name(
                query,
                people_intent=(
                    retrieval_plan.intent == RetrievalIntent.PEOPLE
                ),
            )

            if requested_name is not None:
                request.requested_person_name = requested_name
                request.request_type = RequestType.PROSPECTUS

            # request.request_type = RequestType.PROSPECTUS
            # request.needs_clarification = True
            # request.clarification_question = (
            #     "I found multiple people matching "
            #     f"your query, can you please specify which one you mean: {', '.join(names)}. "
            #     "Which person do you mean?"
            # )

        # elif (
        #     request_type == RequestType.UNKNOWN
        #     and PersonMatcher.is_person_query(query)
        # ):
        #     request.request_type = RequestType.PROSPECTUS

        if state.pending_context:
            request.pending_context = dict(
                state.pending_context
            )

        # --------------------------------------------------------
        # Known request
        #
        # Greeting, goodbye, system, irrelevant and gibberish
        # continue through their existing handlers.
        #
        # Curriculum routing remains inside ConversationRouter.
        # --------------------------------------------------------

        # if request_type != RequestType.UNKNOWN:
        if request.request_type != RequestType.UNKNOWN:

            response = self._router.route(
                request,
            )

            self._record_turn(
                response,
                session,
            )

            return response

        # --------------------------------------------------------
        # UNKNOWN
        #
        # The deterministic classifier did not recognise this
        # message.
        #
        # Give the QueryInterpreter the current session so the LLM
        # can see the latest 20 messages and understand the query
        # in conversation context.
        # --------------------------------------------------------

        ###changes at 13/10

        request = self._interpreter.interpret(
            request=request,
            session=session,
        )
        self._interpreter.commit_pending_context(
            request,
            session,
        )
        if request.needs_clarification:
            state.pending_context = request.pending_context

        # request = self._interpreter.interpret(
        #     request=request,
        #     session=session,
        # )
        # if request.needs_clarification:
        #     state.pending_context = request.pending_context

        # --------------------------------------------------------
        # The interpreter now decides what UNKNOWN actually is:
        #
        # conversation
        # prospectus
        # irrelevant
        # greeting
        # goodbye
        # system
        # gibberish
        #
        # ConversationRouter handles the resulting type.
        #
        # Curriculum routing remains untouched inside the router.
        # --------------------------------------------------------

        response = self._router.route(
            request,
        )

        self._record_turn(
            response,
            session,
        )

        return response

    @staticmethod
    def _record_turn(
        response: ConversationResponse | dict,
        session: ConversationSession,
    ) -> None:

        if isinstance(
            response,
            ConversationResponse,
        ):

            session.add_message(
                role="assistant",
                content=response.answer,
            )