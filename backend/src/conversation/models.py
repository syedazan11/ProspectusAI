from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.conversation.session import (
    ConversationSession,
)

class RequestType(str, Enum):

    GREETING = "greeting"

    GOODBYE = "goodbye"

    SYSTEM = "system"

    PROSPECTUS = "prospectus"

    IRRELEVANT = "irrelevant"

    GIBBERISH = "gibberish"

    UNKNOWN = "unknown"

    CONVERSATION = "conversation"


@dataclass(slots=True)
class ConversationState:

    session_id: str

    current_topic: str | None = None

    current_department: str | None = None

    current_programme: str | None = None

    current_document: str | None = None

    pending_question: str | None = None

    pending_context: dict[str, Any] | None = None

    chat_summary: str = ""

    user_facts: dict[str, str] = field(
        default_factory=dict,
    )

    recent_messages: list[dict] = field(
        default_factory=list,
    )


@dataclass(slots=True)
class ConversationRequest:

    original_query: str

    rewritten_query: str

    request_type: RequestType

    state: ConversationState

    requested_person_name: str | None = None

    confidence: float = 1.0

    needs_clarification: bool = False

    clarification_question: str | None = None

    is_follow_up: bool = False

    llm_reasoning: str | None = None

    admission_codes: list[str] = field(
        default_factory=list,
    )

    # The live, per-chat session (facts + prospectus context).
    # Optional so existing call sites that don't pass it keep working;
    # handlers that need session continuity (e.g. ConversationHandler)
    # read/write through this reference.
    session: ConversationSession | None = None
    pending_context: dict[str, Any] | None = None


@dataclass(slots=True)
class ConversationResponse:

    answer: str

    handled: bool = True

    sources: list[dict[str, Any]] = field(
        default_factory=list,
    )

    citations: list[str] = field(
        default_factory=list,
    )

    finished: bool = True

    