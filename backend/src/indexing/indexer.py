import json
from pathlib import Path
import uuid
from qdrant_client.models import PointStruct

from src.embeddings.embedder import EmbeddingService
from src.vector_store.qdrant_store import QdrantStore


class Indexer:
    """
    Reads child chunks, generates embeddings,
    and indexes them into Qdrant.
    """
    BATCH_SIZE = 128

    def __init__(self):

        self.embedder = EmbeddingService()
        self.vector_store = QdrantStore()
    
    def index(self, chunks_json: Path):

        with open(chunks_json, "r", encoding="utf-8") as f:
            document = json.load(f)

        child_chunks = document["child_chunks"]

        print(f"Found {len(child_chunks)} child chunks.")

        if not child_chunks:
            print("No child chunks to index.")
            return

        document_id = (
            child_chunks[0]["metadata"]["document"]
        )

        self.vector_store.create_collection()

        self.vector_store.delete_document(
            document_id=document_id,
        )

        for start in range(0, len(child_chunks), self.BATCH_SIZE):

            batch = child_chunks[start:start + self.BATCH_SIZE]

            # Extract text
            texts = [
                chunk["content"]
                for chunk in batch
            ]

            # Generate embeddings
            embeddings = self.embedder.embed_batch(texts)

            points = []

            for chunk, vector in zip(batch, embeddings):

                points.append(
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vector.tolist(),
                        payload={
                            "document": chunk["metadata"]["document"],
                            "page_number": chunk["page_number"],
                            "heading": chunk["heading"],
                            "chunk_id": chunk["chunk_id"],
                            "parent_chunk_id": chunk["parent_chunk_id"],
                            "content": chunk["content"],
                        },
                    )
                )

            self.vector_store.upsert_points(points)

            print(
                f"Indexed {start + len(batch)} / {len(child_chunks)} chunks."
            )

        print("\n✅ Indexing completed successfully!")
    