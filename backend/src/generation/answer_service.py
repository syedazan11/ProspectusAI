import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from groq import Groq

from src.retrieval.retriever import Retriever
from src.processing.prospectus.seat_distribution_router import (
    SeatDistributionRouter,
)
from src.services.document_manager import (
    DocumentManager,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(
    PROJECT_ROOT / ".env"
)


class RescueAnswerService:

    def __init__(
        self,
        collection_name: str,
    ):

        self.retriever = Retriever(
            collection_name=collection_name,
        )

        self.document_manager = DocumentManager()
        self.seat_router = SeatDistributionRouter()

        api_key = os.getenv("LLM_API_KEY")

        if not api_key:
            raise RuntimeError(
                "LLM_API_KEY is missing."
            )

        self.client = Groq(
            api_key=api_key
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
        question: str,
        top_k: int = 8,
        conversation_history: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:

        question = question.strip()

        if not question:
            raise ValueError(
                "Question cannot be empty."
            )

        conversational_response = (
            self._handle_conversation(question)
        )

        if conversational_response is not None:
            return conversational_response

        active_document = (
            self.document_manager.get_active_document()
        )

        sections_path = (
            self.document_manager.storage_dir
            / "sections"
            / (
                f"{active_document['document_id']}"
                ".json"
            )
        )

        seat_response = self.seat_router.route(
            question=question,
            official_url=active_document.get(
                "official_url"
            ),
            sections_path=sections_path,
        )

        if seat_response is not None:
            return seat_response

        recent_history = (
            conversation_history or []
        )[-6:]

        retrieval_query = (
            self._build_retrieval_query(
                question=question,
                conversation_history=recent_history,
            )
        )

        chunks = self.retriever.retrieve(
            query=retrieval_query,
            top_k=min(
                max(top_k, 8),
                12,
            ),
        )

        if not chunks:

            return self._not_found(
                question
            )

        chunks = self._expand_retrieved_context(
            chunks
        )

        # A relevant page may be split into a
        # heading chunk and a separate table chunk.
        # Fetch complex-table companions from the
        # highest-ranked relevant pages.
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

        table_companions = (
            self.retriever
            .retrieve_page_chunks(
                page_numbers=candidate_pages,
                complex_only=True,
            )
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

        context = self._build_context(
            question=retrieval_query,
            chunks=chunks,
        )

        has_complex_table = any(
            bool(
                chunk.get(
                    "is_complex_table",
                    False,
                )
            )
            for chunk in chunks
        )

        prompt = self._build_prompt(
            question=question,
            context=context,
            has_complex_table=(
                has_complex_table
            ),
            conversation_history=recent_history,
        )

        answer = self._call_groq(
            prompt=prompt,
            max_tokens=650,
        )

        if self._is_abstention(answer):

            return self._not_found(
                question
            )

        page_references = []

        page_references = (
            self._build_page_references(
                chunks=chunks,
                answer=answer,
                complex_only=has_complex_table,
            )
        )

        status = "answered"

        if page_references:

            status = (
                "answered_with_page_review"
            )

        return {
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


    def stream_answer(
        self,
        question: str,
        top_k: int = 8,
        conversation_history: list[dict[str, Any]]
        | None = None,
    ) -> dict[str, Any]:

        question = question.strip()

        if not question:
            raise ValueError(
                "Question cannot be empty."
            )

        conversational_response = (
            self._handle_conversation(question)
        )

        if conversational_response is not None:
            yield {
                "type": "done",
                "result": conversational_response,
            }
            return

        active_document = (
            self.document_manager.get_active_document()
        )

        sections_path = (
            self.document_manager.storage_dir
            / "sections"
            / (
                f"{active_document['document_id']}"
                ".json"
            )
        )

        seat_response = self.seat_router.route(
            question=question,
            official_url=active_document.get(
                "official_url"
            ),
            sections_path=sections_path,
        )

        if seat_response is not None:
            yield {
                "type": "done",
                "result": seat_response,
            }
            return

        recent_history = (
            conversation_history or []
        )[-6:]

        retrieval_query = (
            self._build_retrieval_query(
                question=question,
                conversation_history=recent_history,
            )
        )

        chunks = self.retriever.retrieve(
            query=retrieval_query,
            top_k=min(
                max(top_k, 8),
                12,
            ),
        )

        if not chunks:

            yield {
                "type": "done",
                "result": self._not_found(question),
            }
            return

        chunks = self._expand_retrieved_context(
            chunks
        )

        # A relevant page may be split into a
        # heading chunk and a separate table chunk.
        # Fetch complex-table companions from the
        # highest-ranked relevant pages.
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

        table_companions = (
            self.retriever
            .retrieve_page_chunks(
                page_numbers=candidate_pages,
                complex_only=True,
            )
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

        context = self._build_context(
            question=retrieval_query,
            chunks=chunks,
        )

        has_complex_table = any(
            bool(
                chunk.get(
                    "is_complex_table",
                    False,
                )
            )
            for chunk in chunks
        )

        prompt = self._build_prompt(
            question=question,
            context=context,
            has_complex_table=(
                has_complex_table
            ),
            conversation_history=recent_history,
        )

        answer_parts = []

        for token in self._stream_groq(
            prompt=prompt,
            max_tokens=650,
        ):
            answer_parts.append(token)

            yield {
                "type": "token",
                "content": token,
            }

        answer = "".join(answer_parts).strip()

        if self._is_abstention(answer):

            yield {
                "type": "done",
                "result": self._not_found(question),
            }
            return

        page_references = []

        page_references = (
            self._build_page_references(
                chunks=chunks,
                answer=answer,
                complex_only=has_complex_table,
            )
        )

        status = "answered"

        if page_references:

            status = (
                "answered_with_page_review"
            )

        yield {
            "type": "done",
            "result": {
                "question": question,
                "answer": answer,
                "status": status,
                "sources": self._build_sources(
                    chunks
                ),
                "page_references": (
                    page_references
                ),
            },
        }


    def _handle_conversation(
        self,
        question: str,
    ) -> dict[str, Any] | None:

        normalized = " ".join(
            question.casefold().split()
        ).strip("?!., ")

        greeting_patterns = (
            r"^(hi|hello|hey|hiya|howdy)"
            r"( there| everyone| bro| bot)?$",
            r"^good (morning|afternoon|evening)$",
        )

        function_patterns = (
            r"^(who|what) are you$",
            r"^what (can|do) you do$",
            r"^what can you do for me$",
            r"^what('s| is) your (function|purpose)$",
            r"^how can you help( me)?$",
            r"^how do you help( me)?$",
            r"^what can i ask( you)?$",
        )

        thanks_patterns = (
            r"^(thanks|thank you|thank you so much|"
            r"thanks a lot|thx)$",
        )

        if any(
            re.fullmatch(pattern, normalized)
            for pattern in greeting_patterns
        ):
            answers = (
                "Hi! I'm NED ProspectusAI. "
                "What would you like to know?",
                "Hello! I can help with the NED "
                "prospectus. What can I help you find?",
                "Hey! Ask me anything about the "
                "NED prospectus.",
            )

        elif any(
            re.fullmatch(pattern, normalized)
            for pattern in function_patterns
        ):
            answers = (
                "I can help with NED admissions, "
                "eligibility, fees, programmes, "
                "curriculum, deadlines, and other "
                "prospectus information.",
                "I'm NED ProspectusAI. I answer "
                "questions using the official NED "
                "prospectus.",
            )

        elif any(
            re.fullmatch(pattern, normalized)
            for pattern in thanks_patterns
        ):
            answers = (
                "You're welcome!",
                "Happy to help!",
                "You're welcome. Ask me anything else "
                "about the NED prospectus.",
            )

        else:
            return None

        answer_index = (
            sum(ord(character) for character in normalized)
            % len(answers)
        )

        return {
            "question": question,
            "answer": answers[answer_index],
            "status": "answered",
            "sources": [],
            "page_references": [],
        }


    def _build_retrieval_query(
        self,
        question: str,
        conversation_history: list[dict[str, Any]],
    ) -> str:

        if not conversation_history:
            return question

        entity_hint = self._conversation_entity_hint(
            conversation_history[-4:]
        )

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

        history_lines = []

        for message in conversation_history[-4:]:
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


    def _build_prompt(
        self,
        question: str,
        context: str,
        has_complex_table: bool,
        conversation_history: list[dict[str, Any]]
        | None = None,
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

        return f"""
You are ProspectusAI.

Answer the user's question using ONLY the supplied
prospectus context.

The uploaded prospectus is the only source of truth.

Rules:
- Do not use outside knowledge.
- Do not invent facts.
- Do not assume the university, programme,
  abbreviation, category, scheme, or year.
- Learn names, abbreviations, codes, meanings,
  categories, and terminology from the supplied
  prospectus context itself.
- The supplied context sections are ordered by
  retrieval relevance. Give stronger weight to
  earlier sections.
- Match the entity, department, programme, topic,
  abbreviation, year, semester, or scheme in the
  question to the most specific matching heading
  and content.
- When a matching section explicitly contains the
  requested fact, extract it and answer directly.
- Do not let unrelated sections about other
  departments, programmes, people, schemes, or
  topics create uncertainty about a clear answer
  in the matching section.
- For labelled facts such as Chairperson, Code,
  Course, Credit Hours, Semester, Fee, Category,
  Facility, or Abbreviation, preserve the
  relationship between the label and the value
  shown in the matching section.
- For abbreviations, use the expansion supported
  by the prospectus context and do not guess from
  outside knowledge.
- For facilities and amenities, distinguish
  between an explicitly confirmed facility and a
  related activity or service. Do not infer that a
  facility exists merely from related wording.
- Answer the exact question asked.
- Give the direct answer first.
- Keep answers as short as the question allows.
- For a simple definition, abbreviation, code,
  name, date, number, or other single fact, answer
  in one sentence only.
- Example style: "EL stands for Electronic
  Engineering."
- Do not explain how you found the answer.
- Do not narrate the evidence or retrieved context.
- Do not mention a page, heading, course code, or
  supporting passage unless the user asks for it
  or it is necessary to avoid ambiguity.
- Give additional explanation only when the user
  asks to explain, compare, summarize, or provide
  details.
- Do not mention retrieval, vectors, chunks,
  embeddings, or a knowledge graph.
- Do not claim information is missing when it is
  clearly present in the context.
{table_instruction}
If the supplied context genuinely does not contain
enough information to answer safely, reply exactly:

I couldn't reliably find the exact answer in the prospectus.

PROSPECTUS CONTEXT:

{context}

USER QUESTION:

{question}
""".strip()


    def _stream_groq(
        self,
        prompt: str,
        max_tokens: int,
    ):

        stream = (
            self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                temperature=0.0,
                max_tokens=max_tokens,
                stream=True,
            )
        )

        for chunk in stream:

            content = (
                chunk
                .choices[0]
                .delta
                .content
            )

            if content:
                yield content


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
                        "role": "user",
                        "content": prompt,
                    }
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

        def normalized_heading(
            chunk: dict[str, Any],
        ) -> str:

            return " ".join(
                str(
                    chunk.get("heading", "")
                ).casefold().split()
            )

        focus_chunk = next(
            (
                chunk
                for chunk in chunks
                if normalized_heading(chunk)
            ),
            chunks[0],
        )

        focus_heading = normalized_heading(
            focus_chunk
        )
        focus_page = focus_chunk.get(
            "page_number"
        )

        def is_focus_chunk(
            chunk: dict[str, Any],
        ) -> bool:

            if focus_heading:
                return (
                    normalized_heading(chunk)
                    == focus_heading
                )

            if focus_page is None:
                return chunk is focus_chunk

            return (
                chunk.get("page_number")
                == focus_page
            )

        companions = [
            chunk
            for chunk in self.retriever._all_chunks()
            if is_focus_chunk(chunk)
        ]

        expanded = []
        seen_chunk_ids = set()

        def add_chunk(
            chunk: dict[str, Any],
        ) -> None:

            chunk_id = chunk.get("chunk_id")

            if chunk_id in seen_chunk_ids:
                return

            expanded.append(chunk)

            if chunk_id is not None:
                seen_chunk_ids.add(chunk_id)

        for chunk in chunks:
            if is_focus_chunk(chunk):
                add_chunk(chunk)

        for companion in companions:
            add_chunk(companion)

        return expanded


    def _build_context(
        self,
        question: str,
        chunks: list[dict],
    ) -> str:

        query_terms = self._context_terms(
            question
        )

        table_chunks = [
            chunk
            for chunk in chunks
            if chunk.get(
                "is_complex_table",
                False,
            )
        ]

        normal_chunks = [
            chunk
            for chunk in chunks
            if not chunk.get(
                "is_complex_table",
                False,
            )
        ]

        def context_relevance(
            chunk: dict[str, Any],
        ) -> tuple[int, int, float]:

            heading = str(
                chunk.get("heading", "")
            ).casefold()

            content = str(
                chunk.get("content", "")
            ).casefold()

            searchable = (
                f"{heading}\n{content}"
            )

            matched_terms = sum(
                1
                for term in query_terms
                if term in searchable
            )

            heading_matches = sum(
                1
                for term in query_terms
                if term in heading
            )

            original_score = float(
                chunk.get(
                    "final_score",
                    0.0,
                )
                or 0.0
            )

            return (
                matched_terms,
                heading_matches,
                original_score,
            )

        normal_chunks.sort(
            key=context_relevance,
            reverse=True,
        )

        selected = []

        # Keep complete table chunks.
        # Maximum two relevant tables prevents
        # token overflow while preserving rows.
        selected.extend(
            table_chunks[:2]
        )

        # Add small supporting context for names,
        # abbreviations and section meaning.
        selected.extend(
            normal_chunks[:4]
        )

        sections = []

        for chunk in selected:

            page_number = chunk.get(
                "page_number",
                "unknown",
            )

            heading = chunk.get(
                "heading",
                "",
            )

            content = chunk.get(
                "content",
                "",
            ).strip()

            if not content:
                continue

            if chunk.get(
                "is_complex_table",
                False,
            ):
                # Keep multiple relevant tables in
                # context without exceeding Groq TPM.
                # Full source pages remain available
                # through page_references.
                final_content = content[:7000]
            else:
                # Keep a query-aware prose window so
                # the matched evidence survives even
                # when the answer appears later in the
                # chunk than the heading does.
                final_content = self._extract_context_window(
                    content=content,
                    query_terms=query_terms,
                    max_length=1000,
                )

            sections.append(
                "\n".join(
                    [
                        (
                            f"[PDF PAGE "
                            f"{page_number}]"
                        ),
                        (
                            f"HEADING: "
                            f"{heading}"
                        ),
                        final_content,
                    ]
                )
            )

        return "\n\n---\n\n".join(
            sections
        )


    def _context_terms(
        self,
        question: str,
    ) -> list[str]:

        terms = []

        for term in self.retriever._query_terms(
            question
        ):

            folded = term.casefold()

            if folded not in terms:
                terms.append(folded)

        for code in self.retriever._query_codes(
            question
        ):

            folded = code.casefold()

            if folded not in terms:
                terms.append(folded)

        return terms


    def _extract_context_window(
        self,
        content: str,
        query_terms: list[str],
        max_length: int,
    ) -> str:

        if len(content) <= max_length:
            return content

        folded_content = content.casefold()

        best_index = None
        best_term = ""

        for term in query_terms:

            if not term:
                continue

            index = folded_content.find(term)

            if index < 0:
                continue

            if best_index is None:
                best_index = index
                best_term = term
                continue

            if (
                len(term) > len(best_term)
                or (
                    len(term) == len(best_term)
                    and index < best_index
                )
            ):
                best_index = index
                best_term = term

        if best_index is None:
            return content[:max_length]

        start = max(
            0,
            best_index - 320,
        )

        end = start + max_length

        if end > len(content):
            end = len(content)
            start = max(
                0,
                end - max_length,
            )

        window = content[start:end].strip()

        if start > 0:
            window = "..." + window

        if end < len(content):
            window = window + "..."

        return window


    def _build_page_references(
        self,
        chunks: list[dict],
        answer: str | None = None,
        complex_only: bool = False,
    ) -> list[dict[str, Any]]:

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

        references = []
        seen = set()

        for chunk in chunks:

            if (
                complex_only
                and not chunk.get(
                    "is_complex_table",
                    False,
                )
            ):
                continue

            document = chunk.get(
                "document"
            )

            page_number = chunk.get(
                "page_number"
            )

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

            references.append(
                {
                    "document": document,
                    "page_number": (
                        page_number
                    ),
                    "page_path": None,
                    "reason": (
                        "Relevant complex "
                        "prospectus table."
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

            references.append(
                {
                    "document": document,
                    "page_number": page_number,
                    "page_path": None,
                    "reason": (
                        "Explicit page citation "
                        "in answer."
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

        sources = []
        seen = set()

        for chunk in chunks:

            document = chunk.get(
                "document"
            )

            page_number = chunk.get(
                "page_number"
            )

            key = (
                document,
                page_number,
            )

            if key in seen:
                continue

            seen.add(key)

            sources.append(
                {
                    "document": document,
                    "page_number": (
                        page_number
                    ),
                    "heading": chunk.get(
                        "heading",
                        "",
                    ),
                    "score": chunk.get(
                        "final_score",
                        chunk.get("score"),
                    ),
                }
            )

            if len(sources) >= 5:
                break

        return sources


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
                "prospectus?look here."
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
        ]

        return any(
            marker in normalized
            for marker in markers
        )




