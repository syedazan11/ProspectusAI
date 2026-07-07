from pathlib import Path

from src.services.rag_service import RAGService


graph_path = Path(
    "../storage/graph/UGProspectus2025.json"
)

rag = RAGService(
    graph_path=graph_path,
)

question = "What is the eligibility criteria for category R-1(g)?"

result = rag.ask(
    question=question,
    vector_top_k=10,
    graph_top_k=10,
)

print("\n=== QUESTION ===")
print(result["question"])

print("\n=== ANSWER ===")
print(result["answer"])

print("\n=== SOURCES ===")
for source in result["sources"]:
    print(
        f"Page {source['page_number']} | "
        f"{source['heading']} | "
        f"{source['document']}"
    )

print("\n=== RETRIEVAL METADATA ===")
print(result["retrieval_metadata"])

