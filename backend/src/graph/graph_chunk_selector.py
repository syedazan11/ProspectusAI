import re
from typing import Any


class GraphChunkSelector:
    """
    Selects parent chunks that are worth sending
    to the LLM for knowledge-graph extraction.

    This stage is completely local and uses zero API calls.
    """

    GRAPH_SIGNALS = (
        "admission",
        "eligible",
        "eligibility",
        "candidate",
        "requirement",
        "program",
        "programme",
        "department",
        "faculty",
        "board",
        "university",
        "category",
        "quota",
        "seat",
        "fee",
        "scholarship",
        "degree",
        "course",
        "semester",
        "test",
        "marks",
        "application",
        "document",
    )

    RELATIONSHIP_SIGNALS = (
        "eligible for",
        "admitted to",
        "offered by",
        "belongs to",
        "required for",
        "applies to",
        "passed",
        "recognized by",
        "located in",
        "consists of",
    )

    def should_process(
        self,
        chunk: dict[str, Any],
    ) -> tuple[bool, str]:

        content = chunk.get("content", "").strip()
        heading = chunk.get("heading", "").strip()

        if not content:
            return False, "empty_content"

        word_count = len(content.split())

        if word_count < 80:
            return False, "too_short"

        combined_text = (
            f"{heading}\n{content}"
        ).lower()

        signal_count = sum(
            1
            for signal in self.GRAPH_SIGNALS
            if signal in combined_text
        )

        relationship_count = sum(
            1
            for signal in self.RELATIONSHIP_SIGNALS
            if signal in combined_text
        )

        admission_categories = len(
            re.findall(
                r"\bR-\d+(?:\([a-z]\))?",
                content,
                flags=re.IGNORECASE,
            )
        )

        score = (
            signal_count
            + relationship_count * 2
            + min(admission_categories, 5)
        )

        if score < 2:
            return False, f"low_graph_score:{score}"

        return True, f"graph_score:{score}"

    def select(
        self,
        chunks: list[dict[str, Any]],
    ) -> dict[str, Any]:

        selected = []
        skipped = []

        for chunk in chunks:
            should_process, reason = (
                self.should_process(chunk)
            )

            record = {
                "chunk_id": chunk.get(
                    "chunk_id",
                    "unknown",
                ),
                "page_number": chunk.get(
                    "page_number",
                    chunk.get(
                        "metadata",
                        {},
                    ).get("page"),
                ),
                "reason": reason,
            }

            if should_process:
                selected.append(chunk)
            else:
                skipped.append(record)

        return {
            "selected_chunks": selected,
            "skipped_chunks": skipped,
            "metadata": {
                "input_count": len(chunks),
                "selected_count": len(selected),
                "skipped_count": len(skipped),
                "estimated_api_calls": len(selected),
            },
        }