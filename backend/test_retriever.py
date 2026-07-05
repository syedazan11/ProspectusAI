from src.retrieval.retriever import Retriever

retriever = Retriever()

results = retriever.retrieve(
    "What is the eligibility criteria?"
)

print("\nTop Results:\n")

for result in results:

    print("-" * 60)

    print("Score:", result["score"])
    print("Heading:", result["heading"])
    print("Page:", result["page_number"])
    print(result["content"][:300])