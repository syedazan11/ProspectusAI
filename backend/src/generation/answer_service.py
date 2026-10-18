import os
import time
import re
from pathlib import Path
from typing import Any
from collections.abc import Generator
from dotenv import load_dotenv
from groq import Groq, RateLimitError
from src.conversation.models import (
    ConversationRequest,
)
from src.retrieval.retriever import Retriever
from src.retrieval.models import (
    RetrievalPlan,
    RetrievalIntent,
)
from src.retrieval.curriculum_question_router import (
    CurriculumQuestionRouter,
)
from src.retrieval.curriculum_retriever import (
    CurriculumRetriever,
)
from src.retrieval.programme_entity_resolver import (
    ProgrammeEntityResolver,
)
from src.processing.prospectus.seat_distribution_router import (
    SeatDistributionRouter,
)
from src.services.document_manager import (
    DocumentManager,
)
from src.generation.context_builder import (
    ContextBuilder,
)
from src.retrieval.planner import( 
    RetrievalPlanner,
)
from src.conversation.session import ConversationTopic
from dataclasses import dataclass

PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(
    PROJECT_ROOT / ".env"
)

@dataclass(slots=True)
class PreparedAnswer:

    question: str

    plan: RetrievalPlan

    chunks: list[dict[str, Any]]

    selected_chunks: list[dict[str, Any]]

    context: str

    has_complex_table: bool

    early_return: dict[str, Any] | None = None

class RescueAnswerService:

    def __init__(
        self,
        collection_name: str,
    ):

        self.collection_name = collection_name

        self.retriever = Retriever(
            collection_name=collection_name,
        )

        self.curriculum_router = CurriculumQuestionRouter()

        self.curriculum_retriever = CurriculumRetriever(
            collection_name=collection_name,
        )

        self.document_manager = DocumentManager()
        self.seat_router = SeatDistributionRouter()
        self._context_builder = (
            ContextBuilder()
        )

        api_key = os.getenv("LLM_API_KEY")

        if not api_key:
            raise RuntimeError(
                "LLM_API_KEY is missing."
            )

        self.client = Groq(
            api_key=api_key,
            max_retries=0,
        )

        self.model = os.getenv(
            "LLM_MODEL"
        )

        if not self.model:
            raise RuntimeError(
                "LLM_MODEL is missing."
            )


    def answer(
        self,
        request: ConversationRequest,
        top_k: int = 8,
    ) -> dict[str, Any]:
        prepared = self._prepare_answer(
            request=request,
            top_k=top_k,
        )

        if prepared.early_return is not None:

            return prepared.early_return
        
        question = prepared.question

        chunks = prepared.chunks

        selected_chunks = prepared.selected_chunks

        context = prepared.context

        has_complex_table = prepared.has_complex_table

        prompt = self._build_prompt(
            question=request.rewritten_query,
            context=context,
            has_complex_table=(
                has_complex_table
            ),
        )

        
        answer = self._call_groq(
            prompt=prompt,
            max_tokens=650,
        )

        print("[GROQ ANSWER]")
        print(answer)
        
        if self._is_abstention(answer):

            return self._not_found(
                question
            )

        page_references = []

        page_references = (
            self._build_page_references(
                chunks=selected_chunks,
                answer=answer,
                complex_only=has_complex_table,
            )
        )

        status = "answered"

        if page_references:

            status = (
                "answered_with_page_review"
            )

        result = {
            "question": question,
            "answer": answer,
            "status": status,
            "sources": self._build_sources(
                chunks
            ),
            "page_references": (
                page_references
            ),
        }

        return result

    def stream_answer(
        self,
        request: ConversationRequest,
        top_k: int = 8,
    ) -> Generator[dict[str, Any], None, None]:
        
        prepared = self._prepare_answer(
            request=request,
            top_k=top_k,
        )

        if prepared.early_return is not None:
            yield {
                "type": "done",
                "result": prepared.early_return,
            }
            return

        question = prepared.question

        chunks = prepared.chunks

        selected_chunks = prepared.selected_chunks

##change on 17 oct
        # if prepared.plan.intent == RetrievalIntent.PEOPLE:
        if (
            prepared.plan.intent == RetrievalIntent.PEOPLE
            and request.requested_person_name is None
        ):
            named_people = []

            for chunk in selected_chunks:
                content = chunk.get("content", "")

                match = re.search(
                    r"(?ms)^Name:\s*\n\s*(.+?)\s*\n\s*Role:\s*\n\s*(.+?)\s*\n\s*Department:\s*\n\s*(.+?)\s*\n\s*Qualifications:\s*\n(.*?)(?:\n\s*Source Page:|\Z)",
                    content,
                )

                if match:
                    named_people.append(
                        {
                            "name": match.group(1).strip(),
                            "role": match.group(2).strip(),
                            "department": match.group(3).strip(),
                            "qualifications": match.group(4).strip(),
                        }
                    )

            if len(named_people) > 5:
                # print(
                #     f"[PEOPLE LIST] Direct formatting "
                #     f"for {len(named_people)} named people."
                # )

                lines = [
                    f"**{named_people[0]['role']} – "
                    f"{named_people[0]['department'].replace('Department of ', 'Department of ')}**"
                ]

                for person in named_people:
                    qualification = person["qualifications"].replace(
                        "- ",
                        "",
                    )

                    lines.append(
                        f"- **{person['name']}** – "
                        f"{qualification}"
                    )

                answer = "\n".join(lines)

                yield {
                    "type": "token",
                    "content": answer,
                }

                yield {
                    "type": "done",
                    "result": {
                        "question": question,
                        "answer": answer,
                        "status": "answered",
                        "sources": self._build_sources(
                            chunks
                        ),
                        "page_references": self._build_page_references(
                            chunks=selected_chunks,
                            answer=answer,
                            complex_only=prepared.has_complex_table,
                        ),
                    },
                }

                return

        context = prepared.context

        has_complex_table = prepared.has_complex_table

        prompt = self._build_prompt(
            question=request.rewritten_query,
            context=context,
            has_complex_table= has_complex_table,
        )
        system_prompt = self._system_prompt()

        print(
            f"[GROQ REQUEST] "
            f"system_chars={len(system_prompt)} "
            f"system_est_tokens={len(system_prompt) // 4} "
            f"prompt_chars={len(prompt)} "
            f"prompt_est_tokens={len(prompt) // 4} "
            f"combined_est_tokens="
            f"{(len(system_prompt) + len(prompt)) // 4}"
        )

        llm_start = time.perf_counter()
        first_token_time = None
        answer_parts = []
        stream_meta = {}

        for token in self._stream_groq(
            prompt=prompt,
            max_tokens=1200,
            stream_meta=stream_meta,
        ):
            if first_token_time is None:
                first_token_time = time.perf_counter()
                print(
                    f"[TIMING] Groq first token: "
                    f"{first_token_time - llm_start:.3f}s"
                )
            answer_parts.append(token)

            yield {
                "type": "token",
                "content": token,
            }

        llm_end = time.perf_counter()

        print(
            f"[TIMING] Groq generation total: "
            f"{llm_end - llm_start:.3f}s"
        )

        answer = "".join(answer_parts).strip()

#         if stream_meta.get("finish_reason") == "length":
#             print("[GROQ RECOVERY] Continuing incomplete answer.")

#             max_continuations = 4

#             for continuation_number in range(max_continuations):
#                 continuation_prompt = f"""
# Continue the answer below from exactly where it ends.

# Rules:
# - Do not repeat any part of the existing answer.
# - Continue the final sentence if it is incomplete.
# - Preserve the existing Markdown formatting.
# - Include all remaining important facts supported by the context.
# - Do not restart the answer or add a new introduction.
# - Return only the continuation text.

# PROSPECTUS CONTEXT:
# {context}

# USER QUESTION:
# {request.rewritten_query}

# ANSWER SO FAR:
# {answer}
# """.strip()

#                 continuation_meta = {}
#                 continuation_parts = []

#                 for retry_number in range(3):
#                     try:
#                         continuation_parts = []

#                         for token in self._stream_groq(
#                             prompt=continuation_prompt,
#                             max_tokens=1200,
#                             stream_meta=continuation_meta,
#                         ):
#                             continuation_parts.append(token)

#                         break

#                     except RateLimitError as exc:
#                         error_text = str(exc)
#                         wait_match = re.search(
#                             r"try again in ([\d.]+)s",
#                             error_text,
#                             re.IGNORECASE,
#                         )

#                         wait_seconds = (
#                             float(wait_match.group(1))
#                             if wait_match
#                             else None
#                         )

#                         if wait_seconds is None :
#                             raise

#                         if retry_number >= 2:
#                             raise

#                         print(
#                             f"[GROQ RECOVERY] Rate limit reached. "
#                             f"Retrying in {wait_seconds:.1f}s "
#                             f"(retry {retry_number + 1}/2)."
#                         )

#                         time.sleep(wait_seconds + 1)

#                 continuation = "".join(continuation_parts)
#                 continuation = "".join(continuation_parts)

#                 if not continuation.strip():
#                     print(
#                         "[GROQ RECOVERY] Empty continuation; stopping."
#                     )
#                     break

#                 answer = answer.rstrip() + " " + continuation.lstrip()

#                 print(
#                     f"[GROQ RECOVERY] Continuation "
#                     f"{continuation_number + 1}/{max_continuations}; "
#                     f"finish_reason="
#                     f"{continuation_meta.get('finish_reason')}"
#                 )

#                 if continuation_meta.get("finish_reason") != "length":
#                     break

#             else:
#                 print(
#                     "[GROQ RECOVERY] Safety limit reached; "
#                     "the answer may still be incomplete."
#                 )

#             yield {
#                 "type": "replace",
#                 "content": answer,
#             }


#changes made 15 oct
        if stream_meta.get("finish_reason") == "length":
            print(
                "[GROQ RECOVERY] Generation hit length limit."
            )

            recovery_prompt = f"""
The previous answer was cut off before it was complete.

Rewrite the answer to the user's question from the supplied
prospectus context.

Return ONLY the final answer.
Keep it concise but complete.
Do not mention that the previous answer was cut off.
Do not mention this recovery request.
Do not omit important supported facts.

PROSPECTUS CONTEXT:
{context}

USER QUESTION:
{request.rewritten_query}
""".strip()

            recovery_answer = self._call_groq(
                prompt=recovery_prompt,
                max_tokens=1200,
            )

            if recovery_answer:
                print(
                    "[GROQ RECOVERY] Answer generated successfully."
                )

                yield {
                    "type": "replace",
                    "content": recovery_answer,
                }

                answer = recovery_answer

        print("\n========== FINAL STREAMED ANSWER ==========")
        print(repr(answer))
        print("============================================")

        # if self._is_abstention(answer):
        if not answer or self._is_abstention(answer):

            fallback = self._not_found(question)
            print("[FALLBACK RESULT]", fallback)

            fallback["page_references"] = [
                ref
                for ref in fallback.get("page_references", [])
                if not ref.get("page_number")
            ]

            print("\n========== ABSTENTION FALLBACK DEBUG ==========")
            print(fallback)
            print("===============================================")

            yield {
                "type": "done",
                # "result": self._not_found(question),
                "result": fallback,
            }
            return

        page_references = []

        page_references = (
            self._build_page_references(
                chunks=selected_chunks,
                answer=answer,
                complex_only=prepared.has_complex_table,
            )
        )

        status = "answered"

        if page_references:

            status = (
                "answered_with_page_review"
            )

        result = {
                "question": question,
                "answer": answer,
                "status": status,
                "sources": self._build_sources(
                    chunks
                ),
                "page_references": (
                    page_references
                ),
            }
        
        yield {
            "type": "done",
            "result": result,
        }
    
    def _prepare_answer(
        self,
        request: ConversationRequest,
        top_k: int,
    ) -> PreparedAnswer:
        question = request.rewritten_query
        plan = RetrievalPlanner.plan(
            query=question,
        )

        conversation_history = (
            request.session.recent_turns
            if request.session is not None
            else request.state.recent_messages
        )

        question = question.strip()

        if not question:
            raise ValueError(
                "Question cannot be empty."
            )


        active_document = (
            self.document_manager.get_active_document()
        )

        curriculum_selection = (
            self._handle_curriculum_selection(
                # question=request.rewritten_query,
                question=request.original_query,
                conversation_history=conversation_history,
                active_document=active_document,
            )
        )

        if curriculum_selection is not None:
            return PreparedAnswer(
                question=question,
                plan=plan,
                chunks=[],
                selected_chunks=[],
                context="",
                has_complex_table=False,
                early_return=curriculum_selection,
            )
        curriculum_year_selection = (
            self._handle_curriculum_year_selection(
                # question=request.rewritten_query,
                 question=request.original_query,
                conversation_history=conversation_history,
                active_document=active_document,
            )
        )

        if curriculum_year_selection is not None:
            return PreparedAnswer(
                question=question,
                plan=plan,
                chunks=[],
                selected_chunks=[],
                context="",
                has_complex_table=False,
                early_return=curriculum_year_selection,
            )

        sections_path = (
            self.document_manager.storage_dir
            / "sections"
            / (
                f"{active_document['document_id']}"
                ".json"
            )
        )

        curriculum_response = None

        if plan.intent == RetrievalIntent.GENERAL:

            curriculum_start = time.perf_counter()
            curriculum_response = self._handle_curriculum_question(
                question=request.rewritten_query,
                active_document=active_document,
                conversation_history=conversation_history,
            )

            print(
                f"[TIMING] Curriculum handling: "
                f"{time.perf_counter() - curriculum_start:.3f}s"
            )

            if curriculum_response is not None:
                return PreparedAnswer(
                    question=question,
                    plan=plan,
                    chunks=[],
                    selected_chunks=[],
                    context="",
                    has_complex_table=False,
                    early_return=curriculum_response,
                )
        
        seat_start = time.perf_counter()

        seat_response = self.seat_router.route(
            question=request.rewritten_query,
            official_url=active_document.get(
                "official_url"
            ),
            sections_path=sections_path,
            
            )
        print(
            f"[TIMING] Seat routing: "
            f"{time.perf_counter() - seat_start:.3f}s"
        )
        
        if seat_response is not None:
            return PreparedAnswer(
                question=question,
                plan=plan,
                chunks=[],
                selected_chunks=[],
                context="",
                has_complex_table=False,
                early_return=seat_response,
            )
        
        recent_history = (
            conversation_history or []
        )[-20:]

        retrieval_query = (
            self._build_retrieval_query(
                question=request.rewritten_query,
                conversation_history=recent_history,
            )
        )

        retrieval_start = time.perf_counter()

        print(
            f"[FEE ROUTING DEBUG] query={retrieval_query!r} "
            f"intent={plan.intent} "
            f"is_follow_up={request.is_follow_up} "
            f"requested_person_name={request.requested_person_name!r} "
            f"session_topic={request.session.context.topic if request.session else None}"
        )


        retrieval = self.retriever.retrieve(
            query=retrieval_query,
            top_k=min(
                max(top_k, 8),
                12,
            ),
            # is_follow_up=bool(recent_history),
            is_follow_up=request.is_follow_up,
            context=(
                ##change on 17 oct
                # {
                #     "topic": (
                #         request.session.context.topic.value
                #         if request.session.context.topic
                #         else None
                #     ),
                #     "department": request.session.context.department,
                #     "programme": request.session.context.programme,
                #     "person_name": request.session.context.person_name,
                #     # "person_name": (
                #     #     None
                #     #     if not request.is_follow_up
                #     #     else request.session.context.person_name
                #     # ),
                #     # "person_name": (
                #     #     None
                #     #     if (
                #     #         not request.is_follow_up
                #     #         and request.pending_context
                #     #         and request.pending_context.get("person_role")
                #     #     )
                #     #     else request.session.context.person_name
                #     # ),
                #     "role": request.session.context.person_role,
                # }
                # if request.session is not None
                # else None
                {
                    "topic": (
                        "people"
                        if (
                            request.requested_person_name is not None
                            or plan.intent == RetrievalIntent.PEOPLE
                            or (
                                request.is_follow_up
                                and request.session.context.topic
                                == ConversationTopic.PEOPLE
                            )
                        )
                        else (
                            request.session.context.topic.value
                            if request.is_follow_up
                            and request.session.context.topic
                            else None
                        )
                    ),
                    "department": (
                        request.session.context.department
                        if (
                            request.is_follow_up
                            or plan.intent == RetrievalIntent.PEOPLE
                        )
                        else None
                    ),
                    "programme": (
                        request.session.context.programme
                        if (
                            request.is_follow_up
                            or plan.intent == RetrievalIntent.PEOPLE
                        )
                        else None
                    ),
                    "person_name": (
                        request.requested_person_name
                        if request.requested_person_name is not None
                        else (
                            request.session.context.person_name
                            if request.is_follow_up
                            else None
                        )
                    ),
                    "role": (
                        request.session.context.person_role
                        if (
                            request.is_follow_up
                            or plan.intent == RetrievalIntent.PEOPLE
                        )
                        else None
                    ),
                }
                if request.session is not None
                else (
                    {
                        "topic": "people",
                        "person_name": request.requested_person_name,
                    }
                    if request.requested_person_name is not None
                    else None
                )  
            ),
        )
        print(
            f"[TIMING] Main retrieval: "
            f"{time.perf_counter() - retrieval_start:.3f}s"
        )

        plan = retrieval["plan"]

        chunks = retrieval["chunks"]

        # chunks = self.retriever.retrieve(
        #     query=retrieval_query,
        #     top_k=min(
        #         max(top_k, 8),
        #         12,
        #     ),
        # )

        # print("\n========== RETRIEVER RETURNED ==========")

        # for i, chunk in enumerate(chunks[:15], 1):
        #     print(
        #         i,
        #         chunk.get("chunk_id"),
        #         chunk.get("page_number"),
        #         chunk.get("heading"),
        #         chunk.get("final_score"),
        #     )

        # print("========================================")

        if not chunks:

            return PreparedAnswer(
                question=question,
                plan=plan,
                chunks=[],
                selected_chunks=[],
                context="",
                has_complex_table=False,
                early_return=self._not_found(
                    question
                )
            )
        
        candidate_pages = []

        for chunk in chunks[:5]:

            page_number = chunk.get(
                "page_number"
            )

            if (
                page_number is not None
                and page_number
                not in candidate_pages
            ):
                candidate_pages.append(
                    page_number
                )

        table_start = time.perf_counter()

        table_companions = (
            self.retriever
            .retrieve_page_chunks(
                page_numbers=candidate_pages,
                complex_only=True,
            )
        )

        print(
            f"[TIMING] Table companions: "
            f"{time.perf_counter() - table_start:.3f}s"
        )

        seen_chunk_ids = {
            chunk.get("chunk_id")
            for chunk in chunks
        }

        for companion in table_companions:

            chunk_id = companion.get(
                "chunk_id"
            )

            if chunk_id in seen_chunk_ids:
                continue

            chunks.append(companion)

            seen_chunk_ids.add(
                chunk_id
            )

        context_start = time.perf_counter()

        context_result = self._context_builder.build(
            plan=plan,
            chunks=chunks,
        )
        print(
            f"[TIMING] Context builder: "
            f"{time.perf_counter() - context_start:.3f}s"
        )

        context = context_result["context"]
        selected_chunks = context_result["selected_chunks"]

        # if plan.intent == RetrievalIntent.PEOPLE:
            # print(
            #     "[PEOPLE ANSWER INPUT]",
            #     [
            #         {
            #             "chunk_id": chunk.get("chunk_id"),
            #             "name": re.search(
            #                 r"(?mi)^Name:\s*(?:\n\s*)?(.+)$",
            #                 chunk.get("content", ""),
            #             ).group(1).strip()
            #             if re.search(
            #                 r"(?mi)^Name:\s*(?:\n\s*)?(.+)$",
            #                 chunk.get("content", ""),
            #             )
            #             else None,
            #             "role": re.search(
            #                 r"(?mi)^Role:\s*(?:\n\s*)?(.+)$",
            #                 chunk.get("content", ""),
            #             ).group(1).strip()
            #             if re.search(
            #                 r"(?mi)^Role:\s*(?:\n\s*)?(.+)$",
            #                 chunk.get("content", ""),
            #             )
            #             else None,
            #             "department": re.search(
            #                 r"(?mi)^Department:\s*(?:\n\s*)?(.+)$",
            #                 chunk.get("content", ""),
            #             ).group(1).strip()
            #             if re.search(
            #                 r"(?mi)^Department:\s*(?:\n\s*)?(.+)$",
            #                 chunk.get("content", ""),
            #             )
            #             else None,
            #         }
            #         for chunk in selected_chunks
            #     ],
            # )

        print("\n========== FINAL LLM CONTEXT ==========")
        print(context)
        print("========================================")

        has_complex_table = any(
            bool(
                chunk.get(
                    "is_complex_table",
                    False,
                )
            )
            for chunk in chunks
        )

        return PreparedAnswer(

            question=question,

            plan=plan,

            chunks=chunks,

            selected_chunks=selected_chunks,

            context=context,

            has_complex_table=has_complex_table,
        )

    
    def _handle_curriculum_selection(
        self,
        question: str,
        conversation_history: list[dict[str, Any]] | None,
        active_document: dict,
    ):
        if not conversation_history:
            return None

        # last_assistant = None

        # for message in reversed(conversation_history):
        #     if message.get("role") == "assistant":
        #         last_assistant = message
        #         break

        # if last_assistant is None:
        #     return None

        # curriculum_route = (
        #     last_assistant.get("curriculum_route", {}) or {}
        # )

        print("\n========== CURRICULUM HISTORY DEBUG ==========")
        print(conversation_history)
        print("==============================================")

        last_assistant = None

        for message in reversed(conversation_history):
            if message.get("role") == "assistant":
                last_assistant = message
                break

        print("\n========== LAST ASSISTANT DEBUG ==========")
        print(last_assistant)
        print("==========================================")

        if last_assistant is None:
            return None

        curriculum_route = (
            last_assistant.get("curriculum_route", {}) or {}
        )

        print(
            "\n========== CURRICULUM ROUTE DEBUG =========="
        )
        print(curriculum_route)
        print("============================================")

        print(
            "[CURRICULUM SELECTION DEBUG]",
            "question=", question,
            "route=", curriculum_route,
        )

        if curriculum_route.get("status") != "awaiting_programme_selection":
            return None

        selection_map = {
            "1": 0,
            "one": 0,
            "first": 0,
            "first one": 0,
            "main campus": 0,
            "karachi campus": 0,
            "2": 1,
            "two": 1,
            "second": 1,
            "second one": 1,
            "tiest": 1,
            "thar institute": 1,
            "thar": 1,
        }

        selection = selection_map.get(
            question.casefold().strip()
        )

        if selection is None:
            return None

        programme_matches = curriculum_route.get(
            "programme_matches",
            [],
        )

        if selection >= len(programme_matches):
            return {
                "question": question,
                "answer": "Please choose one of the listed programmes.",
                "status": "curriculum_ambiguous",
                "sources": [],
                "page_references": [],
                "curriculum_route": curriculum_route,
            }

        selected = programme_matches[selection]

        print("\n===== SELECTED PROGRAMME =====")
        print(selected)
        print("==============================\n")

        route = {
            "programme": selected["programme"],
            "programme_code": selected["programme_code"],
            "study_year": curriculum_route.get("study_year"),
            "semester": curriculum_route.get("semester"),
            "course_code": curriculum_route.get("course_code"),
        }
        #
        # Ask for study year before retrieving anything.
        #
        if (
            route["study_year"] is None
            and route["course_code"] is None
        ):
            return {
                "question": question,
                "answer": (
                    f"Which study year of {route['programme']} would you like to see?\n\n"
                    "1. First Year\n"
                    "2. Second Year\n"
                    "3. Third Year\n"
                    "4. Final Year"
                ),
                "status": "curriculum_year_selection",
                "sources": [],
                "page_references": [],
                "curriculum_route": {
                    **route,
                    "status": "awaiting_study_year",
                },
            }

        curriculum_retriever = CurriculumRetriever(
            collection_name=self.collection_name,
            document_id=active_document["document_id"],
        )

        records = curriculum_retriever.retrieve(
            programme_code=route["programme_code"],
            study_year=route.get("study_year"),
            semester=route.get("semester"),
            course_code=route.get("course_code"),
            limit=200,
        )
        print("\n[CURRICULUM DEBUG] retrieved records:")
        print(f"count={len(records)}")
        for record in records:
            print(
                record.get("programme_code"),
                "|",
                record.get("programme"),
                "|",
                record.get("course_code"),
                "|",
                record.get("course_title"),
                "|",
                record.get("study_year"),
                "|",
                record.get("semester"),
            )
        print(
            "[CURRICULUM SELECTION] selected programme:",
            route,
            "records:",
            len(records),
        )

        if not records:
            return None

        return {
            "question": question,
            "answer": self._format_curriculum_answer(
                route=route,
                records=records,
            ),
            "status": "curriculum_answered",
            "sources": [],
            "page_references": self._build_curriculum_page_references(
                records=records,
                official_url=active_document.get(
                    "official_url"
                ),
            ),
            "curriculum_route": route,
        }
    
    def _handle_curriculum_year_selection(
        self,
        question: str,
        conversation_history: list[dict[str, Any]] | None,
        active_document: dict,
    ):
        if not conversation_history:
            return None

        last_assistant = None

        for message in reversed(conversation_history):
            if message.get("role") == "assistant":
                last_assistant = message
                break

        if last_assistant is None:
            return None

        curriculum_route = (
            last_assistant.get("curriculum_route", {}) or {}
        )

        if (
            curriculum_route.get("status")
            != "awaiting_study_year"
        ):
            return None

        year_map = {
            "1": "FIRST YEAR",
            "1st": "FIRST YEAR",
            "first": "FIRST YEAR",
            "first year": "FIRST YEAR",

            "2": "SECOND YEAR",
            "2nd": "SECOND YEAR",
            "second": "SECOND YEAR",
            "second year": "SECOND YEAR",

            "3": "THIRD YEAR",
            "3rd": "THIRD YEAR",
            "third": "THIRD YEAR",
            "third year": "THIRD YEAR",

            "4": "FINAL YEAR",
            "4th": "FINAL YEAR",
            "fourth": "FINAL YEAR",
            "final": "FINAL YEAR",
            "final year": "FINAL YEAR",
        }

        study_year = year_map.get(
            question.casefold().strip()
        )

        if study_year is None:
            return {
                "question": question,
                "answer": (
                    "Please choose:\n\n"
                    "1. First Year\n"
                    "2. Second Year\n"
                    "3. Third Year\n"
                    "4. Final Year"
                ),
                "status": "curriculum_year_selection",
                "sources": [],
                "page_references": [],
                "curriculum_route": curriculum_route,
            }

        route = {
            **curriculum_route,
            "study_year": study_year,
        }

        curriculum_retriever = CurriculumRetriever(
            collection_name=self.collection_name,
            document_id=active_document["document_id"],
        )

        records = curriculum_retriever.retrieve(
            programme_code=route["programme_code"],
            study_year=route["study_year"],
            semester=None,
            course_code=route.get("course_code"),
            limit=200,
        )

        if not records:
            return None

        return {
            "question": question,
            "answer": self._format_curriculum_answer(
                route=route,
                records=records,
            ),
            "status": "curriculum_answered",
            "sources": [],
            "page_references": self._build_curriculum_page_references(
                records=records,
                official_url=active_document.get(
                    "official_url"
                ),
            ),
            "curriculum_route": route,
        }


    def _build_retrieval_query(
        self,
        question: str,
        conversation_history: list[dict[str, Any]],
    ) -> str:

        if not conversation_history:
            return question

        normalized = question.casefold().strip()

        follow_up_patterns = (
            r"\b(it|its|this|that|they|them|their|theirs|he|him|his|she|her|hers|these|those)\b",
            r"^(what|how) about\b",
            r"^(and|also)\b",
        )

        is_ambiguous_follow_up = any(
            re.search(pattern, normalized)
            for pattern in follow_up_patterns
        )

        if not is_ambiguous_follow_up:
            return question
        
        entity_hint = self._conversation_entity_hint(
            conversation_history[-20:]
        )

        print("\n========== RETRIEVAL QUERY ==========")
        print("QUESTION :", question)
        print("ENTITY   :", entity_hint)
        print(
            "HAS ENTITY:",
            self._question_has_explicit_entity(question),
        )
        print("====================================\n")

        if (
            entity_hint
            and not self._question_has_explicit_entity(
                question
            )
            and entity_hint.casefold()
            not in question.casefold()
        ):

            return (
                question.rstrip(" \t\r\n?!.,")
                + " "
                + entity_hint
            )

        history_lines = []

        for message in conversation_history[-20:]:
            role = str(
                message.get("role", "")
            ).strip()

            content = str(
                message.get("content", "")
            ).strip()[:400]

            if role in {"user", "assistant"} and content:
                history_lines.append(
                    f"{role.title()}: {content}"
                )

        if not history_lines:
            return question

        history_text = "\n".join(history_lines)

        resolver_prompt = f"""
You rewrite ambiguous follow-up questions for a
NED University prospectus search system.

Recent conversation:
{history_text}

Follow-up question:
{question}

Rewrite the follow-up as one standalone search
question.

Rules:
- Resolve pronouns such as it, this, that, they,
  and them from the conversation.
- Preserve exact abbreviations and their resolved
  meanings when known.
- Include both an abbreviation and its full form
  when the conversation provides both.
- Do not answer the question.
- Do not add facts.
- Do not change the user's intent.
- Return only the rewritten question.
"""

        try:
            resolved = self._call_groq(
                prompt=resolver_prompt,
                max_tokens=80,
            ).strip()

        except Exception:
            return question

        resolved = resolved.strip(
            " \t\r\n\"'"
        )

        if (
            not resolved
            or len(resolved) > 300
        ):
            return question

        return resolved


    def _question_has_explicit_entity(
        self,
        question: str,
    ) -> bool:

        return bool(
            re.search(
                r"\b(?:"
                r"[A-Z]{2,}(?:[-/][A-Z0-9]+)?"
                r"|[A-Z][\w&()./-]*"
                r"(?:\s+[A-Z][\w&()./-]*)+"
                r")\b",
                question,
            )
        )


    def _conversation_entity_hint(
        self,
        conversation_history: list[dict[str, Any]],
    ) -> str | None:

        if not conversation_history:
            return None

        for preferred_role in ("user", "assistant"):

            for message in reversed(conversation_history):

                role = str(
                    message.get("role", "")
                ).strip().casefold()

                if role != preferred_role:
                    continue

                content = str(
                    message.get("content", "")
                ).strip()

                hint = self._extract_entity_hint(
                    content
                )

                if hint:
                    return hint

        return None


    def _extract_entity_hint(
        self,
        text: str,
    ) -> str | None:

        text = " ".join(text.split())

        if not text:
            return None

        candidates = []

        for match in re.finditer(
            r"\b(?:of|for|in|at|from|about|to)\s+"
            r"(?:the\s+|a\s+|an\s+)?"
            r"((?:[A-Z0-9][\w&()./-]*)"
            r"(?:\s+(?:[A-Z0-9][\w&()./-]*)){0,6})",
            text,
        ):

            candidates.append(
                match.group(1).strip(" ,.;:!?")
            )

        for match in re.finditer(
            r"\b(?:[A-Z][\w&()./-]*|[A-Z]{2,})"
            r"(?:\s+(?:[A-Z][\w&()./-]*|[A-Z]{2,})){1,6}\b",
            text,
        ):

            candidates.append(
                match.group(0).strip(" ,.;:!?")
            )

        best_candidate = ""

        for candidate in candidates:

            cleaned = " ".join(candidate.split())

            if not cleaned:
                continue

            if len(cleaned) > len(best_candidate):
                best_candidate = cleaned

        if best_candidate:
            return best_candidate

        return None
    

    def _system_prompt(self) -> str:
        return """
You are ProspectusAI, the official academic assistant for the NED University.

Use ONLY the supplied prospectus context as evidence for prospectus-related
answers. Answer the user's exact question directly and naturally.

CORE EVIDENCE RULES
- Treat all supplied context as one combined evidence set.
- Use every relevant piece of evidence needed for a complete answer.
- Information may be distributed across different chunks, pages, headings,
  or general and programme-specific sections.
- Do not expose retrieval, chunks, scores, databases, RAG, or implementation.
- Never use outside knowledge to fill a missing fact.
- If the requested information is genuinely absent from the entire context,
  use the application's fallback response.
- Do not claim information is absent merely because it is missing from one
  chunk or heading.

PEOPLE
- For faculty and staff queries that mention a name, use the exact name as it appears in the context and write the answer properly formatted with the correct title, department, and qualifications (if given).
- For people/faculty/staff list queries, list each matching person's exact name and include their qualifications if given. Include the role too, but do not add unnecessary information.
- Tell the department AND qualifications of the person if asked about their department, and tell the faculty of the person if asked about their faculty.
RELATIONSHIP AND ACCURACY RULES
- Never mix departments, programmes, admission categories, schemes, years,
  campuses, institutes, people, or accommodation types.
- Preserve exact names, labels, codes, amounts, percentages, dates, credit
  hours, and other numerical values.
- Keep every value attached to its correct item and preserve parent-child
  relationships.
- When several relevant records answer the question, combine them while
  keeping their meaningful distinctions.
- A keyword match alone is not sufficient; use surrounding context.
- Do not invent, estimate, calculate, or substitute missing values.
- Absence of a statement is not proof of absence.

LISTS AND TABLES
- Preserve row/column relationships in explicit tables.
- Use a Markdown table only when the supplied context contains genuine
  row-and-column data or the user explicitly requests a table.
- Do not turn ordinary lists, facilities, services, prose, or headings into
  tables.
- For lists, use a heading and individual bullet points.
- Never over-compress a list of named items into a generic summary.
- For complex tables, keep schemes, categories, quotas, programmes,
  campuses, and years separate; never combine values unless the user asks
  for a safe total.

FACILITIES
- For broad facilities questions, include relevant university-wide facilities.
- Also include department/programme-specific facilities when explicitly
  supported.
- Distinguish university-wide facilities from department-specific ones.
- Do not infer a facility's absence from a section that simply does not
  repeat it.

ADMISSION AND ELIGIBILITY
- General undergraduate admission requirements apply to a programme unless
  the supplied context explicitly states a different programme-specific rule.
- Combine general admission requirements with supported programme-specific
  requirements.
- When the user asks for the eligibility criteria for a specific undergraduate
programme, do not require that programme name to appear explicitly inside
the retrieved eligibility section.
If the prospectus provides general eligibility conditions for undergraduate
admission, those conditions apply to the requested programme unless the
prospectus explicitly states a different programme-specific eligibility
condition.
For example:
"eligibility criteria for Electrical Engineering"

must use the general eligibility conditions from the prospectus if no
separate Electrical Engineering eligibility rule is provided.

Do NOT answer that eligibility information is unavailable merely because
"Electrical Engineering" does not appear in the retrieved eligibility
heading or text.


FEES
- Identify the complete fee section and its scope before selecting a value.
- Preserve separate programme groups, campuses/institutes, and applicant
  categories.
- Give both local and foreign fee values when supported, unless the user explicitly asks for one.
- For a normal local NED programme, use the applicable local fee unless the
  user explicitly asks for foreign/international fees.
- Do not select a fee merely because it is the highest-scoring or nearest
  record.
- For admission fees, determine the programme group covered by the relevant
  fee section and apply that group-level fee when supported.
- Do not combine adjacent fee sections belonging to different campuses or
  institutes.
- CT means Computer science and CS means Computer system engineering.

ABBREVIATIONS
- Use only meanings explicitly supported by the supplied context.
- Never guess an expansion.

ANSWER STYLE
- Match detail to the question.
- Keep answers concise but complete. Do not add unnecessary tables,
  repetition, summaries, or explanations. Include all important facts
  needed to answer the question, but stop once the answer is complete.
- Preserve names, labels, qualifiers, quantities, relationships, and
  explanatory details that make the answer accurate.
- Do not mention page numbers; the application supplies page references.
- Do not say "according to the retrieved context", "based on the context",
  "the records say", or similar implementation/source-process phrases.
- Do not expose uncertainty or retrieval limitations when the answer is
  actually supported by the supplied context.

- If the retrieved context contains relevant information about the user's
  topic or entity, use it even if it answers a related aspect rather than
  the exact wording of the query.
- Do not abstain just because the context does not exactly answer the
  rewritten query.
- Never infer or invent information beyond the retrieved context.

""".strip()


    def _user_prompt(
        self,
        *,
        context: str,
        question: str,
        table_instruction: str,
    ) -> str:

        return f"""
{table_instruction}

Use the supplied prospectus context as the complete evidence set.
Answer the user's question directly.

- If the answer is supported anywhere in the context, provide the complete
  supported answer.
- Combine relevant sections when needed, while preserving distinctions.
- If only part is supported, provide that supported part.
- If the answer is genuinely absent from the entire context, follow the
  fallback rule in the system instructions.
- Do not mention page numbers.

PROSPECTUS CONTEXT:
{context}

USER QUESTION:
{question}
""".strip()


    def _build_prompt(
        self,
        question: str,
        context: str,
        has_complex_table: bool,
    ) -> str:

        table_instruction = ""

        if has_complex_table:

            table_instruction = """
Some retrieved context may contain complex tables.

For table questions:
- Read row labels and column labels carefully.
- Keep different schemes, categories, quotas,
  programmes, campuses, and years separate.
- Never combine values unless the user asks
  for a total and the values can be safely
  combined.
- Use only values explicitly present in the
  supplied context.
- Do not estimate missing values.
- If multiple relevant groups exist and the
  question is ambiguous, report them
  separately.
"""

        return self._user_prompt(
            context=context,
            question= question,
            table_instruction=table_instruction,
        )


    def _stream_groq(
        self,
        prompt: str,
        max_tokens: int,
        stream_meta: dict[str, Any],
    ):
        request_start = time.perf_counter()

        print(
            f"[GROQ START] {id(self)} "
            f"{request_start:.6f}"
        )

        print(
            f"[GROQ MODEL] {self.model}"
        )

        stream = (
            self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._system_prompt(),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.0,
                max_tokens=max_tokens,
                stream=True,
            )
        )

        request_ready = time.perf_counter()

        print(
            f"[GROQ TIMING] stream create: "
            f"{request_ready - request_start:.3f}s"
        )

        first_chunk_time = None
        first_content_time = None
        content_chunk_count = 0
        last_chunk = None
        finish_reason = None

        for chunk in stream:
            last_chunk = chunk

            if chunk.choices:
                finish_reason = (
                    chunk.choices[0].finish_reason
                )

            now = time.perf_counter()
            if first_chunk_time is None:
                first_chunk_time = now
                print(
                    f"[GROQ TIMING] first stream chunk: "
                    f"{now - request_ready:.3f}s"
                )

            if not chunk.choices:
                continue

##changes made 14 oct
            content = (
                chunk
                .choices[0]
                .delta
                .content
            )

            # delta = chunk.choices[0].delta

            # reasoning = getattr(delta, "reasoning", None)

            # if reasoning and not stream_meta.get("_first_reasoning_logged"):
            #     stream_meta["_first_reasoning_logged"] = True
            #     print(
            #         f"[GROQ TIMING] first reasoning: "
            #         f"{time.perf_counter() - request_start:.3f}s"
            #     )

            # content = delta.content


        # for chunk in stream:

        #     content = (
        #         chunk
        #         .choices[0]
        #         .delta
        #         .content
        #     )

            if content:
                if first_content_time is None:
                    first_content_time = now

                    print(
                        f"[GROQ TIMING] first content token: "
                        f"{now - request_start:.3f}s"
                    )

                content_chunk_count += 1

                yield content

        print(
            f"[GROQ FINISH] {finish_reason}"
        )

        stream_meta["finish_reason"] = finish_reason

        stream_end = time.perf_counter()

        print(
            f"[GROQ TIMING] stream total: "
            f"{stream_end - request_start:.3f}s"
        )

        if first_content_time is not None:
            print(
                f"[GROQ TIMING] content generation: "
                f"{stream_end - first_content_time:.3f}s"
            )

        print(
            f"[GROQ TIMING] content chunks: "
            f"{content_chunk_count}"
        )

        if last_chunk is not None:

            usage = getattr(
                last_chunk,
                "usage",
                None,
            )

            print("[GROQ RAW USAGE]", usage) 

            if usage is not None:

                print(
                    "[GROQ USAGE] "
                    f"prompt={getattr(usage, 'prompt_tokens', None)} "
                    f"completion={getattr(usage, 'completion_tokens', None)} "
                    f"total={getattr(usage, 'total_tokens', None)}"
                )

                prompt_details = getattr(
                    usage,
                    "prompt_tokens_details",
                    None,
                )

                if prompt_details is not None:
                    print(
                        "[GROQ PROMPT DETAILS] "
                        f"cached={getattr(prompt_details, 'cached_tokens', None)}"
                    )


                details = getattr(
                    usage,
                    "completion_tokens_details",
                    None,
                )

                if details is not None:
                    print(
                        "[GROQ USAGE DETAILS] "
                        f"reasoning={getattr(details, 'reasoning_tokens', None)}"
                    )
            else:
                print(
                    "[GROQ USAGE] not present"
                )

        print(
            f"[GROQ END] {id(self)} "
            f"{time.perf_counter():.6f}"
        )

                


    def _call_groq(
        self,
        prompt: str,
        max_tokens: int,
    ) -> str:

        completion = (
            self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._system_prompt(),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.0,
                max_tokens=max_tokens,
            )
        )

        content = (
            completion
            .choices[0]
            .message
            .content
        )

        if not content:
            return (
                "I couldn't reliably find the "
                "exact answer in the prospectus."
            )

        return content.strip()


    
    def _expand_retrieved_context(
        self,
        chunks: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

        if not chunks:
            return []

        expanded=[]
        seen=set()

        def add(chunk):

            cid=chunk.get("chunk_id")

            if cid in seen:
                return

            expanded.append(chunk)

            if cid is not None:
                seen.add(cid)

        # Preserve every retrieved chunk.
        for chunk in chunks:
            add(chunk)

        # Only expand from specific headings.
        for chunk in list(expanded):

            heading=str(
                chunk.get(
                    "heading",
                    ""
                )
            ).strip()

            if (
                not heading
                or heading.casefold()=="prospectus 2026"
            ):
                continue

            page=chunk.get("page_number")

            if page is None:
                continue

            added=0

            for companion in self.retriever._all_chunks():

                if (
                    companion.get("page_number")!=page
                ):
                    continue

                add(companion)

                added+=1

                if added>=3:
                    break

        return expanded

    # def _context_terms(
    #     self,
    #     question: str,
    # ) -> list[str]:

    #     terms = []

    #     for term in self.retriever._query_terms(
    #         question
    #     ):

    #         folded = term.casefold()

    #         if folded not in terms:
    #             terms.append(folded)

    #     for code in self.retriever._query_codes(
    #         question
    #     ):

    #         folded = code.casefold()

    #         if folded not in terms:
    #             terms.append(folded)

    #     return terms


    def _build_page_references(
        self,
        chunks: list[dict],
        answer: str | None = None,
        complex_only: bool = False,
    ) -> list[dict[str, Any]]:
        
        active_document = self.document_manager.get_active_document()

        official_url = str(
            active_document.get("official_url") or ""
        ).strip()

        cited_pages = self._extract_cited_pages(
            answer=answer,
        )

        if cited_pages:

            referenced_pages = self._referenced_pages_by_number(
                chunks=chunks,
                page_numbers=cited_pages,
                complex_only=complex_only,
            )

            if referenced_pages:
                return referenced_pages

        # references = []
        # seen = set()

        # for chunk in chunks:

        #     if (
        #         complex_only
        #         and not chunk.get(
        #             "is_complex_table",
        #             False,
        #         )
        #     ):
        #         continue

        #     document = chunk.get(
        #         "document"
        #     )

        #     page_number = chunk.get(
        #         "page_number"
        #     )

        #     if (
        #         not document
        #         or page_number is None
        #     ):
        #         continue

        #     key = (
        #         document,
        #         page_number,
        #     )

        #     if key in seen:
        #         continue

        #     seen.add(key)

        #     page_url = None

        #     if official_url:
        #         page_url = (
        #             f"{official_url}#page={page_number}"
        #         )

        #     references.append(
        #         {
        #             "document": document,
        #             "page_number": page_number,
        #             "page_path": None,
        #             "page_url": page_url,
        #             "reason": (
        #                 "Relevant prospectus page."
        #             ),
        #         }
        #     )

        #     reference_limit = (
        #         2 if complex_only else 1
        #     )

        #     if (
        #         len(references)
        #         >= reference_limit
        #     ):
        #         break

        # return references

        references = []
        seen = set()

        # When the answer does not explicitly cite a PDF page,
        # choose the selected chunk that best supports the answer.
        #
        # This only affects page-reference generation. It does not
        # change retrieval or context ordering.
        answer_terms = set(
            re.findall(
                r"\b[a-zA-Z]{3,}\b",
                answer or "",
                flags=re.IGNORECASE,
            )
        )

        best_chunk = None
        best_score = 0

        for chunk in chunks:

            if (
                complex_only
                and not chunk.get(
                    "is_complex_table",
                    False,
                )
            ):
                continue

            document = chunk.get("document")
            page_number = chunk.get("page_number")
            content = chunk.get("content", "")

            if (
                not document
                or page_number is None
                or not content
            ):
                continue

            content_terms = set(
                re.findall(
                    r"\b[a-zA-Z]{3,}\b",
                    content,
                    flags=re.IGNORECASE,
                )
            )

            score = len(
                answer_terms & content_terms
            )

            if score > best_score:
                best_score = score
                best_chunk = chunk

        # If an answer-supporting chunk was found, use its page.
        # Otherwise preserve the old first-chunk fallback.
        ordered_chunks = []

        if best_chunk is not None:
            ordered_chunks.append(best_chunk)

        ordered_chunks.extend(
            chunk
            for chunk in chunks
            if chunk is not best_chunk
        )

        for chunk in ordered_chunks:

            if (
                complex_only
                and not chunk.get(
                    "is_complex_table",
                    False,
                )
            ):
                continue

            document = chunk.get("document")
            page_number = chunk.get("page_number")

            if (
                not document
                or page_number is None
            ):
                continue

            key = (
                document,
                page_number,
            )

            if key in seen:
                continue

            seen.add(key)

            page_url = None

            if official_url:
                page_url = (
                    f"{official_url}#page={page_number}"
                )

            references.append(
                {
                    "document": document,
                    "page_number": page_number,
                    "page_path": None,
                    "page_url": page_url,
                    "reason": (
                        "Relevant prospectus page."
                    ),
                }
            )

            reference_limit = (
                2 if complex_only else 1
            )

            if (
                len(references)
                >= reference_limit
            ):
                break

        return references


    def _extract_cited_pages(
        self,
        answer: str | None,
    ) -> list[int]:

        if not answer:
            return []

        page_numbers = []
        seen = set()

        for match in re.finditer(
            r"\bPDF\s+pages?\b",
            answer,
            flags=re.IGNORECASE,
        ):

            tail = answer[match.end(): match.end() + 60]

            for page_number in re.findall(
                r"\d+",
                tail,
            ):

                page_value = int(page_number)

                if page_value in seen:
                    continue

                seen.add(page_value)
                page_numbers.append(page_value)

        return page_numbers


    def _referenced_pages_by_number(
        self,
        chunks: list[dict],
        page_numbers: list[int],
        complex_only: bool = False,
    ) -> list[dict[str, Any]]:

        chunks_by_page = {}

        for chunk in chunks:

            if (
                complex_only
                and not chunk.get(
                    "is_complex_table",
                    False,
                )
            ):
                continue

            page_number = chunk.get(
                "page_number"
            )

            document = chunk.get(
                "document"
            )

            if (
                document is None
                or page_number is None
            ):
                continue

            chunks_by_page.setdefault(
                page_number,
                chunk,
            )

        references = []

        for page_number in page_numbers:

            chunk = chunks_by_page.get(
                page_number
            )

            if chunk is None:
                continue

            document = chunk.get(
                "document"
            )

            key = (
                document,
                page_number,
            )

            active_document = self.document_manager.get_active_document()

            official_url = str(
                active_document.get("official_url") or ""
            ).strip()

            page_url = None

            if official_url:
                page_url = (
                    f"{official_url}#page={page_number}"
                )

            references.append(
                {
                    "document": document,
                    "page_number": page_number,
                    "page_path": None,
                    "page_url": page_url,
                    "reason": (
                        "Explicit page citation in answer."
                    ),
                }
            )

            reference_limit = (
                2 if complex_only else 1
            )

            if (
                len(references)
                >= reference_limit
            ):
                break

        return references


    def _build_sources(
        self,
        chunks: list[dict],
    ) -> list[dict]:
        return []

        # sources = []
        # seen = set()

        # for chunk in chunks:

        #     document = chunk.get(
        #         "document"
        #     )

        #     page_number = chunk.get(
        #         "page_number"
        #     )

        #     key = (
        #         document,
        #         page_number,
        #     )

        #     if key in seen:
        #         continue

        #     seen.add(key)

        #     sources.append(
        #         {
        #             "document": document,
        #             "page_number": (
        #                 page_number
        #             ),
        #             "heading": chunk.get(
        #                 "heading",
        #                 "",
        #             ),
        #             "score": chunk.get(
        #                 "final_score",
        #                 chunk.get("score"),
        #             ),
        #         }
        #     )

        #     if len(sources) >= 5:
        #         break

        # return sources


    def _handle_curriculum_question(
        self,
        question: str,
        active_document: dict,
        conversation_history: list[dict[str, Any]] | None,
    ):

        records_path = (
            self.document_manager.storage_dir
            / "processed"
            / active_document["document_id"]
            / "curriculum_records_v2.json"
        )

        if not records_path.exists():
            return None

        import json

        payload = json.loads(
            records_path.read_text(encoding="utf-8")
        )

        curriculum_metadata = payload.get(
            "curriculum_metadata",
            {},
        )

        curriculum_scheme = curriculum_metadata.get(
            "curriculum_scheme",
        )

        term_names = curriculum_metadata.get(
            "term_names",
            [],
        )

        curriculum_records = payload.get(
            "records",
            payload,
        )

        # print("\n===== AVAILABLE PROGRAMMES =====")

        # seen = set()

        # for record in curriculum_records:
        #     key = (
        #         record.get("programme_code"),
        #         record.get("programme"),
        #     )

        #     if key not in seen:
        #         seen.add(key)
        #         print(key)

        # print("TOTAL:", len(seen))
        # print("===============================\n")


        route = self.curriculum_router.route(
            question= question,
            curriculum_scheme=curriculum_scheme,
            term_names=term_names,
        )

        print("\n===== CURRICULUM ROUTE =====")
        print(route)
        print("============================\n")

        if (
            route is not None
            and conversation_history
        ):

            for message in reversed(conversation_history):

                if message.get("role") != "assistant":
                    continue

                previous_route = message.get("curriculum_route")

                if not previous_route:
                    continue

                if route.get("programme_code") is None:
                    route["programme_code"] = previous_route.get("programme_code")

                if route.get("programme") is None:
                    route["programme"] = previous_route.get("programme")

                if route.get("study_year") is None:
                    route["study_year"] = previous_route.get("study_year")

                if route.get("semester") is None:
                    route["semester"] = previous_route.get("semester")

                break

        if route is None:
            return None
        
        resolver = ProgrammeEntityResolver(
            curriculum_records=curriculum_records,
        )

        programme_matches = resolver.resolve(question)
        print("\n[CURRICULUM DEBUG] programme_matches:")
        print(programme_matches)

        if not programme_matches:
            return None

        if len(programme_matches) > 1:

            options = []

            for item in programme_matches:

                sample = next(
                    (
                        r
                        for r in curriculum_records
                        if r["programme_code"] == item["programme_code"]
                    ),
                    {},
                )

                label = item["programme"]

                parent = str(
                    sample.get("parent_section", "") or ""
                ).strip()

                if (
                    "with specialization"
                    not in label.casefold()
                    and parent
                ):
                    label += f" ({parent})"

                options.append(label)

            return {
                "question": question,
                "answer":
                    "I found more than one matching programme.\n\n"
                    + "\n".join(
                        f"{i+1}. {option}"
                        for i, option in enumerate(options)
                    ),
                "status": "curriculum_ambiguous",
                "sources": [],
                "page_references": [],
                "curriculum_route": {
                    "status": "awaiting_programme_selection",
                    "programme_matches": programme_matches,
                    "study_year": route.get("study_year"),
                    "semester": route.get("semester"),
                    "course_code": route.get("course_code"),
                },
            }

        programme = programme_matches[0]

        route.update(
            {
                "programme": programme["programme"],
                "programme_code": programme["programme_code"],
            }
        )


        if route["status"] == "unsupported_study_year":
            return {
                "question": question,
                "answer": (
                    f"{programme['programme']} does not have that study year "
                    "in this prospectus. Its curriculum is available only for "
                    "First Year, Second Year, Third Year, and Final Year."
                ),
                "status": "curriculum_not_found",
                "sources": [],
                "page_references": [],
            }
        
        # If the user only asked for the curriculum, ask for the study year first.
        if (
            route.get("study_year") is None
            and route.get("semester") is None
            and route.get("course_code") is None
        ):
            return {
                "question": question,
                "answer": (
                    f"Which study year of {route['programme']} would you like to see?\n\n"
                    "1. First Year\n"
                    "2. Second Year\n"
                    "3. Third Year\n"
                    "4. Final Year"
                ),
                "status": "curriculum_year_selection",
                "sources": [],
                "page_references": [],
                "curriculum_route": {
                    "status": "awaiting_study_year",
                    "programme": route["programme"],
                    "programme_code": route["programme_code"],
                },
            }

        curriculum_retriever = CurriculumRetriever(
            collection_name=self.collection_name,
            document_id=active_document["document_id"],
        )

        records = curriculum_retriever.retrieve(
            programme_code=route["programme_code"],
            study_year=route.get("study_year"),
            semester=route.get("semester"),
            course_code=route.get("course_code"),
            limit=200,
        )

        if not records:
            return None

        return {
            "question": question,
            "answer": self._format_curriculum_answer(
                
                route=route,
                records=records,
            ),
            "status": "curriculum_answered",
            "sources": [],
            "page_references": self._build_curriculum_page_references(
                records=records,
                official_url=active_document.get(
                    "official_url"
                ),
            ),

            # Internal conversation state
            "curriculum_route": {
                "programme": route.get("programme"),
                "programme_code": route.get("programme_code"),
                "study_year": route.get("study_year"),
                "semester": route.get("semester"),
                "course_code": route.get("course_code"),
            },
        }


    @staticmethod
    def _format_curriculum_answer(
        *,
        route: dict,
        records: list[dict],
    ) -> str:

        course_code = route.get("course_code")

        if course_code:
            record = records[0]

            return (
                f"**{record.get('course_code')} — "
                f"{record.get('course_title')}**\n\n"
                f"{record.get('total_credit_hours')} total credit hours "
                f"(Theory: {record.get('theory_hours')}, "
                f"Practical: {record.get('practical_hours')})."
            )

        programme = route["programme"]

        heading_parts = [programme]

        if route.get("semester"):
            heading_parts.append(
                f"{route['semester']} Semester"
            )

        lines = [
            f"**{' — '.join(heading_parts)}**"
        ]

        if (
            route.get("semester")
            and not route.get("study_year")
        ):
            year_order = (
                "FIRST YEAR",
                "SECOND YEAR",
                "THIRD YEAR",
                "FINAL YEAR",
            )

            grouped = {}

            for record in records:
                year = str(
                    record.get("study_year", "")
                    or ""
                ).strip()

                grouped.setdefault(
                    year,
                    [],
                ).append(record)

            ordered_years = [
                year
                for year in year_order
                if year in grouped
            ]

            ordered_years.extend(
                year
                for year in grouped
                if year not in ordered_years
            )

            for year in ordered_years:

                if year:
                    lines.append("")
                    lines.append(
                        f"### {year.title()}"
                    )

                for record in grouped[year]:
                    lines.append(
                        f"- **{record.get('course_code')}**: "
                        f"{record.get('course_title')} "
                        f"({record.get('total_credit_hours')} "
                        f"credit hours)"
                    )

            return "\n".join(lines)

        grouped = {}

        for record in records:

            semester = str(
                record.get("semester", "")
                or ""
            ).strip()

            if not semester:
                semester = "Other"

            grouped.setdefault(
                semester,
                [],
            ).append(record)

        semester_order = (
            "Fall",
            "Spring",
        )

        ordered_semesters = [
            semester
            for semester in semester_order
            if semester in grouped
        ]

        ordered_semesters.extend(
            semester
            for semester in grouped
            if semester not in ordered_semesters
        )

        for semester in ordered_semesters:

            lines.append("")
            lines.append(
                f"### {semester} Semester"
            )

            lines.append("")
            lines.append(
                "| Course | Title | Credit Hours |"
            )
            lines.append(
                "|---|---|---:|"
            )

            for record in grouped[semester]:

                lines.append(
                    f"| {record.get('course_code')} "
                    f"| {record.get('course_title')} "
                    f"| {record.get('total_credit_hours')} |"
                )

        return "\n".join(lines)

    @staticmethod
    def _build_curriculum_page_references(
        *,
        records: list[dict],
        official_url: str | None,
    ) -> list[dict]:

        if not official_url:
            return []

        page_references = []
        seen_pages = set()

        for record in records:

            page_number = record.get(
                "page_number",
                record.get("source_page"),
            )

            if page_number is None:
                continue

            try:
                page_number = int(page_number)
            except (
                TypeError,
                ValueError,
            ):
                continue

            if page_number in seen_pages:
                continue

            seen_pages.add(page_number)

            page_references.append(
                {
                    "document": record.get(
                        "document",
                        "official_prospectus",
                    ),
                    "page_number": page_number,
                    "page_path": None,
                    "page_url": (
                        f"{official_url}"
                        f"#page={page_number}"
                    ),
                    "reason": (
                        "Open the prospectus page "
                        "containing the relevant "
                        "curriculum information."
                    ),
                }
            )

        return page_references

    
    @staticmethod
    def _build_curriculum_sources(
        records: list[dict],
    ) -> list[dict]:

        sources = []
        seen = set()

        for record in records:
            page_number = record.get(
                "page_number",
                record.get("source_page"),
            )

            key = (
                record.get("document"),
                page_number,
            )

            if key in seen:
                continue

            seen.add(key)

            sources.append(
                {
                    "document": record.get("document"),
                    "page_number": page_number,
                    "heading": record.get("programme", ""),
                    "score": None,
                }
            )

            if len(sources) >= 5:
                break

        return sources
    
    def _format_curriculum_with_llm(
        self,
        *,
        question: str,
        route: dict,
        records: list[dict],
    ) -> str:

        curriculum_data = "\n".join(
            (
                f"Course Code: {record.get('course_code')}\n"
                f"Course Title: {record.get('course_title')}\n"
                f"Credit Hours: {record.get('total_credit_hours')}\n"
                f"Study Year: {record.get('study_year')}\n"
                f"Semester: {record.get('semester')}\n"
            )
            for record in records
        )

        route_data = (
            f"Programme: {route.get('programme')}\n"
            f"Study Year: {route.get('study_year')}\n"
            f"Semester: {route.get('semester')}\n"
            f"Course Code: {route.get('course_code')}\n"
        )

        prompt = f"""
You are formatting a curriculum answer.

The application has ALREADY identified the programme and
retrieved the relevant curriculum records.

Do NOT perform retrieval.
Do NOT question whether the records are relevant.
Do NOT say that the information is missing when records
are supplied below.

USER QUESTION:
{question}

CURRICULUM ROUTE:
{route_data}

SUPPLIED CURRICULUM COURSES:
{curriculum_data}

RULES:

1. Answer the user's question directly.

2. The supplied curriculum courses are the authoritative
   answer data.

3. Use the supplied records. Do not ignore them.

4. Never invent, infer, estimate, or modify course information.

5. Never say:
   - "I couldn't find"
   - "The information is not available"
   - "not found"
   - "assuming"
   - "likely"
   - "probably"
   - "it appears"
   - "based on common academic structure"
   - "the data only mentions"
   - "the records do not provide"

   when relevant course records are supplied.

6. Do not explain how the programme, study year, or semester
   was determined.

7. Do not mention retrieval, records, context, databases,
   RAG, or implementation details.

8. Preserve course codes and course titles exactly.

9. Preserve credit-hour values exactly.

10. If a credit-hour value is genuinely missing for a supplied
    course, display "—". Do not invent a value.

11. For a request asking for the courses in a semester,
    use a simple Markdown bullet list.

12. Each course must use this format:

    - **COURSE CODE** — Course Title — **X credit hours**

13. Do not use a Markdown table unless the user explicitly
    asks for a table.

14. Do not include theory hours or practical hours unless
    the user explicitly asks for them.

15. Do not add unnecessary introduction or conclusion.

16. Do not add notes unless they are necessary to accurately
    represent a missing value.

17. If multiple years are supplied because the requested
    semester occurs in more than one year, separate them
    with short headings.

18. If the user asks about one specific course, answer only
    that course.

19. Return ONLY the final answer.

Example format:

### Mechanical Engineering — 2nd Semester

- **EE-210** — Basic Electrical and Electronics Engineering — **3 credit hours**
- **ES-108** — Ideology and Constitution of Pakistan — **2 credit hours**
- **ME-120** — Statics — **3 credit hours**
""".strip()

        return self._call_groq(
            prompt=prompt,
            max_tokens=650,
        )

    def _not_found(
        self,
        question: str,
    ) -> dict[str, Any]:

        official_url = ""

        try:
            active_document = (
                self.document_manager
                .get_active_document()
            )

            official_url = str(
                active_document.get(
                    "official_url"
                )
                or ""
            ).strip()

        except Exception:
            official_url = ""

        answer = (
            "I couldn't reliably find the exact "
            "answer in the prospectus."
        )

        page_references = []

        if official_url:
            answer += (
                " Here's the official NED "
                "prospectus look here."
            )

            page_references.append(
                {
                    "document": (
                        "official_prospectus"
                    ),
                    "page_number": None,
                    "page_path": None,
                    "page_url": official_url,
                    "reason": (
                        "Open the official NED "
                        "prospectus and search "
                        "for the information."
                    ),
                }
            )

        return {
            "question": question,
            "answer": answer,
            "status": "not_found",
            "sources": [],
            "page_references": page_references,
        }


    def _is_abstention(
        self,
        answer: str,
    ) -> bool:

        normalized = answer.casefold()

        markers = [
            "couldn't reliably find",
            "could not reliably find",
            "couldn't find",
            "could not find",
            "cannot find",
            "can't find",
            "the prospectus does not provide",
            "the prospectus does not mention",
            "the prospectus does not contain",
            "not found in the prospectus",
            "not available in the provided prospectus",
            "information is not available",
            "not provided in the available prospectus information",
            "I'm sorry, but I don't have that information.",
            "i am sorry",
            "i’m sorry",
            "i'm sorry",
        ]

        return any(
            marker in normalized
            for marker in markers
        )