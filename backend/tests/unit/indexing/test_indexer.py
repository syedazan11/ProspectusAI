import json
from unittest.mock import MagicMock, patch

import numpy as np

from src.indexing.indexer import Indexer


def test_indexer_wires_vector_size():
    mock_embedder = MagicMock()
    mock_embedder.vector_size = 384

    with patch(
        "src.indexing.indexer.EmbeddingService",
        return_value=mock_embedder,
    ):
        with patch(
            "src.indexing.indexer.QdrantStore"
        ) as mock_store_class:
            Indexer()

    mock_store_class.assert_called_once_with(
        vector_size=384
    )


def test_indexes_real_chunk_schema(
    tmp_path,
):
    chunks_path = tmp_path / "chunks.json"

    chunks_path.write_text(
        json.dumps(
            {
                "source_file": (
                    "UGProspectus2025.pdf"
                ),
                "total_chunks": 2,
                "chunks": [
                    {
                        "chunk_id": "ug2025-0001",
                        "page_number": 75,
                        "text": (
                            "Admission requirements"
                        ),
                        "section_heading": (
                            "ADMISSION POLICY"
                        ),
                        "character_count": 22,
                    },
                    {
                        "chunk_id": "ug2025-0002",
                        "page_number": 99,
                        "text": "Fee information",
                        "section_heading": (
                            "FEE STRUCTURE"
                        ),
                        "character_count": 15,
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    mock_embedder = MagicMock()
    mock_embedder.vector_size = 384
    mock_embedder.embed_documents.return_value = [
        np.array([0.1, 0.2]),
        np.array([0.3, 0.4]),
    ]

    mock_store = MagicMock()

    with patch(
        "src.indexing.indexer.EmbeddingService",
        return_value=mock_embedder,
    ):
        with patch(
            "src.indexing.indexer.QdrantStore",
            return_value=mock_store,
        ):
            indexer = Indexer()
            indexer.index(chunks_path)

    mock_embedder.embed_documents.assert_called_once_with(
        [
            "Admission requirements",
            "Fee information",
        ]
    )

    mock_store.create_collection.assert_called_once_with()

    mock_store.delete_document.assert_called_once_with(
        document_id="UGProspectus2025",
        content_type="prospectus_chunk"
    )

    mock_store.upsert_points.assert_called_once()

    points = mock_store.upsert_points.call_args.args[0]

    assert len(points) == 2

    assert points[0].payload == {
        "document": "UGProspectus2025",
        "content_type": "prospectus_chunk",
        "page_number": 75,
        "heading": "ADMISSION POLICY",
        "chunk_id": "ug2025-0001",
        "content": "Admission requirements",
    }

    assert points[1].payload["chunk_id"] == (
        "ug2025-0002"
    )


