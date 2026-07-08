import json
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from qdrant_client import QdrantClient, models


PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / "backend" / ".env")

INPUT_PATH = (
    PROJECT_ROOT
    / "storage"
    / "rescue"
    / "UGProspectus2025_chunks.json"
)

QDRANT_URL = os.getenv("QDRANT_HOST")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

COLLECTION = "prospectus_rescue_v1"
MODEL = "sentence-transformers/all-minilm-l6-v2"


def build_embedding_text(chunk: dict) -> str:

    heading = chunk.get("heading", "").strip()
    content = chunk.get("content", "").strip()

    return f"{heading}\n\n{content[:900]}"


data = json.loads(
    INPUT_PATH.read_text(encoding="utf-8")
)

chunks = data["chunks"]

client = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY,
    cloud_inference=True,
    timeout=120,
)

print("CONNECTED TO QDRANT CLOUD")
print("CHUNKS TO INDEX:", len(chunks))


if client.collection_exists(COLLECTION):

    print("Deleting incomplete collection...")

    client.delete_collection(
        collection_name=COLLECTION
    )


client.create_collection(
    collection_name=COLLECTION,
    vectors_config=models.VectorParams(
        size=384,
        distance=models.Distance.COSINE,
    ),
)

print("CREATED COLLECTION:", COLLECTION)


BATCH_SIZE = 16

for start in range(
    0,
    len(chunks),
    BATCH_SIZE,
):

    batch = chunks[start:start + BATCH_SIZE]

    points = []

    for chunk in batch:

        embedding_text = build_embedding_text(
            chunk
        )

        points.append(
            models.PointStruct(
                id=str(
                    uuid.uuid5(
                        uuid.NAMESPACE_URL,
                        chunk["chunk_id"],
                    )
                ),

                # Qdrant Cloud performs the
                # embedding remotely here.
                vector=models.Document(
                    text=embedding_text,
                    model=MODEL,
                ),

                payload={
                    "chunk_id": chunk["chunk_id"],
                    "document": chunk["document"],
                    "page_number": (
                        chunk["page_number"]
                    ),
                    "heading": chunk["heading"],
                    "content": chunk["content"],
                    "is_complex_table": (
                        chunk["is_complex_table"]
                    ),
                },
            )
        )

    client.upsert(
        collection_name=COLLECTION,
        points=points,
        wait=True,
    )

    completed = min(
        start + BATCH_SIZE,
        len(chunks),
    )

    print(
        f"INDEXED: {completed} / "
        f"{len(chunks)}"
    )


count = client.count(
    collection_name=COLLECTION,
    exact=True,
)

print("\n=== RESCUE INDEX COMPLETE ===")
print("COLLECTION:", COLLECTION)
print("POINTS:", count.count)
print("MODEL:", MODEL)
