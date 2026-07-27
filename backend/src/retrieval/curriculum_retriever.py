from pathlib import Path

from src.embeddings.embedder import EmbeddingService
from src.services.document_manager import DocumentManager
from src.vector_store.qdrant_store import QdrantStore


class CurriculumRetriever:
    """
    Retrieves structured curriculum records using
    exact Qdrant payload filters.
    """

    def __init__(
        self,
        collection_name: str | None = None,
        document_id: str | None = None,
    ):
        self.embedder = EmbeddingService()
        self.document_id = document_id

        self.vector_store = QdrantStore(
            vector_size=self.embedder.vector_size,
            collection_name=collection_name,
        )

    def retrieve(
        self,
        *,
        programme_code: str,
        study_year: str | None = None,
        semester: str | None = None,
        course_code: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        document_id = self.document_id

        if document_id is None:
            active_document = (
                DocumentManager()
                .get_active_document()
            )

            document_id = active_document[
                "document_id"
            ]

        filters = {
            "programme_code": programme_code,
        }

        if study_year is not None:
            filters["study_year"] = study_year

        if semester is not None:
            filters["semester"] = semester

        if course_code is not None:
            filters["course_code"] = course_code

        points = self.vector_store.filter_points(
            document_id=document_id,
            content_type="curriculum_record",
            filters=filters,
            limit=limit,
        )

        records = [
            dict(point.payload or {})
            for point in points
        ]

        print("\n========== CURRICULUM RETRIEVER ==========")
        print(f"Retrieved {len(records)} records")
        for r in records:
            print(
                r.get("course_code"),
                "|",
                r.get("course_title"),
                "|",
                r.get("study_year"),
                "|",
                r.get("semester"),
            )
        print("=========================================\n")

        records.sort(
            key=lambda record: (
                self._semester_order(
                    record.get("semester")
                ),
                record.get("course_code", ""),
                record.get("course_title", ""),
            )
        )

        return records

    @staticmethod
    def _semester_order(
        semester: str | None,
    ) -> int:
        order = {
            "Fall": 0,
            "Spring": 1,
        }

        return order.get(
            semester,
            99,
        )

