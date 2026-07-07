import os

from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    FilterSelector,
)

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

        collections = (
            self.client
            .get_collections()
            .collections
        )

        existing = {
            collection.name
            for collection in collections
        }

        if self.collection_name in existing:
            print(
                f"Collection "
                f"'{self.collection_name}' "
                f"already exists."
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
            f"Collection "
            f"'{self.collection_name}' "
            f"created successfully."
        )

    def reset_collection(self):
        """
        Deletes the existing collection and recreates it.
        Use before a full document re-index.
        """

        collections = (
            self.client
            .get_collections()
            .collections
        )

        existing = {
            collection.name
            for collection in collections
        }

        if self.collection_name in existing:
            self.client.delete_collection(
                collection_name=self.collection_name,
            )

            print(
                f"Deleted collection "
                f"'{self.collection_name}'."
            )

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=384,
                distance=Distance.COSINE,
            ),
        )

        print(
            f"Collection "
            f"'{self.collection_name}' "
            f"recreated successfully."
        )

    def upsert_points(
        self,
        points: list[PointStruct],
    ):
        """
        Inserts or updates points in the collection.
        """

        self.client.upsert(
            collection_name=self.collection_name,
            wait=True,
            points=points,
        )

        print(
            f"Uploaded {len(points)} "
            f"points to Qdrant."
        )

    def delete_document(
        self,
        document_id: str,
    ) -> None:
        """
        Deletes only vectors belonging to one document.
        """

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=FilterSelector(
                filter=Filter(
                    must=[
                        FieldCondition(
                            key="document",
                            match=MatchValue(
                                value=document_id
                            ),
                        )
                    ]
                )
            ),
            wait=True,
        )

        print(
            f"Deleted existing vectors for "
            f"document '{document_id}'."
        )

    def search(
        self,
        query_vector: list[float],
        limit: int = 5,
        document_id: str | None = None,
    ):
        """
        Searches for similar vectors.

        When document_id is provided, results are
        restricted to that prospectus.
        """

        query_filter = None

        if document_id is not None:
            query_filter = Filter(
                must=[
                    FieldCondition(
                        key="document",
                        match=MatchValue(
                            value=document_id
                        ),
                    )
                ]
            )

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
        )

        return results.points
