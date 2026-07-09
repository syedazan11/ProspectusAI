from unittest.mock import MagicMock, patch

from src.retrieval.curriculum_retriever import (
    CurriculumRetriever,
)


def test_retrieve_uses_exact_curriculum_filters():
    mock_embedder = MagicMock()
    mock_embedder.vector_size = 384

    mock_store = MagicMock()
    mock_store.filter_points.return_value = []

    with patch(
        "src.retrieval.curriculum_retriever.EmbeddingService",
        return_value=mock_embedder,
    ):
        with patch(
            "src.retrieval.curriculum_retriever.QdrantStore",
            return_value=mock_store,
        ):
            with patch(
                "src.retrieval.curriculum_retriever.DocumentManager",
            ) as manager_class:
                manager_class.return_value.get_active_document.return_value = {
                    "filename": "UGProspectus2025.pdf"
                }

                retriever = CurriculumRetriever()

                results = retriever.retrieve(
                    programme_code="3.1.1",
                    study_year="SECOND YEAR",
                )

    assert results == []

    mock_store.filter_points.assert_called_once_with(
        document_id="UGProspectus2025",
        content_type="curriculum_record",
        filters={
            "programme_code": "3.1.1",
            "study_year": "SECOND YEAR",
        },
        limit=100,
    )


def test_retrieve_sorts_fall_before_spring():
    mock_embedder = MagicMock()
    mock_embedder.vector_size = 384

    spring_point = MagicMock()
    spring_point.payload = {
        "semester": "Spring",
        "course_code": "CE-228",
        "course_title": "Engineering Drawing-II",
    }

    fall_point = MagicMock()
    fall_point.payload = {
        "semester": "Fall",
        "course_code": "CE-224",
        "course_title": "Engineering Surveying-II",
    }

    mock_store = MagicMock()
    mock_store.filter_points.return_value = [
        spring_point,
        fall_point,
    ]

    with patch(
        "src.retrieval.curriculum_retriever.EmbeddingService",
        return_value=mock_embedder,
    ):
        with patch(
            "src.retrieval.curriculum_retriever.QdrantStore",
            return_value=mock_store,
        ):
            with patch(
                "src.retrieval.curriculum_retriever.DocumentManager",
            ) as manager_class:
                manager_class.return_value.get_active_document.return_value = {
                    "filename": "UGProspectus2025.pdf"
                }

                results = CurriculumRetriever().retrieve(
                    programme_code="3.1.1",
                    study_year="SECOND YEAR",
                )

    assert [
        record["course_code"]
        for record in results
    ] == [
        "CE-224",
        "CE-228",
    ]
