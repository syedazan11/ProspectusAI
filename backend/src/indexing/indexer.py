import json
from pathlib import Path
import uuid

from qdrant_client.models import PointStruct

from src.embeddings.embedder import EmbeddingService
from src.vector_store.qdrant_store import QdrantStore


class Indexer:
    """
    Reads current child chunks, generates embeddings,
    and indexes them into a target Qdrant collection.
    """

    BATCH_SIZE = 32

    def __init__(
        self,
        collection_name: str | None = None,
    ):
        self.embedder = EmbeddingService()
        self.vector_store = QdrantStore(
            vector_size=self.embedder.vector_size,
            collection_name=collection_name,
        )

    def index(
        self,
        chunks_json: Path,
        document_id: str,
    ) -> None:
        with open(
            chunks_json,
            "r",
            encoding="utf-8",
        ) as file:
            document = json.load(file)

        chunks = document["chunks"]

        print(
            f"Found {len(chunks)} chunks."
        )

        if not chunks:
            raise ValueError(
                "No chunks available to index."
            )

        self.vector_store.create_collection()

        self.vector_store.delete_document(
            document_id=document_id,
            content_type="prospectus_chunk",
        )

        for start in range(
            0,
            len(chunks),
            self.BATCH_SIZE,
        ):
            batch = chunks[
                start:start + self.BATCH_SIZE
            ]

            texts = [
                chunk.get(
                    "embedding_text",
                    chunk["content"],
                )
                for chunk in batch
            ]

            embeddings = (
                self.embedder.embed_documents(texts)
            )

            points = []

            for chunk, vector in zip(
                batch,
                embeddings,
            ):
                points.append(
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vector.tolist(),
                        payload={
                            **chunk.get("metadata", {}),
                            "document": document_id,
                            "content_type": "prospectus_chunk",
                            "chunk_id": chunk["chunk_id"],
                            "chunk_type": chunk.get("chunk_type", "semantic"),
                            "content": chunk["content"],
                            # **chunk.get("metadata", {}),
                        },
                    )
                )

            self.vector_store.upsert_points(
                points
            )

            print(
                "Indexed "
                f"{start + len(batch)} / "
                f"{len(chunks)} chunks."
            )

        print(
            "\nIndexing completed successfully!"
        )
