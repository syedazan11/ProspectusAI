import contextlib
import io

from src.retrieval.retriever import Retriever

r = Retriever(
    collection_name="prospectus_ugprospectus2026"
)

buffer = io.StringIO()

with contextlib.redirect_stdout(buffer):
    result = r.retrieve(
        "what facilities are available for computer science?",
        top_k=24,
    )

chunks = result.get("chunks", [])

print("CHUNKS =", len(chunks))

for i, chunk in enumerate(chunks, 1):
    print(
        i,
        "| page=", chunk.get("page_number"),
        "| section=", chunk.get("section_title"),
        "| score=", chunk.get("final_score"),
    )
