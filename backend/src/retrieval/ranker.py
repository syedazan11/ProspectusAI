from __future__ import annotations
import re
from src.retrieval.models import (
    RetrievalCandidate,
    RetrievalIntent,
    ChunkKind,
    RetrievalPlan,
)
from src.conversation.person_matcher import PersonMatcher
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.retrieval.retriever import Retriever


class Ranker:
    """
    Responsible only for ranking candidates.

    No retrieval.

    No generation.
    """

    def __init__(
        self,
        retriever: "Retriever",
    ) -> None:

        self._retriever = retriever

    def rank(
        self,
        plan: RetrievalPlan,
        candidates: list[RetrievalCandidate],
        top_k: int,
        context: dict | None = None,
    ) -> list[RetrievalCandidate]:

        for candidate in candidates:
            self._compute_score(
                plan,
                candidate,
                context,
            )
        # print("\n===== BEFORE SORT =====")

        # for c in candidates:
        #     if c.chunk.get("chunk_id") in {
        #         "structured-people-52",
        #         "structured-people-42",
        #         "structured-people-350",
        #     }:
        #         print(
        #             c.chunk.get("chunk_id"),
        #             "final=", c.final_score,
        #             "semantic=", c.semantic_score,
        #             "lexical=", c.lexical_score,
        #             "heading=", c.heading_score,
        #             "metadata=", c.metadata_score,
        #             "structured=", c.structured_score,
        #         )

        candidates.sort(
            key=lambda c: c.final_score,
            reverse=True,
        )

        candidates = self._expand_neighbors(
            candidates,
            plan,
        )

        candidates.sort(
            key=lambda c: c.final_score,
            reverse=True,
        )

        candidates = self._remove_duplicates(
            candidates,
        )

        if plan.intent == RetrievalIntent.PEOPLE:
            candidates = [
                candidate
                for candidate in candidates
                if self._people_context_matches(
                    candidate,
                    context,
                )
            ]       

        for candidate in candidates:

            candidate.chunk["final_score"] = candidate.final_score

            candidate.chunk["semantic_score"] = candidate.semantic_score

            candidate.chunk["lexical_score"] = candidate.lexical_score

            candidate.chunk["heading_score"] = candidate.heading_score

            candidate.chunk["metadata_score"] = candidate.metadata_score

            candidate.chunk["structured_score"] = candidate.structured_score

        if plan.intent == RetrievalIntent.PEOPLE:
            return candidates
        
        return candidates[:top_k]

    def _compute_score(
        self,
        plan: RetrievalPlan,
        candidate: RetrievalCandidate,
        context: dict | None = None,
    ) -> None:

        candidate.semantic_score = 0.0
        candidate.lexical_score = 0.0
        candidate.heading_score = 0.0
        candidate.metadata_score = 0.0
        candidate.structured_score = 0.0
        candidate.final_score = 0.0

        self._semantic_score(
            candidate,
        )

        self._lexical_score(
            candidate,
        )

        self._heading_score(
            plan,
            candidate,
        )

        self._structured_score(
            plan,
            candidate,
            context,
        )

        self._metadata_score(
            plan,
            candidate,
        )


        if plan.intent == RetrievalIntent.GENERAL:

            candidate.final_score = (
                candidate.semantic_score * 10.0
                + candidate.lexical_score * 0.35
                + candidate.heading_score * 0.50
                + candidate.metadata_score * 0.20
            )

        else:

            candidate.final_score = (
                candidate.semantic_score
                + candidate.lexical_score
                + candidate.heading_score
                + candidate.metadata_score
                + candidate.structured_score
            )

        self._entity_topic_score(
            plan,
            candidate,
        )
####what

    def _semantic_score(
        self,
        candidate: RetrievalCandidate,
    ) -> None:

        score = float(
            candidate.chunk.get(
                "semantic_score",
            0.0,
            )
        )

        candidate.semantic_score = score

        candidate.final_score += score

    def _lexical_score(
        self,
        candidate: RetrievalCandidate,
    ) -> None:

        score = float(
            candidate.chunk.get(
                "bm25_score",
                0.0,
            )
        )

        candidate.lexical_score = score

        candidate.final_score += score

    def _heading_score(
        self,
        plan: RetrievalPlan,
        candidate: RetrievalCandidate,
    ) -> None:

        metadata = candidate.chunk

        if candidate.kind == ChunkKind.STRUCTURED:

            searchable = candidate.chunk.get(
                "content",
                "",
            ).casefold()

        else:

            searchable = " ".join(
                filter(
                    None,
                    [
                        metadata.get(
                            "heading_path",
                            "",
                        ),
                        metadata.get(
                            "section_title",
                            "",
                        ),
                        metadata.get(
                            "h1",
                            "",
                        ),
                        metadata.get(
                            "h2",
                            "",
                        ),
                        metadata.get(
                            "h3",
                            "",
                        ),
                        metadata.get(
                            "h4",
                            "",
                        ),
                    ],
                )
            ).casefold()

        score = 0.0

        # -------------------------------------------------
        # Strong signal: topics
        # -------------------------------------------------

        for topic in plan.topics:

            topic = topic.casefold().strip()

            if not topic:
                continue

            variants = self._term_variants(
                topic
            )

            if any(
                re.search(
                    rf"\b{re.escape(variant)}\b",
                    searchable,
                )
                for variant in variants
            ):
                score += 8.0

        # -------------------------------------------------
        # Strong signal: extracted entities
        # -------------------------------------------------

        for entity in plan.entities:

            entity = entity.casefold().strip()

            if not entity:
                continue

            if re.search(
                rf"\b{re.escape(entity)}\b",
                searchable,
            ):
                if plan.topics:
                    score += 2.0
                else:
                    score += 5.0

        # -------------------------------------------------
        # Phrase matches
        # -------------------------------------------------

        for phrase in plan.phrases:

            phrase = phrase.casefold().strip()

            if not phrase:
                continue

            if phrase in searchable:
                score += 4.0

        # -------------------------------------------------
        # Ordinary keyword matches
        # -------------------------------------------------

        matched_keywords = 0

        for keyword in plan.keywords:

            keyword = keyword.casefold().strip()

            if not keyword:
                continue

            if re.search(
                rf"\b{re.escape(keyword)}\b",
                searchable,
            ):
                matched_keywords += 1

        if plan.keywords:

            coverage = (
                matched_keywords
                / len(plan.keywords)
            )

            score += coverage * 2.0

        candidate.heading_score = score

        candidate.final_score += score


    # def _structured_score(
    #     self,
    #     plan: RetrievalPlan,
    #     candidate: RetrievalCandidate,
    # ) -> None:

    #     if candidate.kind != ChunkKind.STRUCTURED:
    #         return

    #     score = 0.0

    #     if plan.intent == RetrievalIntent.PEOPLE:
    #         score = 100.0

    #     elif plan.intent == RetrievalIntent.FEES:
    #         score = 100.0

    #     elif (
    #         plan.intent
    #         == RetrievalIntent.ADMISSION_CATEGORY
    #     ):
    #         score = 100.0

    #     candidate.structured_score = score

    #     candidate.final_score += score

    def _structured_score(
        self,
        plan: RetrievalPlan,
        candidate: RetrievalCandidate,
        context: dict | None = None,
    ) -> None:


        if candidate.kind != ChunkKind.STRUCTURED:
            return

        metadata = candidate.chunk

        content = (
            candidate.chunk.get("content", "")
        ).casefold()

        # -------------------------------------------------
        # Parse generic labeled fields
        # -------------------------------------------------

        fields = {}

        current_field = None

        for line in content.splitlines():

            line = line.strip()

            if not line:
                continue

            if line.endswith(":"):

                current_field = " ".join(
                    line[:-1].casefold().split()
                )

                fields[current_field] = ""

                continue

            if current_field is not None:

                if fields[current_field]:

                    fields[current_field] += " " + " ".join(
                        line.split()
                    )

                else:

                    fields[current_field] = " ".join(
                        line.split()
                    )

        record_type = (
            metadata.get("record_type", "")
        )

        score = 0.0

        # -------------------------------------------------
        # Base score for matching retrieval intent
        # -------------------------------------------------

        intent_record_map = {
            RetrievalIntent.PEOPLE: "people",
            RetrievalIntent.FEES: "fees",
            RetrievalIntent.ADMISSION_CATEGORY: "admission_categories",
        }

        expected = intent_record_map.get(plan.intent)

        if expected and record_type == expected:
            score += 100.0

        # -------------------------------------------------
        # Field-aware query matching
        # -------------------------------------------------

        query_terms = [
            keyword.casefold().strip()
            for keyword in plan.keywords
            if keyword.casefold().strip()
        ]


        query_phrases = [
            phrase.casefold().strip()
            for phrase in plan.phrases
            if phrase.casefold().strip()
        ]

        # field_scores = []

        # for field_value in fields.values():

        #     value = field_value.casefold().strip()

        #     if not value:
        #         continue

        #     phrase_matches = sum(
        #         1
        #         for phrase in query_phrases
        #         if phrase in value
        #     )

        #     value_tokens = value.split()

        #     if not value_tokens:
        #         continue

        #     matched_keywords = [
        #         keyword
        #         for keyword in query_terms
        #         if re.search(
        #             rf"\b{re.escape(keyword)}\b",
        #             value,
        #         )
        #     ]

        #     matched_phrases = [
        #         phrase
        #         for phrase in query_phrases
        #         if phrase in value
        #     ]

        #     if not matched_keywords and not matched_phrases:
        #         continue

        #     phrase_keyword_coverage = set()

        #     for phrase in matched_phrases:
        #         phrase_keyword_coverage.update(
        #             phrase.split()
        #         )

        #     independent_keywords = [
        #         keyword
        #         for keyword in matched_keywords
        #         if keyword not in phrase_keyword_coverage
        #     ]

        #     matched_units = (
        #         len(matched_phrases)
        #         + len(independent_keywords)
        #     )
        #     total_query_units = (
        #         len(query_phrases)
        #         + len(query_terms)
        #     )

        #     coverage = (
        #         matched_units / total_query_units
        #         if total_query_units
        #         else 0.0
        #     )

        #     density = (
        #         matched_units / len(value_tokens)
        #         if value_tokens
        #         else 0.0
        #     )

        #     field_score = (
        #         coverage * 30.0
        #         + density * 100.0
        #         + len(matched_phrases) * 25.0
        #     )

        #     field_scores.append(
        #         field_score
        #     )

        # field_scores.sort(
        #     reverse=True
        # )

        # if field_scores:

        #     score += field_scores[0]

        #     if len(field_scores) > 1:
        #         score += field_scores[1] * 0.10

        # -------------------------------------------------
        # Field-aware query matching
        #
        # Structured records have meaningful fields.
        # A match in the category/details is much more
        # important than a match in incidental metadata.
        # -------------------------------------------------

        field_weights = {
            "category": 3.0,
            "details": 2.5,
            "applicability": 2.0,
            "scheme": 1.5,
            "amount": 0.5,
            "currency": 0.25,
            "source heading": 0.5,
            "source page": 0.1,
        }

        field_scores = []

        for field_name, field_value in fields.items():

            value = field_value.casefold().strip()

            if not value:
                continue

            weight = field_weights.get(
                field_name,
                1.0,
            )

            matched_keywords = [
                keyword
                for keyword in query_terms
                if re.search(
                    rf"\b{re.escape(keyword)}\b",
                    value,
                )
            ]

            matched_phrases = [
                phrase
                for phrase in query_phrases
                if phrase in value
            ]

            if (
                not matched_keywords
                and not matched_phrases
            ):
                continue

            # A phrase already contains its component
            # keywords, so do not double-count them.
            phrase_words = set()

            for phrase in matched_phrases:
                phrase_words.update(
                    phrase.split()
                )

            independent_keywords = [
                keyword
                for keyword in matched_keywords
                if keyword not in phrase_words
            ]

            matched_units = (
                len(matched_phrases)
                + len(independent_keywords)
            )

            # Query units are unique words/phrases rather
            # than every generated overlapping phrase.
            unique_query_units = set(
                query_terms
            )

            matched_query_words = set(
                independent_keywords
            )

            for phrase in matched_phrases:
                matched_query_words.update(
                    phrase.split()
                )

            coverage = (
                len(
                    matched_query_words
                    & unique_query_units
                )
                / len(unique_query_units)
                if unique_query_units
                else 0.0
            )

            # Keep density as a small supporting signal.
            # It must not dominate the category/details match.
            density = (
                matched_units
                / len(value.split())
                if value.split()
                else 0.0
            )

            field_score = (
                coverage * 40.0
                + density * 10.0
                + len(matched_phrases) * 30.0
            )

            field_scores.append(
                field_score * weight
            )

        field_scores.sort(
            reverse=True
        )

        if field_scores:
            score += field_scores[0]

            if len(field_scores) > 1:
                score += field_scores[1] * 0.25

        # -------------------------------------------------
        # People role matching
        # -------------------------------------------------

        if plan.intent == RetrievalIntent.PEOPLE:

            role_value = fields.get(
                "role",
                "",
            ).casefold().strip()

            department_value = fields.get(
                "department",
                "",
            ).casefold().strip()

            if context and context.get("topic") == "people":

                requested_role = context.get("role")

                if requested_role:
                    requested_variants = self._term_variants(
                        requested_role
                    )
                    record_variants = self._term_variants(
                        role_value
                    )

                    if requested_variants & record_variants:
                        score += 100.0
                    else:
                        score -= 100.0

                requested_department = context.get("department")
                requested_programme = context.get("programme")

                requested_location = (
                    requested_department
                    or requested_programme
                )

                if requested_location:
                    requested_location = (
                        requested_location
                        .casefold()
                        .strip()
                    )

                    record_department = (
                        f"{department_value} {role_value}"
                        # department_value
                        .casefold()
                        .strip()
                    )

                    requested_words = set(
                        requested_location.split()
                    )

                    record_words = set(
                        record_department.split()
                    )

                    if (
                        requested_location in record_department
                        or record_department in requested_location
                        or all(
                            word in record_words
                            or (
                                word.endswith("s")
                                and word[:-1] in record_words
                            )
                            or (
                                word + "s" in record_words
                            )
                            for word in requested_words
                        )
                    ):
                        score += 120.0
                    else:
                        score -= 120.0

            # if role_value:

            #     role_keywords = {
            #         "dean",
            #         "registrar",
            #         "director",
            #         "principal",
            #         "treasurer",
            #         "librarian",
            #         "chairman",
            #         "chairperson",
            #         "vice chancellor",
            #         "pro vice chancellor",
            #         "professor",
            #         "associate professor",
            #         "assistant professor",
            #         "lecturer",
            #     }

            #     for keyword in query_terms:

            #         if keyword in role_keywords and re.search(
            #             rf"\b{re.escape(keyword)}\b",
            #             role_value,
            #         ):
            #             score += 80.0
            for keyword in query_terms:
                variants = self._term_variants(keyword)

                if any(
                    re.search(
                        rf"\b{re.escape(variant)}\b",
                        role_value,
                    )
                    for variant in variants
                ):
                    score += 80.0

        # -------------------------------------------------
        # Admission code matches
        # -------------------------------------------------

        for code in plan.admission_codes:

            code = code.casefold().strip()

            if not code:
                continue

            if re.search(
                rf"(?<!\w){re.escape(code)}(?!\w)",
                content,
            ):
                score += 80.0
        

        candidate.structured_score = score
        candidate.final_score += score
        if plan.intent == RetrievalIntent.FEES:
            print(
                "[FEE SCORE]",
                candidate.chunk.get("chunk_id"),
                "| category=",
                fields.get("category"),
                "| applicability=",
                fields.get("applicability"),
                "| details=",
                fields.get("details"),
                "| structured=",
                score,
                "| final=",
                candidate.final_score,
            )    

    # def _structured_score(
    #     self,
    #     plan: RetrievalPlan,
    #     candidate: RetrievalCandidate,
    # ) -> None:

    #     if candidate.kind != ChunkKind.STRUCTURED:
    #         return

    #     # metadata = candidate.chunk.get("metadata") or {}
    #     metadata = candidate.chunk

    #     content = (
    #         candidate.chunk.get("content", "")
    #     ).casefold()

    #     field_scores = []

    #     query_terms = [
    #         keyword.casefold().strip()
    #         for keyword in plan.keywords
    #         if keyword.casefold().strip()
    #     ]

    #     for field_value in fields.values():

    #         value = field_value.casefold().strip()

    #         if not value:
    #             continue

    #         value_tokens = value.split()

    #         if not value_tokens:
    #             continue

    #         matched = sum(
    #             1
    #             for keyword in query_terms
    #             if keyword in value
    #         )

    #         if matched == 0:
    #             continue

    #         coverage = matched / len(query_terms)

    #         density = matched / len(value_tokens)

    #         field_score = (
    #             coverage * 30.0
    #             + density * 100.0
    #         )

    #         field_scores.append(field_score)

    #     if field_scores:
    #         score += max(field_scores)

    # # -------------------------------------------------
    # # Base score for matching retrieval intent
    # # -------------------------------------------------

    #     intent_record_map = {
    #         RetrievalIntent.PEOPLE: "people",
    #         RetrievalIntent.FEES: "fees",
    #         RetrievalIntent.ADMISSION_CATEGORY: "admission_categories",
    #     }

    #     expected = intent_record_map.get(plan.intent)

    #     if expected and record_type == expected:
    #         score += 100.0


    #     candidate.structured_score = score
    #     candidate.final_score += score

    def _metadata_score(
        self,
        plan: RetrievalPlan,
        candidate: RetrievalCandidate,
    ) -> None:

        searchable = " ".join(
            filter(
                None,
                [
                    candidate.chunk.get(
                        "h1",
                        "",
                    ),
                    candidate.chunk.get(
                        "h2",
                        "",
                    ),
                    candidate.chunk.get(
                        "h3",
                        "",
                    ),
                    candidate.chunk.get(
                        "h4",
                        "",
                    ),
                    candidate.chunk.get(
                        "section_title",
                        "",
                    ),
                ],
            )
        ).casefold()

        score = 0.0

        for phrase in plan.phrases:

            phrase = phrase.casefold().strip()

            if phrase and phrase in searchable:
                score += 3.0

        for keyword in plan.keywords:

            keyword = keyword.casefold().strip()

            if not keyword:
                continue

            if re.search(
                rf"\b{re.escape(keyword)}\b",
                searchable,
            ):
                score += 1.0

        if plan.keywords:

            matched_keywords = sum(
                1
                for keyword in plan.keywords
                if re.search(
                    rf"\b{re.escape(keyword.casefold().strip())}\b",
                    searchable,
                )
            )

            coverage = (
                matched_keywords
                / len(plan.keywords)
            )

            score += coverage * 2.0

        candidate.metadata_score = score

        candidate.final_score += score

    # def _entity_topic_score(
    #     self,
    #     plan: RetrievalPlan,
    #     candidate: RetrievalCandidate,
    # ) -> None:

    #     content = (
    #         candidate.chunk.get(
    #             "content",
    #             "",
    #         )
    #     ).casefold()

    #     if not content:
    #         return

    #     score = 0.0

    #     # -------------------------------------------------
    #     # Multi-word query phrases
    #     # -------------------------------------------------

    #     for phrase in plan.phrases:

    #         phrase = (
    #             phrase.casefold()
    #             .strip()
    #         )

    #         if (
    #             len(phrase.split()) >= 2
    #             and phrase in content
    #         ):
    #             score += 2.0

    #     # -------------------------------------------------
    #     # Individual query terms
    #     #
    #     # Ignore generic conversational words.
    #     # -------------------------------------------------

    #     generic_terms = {
    #         "a",
    #         "an",
    #         "and",
    #         "are",
    #         "at",
    #         "be",
    #         "for",
    #         "from",
    #         "how",
    #         "in",
    #         "is",
    #         "it",
    #         "of",
    #         "on",
    #         "or",
    #         "the",
    #         "there",
    #         "this",
    #         "to",
    #         "what",
    #         "where",
    #         "which",
    #         "who",
    #         "with",
    #     }

    #     meaningful_keywords = []

    #     for keyword in plan.keywords:

    #         keyword = (
    #             keyword.casefold()
    #             .strip()
    #         )

    #         if not keyword:
    #             continue

    #         if keyword in generic_terms:
    #             continue

    #         meaningful_keywords.append(
    #             keyword
    #         )

    #     # -------------------------------------------------
    #     # Direct and lightweight morphological matching
    #     # -------------------------------------------------

    #     matched_keywords = 0

    #     for keyword in meaningful_keywords:

    #         variants = self._term_variants(
    #             keyword
    #         )

    #         matched = False

    #         for variant in variants:

    #             if re.search(
    #                 rf"\b{re.escape(variant)}\b",
    #                 content,
    #             ):
    #                 matched = True
    #                 break

    #         if matched:
    #             matched_keywords += 1
    #             score += 1.0

    #     # -------------------------------------------------
    #     # Topic/content relationship signal
    #     # -------------------------------------------------

    #     if meaningful_keywords:

    #         coverage = (
    #             matched_keywords
    #             / len(meaningful_keywords)
    #         )

    #         score += coverage * 1.0

    #     # -------------------------------------------------
    #     # Keep deliberately small.
    #     # Existing scoring remains dominant.
    #     # -------------------------------------------------

    #     candidate.final_score += score

    def _entity_topic_score(
        self,
        plan: RetrievalPlan,
        candidate: RetrievalCandidate,
    ) -> None:

        content = (
            candidate.chunk.get("content", "")
        ).casefold()

        if not content:
            return

        score = 0.0

        # -------------------------------------------------
        # Topic = primary signal
        # -------------------------------------------------

        topic_matches = 0

        for topic in plan.topics:

            topic = topic.casefold().strip()

            if not topic:
                continue

            variants = self._term_variants(topic)

            if any(
                re.search(
                    rf"\b{re.escape(variant)}\b",
                    content,
                )
                for variant in variants
            ):
                topic_matches += 1

        if plan.topics:
            topic_coverage = (
                topic_matches / len(plan.topics)
            )

            score += topic_coverage * 4.0

        # -------------------------------------------------
        # Entity = secondary signal
        # -------------------------------------------------

        entity_matches = 0

        for entity in plan.entities:

            entity = entity.casefold().strip()

            if not entity:
                continue

            if entity in content:
                entity_matches += 1

        if plan.entities:
            entity_coverage = (
                entity_matches / len(plan.entities)
            )

            score += entity_coverage * 2.0

        # -------------------------------------------------
        # Strong combination:
        # topic + requested entity
        # -------------------------------------------------

        if topic_matches > 0 and entity_matches > 0:
            score += 3.0

        # -------------------------------------------------
        # Other keywords = weak supporting signal
        # -------------------------------------------------

        generic_terms = {
            "a",
            "an",
            "and",
            "are",
            "at",
            "be",
            "for",
            "from",
            "how",
            "in",
            "is",
            "it",
            "of",
            "on",
            "or",
            "the",
            "there",
            "this",
            "to",
            "what",
            "where",
            "which",
            "who",
            "with",
        }

        topic_words = set()

        for topic in plan.topics:
            topic_words.update(
                topic.casefold().split()
            )

        entity_words = set()

        for entity in plan.entities:
            entity_words.update(
                entity.casefold().split()
            )

        supporting_keywords = [
            keyword.casefold().strip()
            for keyword in plan.keywords
            if (
                keyword.casefold().strip()
                and keyword.casefold().strip()
                not in generic_terms
                and keyword.casefold().strip()
                not in topic_words
                and keyword.casefold().strip()
                not in entity_words
            )
        ]

        for keyword in supporting_keywords:

            variants = self._term_variants(keyword)

            if any(
                re.search(
                    rf"\b{re.escape(variant)}\b",
                    content,
                )
                for variant in variants
            ):
                score += 0.5

        candidate.final_score += score

    def _expand_neighbors(
        self,
        candidates: list[RetrievalCandidate],
        plan: RetrievalPlan,
    ) -> list[RetrievalCandidate]:

        expanded = []
        MAX_NEIGHBOR_EXPANSION = 5

        for candidate in candidates[:MAX_NEIGHBOR_EXPANSION]:

            expanded.append(
                candidate
            )
            if candidate.kind != ChunkKind.SEMANTIC:
                continue

            neighbors = (
                self._retriever._neighbor_chunks(
                    chunk_id=(
                        candidate.chunk[
                            "chunk_id"
                        ]
                    ),
                    window=1,
                )
            )

            for chunk in neighbors:

                if chunk.get("structured"):

                    kind = ChunkKind.STRUCTURED

                else:

                    kind = ChunkKind.SEMANTIC

                neighbor = RetrievalCandidate(
                    chunk=chunk,
 
                    kind=kind,
                )

                self._compute_score(
                    plan,
                    neighbor,
                )

                neighbor.is_context = True

                expanded.append(
                    neighbor
                )

        expanded.extend(
            candidates[5:]
        )

        return expanded


    def _remove_duplicates(
        self,
        candidates: list[RetrievalCandidate],
    ) -> list[RetrievalCandidate]:

        seen = set()

        unique = []

        for candidate in candidates:

            chunk_id = (
                candidate.chunk.get(
                    "chunk_id",
                )
            )

            if chunk_id in seen:
                continue

            seen.add(chunk_id)

            unique.append(candidate)

        return unique

    def _people_context_matches(
        self,
        candidate: RetrievalCandidate,
        context: dict | None,
    ) -> bool:

        if not context or context.get("topic") != "people":
            return True

        requested_person = context.get("person_name")


##change on 16 oct

        # if requested_person:
        #     content = candidate.chunk.get("content", "").casefold()

        #     normalized_requested = " ".join(
        #         requested_person.casefold().replace(".", "").split()
        #     )

        #     normalized_content = " ".join(
        #         content.replace(".", "").split()
        #     )

        #     return normalized_requested in normalized_content


        requested_person = context.get("person_name")

        if requested_person:
            record_name = PersonMatcher.extract_record_name(
                candidate.chunk.get("content", "")
            )

            return bool(
                record_name
                and PersonMatcher.names_match(
                    requested_person,
                    record_name,
                )
            )

##change on 18 oct
        # content = candidate.chunk.get("content", "").casefold()

        # fields = {}
        # current_field = None

        # for line in content.splitlines():
        #     line = line.strip()

        #     if not line:
        #         continue

        #     if line.endswith(":"):
        #         current_field = " ".join(
        #             line[:-1].casefold().split()
        #         )
        #         fields[current_field] = ""
        #         continue

        #     if current_field is not None:
        #         fields[current_field] = (
        #             f"{fields[current_field]} {line}".strip()
        #         )

        # role = fields.get("role", "")
        # department = fields.get("department", "")

        content = candidate.chunk.get("content", "").casefold()

        fields = {}
        current_field = None

        for line in content.splitlines():
            line = line.strip()

            if not line:
                continue

            match = re.match(
                r"^(name|role|department|page|qualifications):\s*(.*)$",
                line,
            )

            if match:
                current_field = match.group(1)
                fields[current_field] = match.group(2).strip()
            elif current_field is not None:
                fields[current_field] = (
                    f"{fields[current_field]} {line}".strip()
                )

        role = fields.get("role", "")
        department = fields.get("department", "")

        # print(
        #     "[PEOPLE PARSED]",
        #     {
        #         "chunk_id": candidate.chunk.get("chunk_id"),
        #         "name": fields.get("name"),
        #         "role": role,
        #         "department": department,
        #     },
        # )

        requested_role = context.get("role")
        # if requested_role:
        #     if not (
        #         self._term_variants(requested_role)
        #         & self._term_variants(role)
        #     ):
        #         return False
        # if requested_role:
        #     requested_role = requested_role.casefold().strip()
        #     record_role = role.casefold().strip()

        #     if requested_role not in record_role:
        #         return False
        # if requested_role:
        #     if not (
        #         self._term_variants(requested_role)
        #         & self._term_variants(role)
        #     ):
        #         return False
        # if requested_role:
        #     normalized_role = re.sub(
        #         r"[^a-z0-9]+",
        #         " ",
        #         role.casefold(),
        #     ).split()

        #     requested_variants = self._term_variants(
        #         requested_role
        #     )

        #     if not any(
        #         requested_variant in normalized_role
        #         for requested_variant in requested_variants
        #     ):
        #         return False
        if requested_role:
            normalized_requested_role = re.sub(
                r"[^a-z0-9]+",
                " ",
                requested_role.casefold(),
            ).strip()

            normalized_record_role = re.sub(
                r"[^a-z0-9]+",
                " ",
                role.casefold(),
            ).strip()

##changes 17 oct

            # if not re.search(
            #     rf"\b{re.escape(normalized_requested_role)}\b",
            #     normalized_record_role,
            # ):
            #     return False

##changs on 18
            # role_pass = bool(
            #     self._term_variants(normalized_requested_role)
            #     & self._term_variants(normalized_record_role)
            # )

            
            requested_role_variants = self._term_variants(
                normalized_requested_role
            )

            role_pass = any(
                re.search(
                    rf"\b{re.escape(variant)}\b",
                    normalized_record_role,
                )
                for variant in requested_role_variants
                if variant.strip()
            )


            # print(
            #     "[PEOPLE FILTER]",
            #     {
            #         "chunk_id": candidate.chunk.get("chunk_id"),
            #         "name": fields.get("name"),
            #         "filter": "role",
            #         "requested": normalized_requested_role,
            #         "record": normalized_record_role,
            #         "passed": role_pass,
            #         "reason": (
            #             "role variants match"
            #             if role_pass
            #             else "role variants do not match"
            #         ),
            #     },
            # )

            if not role_pass:
                return False

        requested_location = (
            context.get("department")
            or context.get("programme")
        )

        # if requested_location:
        #     requested_words = set(
        #         requested_location.casefold().split()
        #     )
        #     record_words = set(
        #         department.casefold().split()
        #     )

        #     if not (
        #         requested_location.casefold() in department.casefold()
        #         or department.casefold() in requested_location.casefold()
        #         or all(
        #             word in record_words
        #             or (
        #                 word.endswith("s")
        #                 and word[:-1] in record_words
        #             )
        #             or (
        #                 word + "s" in record_words
        #             )
        #             for word in requested_words
        #         )
        #     ):
        #         return False

        # return True
        if requested_location:
            requested_words = set(
                re.sub(
                    r"[^a-z0-9]+",
                    " ",
                    requested_location.casefold(),
                ).split()
            )

            # location_text = f"{department} {role}".casefold()
            location_text = re.sub(
                r"[^a-z0-9]+",
                " ",
                f"{department} {role}".casefold(),
            )
            record_words = set(location_text.split())

            location_pass = (
                requested_location.casefold() in location_text
                or location_text in requested_location.casefold()
                or all(
                    word in record_words
                    or (
                        word.endswith("s")
                        and word[:-1] in record_words
                    )
                    or (
                        word + "s" in record_words
                    )
                    for word in requested_words
                )
            )
            # print(
            #     "[PEOPLE FILTER]",
            #     {
            #         "chunk_id": candidate.chunk.get("chunk_id"),
            #         "name": fields.get("name"),
            #         "filter": "location",
            #         "requested": requested_location,
            #         "record": location_text,
            #         "passed": location_pass,
            #         "reason": (
            #             "location tokens match"
            #             if location_pass
            #             else "location tokens do not match"
            #         ),
            #     },
            # )

            if not location_pass:
                return False

        return True

    @staticmethod
    def _term_variants(term: str) -> set[str]:

        term = term.casefold().strip()

        if not term:
            return set()

        variants = {
            term,
        }

        if term.endswith("ies") and len(term) > 3:
            variants.add(
                term[:-3] + "y"
            )

        elif term.endswith("s") and not term.endswith("ss"):
            variants.add(
                term[:-1]
            )

        return variants