from pathlib import Path
import sys
import time
import uuid

import streamlit as st


# =========================================================
# PATH SETUP
# =========================================================

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"

sys.path.insert(0, str(BACKEND_DIR))

from src.generation.answer_generator import AnswerGenerator
from src.services.chat_history_service import ChatHistoryService
from src.services.document_manager import DocumentManager


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="ProspectusAI",
    page_icon="🎓",
    layout="wide",
)


# =========================================================
# SERVICES
# =========================================================

@st.cache_resource
def get_chat_service():
    return ChatHistoryService()


@st.cache_resource
def load_answer_generator():

    manager = DocumentManager()

    active_document = manager.get_active_document()

    document_id = active_document["document_id"]

    generator = AnswerGenerator(
        graph_path=manager.get_graph_path(
            document_id
        ),
        tables_path=manager.get_tables_path(
            document_id
        ),
    )

    return generator, active_document


chat_service = get_chat_service()


# =========================================================
# PERSISTENT ANONYMOUS USER ID
# =========================================================

def get_browser_id() -> str:

    existing_id = st.query_params.get(
        "user"
    )

    if existing_id:

        try:
            uuid.UUID(existing_id)
            return existing_id

        except ValueError:
            pass

    browser_id = str(uuid.uuid4())

    st.query_params["user"] = browser_id

    return browser_id


browser_id = get_browser_id()


# =========================================================
# SESSION INITIALIZATION
# =========================================================

def initialize_session_state():

    if "authenticated_admin" not in st.session_state:
        st.session_state.authenticated_admin = False

    if "current_page" not in st.session_state:
        st.session_state.current_page = "Chat"

    if "active_chat_id" not in st.session_state:
        st.session_state.active_chat_id = None


initialize_session_state()


# =========================================================
# CHAT HELPERS
# =========================================================

def create_new_chat():

    chat = chat_service.create_chat(
        browser_id=browser_id,
    )

    st.session_state.active_chat_id = (
        chat["id"]
    )

    return chat


def ensure_active_chat():

    chats = chat_service.list_chats(
        browser_id
    )

    active_chat_id = (
        st.session_state.active_chat_id
    )

    if active_chat_id:

        active_chat = (
            chat_service.get_chat(
                browser_id=browser_id,
                chat_id=active_chat_id,
            )
        )

        if active_chat is not None:
            return active_chat

    if chats:

        st.session_state.active_chat_id = (
            chats[0]["id"]
        )

        return chats[0]

    return create_new_chat()


def get_active_messages():

    return chat_service.get_messages(
        browser_id=browser_id,
        chat_id=(
            st.session_state.active_chat_id
        ),
    )


def update_chat_title(
    question: str,
):

    chat = chat_service.get_chat(
        browser_id=browser_id,
        chat_id=(
            st.session_state.active_chat_id
        ),
    )

    if (
        chat is not None
        and chat["title"] == "New Chat"
    ):

        chat_service.update_title(
            browser_id=browser_id,
            chat_id=chat["id"],
            title=question,
        )


active_chat = ensure_active_chat()


# =========================================================
# DISPLAY HELPERS
# =========================================================

def stream_answer(
    text: str,
):

    words = text.split()

    for word in words:

        yield word + " "

        time.sleep(0.02)


def build_conversation_context(
    messages: list[dict],
) -> str:

    recent_messages = messages[-6:]

    lines = []

    for message in recent_messages:

        role = (
            "User"
            if message["role"] == "user"
            else "Assistant"
        )

        lines.append(
            f"{role}: {message['content']}"
        )

    return "\n".join(lines)


def get_conversational_response(
    message: str,
) -> str | None:

    normalized = (
        message
        .strip()
        .casefold()
        .rstrip("!?.")
    )

    greetings = {
        "hi",
        "hello",
        "hey",
        "hi there",
        "hello there",
        "salam",
        "assalamualaikum",
        "assalam o alaikum",
        "aoa",
    }

    thanks = {
        "thanks",
        "thank you",
        "thx",
        "ty",
    }

    goodbyes = {
        "bye",
        "goodbye",
        "see you",
    }

    if normalized in greetings:

        return (
            "Hi! I'm **ProspectusAI**, your assistant "
            "for the active university prospectus. "
            "I can help with admissions, eligibility, "
            "programmes, categories, seats, fees, and "
            "other prospectus information. "
            "What would you like to know?"
        )

    if normalized in thanks:

        return (
            "You're welcome! Ask me anything else "
            "about the prospectus."
        )

    if normalized in {
        "who are you",
        "what are you",
    }:

        return (
            "I'm **ProspectusAI**, a Hybrid GraphRAG "
            "assistant that answers questions using "
            "the active university prospectus."
        )

    if normalized in goodbyes:

        return (
            "Goodbye! Come back whenever you need "
            "help with the prospectus."
        )

    return None


def render_sources(
    sources: list[dict],
):

    if not sources:
        return

    with st.expander("📚 Sources"):

        seen = set()

        for source in sources:

            source_key = (
                source.get("document"),
                source.get("page_number"),
            )

            if source_key in seen:
                continue

            seen.add(source_key)

            page_number = source.get(
                "page_number",
                "?",
            )

            heading = source.get(
                "heading",
                "Prospectus",
            )

            st.markdown(
                f"**Page {page_number}**"
            )

            st.caption(heading)


def render_page_references(
    page_references: list[dict],
):

    if not page_references:
        return

    st.warning(
        "The exact answer could not be "
        "reliably extracted. Review the "
        "relevant prospectus page below."
    )

    seen_pages = set()

    for reference in page_references:

        page_number = reference.get(
            "page_number"
        )

        document = reference.get(
            "document"
        )

        if page_number in seen_pages:
            continue

        seen_pages.add(page_number)

        st.markdown(
            f"### Prospectus page {page_number}"
        )

        page_path = reference.get(
            "page_path"
        )

        if page_path:

            image_path = Path(page_path)

            if image_path.exists():

                try:

                    st.image(
                        str(image_path),
                        caption=(
                            f"Page {page_number}"
                        ),
                        use_container_width=True,
                    )

                except Exception:

                    pass

        page_url = reference.get(
            "page_url"
        )

        if not page_url and document:

            page_url = (
                f"/api/v1/pages/"
                f"{document}/"
                f"{page_number}"
            )

        if page_url:

            if page_url.startswith("/"):

                page_url = (
                    "http://127.0.0.1:8000"
                    f"{page_url}"
                )

            st.link_button(
                f"Open page {page_number}",
                page_url,
                use_container_width=True,
            )


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:

    st.title("🎓 ProspectusAI")

    if st.button(
        "➕ New Chat",
        use_container_width=True,
        type="primary",
    ):

        create_new_chat()

        st.session_state.current_page = (
            "Chat"
        )

        st.rerun()

    st.divider()

    if st.button(
        "💬 Chat",
        use_container_width=True,
    ):

        st.session_state.current_page = (
            "Chat"
        )

        st.rerun()

    if st.button(
        "🔐 Admin",
        use_container_width=True,
    ):

        st.session_state.current_page = (
            "Admin"
        )

        st.rerun()

    st.divider()

    st.caption("Recent Chats")

    saved_chats = chat_service.list_chats(
        browser_id
    )

    for chat in saved_chats:

        title = chat["title"]

        if (
            chat["id"]
            == st.session_state.active_chat_id
        ):

            title = f"● {title}"

        if st.button(
            title,
            key=f"chat_{chat['id']}",
            use_container_width=True,
        ):

            st.session_state.active_chat_id = (
                chat["id"]
            )

            st.session_state.current_page = (
                "Chat"
            )

            st.rerun()


# =========================================================
# ADMIN PAGE
# =========================================================

if st.session_state.current_page == "Admin":

    if not st.session_state.authenticated_admin:

        st.title("🔐 Admin Login")

        st.caption(
            "Sign in to manage prospectus documents."
        )

        with st.form("admin_login"):

            username = st.text_input(
                "Username"
            )

            password = st.text_input(
                "Password",
                type="password",
            )

            submitted = (
                st.form_submit_button(
                    "Login",
                    use_container_width=True,
                )
            )

        if submitted:

            if (
                username == "admin"
                and password
                == "prospectus-dev-only"
            ):

                st.session_state[
                    "authenticated_admin"
                ] = True

                st.rerun()

            else:

                st.error(
                    "Invalid username or password."
                )

        st.stop()


    col1, col2 = st.columns([5, 1])

    with col1:

        st.title("⚙️ Admin Dashboard")

    with col2:

        if st.button(
            "Logout",
            use_container_width=True,
        ):

            st.session_state[
                "authenticated_admin"
            ] = False

            st.session_state.current_page = (
                "Chat"
            )

            st.rerun()


    manager = DocumentManager()

    try:

        active_document = (
            manager.get_active_document()
        )

        st.success(
            "Active prospectus is ready."
        )

        st.subheader(
            active_document["filename"]
        )

        metric1, metric2, metric3 = (
            st.columns(3)
        )

        metric1.metric(
            "Year",
            active_document["year"],
        )

        metric2.metric(
            "Status",
            active_document["status"],
        )

        metric3.metric(
            "Document ID",
            active_document["document_id"],
        )

    except Exception as error:

        st.warning(
            f"No active prospectus: {error}"
        )


    st.divider()

    st.subheader("Upload Prospectus")

    uploaded_file = st.file_uploader(
        "Choose a PDF prospectus",
        type=["pdf"],
    )

    if uploaded_file is not None:

        st.write(
            f"Selected: "
            f"**{uploaded_file.name}**"
        )

        st.button(
            "Process Prospectus",
            type="primary",
            disabled=True,
        )

        st.caption(
            "Upload processing will be "
            "connected next."
        )

    st.stop()


# =========================================================
# CHAT PAGE
# =========================================================

try:

    answer_generator, active_document = (
        load_answer_generator()
    )

except Exception as error:

    st.error(
        f"Could not load ProspectusAI: "
        f"{error}"
    )

    st.stop()


st.title("🎓 ProspectusAI")

st.caption(
    f"Ask questions about "
    f"{active_document['filename']}"
)


messages = get_active_messages()


# =========================================================
# EMPTY CHAT WELCOME
# =========================================================

if not messages:

    st.markdown(
        """
### How can I help you today?

Ask me about:

- Admission eligibility
- Programme seats
- Admission categories
- Required documents
- Fees and rules
        """
    )


# =========================================================
# CHAT HISTORY
# =========================================================

for message in messages:

    with st.chat_message(
        message["role"]
    ):

        st.markdown(
            message["content"]
        )

        render_sources(
            message.get(
                "sources",
                [],
            )
        )

        render_page_references(
            message.get(
                "page_references",
                [],
            )
        )


# =========================================================
# USER INPUT
# =========================================================

question = st.chat_input(
    "Ask about admissions, eligibility, seats..."
)


if question:

    previous_messages = list(messages)

    update_chat_title(question)

    chat_service.add_message(
        browser_id=browser_id,
        chat_id=(
            st.session_state.active_chat_id
        ),
        role="user",
        content=question,
    )

    with st.chat_message("user"):

        st.markdown(question)


    with st.chat_message("assistant"):

        try:

            conversational_answer = (
                get_conversational_response(
                    question
                )
            )


            # =========================================
            # BASIC CONVERSATION
            # =========================================

            if conversational_answer is not None:

                st.write_stream(
                    stream_answer(
                        conversational_answer
                    )
                )

                chat_service.add_message(
                    browser_id=browser_id,
                    chat_id=(
                        st.session_state
                        .active_chat_id
                    ),
                    role="assistant",
                    content=(
                        conversational_answer
                    ),
                )


            # =========================================
            # RAG QUESTION
            # =========================================

            else:

                conversation_context = (
                    build_conversation_context(
                        previous_messages
                    )
                )

                contextual_question = question

                if conversation_context:

                    contextual_question = (
                        "Use the conversation history "
                        "only to understand references "
                        "in the current question.\n\n"
                        "Conversation history:\n"
                        f"{conversation_context}\n\n"
                        "Current question:\n"
                        f"{question}"
                    )


                with st.spinner(
                    "Searching the prospectus..."
                ):

                    result = (
                        answer_generator.answer(
                            question=(
                                contextual_question
                            ),
                            vector_top_k=10,
                            graph_top_k=10,
                        )
                    )


                answer = result["answer"]

                sources = result.get(
                    "sources",
                    [],
                )

                page_references = result.get(
                    "page_references",
                    [],
                )


                st.write_stream(
                    stream_answer(answer)
                )

                render_sources(sources)

                render_page_references(
                    page_references
                )


                chat_service.add_message(
                    browser_id=browser_id,
                    chat_id=(
                        st.session_state
                        .active_chat_id
                    ),
                    role="assistant",
                    content=answer,
                    sources=sources,
                    page_references=(
                        page_references
                    ),
                )


        except Exception as error:

            error_message = (
                "I encountered an error while "
                f"answering: {error}"
            )

            st.error(error_message)

            chat_service.add_message(
                browser_id=browser_id,
                chat_id=(
                    st.session_state.active_chat_id
                ),
                role="assistant",
                content=error_message,
            )