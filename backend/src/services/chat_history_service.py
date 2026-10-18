from email import message
from pyexpat.errors import messages
import uuid
from datetime import datetime, timezone
from typing import Any
import time
from requests import session
from sqlalchemy import pool, select
from streamlit import user
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
    _user_cache: dict[str, User] = {}

    # def get_or_create_user(
    #     self,
    #     browser_id: str,
    # ) -> User:

    #     with SessionLocal() as session:

    #         user = session.scalar(
    #             select(User).where(
    #                 User.browser_id == browser_id
    #             )
    #         )

    #         if user is not None:
    #             session.expunge(user)
    #             return user

    #         user = User(
    #             browser_id=browser_id,
    #         )

    #         session.add(user)
    #         session.commit()
    #         session.refresh(user)
    #         session.expunge(user)

    #         return user

    def get_or_create_user(
        self,
        browser_id: str,
        session=None,
    ) -> User:

        cached_user = self._user_cache.get(
            browser_id
        )

        if cached_user is not None:
            print(
                "[USER DB] cache HIT"
            )
            return cached_user

        total_start = time.perf_counter()

        def _get_user(db):
            connection_start = time.perf_counter()

            db.connection()

            print(
                f"[USER DB] connection checkout: "
                f"{time.perf_counter() - connection_start:.3f}s"
            )
            query_start = time.perf_counter()

            user = db.scalar(
                select(User).where(
                    User.browser_id == browser_id
                )
            )

            print(
                f"[USER DB] lookup: "
                f"{time.perf_counter() - query_start:.3f}s"
            )

            if user is not None:

                db.expunge(user)

                self._user_cache[
                    browser_id
                ] = user

                print(
                    f"[USER DB] existing user TOTAL: "
                    f"{time.perf_counter() - total_start:.3f}s"
                )

                return user

            user = User(
                browser_id=browser_id,
            )

            db.add(user)
            db.commit()
            db.refresh(user)
            db.expunge(user)

            self._user_cache[
                browser_id
            ] = user

            print(
                f"[USER DB] new user TOTAL: "
                f"{time.perf_counter() - total_start:.3f}s"
            )

            return user

        if session is not None:
            return _get_user(session)

        with SessionLocal() as db:
            return _get_user(db)

        # with SessionLocal() as session:

        #     query_start = time.perf_counter()

        #     user = session.scalar(
        #         select(User).where(
        #             User.browser_id == browser_id
        #         )
        #     )

        #     print(
        #         f"[USER DB] lookup: "
        #         f"{time.perf_counter() - query_start:.3f}s"
        #     )

        #     if user is not None:

        #         session.expunge(user)

        #         self._user_cache[
        #             browser_id
        #         ] = user

        #         print(
        #             f"[USER DB] existing user TOTAL: "
        #             f"{time.perf_counter() - total_start:.3f}s"
        #         )

        #         return user

        #     user = User(
        #         browser_id=browser_id,
        #     )

        #     session.add(user)
        #     session.commit()
        #     session.refresh(user)
        #     session.expunge(user)

        #     self._user_cache[
        #         browser_id
        #     ] = user

        #     print(
        #         f"[USER DB] new user TOTAL: "
        #         f"{time.perf_counter() - total_start:.3f}s"
        #     )

        #     return user


    # def create_chat(
    #     self,
    #     browser_id: str,
    #     title: str = "New Chat",
    # ) -> dict[str, Any]:
    #     total_start = time.perf_counter()

    #     user_start = time.perf_counter()

    #     user = self.get_or_create_user(
    #         browser_id
    #     )

    #     print(
    #         f"[CREATE CHAT DB] get_or_create_user: "
    #         f"{time.perf_counter() - user_start:.3f}s"
    #     )

    #     db_start = time.perf_counter()

    #     with SessionLocal() as session:

    #         session_create_time = (
    #             time.perf_counter() - db_start
    #         )

    #         print(
    #             f"[CREATE CHAT DB] Session created: "
    #             f"{session_create_time:.3f}s"
    #         )

    #         chat = Chat(
    #             user_id=user.id,
    #             title=title,
    #         )

    #         session.add(chat)
    #         flush_start = time.perf_counter()

    #         session.flush()

    #         print(
    #             f"[CREATE CHAT DB] flush: "
    #             f"{time.perf_counter() - flush_start:.3f}s"
    #         )

    #         commit_start = time.perf_counter()
    #         session.commit()
    #         print(
    #             f"[CREATE CHAT DB] commit: "
    #             f"{time.perf_counter() - commit_start:.3f}s"
    #         )

    #         result = self._chat_to_dict(chat)

    #     print(
    #         f"[CREATE CHAT DB] TOTAL: "
    #         f"{time.perf_counter() - total_start:.3f}s"
    #     )

    #     return result
            # session.refresh(chat)

            # return self._chat_to_dict(chat)
    
    def create_chat(
        self,
        browser_id: str,
        title: str = "New Chat",
    ) -> dict[str, Any]:

        total_start = time.perf_counter()

        db_start = time.perf_counter()

        with SessionLocal() as session:

            print(
                f"[CREATE CHAT DB] Session created: "
                f"{time.perf_counter() - db_start:.3f}s"
            )

            user_start = time.perf_counter()

            user = self.get_or_create_user(
                browser_id,
                session=session,
            )

            print(
                f"[CREATE CHAT DB] get_or_create_user: "
                f"{time.perf_counter() - user_start:.3f}s"
            )

            chat = Chat(
                user_id=user.id,
                title=title,
            )

            session.add(chat)

            flush_start = time.perf_counter()

            session.flush()

            print(
                f"[CREATE CHAT DB] flush: "
                f"{time.perf_counter() - flush_start:.3f}s"
            )

            commit_start = time.perf_counter()

            session.commit()

            print(
                f"[CREATE CHAT DB] commit: "
                f"{time.perf_counter() - commit_start:.3f}s"
            )

            result = self._chat_to_dict(chat)

        print(
            f"[CREATE CHAT DB] TOTAL: "
            f"{time.perf_counter() - total_start:.3f}s"
        )

        return result


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
    
    def get_chat_orm(
        self,
        browser_id: str,
        chat_id: str,
        session=None,
        title: str | None = None,
    ) -> Chat | None:

        chat_uuid = self._to_uuid(
            chat_id,
        )

        def _query(db):
            connection_start = time.perf_counter()
            pool = db.get_bind().pool

            print(
                f"[CHAT DB TIMING] pool before checkout: "
                f"size={pool.size()}, "
                f"checked_out={pool.checkedout()}, "
                f"overflow={pool.overflow()}, "
                f"checked_in={pool.checkedin()}"
            )


            db.connection()

            print(
                f"[CHAT DB TIMING] connection checkout: "
                f"{time.perf_counter() - connection_start:.3f}s"
            )

            print(
                f"[CHAT DB TIMING] pool after checkout: "
                f"size={pool.size()}, "
                f"checked_out={pool.checkedout()}, "
                f"overflow={pool.overflow()}, "
                f"checked_in={pool.checkedin()}"
            )

            chat_query_start = time.perf_counter()

            chat = db.scalar(
                select(Chat)
                .join(User)
                .where(
                    Chat.id == chat_uuid,
                    User.browser_id == browser_id,
                )
            )

            print(
                f"[CHAT DB TIMING] chat-only query: "
                f"{time.perf_counter() - chat_query_start:.3f}s"
            )

            if chat is None:
                return None
            
            if title is not None and chat.title == "New Chat":
                clean_title = title.strip()

                if len(clean_title) > 50:
                    clean_title = (
                        clean_title[:50] + "..."
                    )

                chat.title = clean_title or "New Chat"
                chat.updated_at = utc_now()

            return chat

        if session is not None:
            return _query(session)

        with SessionLocal() as db:
            chat = _query(db)

            if title is not None:
                db.commit()

            return chat

    # def get_chat_with_messages(
    #     self,
    #     browser_id: str,
    #     chat_id: str,
    #     limit: int = 6,
    # ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:

    #     chat_uuid = self._to_uuid(chat_id)

    #     with SessionLocal() as session:

    #         chat = session.scalar(
    #             select(Chat)
    #             .join(User)
    #             .where(
    #                 Chat.id == chat_uuid,
    #                 User.browser_id == browser_id,
    #             )
    #         )

    #         if chat is None:
    #             return None, []

    #         messages = session.scalars(
    #             select(Message)
    #             .where(
    #                 Message.chat_id == chat_uuid
    #             )
    #             .order_by(
    #                 Message.created_at.desc()
    #             )
    #             .limit(limit)
    #         ).all()

    #         messages.reverse()

    #         return (
    #             self._chat_to_dict(chat),
    #             [
    #                 self._message_to_dict(message)
    #                 for message in messages
    #             ],
    #         )

    def get_chat_with_messages(
        self,
        browser_id: str,
        chat_id: str,
        limit: int = 20,
        session=None,
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:

        chat_uuid = self._to_uuid(chat_id)

        def _query(db):

            query_start = time.perf_counter()
                    
            chat_query_start = time.perf_counter()

            chat = db.scalar(
                select(Chat)
                .join(User)
                .where(
                    Chat.id == chat_uuid,
                    User.browser_id == browser_id,
                )
            )

            print(
                f"[CHAT DB TIMING] chat query: "
                f"{time.perf_counter() - chat_query_start:.3f}s"
            )

            if chat is None:
                return None, []

            messages_query_start = time.perf_counter()

            messages = db.scalars(
                select(Message)
                .where(
                    Message.chat_id == chat_uuid
                )
                .order_by(
                    Message.created_at.desc()
                )
                .limit(limit)
            ).all()

            messages_query_time = (
                time.perf_counter()
                - messages_query_start
            )

            print(
                f"[CHAT DB TIMING] messages query: "
                f"{messages_query_time:.3f}s"
            )

            conversion_start = time.perf_counter()

            messages.reverse()

            conversation_history = [
                self._message_to_dict(message)
                for message in messages
            ]

            print(
                f"[CHAT DB TIMING] message conversion: "
                f"{time.perf_counter() - conversion_start:.3f}s"
            )

            print(
                f"[CHAT DB TIMING] total _query: "
                f"{time.perf_counter() - query_start:.3f}s"
            )

            return (
                self._chat_to_dict(chat),
                conversation_history,
            )

            # messages.reverse()

            # return (
            #     self._chat_to_dict(chat),
            #     [
            #         self._message_to_dict(message)
            #         for message in messages
            #     ],
            # )

        if session is not None:
            return _query(session)

        with SessionLocal() as db:
            return _query(db)

    def get_chat_with_messages_orm(
        self,
        browser_id: str,
        chat_id: str,
        limit: int = 20,
        session=None,
    ) -> tuple[Chat | None, list[dict[str, Any]]]:

        chat_uuid = self._to_uuid(chat_id)

        def _query(db):
             
            query_start = time.perf_counter()

            chat_query_start = time.perf_counter()

            chat = db.scalar(
                select(Chat)
                .join(User)
                .where(
                    Chat.id == chat_uuid,
                    User.browser_id == browser_id,
                )
            )

            print(
                f"[CHAT DB TIMING] chat query: "
                f"{time.perf_counter() - chat_query_start:.3f}s"
            )

            

            if chat is None:
                return None, []

            messages_query_start = time.perf_counter()

            messages = db.scalars(
                select(Message)
                .where(
                    Message.chat_id == chat_uuid
                )
                .order_by(
                    Message.created_at.desc()
                )
                .limit(limit)
            ).all()

            reverse_start = time.perf_counter()

            messages.reverse()

            conversation_history = [
                self._message_to_dict(message)
                for message in messages
            ]

            print(
                f"[CHAT DB TIMING] message conversion: "
                f"{time.perf_counter() - reverse_start:.3f}s"
            )

            print(
                f"[CHAT DB TIMING] total _query: "
                f"{time.perf_counter() - query_start:.3f}s"
            )

            return chat, conversation_history

        #     return (
        #         chat,
        #         [
        #             self._message_to_dict(message)
        #             for message in messages
        #         ],
        #     )

        if session is not None:
            return _query(session)

        with SessionLocal() as db:
            return _query(db)

    def add_message_by_chat_id(
        self,
        chat_id: str,
        role: str,
        content: str,
        sources: list | None = None,
        page_references: list | None = None,
        curriculum_route: dict | None = None,
        session=None,
        title: str | None = None,
        commit: bool = True,
    ) -> dict[str, Any]:

        if role not in {
            "user",
            "assistant",
        }:
            raise ValueError(
                "Role must be user or assistant."
            )

        chat_uuid = self._to_uuid(chat_id)

        def _add_message(db):

            message = Message(
                chat_id=chat_uuid,
                role=role,
                content=content,
                sources=sources or [],
                page_references=(
                    page_references or []
                ),
                curriculum_route=(
                    curriculum_route or {}
                ),
            )

            add_start = time.perf_counter()

            db.add(message)

            print(
                f"[CHAT DB TIMING] message db.add: "
                f"{time.perf_counter() - add_start:.3f}s"
            )

            print(
                f"[CHAT DB TIMING] session new: "
                f"{len(db.new)}"
            )

            print(
                f"[CHAT DB TIMING] session dirty: "
                f"{len(db.dirty)}"
            )

            print(
                f"[CHAT DB TIMING] session deleted: "
                f"{len(db.deleted)}"
            )

            print(
                f"[CHAT DB TIMING] content length: "
                f"{len(message.content)}"
            )

            print(
                f"[CHAT DB TIMING] sources length: "
                f"{len(message.sources)}"
            )

            print(
                f"[CHAT DB TIMING] page refs length: "
            f"{len(message.page_references)}"
            )

            print(
                f"[CHAT DB TIMING] curriculum keys: "
                f"{len(message.curriculum_route)}"
            )

            # flush_start = time.perf_counter()

            # db.flush()

            # print(
            #     f"[CHAT DB TIMING] message flush: "
            #     f"{time.perf_counter() - flush_start:.3f}s"
            # )


            clean_title = None

            if title is not None:
                clean_title = title.strip()

                if len(clean_title) > 50:
                    clean_title = (
                        clean_title[:50] + "..."
                    )
            
            chat_update_start = time.perf_counter()

            if (
                clean_title
                and role == "user"
            ):
                db.execute(
                    Chat.__table__.update()
                    .where(
                        Chat.id == chat_uuid,
                        Chat.title == "New Chat",
                    )
                    .values(
                        title=clean_title,
                        updated_at=utc_now(),
                    )
                )

            else:
                db.execute(
                    Chat.__table__.update()
                    .where(
                        Chat.id == chat_uuid,
                    )
                    .values(
                        updated_at=utc_now(),
                    )
                )

            print(
                f"[CHAT DB TIMING] chat update: "
                f"{time.perf_counter() - chat_update_start:.3f}s"
            )

            commit_start = time.perf_counter()

            if commit:
                db.commit()
            else:
                db.flush()

            print(
                f"[CHAT DB TIMING] message commit: "
                f"{time.perf_counter() - commit_start:.3f}s"
            )

            return self._message_to_dict(
                message
            )

        if session is not None:

            start = time.perf_counter()

            result = _add_message(session)

            print(
                f"[CHAT DB TIMING] add_message_by_chat_id TOTAL: "
                f"{time.perf_counter() - start:.3f}s"
            )

            return result

        if session is not None:
            return _add_message(session)

        with SessionLocal() as db:
            return _add_message(db)

    def add_message_for_chat(
        self,
        chat: Chat,
        role: str,
        content: str,
        sources: list | None = None,
        page_references: list | None = None,
        curriculum_route: dict | None = None,
        session=None,
        commit: bool = True,
    ) -> dict[str, Any]:

        if role not in {
            "user",
            "assistant",
        }:
            raise ValueError(
                "Role must be user or assistant."
            )

        def _add_message(db):
            message = Message(
                chat_id=chat.id,
                role=role,
                content=content,
                sources=sources or [],
                page_references=(
                    page_references or []
                ),
                curriculum_route=(
                    curriculum_route or {}
                ),
            )

            chat.updated_at = utc_now()
            add_start = time.perf_counter()

            db.add(message)
            print(
                f"[CHAT DB TIMING] assistant db.add: "
                f"{time.perf_counter() - add_start:.3f}s"
            )

            # commit_start = time.perf_counter()

            # db.commit()

            # print(
            #     f"[CHAT DB TIMING] assistant db.commit: "
            #     f"{time.perf_counter() - commit_start:.3f}s"
            # )
            if commit:
                commit_start = time.perf_counter()

                db.commit()

                print(
                    f"[CHAT DB TIMING] assistant db.commit: "
                    f"{time.perf_counter() - commit_start:.3f}s"
                )
            else:
                flush_start = time.perf_counter()

                db.flush()

                print(
                    f"[CHAT DB TIMING] assistant db.flush: "
                    f"{time.perf_counter() - flush_start:.3f}s"
                )

            conversion_start = time.perf_counter()

            result = self._message_to_dict(message)

            print(
                f"[CHAT DB TIMING] assistant conversion: "
                f"{time.perf_counter() - conversion_start:.3f}s"
            )

            return result

            # return self._message_to_dict(
            #     message
            # )

        if session is not None:
            return _add_message(session)

        with SessionLocal() as db:
            return _add_message(db)


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


    # def add_message(
    #     self,
    #     browser_id: str,
    #     chat_id: str,
    #     role: str,
    #     content: str,
    #     sources: list | None = None,
    #     page_references: list | None = None,
    #     curriculum_route: dict | None = None,
    #     session=None,
    # ) -> dict[str, Any]:

    #     if role not in {
    #         "user",
    #         "assistant",
    #     }:
    #         raise ValueError(
    #             "Role must be user or assistant."
    #         )

    #     chat_uuid = self._to_uuid(chat_id)

    #     with SessionLocal() as session:


    #         chat = session.scalar(
    #             select(Chat)
    #             .join(User)
    #             .where(
    #                 Chat.id == chat_uuid,
    #                 User.browser_id == browser_id,
    #             )
    #         )


    #         if chat is None:
    #             raise PermissionError(
    #                 "Chat not found for this user."
    #             )

    #         message = Message(
    #             chat_id=chat.id,
    #             role=role,
    #             content=content,
    #             sources=sources or [],
    #             page_references=(
    #                 page_references or []
    #             ),
    #             curriculum_route=(
    #                     curriculum_route or {}
    #                 ),
    #         )

    #         chat.updated_at = utc_now()

    #         session.add(message)
    #         flush_start = time.perf_counter()

    #         # session.flush()


    #         commit_start = time.perf_counter()

    #         session.commit()

    #         # session.commit()
    #         # session.refresh(message)

    #         result = self._message_to_dict(message)

    #     return result

            # return self._message_to_dict(
            #     message
            # )
    def add_message(
        self,
        browser_id: str,
        chat_id: str,
        role: str,
        content: str,
        sources: list | None = None,
        page_references: list | None = None,
        curriculum_route: dict | None = None,
        session=None,
        
    ) -> dict[str, Any]:

        if role not in {
            "user",
            "assistant",
        }:
            raise ValueError(
                "Role must be user or assistant."
            )

        chat_uuid = self._to_uuid(chat_id)

        def _add_message(db):
            chat = db.scalar(
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
                curriculum_route=(
                    curriculum_route or {}
                ),
            )

            chat.updated_at = utc_now()

            db.add(message)
            db.commit()

            return self._message_to_dict(
                message
            )

        if session is not None:
            return _add_message(session)

        with SessionLocal() as db:
            return _add_message(db)



    # def update_title(
    #     self,
    #     browser_id: str,
    #     chat_id: str,
    #     title: str,
    # ) -> None:

    #     chat_uuid = self._to_uuid(chat_id)

    #     clean_title = title.strip()

    #     if len(clean_title) > 50:
    #         clean_title = (
    #             clean_title[:50] + "..."
    #         )

    #     with SessionLocal() as session:

    #         chat = session.scalar(
    #             select(Chat)
    #             .join(User)
    #             .where(
    #                 Chat.id == chat_uuid,
    #                 User.browser_id == browser_id,
    #             )
    #         )

    #         if chat is None:
    #             raise PermissionError(
    #                 "Chat not found for this user."
    #             )

    #         chat.title = (
    #             clean_title or "New Chat"
    #         )

    #         chat.updated_at = utc_now()

    #         session.commit()


    def update_title(
        self,
        browser_id: str,
        chat_id: str,
        title: str,
        session=None,
    ) -> None:

        chat_uuid = self._to_uuid(chat_id)

        clean_title = title.strip()

        if len(clean_title) > 50:
            clean_title = (
                clean_title[:50] + "..."
            )

        def _update(db):
            chat = db.scalar(
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

        if session is not None:
            _update(session)
            return

        with SessionLocal() as db:
            _update(db)
            db.commit()


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
            "curriculum_route": (
                message.curriculum_route or {}
            ),
            "created_at": (
                message.created_at.isoformat()
            ),
        }
