from src.retrieval.retriever import Retriever


retriever = Retriever(
    "prospectus_ugprospectus2026"
)


queries = [
    "facilities",
    "laboratories",
    "engineering facilities",
    "manufacturing equipment",
    "engineering laboratories equipment workshops testing",
    "research centres laboratories technical equipment",
]


for query in queries:

    print("\n" + "=" * 80)
    print("QUERY:", query)
    print("=" * 80)

    results = retriever._semantic_candidates(
        query=query,
        limit=20,
    )

    for index, chunk in enumerate(
        results,
        1,
    ):

        print(
            index,
            "PAGE=",
            chunk.get("page"),
            "ID=",
            chunk.get("chunk_id"),
            "SCORE=",
            round(
                chunk.get(
                    "semantic_score",
                    0.0,
                ),
                4,
            ),
        )

        print(
            "SECTION=",
            chunk.get(
                "section_title"
            ),
        )

        print(
            str(
                chunk.get(
                    "content",
                    "",
                )
            )[:180]
            .replace("\n", " ")
        )