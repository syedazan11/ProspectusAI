from __future__ import annotations

from pyexpat.errors import messages
from typing import Any


class ConversationStore:
    """In-memory UI conversation history, separate from AI session state."""

    def __init__(self) -> None:
        self._conversations: dict[
            str,
            list[dict[str, Any]],
        ] = {}

    def add_message(
        self,
        conversation_id: str,
        message: dict[str, Any],
    ) -> None:
        self._conversations.setdefault(
            conversation_id,
            [],
        ).append(message)

    # def get_messages(
    #     self,
    #     conversation_id: str,
    # ) -> list[dict[str, Any]]:
    #     return list(
    #         self._conversations.get(
    #             conversation_id,
    #             [],
    #         )
    #     )

    def get_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        messages = list(self._conversations.get(conversation_id, []))
        # print(
        #     f"[CONVERSATION STORE] GET {conversation_id}: "
        #     f"{len(messages)} messages"
        # )
        for message in messages:
            print(
                f"  - {message.get('role')}: "
                f"{message.get('content', '')[:80]}"
            )
        return messages

    def has_conversation(
        self,
        conversation_id: str,
    ) -> bool:
        return conversation_id in self._conversations

    def delete_conversation(
        self,
        conversation_id: str,
    ) -> None:
        self._conversations.pop(
            conversation_id,
            None,
        )

    def clear_all(self) -> None:
        self._conversations.clear()
