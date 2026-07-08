import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from groq import Groq

try:
    from .retriever import RescueRetriever
except ImportError:
    from retriever import RescueRetriever


PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(
    PROJECT_ROOT / "backend" / ".env"
)


class RescueAnswerService:

    def __init__(
        self,
        collection_name: str,
    ):

        self.retriever = RescueRetriever(
            collection_name=collection_name,
        )

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
    ) -> dict[str, Any]:

        question = question.strip()

        if not question:
            raise ValueError(
                "Question cannot be empty."
            )

        chunks = self.retriever.retrieve(
            query=question,
            top_k=min(
                max(top_k, 8),
                12,
            ),
        )

        if not chunks:

            return self._not_found(
                question
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
            question=question,
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
- If the answer is clearly present, answer directly.
- Cite PDF page numbers naturally when useful.
- Keep the answer concise and readable.
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

        return {
            "question": question,
            "answer": (
                "I couldn't reliably find the exact "
                "answer in the prospectus."
            ),
            "status": "not_found",
            "sources": [],
            "page_references": [],
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

