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

from rescue_rag.answer_service import RescueAnswerService
from src.services.chat_history_service import ChatHistoryService
from src.services.document_manager import DocumentManager
from src.services.admin_auth_service import AdminAuthService
from src.services.rescue_document_processing_service import RescueDocumentProcessingService


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

    active_document = (
        manager.get_active_document()
    )

    collection_name = active_document.get(
        "collection_name"
    )

    if not collection_name:
        raise RuntimeError(
            "Active prospectus has no "
            "Qdrant collection configured."
        )

    generator = RescueAnswerService(
        collection_name=collection_name,
    )

    return generator, active_document


chat_service = get_chat_service()
admin_auth_service = AdminAuthService()


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

    if "admin_id" not in st.session_state:
        st.session_state.admin_id = None

    if "admin_username" not in st.session_state:
        st.session_state.admin_username = None

    if "current_page" not in st.session_state:
        st.session_state.current_page = "Chat"

    if "active_chat_id" not in st.session_state:
        st.session_state.active_chat_id = None


initialize_session_state()


# =========================================================
# CHAT HELPERS
# =========================================================

def get_chat_owner_id() -> str:

    if (
        st.session_state.authenticated_admin
        and st.session_state.admin_id
    ):
        return (
            "admin:"
            + str(st.session_state.admin_id)
        )

    return browser_id


def create_new_chat():

    chat_owner_id = get_chat_owner_id()

    chat = chat_service.create_chat(
        browser_id=chat_owner_id,
    )

    st.session_state.active_chat_id = (
        chat["id"]
    )

    return chat


def ensure_active_chat():

    chat_owner_id = get_chat_owner_id()

    chats = chat_service.list_chats(
        chat_owner_id
    )

    active_chat_id = (
        st.session_state.active_chat_id
    )

    if active_chat_id:

        active_chat = (
            chat_service.get_chat(
                browser_id=chat_owner_id,
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

    st.session_state.active_chat_id = None

    return None

def get_active_messages():

    active_chat_id = (
        st.session_state.active_chat_id
    )

    if not active_chat_id:
        return []

    return chat_service.get_messages(
        browser_id=get_chat_owner_id(),
        chat_id=active_chat_id,
    )

def update_chat_title(
    question: str,
):

    chat = chat_service.get_chat(
        browser_id=get_chat_owner_id(),
        chat_id=(
            st.session_state.active_chat_id
        ),
    )

    if (
        chat is not None
        and chat["title"] == "New Chat"
    ):

        chat_service.update_title(
            browser_id=get_chat_owner_id(),
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

    import fitz

    manager = DocumentManager()

    document_id = (
        manager.get_active_document_id()
    )

    pdf_path = manager.get_upload_path(
        document_id
    )

    seen_pages = set()
    references = []

    for reference in page_references:

        page_number = reference.get(
            "page_number"
        )

        if (
            not page_number
            or page_number in seen_pages
        ):
            continue

        seen_pages.add(page_number)
        references.append(reference)

        if len(references) >= 2:
            break

    if not references:
        return

    try:

        pdf = fitz.open(pdf_path)

        for reference in references:

            page_number = reference.get(
                "page_number"
            )

            st.markdown(
                f"### PDF page {page_number}"
            )

            page_index = int(page_number) - 1

            if not (
                0 <= page_index < len(pdf)
            ):
                st.info(
                    f"PDF page {page_number} "
                    f"is unavailable."
                )
                continue

            page = pdf[page_index]

            pixmap = page.get_pixmap(
                matrix=fitz.Matrix(1.5, 1.5),
                alpha=False,
            )

            image_bytes = pixmap.tobytes(
                "png"
            )

            st.image(
                image_bytes,
                caption=(
                    f"Original prospectus - "
                    f"page {page_number}"
                ),
                use_container_width=True,
            )

        pdf.close()

        with pdf_path.open("rb") as pdf_file:

            st.download_button(
                label=(
                    "Open / download full "
                    "prospectus"
                ),
                data=pdf_file.read(),
                file_name=pdf_path.name,
                mime="application/pdf",
                use_container_width=True,
                key=(
                    "prospectus_download_"
                    + "_".join(
                        str(
                            reference.get(
                                "page_number"
                            )
                        )
                        for reference
                        in references
                    )
                ),
            )

    except Exception as error:

        st.info(
            "The source page preview could "
            f"not be displayed: {error}"
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
        get_chat_owner_id()
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

            admin = admin_auth_service.authenticate(
                username=username,
                password=password,
            )

            if admin is not None:

                st.session_state[
                    "authenticated_admin"
                ] = True

                st.session_state[
                    "admin_id"
                ] = admin["id"]

                st.session_state[
                    "admin_username"
                ] = admin["username"]

                st.session_state.active_chat_id = None

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

            st.session_state[
                "admin_id"
            ] = None

            st.session_state[
                "admin_username"
            ] = None

            st.session_state.current_page = (
                "Chat"
            )

            st.session_state.active_chat_id = None

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

    st.subheader("Prospectus Documents")

    documents = manager.list_documents()

    if not documents:

        st.info(
            "No prospectus documents are registered."
        )

    for document in documents:

        document_id = document["document_id"]

        col_info, col_delete = st.columns(
            [5, 1]
        )

        with col_info:

            active_label = ""

            if (
                document_id
                == manager.load_registry().get(
                    "active_document_id"
                )
            ):
                active_label = " ? Active"

            st.markdown(
                f"**{document['filename']}**"
                f"{active_label}"
            )

            st.caption(
                f"Year: {document['year']}  |  "
                f"Status: {document['status']}"
            )

        with col_delete:

            if st.button(
                "Delete",
                key=(
                    f"delete_document_"
                    f"{document_id}"
                ),
                use_container_width=True,
            ):

                manager.delete_document(
                    document_id
                )

                load_answer_generator.clear()

                st.success(
                    "Prospectus deleted."
                )

                st.rerun()


    st.divider()

    st.subheader("Upload Prospectus")

    uploaded_file = st.file_uploader(
        "Choose a PDF prospectus",
        type=["pdf"],
        key="prospectus_uploader",
    )

    if uploaded_file is not None:

        st.write(
            f"Selected: "
            f"**{uploaded_file.name}**"
        )

        prospectus_year = st.number_input(
            "Prospectus year",
            min_value=2000,
            max_value=2100,
            value=2026,
            step=1,
        )

        process_clicked = st.button(
            "Process Prospectus",
            type="primary",
            use_container_width=True,
        )

        if process_clicked:

            safe_name = Path(
                uploaded_file.name
            ).name

            if not safe_name.lower().endswith(
                ".pdf"
            ):
                st.error(
                    "Only PDF files are allowed."
                )
                st.stop()

            uploads_dir = (
                PROJECT_ROOT
                / "storage"
                / "uploads"
            )

            uploads_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            upload_path = (
                uploads_dir
                / safe_name
            )

            document_id = (
                upload_path.stem
            )

            existing_ids = {
                document["document_id"]
                for document
                in manager.list_documents()
            }

            if document_id in existing_ids:

                st.error(
                    "A prospectus with this "
                    "filename is already registered. "
                    "Rename the PDF or delete the "
                    "existing document first."
                )

                st.stop()

            try:

                with st.status(
                    "Processing prospectus...",
                    expanded=True,
                ) as status:

                    st.write(
                        "1/4 Saving uploaded PDF..."
                    )

                    upload_path.write_bytes(
                        uploaded_file.getvalue()
                    )

                    st.write(
                        "2/4 Registering document..."
                    )

                    manager.register_document(
                        pdf_path=upload_path,
                        year=int(
                            prospectus_year
                        ),
                        status="uploaded",
                    )

                    st.write(
                        "3/4 Parsing and indexing..."
                    )

                    processor = (
                        RescueDocumentProcessingService()
                    )

                    result = processor.process(
                        document_id=document_id
                    )

                    st.write(
                        "4/4 Activating prospectus..."
                    )

                    load_answer_generator.clear()

                    status.update(
                        label=(
                            "Prospectus ready."
                        ),
                        state="complete",
                        expanded=True,
                    )

                st.success(
                    f"{safe_name} is now active. "
                    f"Indexed {result['chunks']} chunks."
                )

                time.sleep(1)

                st.rerun()

            except Exception as error:

                st.error(
                    f"Processing failed: {error}"
                )

                st.warning(
                    "The previous active prospectus "
                    "has not been replaced."
                )


    st.divider()

    st.subheader("Admin Settings")

    st.caption(
        f"Signed in as "
        f"**{st.session_state.admin_username}**"
    )

    with st.form(
        "change_admin_password"
    ):

        current_password = st.text_input(
            "Current password",
            type="password",
        )

        new_password = st.text_input(
            "New password",
            type="password",
        )

        confirm_password = st.text_input(
            "Confirm new password",
            type="password",
        )

        change_password_submitted = (
            st.form_submit_button(
                "Change Password",
                use_container_width=True,
            )
        )

    if change_password_submitted:

        if new_password != confirm_password:

            st.error(
                "New passwords do not match."
            )

        else:

            try:

                changed = (
                    admin_auth_service
                    .change_password(
                        admin_id=(
                            st.session_state.admin_id
                        ),
                        current_password=(
                            current_password
                        ),
                        new_password=(
                            new_password
                        ),
                    )
                )

                if changed:

                    st.success(
                        "Password changed successfully."
                    )

                else:

                    st.error(
                        "Current password is incorrect."
                    )

            except ValueError as error:

                st.error(str(error))

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

    if not st.session_state.active_chat_id:
        create_new_chat()

    update_chat_title(question)

    chat_service.add_message(
        browser_id=get_chat_owner_id(),
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
                    browser_id=get_chat_owner_id(),
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

                # The rescue answer service must receive the raw current
                # question. Passing conversation history here corrupts
                # intent detection for seats, abbreviations, and fallbacks.
                contextual_question = question


                with st.spinner(
                    "Searching the prospectus..."
                ):

                    result = (
                        answer_generator.answer(
                            question=contextual_question,
                            top_k=8,
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
                    browser_id=get_chat_owner_id(),
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
                browser_id=get_chat_owner_id(),
                chat_id=(
                    st.session_state.active_chat_id
                ),
                role="assistant",
                content=error_message,
            )