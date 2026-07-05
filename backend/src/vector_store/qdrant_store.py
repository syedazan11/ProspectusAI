import os

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from qdrant_client.models import PointStruct
from qdrant_client.models import Filter

load_dotenv()


class QdrantStore:
    """
    Handles all interactions with Qdrant.
    """

    def __init__(self):

        self.client = QdrantClient(
            host=os.getenv("QDRANT_HOST"),
            port=int(os.getenv("QDRANT_PORT")),
        )

        self.collection_name = os.getenv(
            "QDRANT_COLLECTION"
        )

    def health(self):
        """
        Returns all collections to verify the connection.
        """

        return self.client.get_collections()
    def create_collection(self):
        """
        Creates the collection if it doesn't already exist.
        """

        collections = self.client.get_collections().collections

        existing = {
            collection.name
            for collection in collections
        }

        if self.collection_name in existing:

            print(
                f"Collection '{self.collection_name}' already exists."
            )

            return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=384,
                distance=Distance.COSINE,
            ),
        )

        print(
            f"Collection '{self.collection_name}' created successfully."
        )
    def upsert_points(self, points: list[PointStruct]):
        """
        Inserts or updates points in the collection.
        """

        self.client.upsert(
            collection_name=self.collection_name,
            wait=True,
            points=points,
        )

        print(f"Uploaded {len(points)} points to Qdrant.")
    
    def search(
        self,
        query_vector: list[float],
        limit: int = 5,
    ):
        """
        Searches for the most similar vectors.
        """

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            limit=limit,
        )

        return results.points