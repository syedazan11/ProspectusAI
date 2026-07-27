import json
from pathlib import Path
import uuid

from qdrant_client.models import PointStruct

from src.embeddings.embedder import EmbeddingService
from src.vector_store.qdrant_store import QdrantStore


class CurriculumIndexer:
    """
    Indexes structured curriculum records into Qdrant.
    """

    BATCH_SIZE = 128

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
        records_json: Path,
        *,
        document_id: str,
    ) -> None:
        with open(
            records_json,
            "r",
            encoding="utf-8",
        ) as file:
            document = json.load(file)

        curriculum_metadata = document.get(
            "curriculum_metadata",
            {},
        )

        records = document["records"]

        print(
            f"Found {len(records)} "
            f"curriculum records."
        )

        if not records:
            print(
                "No curriculum records to index."
            )
            return

        self.vector_store.create_collection()

        self.vector_store.delete_document(
            document_id=document_id,
            content_type="curriculum_record",
        )

        for start in range(
            0,
            len(records),
            self.BATCH_SIZE,
        ):
            batch = records[
                start:start + self.BATCH_SIZE
            ]

            texts = [
                self._build_embedding_text(record)
                for record in batch
            ]

            embeddings = (
                self.embedder.embed_documents(texts)
            )

            points = []

            for record, text, vector in zip(
                batch,
                texts,
                embeddings,
            ):
                points.append(
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vector.tolist(),
                        payload={
                            "document": document_id,
                            "curriculum_scheme": (
                                curriculum_metadata.get(
                                    "curriculum_scheme"
                                )
                            ),
                            "term_names": (
                                curriculum_metadata.get(
                                    "term_names",
                                    [],
                                )
                            ),
                            "content_type": (
                                "curriculum_record"
                            ),
                            "parent_section_code": (
                                record.get(
                                    "parent_section_code"
                                )
                            ),
                            "parent_section": (
                                record.get(
                                    "parent_section"
                                )
                            ),
                            "programme_code": (
                                record["programme_code"]
                            ),
                            "programme": (
                                record["programme"]
                            ),
                            "study_year": (
                                record["study_year"]
                            ),
                            "semester": (
                                record["semester"]
                            ),
                            "course_code": (
                                record["course_code"]
                            ),
                            "course_title": (
                                record["course_title"]
                            ),
                            "theory_hours": (
                                record["theory_hours"]
                            ),
                            "practical_hours": (
                                record[
                                    "practical_hours"
                                ]
                            ),
                            "total_credit_hours": (
                                record[
                                    "total_credit_hours"
                                ]
                            ),
                            "page_number": (
                                record["source_page"]
                            ),
                            "content": text,
                        },
                    )
                )

            self.vector_store.upsert_points(
                points
            )

            print(
                f"Indexed "
                f"{start + len(batch)} / "
                f"{len(records)} "
                f"curriculum records."
            )

    @staticmethod
    def _build_embedding_text(
        record: dict,
    ) -> str:
        return (
            f"{record['programme']} | "
            f"{record['study_year']} | "
            f"{record['semester']} Semester | "
            f"{record['course_code']} | "
            f"{record['course_title']} | "
            f"Theory hours: "
            f"{record['theory_hours']} | "
            f"Practical hours: "
            f"{record['practical_hours']} | "
            f"Total credit hours: "
            f"{record['total_credit_hours']}"
        )
