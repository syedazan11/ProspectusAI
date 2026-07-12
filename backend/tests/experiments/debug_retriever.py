import sys
import os
from pathlib import Path

# Ensure project root is in PYTHONPATH
project_root = Path(__file__).resolve().parents[4]
sys.path.append(str(project_root))

# Load environment variables (same as app)
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

# Import the Retriever class
from backend.src.retrieval.retriever import Retriever

def main():
    if len(sys.argv) < 2:
        print("Usage: python debug_retriever.py <query>")
        sys.exit(1)
    query = " ".join(sys.argv[1:])

    # The collection name is taken from the existing application settings.
    # It is stored in the environment variable QDRANT_COLLECTION (fallback to a known default).
    collection_name = os.getenv("QDRANT_COLLECTION", "prospectus_chunks")
    retriever = Retriever(collection_name=collection_name)

    results = retriever.retrieve(query)

    for idx, chunk in enumerate(results, start=1):
        print(f"--- Rank {idx} ---")
        print(f"final_score    : {chunk.get('final_score'):.4f}")
        print(f"lexical_score : {chunk.get('lexical_score'):.4f}")
        print(f"semantic_score : {chunk.get('semantic_score'):.4f}")
        # heading_score, intent_score, entity_score, page_score are stored internally
        # during ranking; they are not part of the returned dict. We retrieve them
        # from the original candidate data if present.
        print(f"heading_score  : {chunk.get('heading_score', 0):.4f}")
        print(f"intent_score   : {chunk.get('intent_score', 0):.4f}")
        print(f"entity_score   : {chunk.get('entity_score', 0):.4f}")
        print(f"page_score     : {chunk.get('page_score', 0):.4f}")
        print(f"page_number    : {chunk.get('page_number')}")
        print(f"heading        : {chunk.get('heading')}")
        print(f"parent_heading : {chunk.get('parent_heading')}")
        content = chunk.get('content', '')
        preview = content[:200].replace("\n", " ")
        print(f"content preview: {preview}")
        print()

if __name__ == "__main__":
    main()
