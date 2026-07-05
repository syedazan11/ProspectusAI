from src.retrieval.retriever import Retriever
from src.retrieval.context_builder import ContextBuilder
from src.llm.llm_service import LLMService


question = "What is the eligibility criteria?"

retriever = Retriever()
context_builder = ContextBuilder()
llm = LLMService()

chunks = retriever.retrieve(
    query=question,
    top_k=5,
)

context = context_builder.build(chunks)

answer = llm.generate_answer(
    question=question,
    context=context,
)

print("\nQUESTION:")
print(question)

print("\nANSWER:")
print(answer)