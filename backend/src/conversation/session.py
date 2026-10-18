from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


# ============================================================
# Prospectus Conversation Context
# ============================================================

class ConversationTopic(str, Enum):

    GENERAL = "general"

    PEOPLE = "people"

    FEES = "fees"

    ADMISSION = "admission"

    CURRICULUM = "curriculum"

    HOSTEL = "hostel"

    SCHOLARSHIP = "scholarship"


@dataclass(slots=True)
class ProspectusContext:

    topic: ConversationTopic | None = None

    department: str | None = None

    programme: str | None = None

    admission_code: str | None = None

    person_name: str | None = None

    person_role: str | None = None

    study_year: str | None = None

    semester: str | None = None

    curriculum_programme: str | None = None

    curriculum_year: str | None = None

    curriculum_semester: str | None = None

    fee_type: str | None = None

    def update(
        self,
        **fields: str | ConversationTopic | None,
    ) -> None:

        for name, value in fields.items():

            if name not in self.__dataclass_fields__:
                raise AttributeError(
                    f"Unknown field '{name}'."
                )

            if value is None:
                continue

            if (
                isinstance(value, str)
                and not value.strip()
            ):
                continue

            setattr(
                self,
                name,
                value,
            )

    def clear(
        self,
    ) -> None:

        for field_name in self.__dataclass_fields__:

            setattr(
                self,
                field_name,
                None,
            )


# ============================================================
# Short-Term Conversation Memory
# ============================================================

MAX_RECENT_MESSAGES = 20


@dataclass(slots=True)
class ConversationSession:
    """
    In-memory state for one chat.

    The session has two separate responsibilities:

    1. ProspectusContext:
       Structured context used by QueryInterpreter for
       prospectus follow-up questions.

    2. messages:
       The latest 20 user/assistant messages used as
       short-term conversational memory for the LLM.
    """

    session_id: str

    context: ProspectusContext = field(
        default_factory=ProspectusContext,
    )

    messages: list[dict[str, str]] = field(
        default_factory=list,
    )

    def add_message(
        self,
        role: str,
        content: str,
        curriculum_route: dict | None = None,
    ) -> None:
        """
        Add one user or assistant message.

        Only the latest MAX_RECENT_MESSAGES messages
        are retained.
        """

        if not content.strip():
            return

        # self.messages.append(
        #     {
        #         "role": role,
        #         "content": content,
        #     }
        # )
        message = {
            "role": role,
            "content": content,
        }

        if curriculum_route is not None:
            message["curriculum_route"] = curriculum_route

        self.messages.append(message)

        if len(self.messages) > MAX_RECENT_MESSAGES:

            self.messages = self.messages[
                -MAX_RECENT_MESSAGES:
            ]

    def add_turn(
        self,
        role: str,
        content: str,
        curriculum_route: dict | None = None,
    ) -> None:
        """
        Compatibility wrapper for existing code.

        A turn is simply stored as a message.
        """

        self.add_message(
            role,
            content,
            curriculum_route,
        )

    def get_messages(
        self,
    ) -> list[dict[str, str]]:
        """
        Return the current short-term conversation history.
        """

        return list(self.messages)

    @property
    def recent_turns(
        self,
    ) -> list[dict[str, str]]:
        """
        Compatibility view for existing code.

        Messages are the single source of truth.
        """

        return self.messages

    def reset(
        self,
    ) -> None:
        """
        Clear both prospectus context and short-term
        conversation memory.
        """

        self.context.clear()

        self.messages.clear()