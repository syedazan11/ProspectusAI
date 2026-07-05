from src.embeddings.embedder import EmbeddingService
from src.vector_store.qdrant_store import QdrantStore


class Retriever:
    """
    Retrieves relevant chunks from Qdrant.
    """

    def __init__(self):

        self.embedder = EmbeddingService()
        self.vector_store = QdrantStore()

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ):

        query_embedding = self.embedder.embed_query(query)

        results = self.vector_store.search(
            query_vector=query_embedding.tolist(),
            limit=top_k,
        )

        retrieved_chunks = []

        for result in results:

            retrieved_chunks.append(
                {
                    "score": result.score,
                    "heading": result.payload["heading"],
                    "page_number": result.payload["page_number"],
                    "content": result.payload["content"],
                    "document": result.payload["document"],
                    "parent_chunk_id": result.payload["parent_chunk_id"],
                    "chunk_id": result.payload["chunk_id"],
                }
            )

        return retrieved_chunks