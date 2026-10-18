# from pprint import pprint

# from src.services.document_manager import DocumentManager
# from src.retrieval.retriever import Retriever


# from pprint import pprint

# from src.services.document_manager import DocumentManager
# from src.retrieval.retriever import Retriever
# from src.retrieval.planner import RetrievalPlanner
# from src.retrieval.collector import Collector


# def main():

#     document_manager = DocumentManager()

#     active_document = (
#         document_manager.get_active_document()
#     )

#     retriever = Retriever(
#         collection_name=active_document[
#             "collection_name"
#         ],
#     )

#     collector = Collector(
#         retriever,
#     )

#     while True:

#         print()
#         print("=" * 80)

#         query = input("Query: ").strip()

#         if not query:
#             break

#         plan = RetrievalPlanner.plan(
#             query,
#         )

#         print()
#         print("INTENT:", plan.intent)
#         print("CODES :", plan.admission_codes)

#         candidates = collector.collect(
#             plan,
#             top_k=10,
#         )

#         print()
#         print(
#             f"Retrieved: {len(candidates)}"
#         )

#         for i, candidate in enumerate(
#             candidates,
#             1,
#         ):

#             print("=" * 80)
#             print(f"[{i}]")

#             pprint(candidate)


# if __name__ == "__main__":

#     main()

from src.services.document_manager import (
    DocumentManager,
)
from src.retrieval.retriever import (
    Retriever,
)
from src.retrieval.planner import (
    RetrievalPlanner,
)
from src.retrieval.collector import (
    Collector,
)
from pprint import pprint


def main():

    document_manager = DocumentManager()

    active_document = (
        document_manager.get_active_document()
    )

    retriever = Retriever(
        collection_name=active_document[
            "collection_name"
        ],
    )

    collector = Collector(
        retriever,
    )

    while True:

        print()
        print("=" * 80)

        query = input(
            "Query: "
        ).strip()

        if not query:
            break

        plan = RetrievalPlanner.plan(
            query,
        )

        print()
        print(
            "INTENT:",
            plan.intent,
        )
        print(
            "CODES :",
            plan.admission_codes,
        )

        candidates = collector.collect(
            plan,
            top_k=10,
        )

        print()
        print(
            f"Retrieved: {len(candidates)}"
        )
        print()

        #
        # Verify chunk ordering.
        #

        retriever._build_chunk_order()

        for chunk in (
            retriever._ordered_chunks[:50]
        ):

            pprint(
                retriever._ordered_chunks[0]
            )


if __name__ == "__main__":

    main()