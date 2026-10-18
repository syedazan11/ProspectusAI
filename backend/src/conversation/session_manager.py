from __future__ import annotations

from src.conversation.session import (
    ConversationSession,
)


class SessionManager:
    """
    Manages all active conversation sessions.

    Each conversation has exactly one
    ConversationSession.
    """

    def __init__(
        self,
    ) -> None:

        self._sessions: dict[
            str,
            ConversationSession,
        ] = {}

    def get_session(
        self,
        conversation_id: str,
    ) -> ConversationSession:

        session = self._sessions.get(
            conversation_id,
        )

        if session is None:

            session = ConversationSession(
                session_id=conversation_id,
            )

            self._sessions[
                conversation_id
            ] = session

        return session

    def has_session(
        self,
        conversation_id: str,
    ) -> bool:

        return (
            conversation_id
            in self._sessions
        )

    def delete_session(
        self,
        conversation_id: str,
    ) -> None:

        session = self._sessions.pop(
            conversation_id,
            None,
        )

        if session is not None:
            session.reset()

    def clear_session(
        self,
        conversation_id: str,
    ) -> None:

        session = self._sessions.get(
            conversation_id,
        )

        if session is not None:

            session.reset()

    def clear_all_sessions(
        self,
    ) -> None:

        self._sessions.clear()

    def session_count(
        self,
    ) -> int:

        return len(
            self._sessions
        )