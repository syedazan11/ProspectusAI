class ContextBuilder:
    """
    Builds the context that will be
    passed to the LLM.
    """

    def build(
        self,
        retrieved_chunks: list[dict],
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