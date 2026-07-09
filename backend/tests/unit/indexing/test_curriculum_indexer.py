import json
from unittest.mock import MagicMock, patch

import numpy as np

from src.indexing.curriculum_indexer import (
    CurriculumIndexer,
)


def test_indexes_curriculum_record(
    tmp_path,
):
    records_path = tmp_path / "curriculum.json"

    records_path.write_text(
        json.dumps(
            {
                "source": "test",
                "total_records": 1,
                "records": [
                    {
                        "programme_code": "3.1.1",
                        "programme": "Civil Engineering",
                        "study_year": "FIRST YEAR",
                        "semester": "Fall",
                        "course_code": "PH-129",
                        "course_title": "Applied Physics",
                        "theory_hours": "3",
                        "practical_hours": "0",
                        "total_credit_hours": "3",
                        "source_page": 38,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    mock_embedder = MagicMock()
    mock_embedder.vector_size = 384
    mock_embedder.embed_documents.return_value = [
        np.array([0.1, 0.2])
    ]

    mock_store = MagicMock()

    with patch(
        "src.indexing.curriculum_indexer.EmbeddingService",
        return_value=mock_embedder,
    ):
        with patch(
            "src.indexing.curriculum_indexer.QdrantStore",
            return_value=mock_store,
        ):
            indexer = CurriculumIndexer()

            indexer.index(
                records_path,
                document_id="UGProspectus2025",
            )

    mock_store.upsert_points.assert_called_once()

    points = mock_store.upsert_points.call_args.args[0]

    assert len(points) == 1

    payload = points[0].payload

    assert payload["document"] == "UGProspectus2025"
    assert payload["content_type"] == "curriculum_record"
    assert payload["programme_code"] == "3.1.1"
    assert payload["course_code"] == "PH-129"
    assert payload["course_title"] == "Applied Physics"
    assert payload["page_number"] == 38
