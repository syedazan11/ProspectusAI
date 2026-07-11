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
    PayloadSchemaType,
)

load_dotenv()


class QdrantStore:
    """
    Handles all interactions with Qdrant.
    """

    def __init__(
        self,
        vector_size: int,
        collection_name: str | None = None,
    ):
        if vector_size <= 0:
            raise ValueError(
                "vector_size must be greater than 0."
            )

        self.vector_size = vector_size

        qdrant_host = os.getenv("QDRANT_HOST")
        qdrant_port = os.getenv("QDRANT_PORT")
        qdrant_api_key = os.getenv(
            "QDRANT_API_KEY"
        )

        if not qdrant_host:
            raise ValueError(
                "QDRANT_HOST is not configured."
            )

        if qdrant_host.startswith(
            ("http://", "https://")
        ):
            self.client = QdrantClient(
                url=qdrant_host,
                api_key=qdrant_api_key,
                timeout=300,
            )
        else:
            self.client = QdrantClient(
                host=qdrant_host,
                port=int(
                    qdrant_port or "6333"
                ),
                api_key=qdrant_api_key,
                timeout=300,
            )

        self.collection_name = (
            collection_name
            or os.getenv("QDRANT_COLLECTION")
        )

        if not self.collection_name:
            raise ValueError(
                "Qdrant collection name is not configured."
            )
    def health(self):
        """
        Returns all collections to verify the connection.
        """

        return self.client.get_collections()

    def _ensure_payload_indexes(self) -> None:
        """
        Ensures payload indexes required by filtered
        deletion and retrieval exist.
        """

        for field_name in (
            "document",
            "content_type",
            "parent_section_code",
            "parent_section",
            "programme_code",
            "programme",
            "study_year",
            "semester",
            "course_code",
        ):
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name=field_name,
                field_schema=(
                    PayloadSchemaType.KEYWORD
                ),
                wait=True,
            )

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
            self._ensure_payload_indexes()
            return

        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.vector_size,
                distance=Distance.COSINE,
            ),
        )

        self._ensure_payload_indexes()

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
                size=self.vector_size,
                distance=Distance.COSINE,
            ),
        )

        self._ensure_payload_indexes()

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
        content_type: str | None = None,
    ) -> None:
        """
        Deletes vectors belonging to one document.

        When content_type is provided, only that
        content type is deleted.
        """

        conditions = [
            FieldCondition(
                key="document",
                match=MatchValue(
                    value=document_id
                ),
            )
        ]

        if content_type is not None:
            conditions.append(
                FieldCondition(
                    key="content_type",
                    match=MatchValue(
                        value=content_type
                    ),
                )
            )

        self.client.delete(
            collection_name=self.collection_name,
            points_selector=FilterSelector(
                filter=Filter(
                    must=conditions
                )
            ),
            wait=True,
        )

        print(
            f"Deleted existing vectors for "
            f"document '{document_id}'"
            + (
                f" with content type "
                f"'{content_type}'."
                if content_type
                else "."
            )
        )
    def filter_points(
        self,
        *,
        document_id: str,
        content_type: str,
        filters: dict[str, str] | None = None,
        limit: int = 100,
    ):
        """
        Returns points matching exact payload filters.
        """

        conditions = [
            FieldCondition(
                key="document",
                match=MatchValue(
                    value=document_id
                ),
            ),
            FieldCondition(
                key="content_type",
                match=MatchValue(
                    value=content_type
                ),
            ),
        ]

        for key, value in (filters or {}).items():
            conditions.append(
                FieldCondition(
                    key=key,
                    match=MatchValue(
                        value=value
                    ),
                )
            )

        points, _ = self.client.scroll(
            collection_name=self.collection_name,
            scroll_filter=Filter(
                must=conditions
            ),
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )

        return points

    def search(
        self,
        query_vector: list[float],
        limit: int = 5,
        document_id: str | None = None,
        content_type: str | None = None,
    ):
        """
        Searches for similar vectors.

        Optional filters restrict results by
        document and content type.
        """

        conditions = []

        if document_id is not None:
            conditions.append(
                FieldCondition(
                    key="document",
                    match=MatchValue(
                        value=document_id
                    ),
                )
            )

        if content_type is not None:
            conditions.append(
                FieldCondition(
                    key="content_type",
                    match=MatchValue(
                        value=content_type
                    ),
                )
            )

        query_filter = (
            Filter(must=conditions)
            if conditions
            else None
        )

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=query_filter,
            limit=limit,
        )

        return results.points

