from pathlib import Path

from src.retrieval.hybrid_retriever import HybridRetriever


GRAPH_PATH = Path(
    "../storage/graph/testingnedprospect.json"
)


TEST_CASES = [
    {
        "name": "Mirpurkhas admission category",
        "question": (
            "Which admission category accepts "
            "students from Mirpurkhas Board?"
        ),
        "expected_pages": {5},
        "expected_graph_terms": {
            "R-2(b)",
            "Mirpurkhas",
        },
    },
    {
        "name": "Sports category",
        "question": (
            "What sports and games are approved "
            "for admission under the sports category?"
        ),
        "expected_pages": {6},
        "expected_graph_terms": set(),
    },
]


def collect_graph_text(
    graph_results: dict,
) -> str:

    parts = []

    for item in graph_results.get(
        "matched_entities",
        [],
    ):
        entity = item.get("entity", {})
        parts.append(entity.get("name", ""))

    for relationship in graph_results.get(
        "relationships",
        [],
    ):
        source = relationship.get(
            "source_entity",
            {},
        )
        target = relationship.get(
            "target_entity",
            {},
        )

        parts.append(source.get("name", ""))
        parts.append(
            relationship.get(
                "relationship_type",
                "",
            )
        )
        parts.append(target.get("name", ""))

    return " ".join(parts).lower()


def main() -> None:

    retriever = HybridRetriever(
        graph_path=GRAPH_PATH,
    )

    passed = 0

    for test in TEST_CASES:

        print(
            f"\nTesting: {test['name']}"
        )

        result = retriever.retrieve(
            query=test["question"],
            vector_top_k=5,
            graph_top_k=3,
        )

        pages = {
            chunk["page_number"]
            for chunk in result["vector_chunks"]
        }

        graph_text = collect_graph_text(
            result["graph_results"]
        )

        page_pass = (
            test["expected_pages"]
            <= pages
        )

        graph_pass = all(
            term.lower() in graph_text
            for term in test[
                "expected_graph_terms"
            ]
        )

        test_pass = (
            page_pass
            and graph_pass
        )

        print(
            "Retrieved pages:",
            sorted(pages),
        )
        print(
            "Expected pages:",
            sorted(
                test["expected_pages"]
            ),
        )
        print(
            "Page check:",
            page_pass,
        )
        print(
            "Graph check:",
            graph_pass,
        )

        if test_pass:
            print("RESULT: PASS")
            passed += 1
        else:
            print("RESULT: FAIL")

    print(
        f"\nFINAL: {passed}/"
        f"{len(TEST_CASES)} tests passed."
    )


if __name__ == "__main__":
    main()