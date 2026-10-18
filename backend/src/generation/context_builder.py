from __future__ import annotations

from typing import Any

from src.retrieval.models import RetrievalPlan
import re

class ContextBuilder:

    def build(
            self,
            plan: RetrievalPlan,
            chunks: list[dict],
        ) -> str:


            chunks = [
                self._normalize_chunk(chunk)
                for chunk in chunks
            ]
            print("\n===== BUILD_CONTEXT INPUT =====")
            
            for chunk in chunks[:10]:
                print(
                    chunk.get("chunk_id"),
                    chunk.get("chunk_type"),
                    chunk.get("structured"),
                    chunk.get("record_type"),
                    chunk.get("page"),
                    chunk.get("metadata"),
                    )
    
            query_terms = []
    
            query_terms.extend(plan.keywords)
            query_terms.extend(plan.admission_codes)
            query_terms.extend(plan.phrases)
    
            (
                table_chunks,
                normal_chunks,
                structured_chunks,
            ) = self._split_chunk_types(
                chunks,
            )
    
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
                    for term in plan.keywords
                    if term
                    and re.search(
                        rf"(?<!\w){re.escape(term)}(?!\w)",
                        searchable,
                    )
                )

                heading_matches = sum(
                    1
                    for term in plan.keywords
                    if term
                    and re.search(
                        rf"(?<!\w){re.escape(term)}(?!\w)",
                        heading,
                    )
                )

                phrase_matches = sum(
                    1
                    for phrase in plan.phrases
                    if phrase
                    and phrase in searchable
                )

                phrase_heading_matches = sum(
                    1
                    for phrase in plan.phrases
                    if phrase
                    and phrase in heading
                )

                matched_terms += phrase_matches * 2
                heading_matches += phrase_heading_matches * 3
    
                original_score = float(
                    chunk.get(
                        "final_score",
                        0.0,
                    )
                    or 0.0
                )
    
                return (
                    original_score,
                    heading_matches,
                    matched_terms,
                )
    
            normal_chunks.sort(
                key=context_relevance,
                reverse=True,
            )
    
            selected = []

            def is_institution_level_entity(
                entity: str,
            ) -> bool:
                entity = entity.strip().casefold()

                institution_terms = {
                    "university",
                    "institute",
                    "college",
                    "campus",
                }

                tokens = set(
                    re.findall(
                        r"[a-z0-9]+",
                        entity,
                    )
                )

                return bool(
                    tokens
                    and tokens & institution_terms
                )

            specific_entities = [
                entity
                for entity in plan.entities
                if not is_institution_level_entity(entity)
            ]

            is_broad_query = (
                plan.intent.value == "general"
                and not specific_entities
            )

            is_broad_topic_query = (
                plan.intent.value == "general"
                and bool(specific_entities)
                and bool(plan.topics)
            )

            print(
                "[BROAD CONTEXT]",
                "intent=", plan.intent,
                "entities=", plan.entities,
                "is_broad=", is_broad_query,
                "is_broad_topic=", is_broad_topic_query,
            )

            print(
                "[BROAD CONTEXT]",
                "intent=", plan.intent,
                "entities=", plan.entities,
                "is_broad=", is_broad_query,
            )
    
    
    # Keep up to two relevant table chunks first.
    
            selected.extend(table_chunks[:2])

            if is_broad_query or is_broad_topic_query:

                # Broad questions need coverage across the document.
                # Prefer relevant chunks from different sections/pages,
                # while still allowing multiple chunks when they contain
                # genuinely different information.

                selected_keys = set()
                selected_pages = set()
                selected_parents = set()

                for chunk in normal_chunks:

                    heading = (
                        chunk.get("heading")
                        or chunk.get("section_title")
                        or ""
                    ).strip().casefold()

                    content = (
                        str(chunk.get("content", ""))
                        .strip()
                        .casefold()
                    )

                    page = chunk.get("page_number")

                    heading_number = str(
                        chunk.get("heading_number") or ""
                    ).strip()

                    # Prefer the actual structural identity when available.
                    section_key = (
                        heading_number
                        or heading
                    )

                    # Avoid exact duplicate chunks.
                    content_key = (
                        re.sub(r"\s+", " ", content)[:500]
                    )

                    duplicate_key = (
                        section_key,
                        content_key,
                    )

                    if duplicate_key in selected_keys:
                        continue

                    # Avoid excessive clustering on the same page/section.
                    same_page = (
                        page is not None
                        and page in selected_pages
                    )

                    same_section = (
                        section_key
                        and section_key in selected_parents
                    )

                    # For broad queries, prefer one representative chunk
                    # per structural section. This prevents duplicate evidence
                    # from consuming the limited broad-context slots.
                    if same_section:
                        continue

                    selected_keys.add(duplicate_key)

                    if page is not None:
                        selected_pages.add(page)

                    if section_key:
                        selected_parents.add(section_key)

                    if chunk not in selected:
                        selected.append(chunk)

                    if is_broad_topic_query:
                        selection_limit = min(
                            len(normal_chunks),
                            max(8, int(len(normal_chunks) * 0.5)),
                        )
                    else:
                        selection_limit = min(
                            len(normal_chunks),
                            max(8, int(len(normal_chunks) * 0.6)),
                        )

                    if len(selected) >= selection_limit:
                        break
    # Focus normal chunks around the highest-ranked evidence instead of
    # mixing unrelated sections.
            # for  chunk in structured_chunks:
            #     if chunk not in selected:
            #         selected.append(chunk)
    
            #     if len(selected) >= 5:
            #         break
            structured_chunks.sort(
                key=lambda c: float(c.get("final_score", 0.0)),
                reverse=True,
            )

            # if not is_broad_query:

            #     for chunk in structured_chunks:

            #         if chunk not in selected:
            #             selected.append(chunk)

            #         if len(selected) >= (
            #             7 if normal_chunks else 8
            #         ):
            #             break
            if not is_broad_query:

                for chunk in structured_chunks:

                    if chunk not in selected:
                        selected.append(chunk)

                    if len(selected) >= (
                        len(structured_chunks)
                        if plan.intent.value == "people"
                        else (7 if normal_chunks else 8)
                    ):
                        break
    
            if normal_chunks and not is_broad_query:
    
                primary = normal_chunks[0]
    
                if primary not in selected:
                    selected.append(primary)
    
                primary_score = float(primary.get("final_score", 0.0))
    
                if primary_score >= 40:
                    min_score = primary_score * 0.75
                elif primary_score >= 20:
                    min_score = primary_score * 0.65
                else:
                    min_score = primary_score * 0.50
    
                primary_page = primary.get("page_number")
                primary_heading = (
                    primary.get("heading") or ""
                ).casefold()
    
                primary_heading_number = str(
                    primary.get(
                        "heading_number",
                        "",
                    )
                )
    
                for chunk in normal_chunks[1:]:
                    chunk_score = float(chunk.get("final_score", 0.0))
    
                    if chunk_score < min_score:
                        continue
    
                    if len(selected) >= 14:
                        break
    
                    same_page = (
                        chunk.get("page_number")
                        == primary_page
                    )
    
                    heading = (
                        chunk.get("heading") or ""
                    ).casefold()
    
                    current_heading_number = str(
                        chunk.get(
                            "heading_number",
                            "",
                        )
                    )
    
                    same_heading = (
                        heading == primary_heading
                        or primary_heading in heading
                        or heading in primary_heading
                    )
    
                    same_parent = False
                    same_chapter = False
    
                    if (
                        primary_heading_number
                        and current_heading_number
                    ):
    
                        primary_parts = (
                            primary_heading_number.split(".")
                        )
    
                        current_parts = (
                            current_heading_number.split(".")
                        )
    
                        if (
                            len(primary_parts) > 1
                            and len(current_parts) > 1
                            and primary_parts[:-1]
                            == current_parts[:-1]
                        ):
                            same_parent = True
    
                        elif (
                            primary_parts[0]
                            == current_parts[0]
                        ):
                            same_chapter = True
    
                    if (
                        same_page
                        or same_heading
                        or same_parent
                    ):
    
                        if chunk not in selected:
                            selected.append(chunk)
    
                    elif (
                        same_chapter
                        and len(selected) < 4
                        and chunk.get("final_score", 0.0)
                            >= primary.get("final_score", 0.0) * 0.85
                    ):
                        if chunk not in selected:
                            selected.append(chunk)
    
        # Still not enough?
                if len(selected) < 3:
    
                    primary_score = float(
                        primary.get(
                            "final_score",
                            0.0,
                        )
                    )
    
                    minimum_score = primary_score * 0.60
    
                    for chunk in normal_chunks[1:]:
    
                        if chunk in selected:
                            continue
    
                        score = float(
                            chunk.get(
                                "final_score",
                                0.0,
                            )
                        )
    
                        if score < minimum_score:
                            continue
    
                        if chunk not in selected:
                            selected.append(chunk)
    
                        if len(selected) >= 5:
                            break
    
            print("=" * 80)
            print("[BUILD_CONTEXT SELECTED]")
            print("selected =", len(selected))
    
            for i, c in enumerate(selected, 1):
                print(
                    i,
                    c.get("page_number"),
                    c.get("heading"),
                    c.get("parent_chunk_id"),
                    c.get("final_score"),
                )

            for i, chunk in enumerate(selected, 1):
                content = chunk.get("content", "")

                print(
                    f"[CONTEXT SIZE] "
                    f"{i}: "
                    f"page={chunk.get('page_number')} "
                    f"heading={chunk.get('heading')} "
                    f"chars={len(content)}"
                )
    
            analysis = self._analyze_context(
                    selected
                )
    
            print("\n[CONTEXT ANALYSIS]")
            for key, value in analysis.items():
                print(f"{key}: {value}")
    
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
                        max_length=1800,
                    )
    
                heading_number = chunk.get("heading_number") or ""
                heading_level = chunk.get("heading_level") or ""
    
                sections.append(
                    "\n".join(
                        [
                            # "=" * 60,
                            # "RETRIEVED SECTION",
                            # "=" * 60,
                            # f"PDF PAGE: {page_number}",
                            # f"HEADING: {heading}",
                            # f"HEADING NUMBER: {heading_number}",
                            # f"HEADING LEVEL: {heading_level}",
                            # "",
                            f"[Page {page_number} | {heading}]",
                            "CONTENT:",
                            final_content,
                        ]
                    )
                )

            final_context = "\n\n".join(sections)

            print(
                f"[CONTEXT FINAL SIZE] "
                f"chars={len(final_context)}"
            )
    
            return {
                "context": final_context,
                "selected_chunks": selected,
            }

    def _compact_context_text(
        self,
        context: str,
    ) -> str:
        lines = context.splitlines()

        compact_lines = []
        previous_blank = False

        for line in lines:
            line = line.strip()

            if not line:
                if previous_blank:
                    continue

                previous_blank = True
                compact_lines.append("")
                continue

            previous_blank = False
            compact_lines.append(line)

        return "\n".join(compact_lines).strip()

    def _normalize_chunk(
        self,
        chunk: dict[str, Any],
    ) -> dict[str, Any]:

        normalized = dict(chunk)

        metadata = normalized.get("metadata") or {}

    #
    # Structured flag
    #

        normalized["structured"] = (
            normalized.get("structured")
            or metadata.get("structured", False)
        )

    #
    # Page
    #

        normalized["page_number"] = (
            normalized.get("page_number")
            or normalized.get("page")
            or metadata.get("page")
        )

    #
    # Heading
    #

        normalized["heading"] = (
            normalized.get("heading")
            or normalized.get("section_title")
            or normalized.get("heading_path")
            or metadata.get("source_heading")
            or ""
        )

        if (
            normalized["structured"]
            and not normalized["heading"]
        ):
            normalized["heading"] = (
                metadata.get("record_type", "")
                .replace("_", " ")
                .title()
            )

    #
    # Heading Number
    #
    # Heading Number
    #

        normalized["heading_number"] = (
            normalized.get("heading_number")
            or metadata.get("heading_number")
            or ""
        )

    #
    # Heading Level
    #

        normalized["heading_level"] = (
            normalized.get("heading_level")
            or metadata.get("heading_level")
            or ""
        )


        return normalized

    
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

    def _analyze_context(
            self,
            selected_chunks: list[dict],
        ) -> dict:
            """
            Analyze retrieved context before sending it to the LLM.
    
            Returns generic signals describing whether the context
            appears focused or ambiguous.
            """
    
            headings = []
            heading_numbers = []
            heading_levels = []
            pages = set()
            scores = []
    
            for chunk in selected_chunks:
    
                heading = (chunk.get("heading") or "").strip()
                if heading:
                    headings.append(heading)
    
                number = (chunk.get("heading_number") or "").strip()
                if number:
                    heading_numbers.append(number)
    
                level = chunk.get("heading_level")
                if level is not None:
                    heading_levels.append(level)
    
                page = chunk.get("page_number")
                if page is not None:
                    pages.add(page)
    
                scores.append(
                    float(chunk.get("final_score", 0.0))
                )
    
            unique_headings = len(set(headings))
    
            top_level_groups = set()
    
            for number in heading_numbers:
    
                top = number.split(".")[0]
    
                top_level_groups.add(top)
    
            is_ambiguous = (
                len(top_level_groups) >= 3
                or (
                    unique_headings >= 4
                    and len(top_level_groups) >= 2
                )
            )
    
            highest_score = max(scores) if scores else 0.0
            lowest_score = min(scores) if scores else 0.0
            score_gap = highest_score - lowest_score
    
            return {
                "is_ambiguous": is_ambiguous,
                "reason": (
                    "multiple independent sections"
                    if is_ambiguous
                    else "focused context"
                ),
                "unique_headings": unique_headings,
                "heading_numbers": heading_numbers,
                "top_level_groups": sorted(top_level_groups),
                "page_count": len(pages),
                "highest_score": highest_score,
                "lowest_score": lowest_score,
                "score_gap": score_gap,
            }

    def _split_chunk_types(
            self,
            chunks: list[dict[str, Any]],
        ) -> tuple[
            list[dict[str, Any]],
            list[dict[str, Any]],
            list[dict[str, Any]],
        ]:
    
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
    
            structured_chunks = [
                chunk
                for chunk in normal_chunks
                if chunk.get("structured")
                # if str(
                #     chunk.get(
                #         "chunk_id",
                #         "",
                #     )
                # ).startswith(
                #     "structured-people"
                # )
            ]
    
            normal_chunks = [
                chunk
                for chunk in normal_chunks
                if not chunk.get("structured")
            ]
    
            return (
                table_chunks,
                normal_chunks,
                structured_chunks,
            )