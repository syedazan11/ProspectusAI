from src.retrieval.retriever import Retriever
from src.retrieval.context_builder import ContextBuilder

retriever = Retriever()
builder = ContextBuilder()

results = retriever.retrieve(
    "What is the eligibility criteria?"
)

context = builder.build(results)

print(context)