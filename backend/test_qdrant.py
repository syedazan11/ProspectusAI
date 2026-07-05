from src.vector_store.qdrant_store import QdrantStore

store = QdrantStore()

print("Connecting to Qdrant...")

store.create_collection()

print(store.health())