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

        return "\n".join(context_parts)