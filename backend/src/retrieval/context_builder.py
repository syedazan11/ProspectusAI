from typing import Any


class ContextBuilder:
    """
    Builds combined context from:
    - vector-retrieved document chunks
    - graph-retrieved entities and relationships
    """

    def build(
        self,
        retrieved_chunks: list[dict[str, Any]],
        graph_results: dict[str, Any] | None = None,
    ) -> str:

        context_parts = []

        context_parts.append(
            "=========== DOCUMENT CONTEXT ===========\n"
        )

        for chunk in retrieved_chunks:

            context_parts.append(
                f"""
Document: {chunk['document']}
Page: {chunk['page_number']}
Heading: {chunk['heading']}

{chunk['content']}

----------------------------------------
"""
            )

        if graph_results:
            relationships = graph_results.get(
                "relationships",
                [],
            )

            if relationships:
                context_parts.append(
                    "\n=========== KNOWLEDGE GRAPH CONTEXT ===========\n"
                )

                seen_facts = set()

                for relationship in relationships:

                    source = relationship.get(
                        "source_entity"
                    ) or {}

                    target = relationship.get(
                        "target_entity"
                    ) or {}

                    source_name = source.get(
                        "name",
                        relationship.get(
                            "source_entity_id",
                            "unknown",
                        ),
                    )

                    target_name = target.get(
                        "name",
                        relationship.get(
                            "target_entity_id",
                            "unknown",
                        ),
                    )

                    relationship_type = (
                        relationship.get(
                            "relationship_type",
                            "RELATED_TO",
                        )
                    )

                    fact = (
                        f"{source_name} "
                        f"--{relationship_type}--> "
                        f"{target_name}"
                    )

                    if fact in seen_facts:
                        continue

                    seen_facts.add(fact)

                    context_parts.append(
                        f"- {fact}"
                    )

        return "\n".join(context_parts)