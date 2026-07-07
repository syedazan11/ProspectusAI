import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from src.database.database import SessionLocal
from src.database.models import Chat, Message, User


def utc_now():
    return datetime.now(timezone.utc)


class ChatHistoryService:
    """
    Persistent Neon-backed chat history.

    Every operation is scoped to browser_id so one
    anonymous user cannot access another user's chats.
    """

    def get_or_create_user(
        self,
        browser_id: str,
    ) -> User:

        with SessionLocal() as session:

            user = session.scalar(
                select(User).where(
                    User.browser_id == browser_id
                )
            )

            if user is not None:
                session.expunge(user)
                return user

            user = User(
                browser_id=browser_id,
            )

            session.add(user)
            session.commit()
            session.refresh(user)
            session.expunge(user)

            return user


    def create_chat(
        self,
        browser_id: str,
        title: str = "New Chat",
    ) -> dict[str, Any]:

        user = self.get_or_create_user(
            browser_id
        )

        with SessionLocal() as session:

            chat = Chat(
                user_id=user.id,
                title=title,
            )

            session.add(chat)
            session.commit()
            session.refresh(chat)

            return self._chat_to_dict(chat)


    def list_chats(
        self,
        browser_id: str,
    ) -> list[dict[str, Any]]:

        with SessionLocal() as session:

            chats = session.scalars(
                select(Chat)
                .join(User)
                .where(
                    User.browser_id == browser_id
                )
                .order_by(
                    Chat.updated_at.desc()
                )
            ).all()

            return [
                self._chat_to_dict(chat)
                for chat in chats
            ]


    def get_chat(
        self,
        browser_id: str,
        chat_id: str,
    ) -> dict[str, Any] | None:

        chat_uuid = self._to_uuid(chat_id)

        with SessionLocal() as session:

            chat = session.scalar(
                select(Chat)
                .join(User)
                .where(
                    Chat.id == chat_uuid,
                    User.browser_id == browser_id,
                )
            )

            if chat is None:
                return None

            return self._chat_to_dict(chat)


    def get_messages(
        self,
        browser_id: str,
        chat_id: str,
    ) -> list[dict[str, Any]]:

        chat_uuid = self._to_uuid(chat_id)

        with SessionLocal() as session:

            owned_chat = session.scalar(
                select(Chat.id)
                .join(User)
                .where(
                    Chat.id == chat_uuid,
                    User.browser_id == browser_id,
                )
            )

            if owned_chat is None:
                return []

            messages = session.scalars(
                select(Message)
                .where(
                    Message.chat_id == chat_uuid
                )
                .order_by(
                    Message.created_at.asc()
                )
            ).all()

            return [
                self._message_to_dict(message)
                for message in messages
            ]


    def add_message(
        self,
        browser_id: str,
        chat_id: str,
        role: str,
        content: str,
        sources: list | None = None,
        page_references: list | None = None,
    ) -> dict[str, Any]:

        if role not in {
            "user",
            "assistant",
        }:
            raise ValueError(
                "Role must be user or assistant."
            )

        chat_uuid = self._to_uuid(chat_id)

        with SessionLocal() as session:

            chat = session.scalar(
                select(Chat)
                .join(User)
                .where(
                    Chat.id == chat_uuid,
                    User.browser_id == browser_id,
                )
            )

            if chat is None:
                raise PermissionError(
                    "Chat not found for this user."
                )

            message = Message(
                chat_id=chat.id,
                role=role,
                content=content,
                sources=sources or [],
                page_references=(
                    page_references or []
                ),
            )

            chat.updated_at = utc_now()

            session.add(message)
            session.commit()
            session.refresh(message)

            return self._message_to_dict(
                message
            )


    def update_title(
        self,
        browser_id: str,
        chat_id: str,
        title: str,
    ) -> None:

        chat_uuid = self._to_uuid(chat_id)

        clean_title = title.strip()

        if len(clean_title) > 50:
            clean_title = (
                clean_title[:50] + "..."
            )

        with SessionLocal() as session:

            chat = session.scalar(
                select(Chat)
                .join(User)
                .where(
                    Chat.id == chat_uuid,
                    User.browser_id == browser_id,
                )
            )

            if chat is None:
                raise PermissionError(
                    "Chat not found for this user."
                )

            chat.title = (
                clean_title or "New Chat"
            )

            chat.updated_at = utc_now()

            session.commit()


    def delete_chat(
        self,
        browser_id: str,
        chat_id: str,
    ) -> bool:

        chat_uuid = self._to_uuid(chat_id)

        with SessionLocal() as session:

            chat = session.scalar(
                select(Chat)
                .join(User)
                .where(
                    Chat.id == chat_uuid,
                    User.browser_id == browser_id,
                )
            )

            if chat is None:
                return False

            session.delete(chat)
            session.commit()

            return True


    @staticmethod
    def _to_uuid(value: str) -> uuid.UUID:

        try:
            return uuid.UUID(str(value))
        except ValueError as error:
            raise ValueError(
                "Invalid chat ID."
            ) from error


    @staticmethod
    def _chat_to_dict(
        chat: Chat,
    ) -> dict[str, Any]:

        return {
            "id": str(chat.id),
            "title": chat.title,
            "created_at": (
                chat.created_at.isoformat()
            ),
            "updated_at": (
                chat.updated_at.isoformat()
            ),
        }


    @staticmethod
    def _message_to_dict(
        message: Message,
    ) -> dict[str, Any]:

        return {
            "id": str(message.id),
            "role": message.role,
            "content": message.content,
            "sources": message.sources or [],
            "page_references": (
                message.page_references or []
            ),
            "created_at": (
                message.created_at.isoformat()
            ),
        }
