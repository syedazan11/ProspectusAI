from pathlib import Path

from src.retrieval.hybrid_retriever import (
    HybridRetriever,
)


retriever = HybridRetriever(
    Path(
        "../storage/graph/"
        "testingnedprospect.json"
    )
)


tests = [
    {
        "name": "Text + Graph",
        "query": (
            "Which admission category accepts "
            "students from Mirpurkhas Board?"
        ),
    },
    {
        "name": "Text",
        "query": (
            "What sports and games are approved "
            "for admission under the sports category?"
        ),
    },
    {
        "name": "Table Exact Number",
        "query": (
            "How many total seats are available "
            "under category R-2(b)?"
        ),
    },
    {
        "name": "Table Row",
        "query": (
            "How many R-2(b) seats are available "
            "for TCE?"
        ),
    },
    {
        "name": "Missing Information",
        "query": (
            "What is the hostel fee for "
            "international students?"
        ),
    },
]


for test in tests:

    print("\n" + "=" * 70)
    print(test["name"])
    print("QUERY:", test["query"])
    print("=" * 70)

    result = retriever.retrieve(
        query=test["query"],
        vector_top_k=5,
        graph_top_k=3,
    )

    print("\nVECTOR RESULTS:")

    for index, chunk in enumerate(
        result["vector_chunks"],
        start=1,
    ):
        print(
            f"\n{index}. "
            f"Score: {chunk['score']:.4f}"
        )
        print(
            f"Page: {chunk['page_number']}"
        )
        print(
            f"Heading: {chunk['heading']}"
        )
        print(
            chunk["content"][:500]
        )

    print("\nGRAPH RELATIONSHIPS:")

    for relationship in (
        result["graph_results"]
        .get("relationships", [])
    ):
        source = (
            relationship
            .get("source_entity", {})
            .get("name")
        )

        target = (
            relationship
            .get("target_entity", {})
            .get("name")
        )

        relation = relationship.get(
            "relationship_type"
        )

        print(
            f"- {source} "
            f"--{relation}--> "
            f"{target}"
        )