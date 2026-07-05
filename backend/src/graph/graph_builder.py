import json
from pathlib import Path
from typing import Any

from src.graph.entity_extractor import EntityExtractor
from src.graph.graph_chunk_selector import GraphChunkSelector


class GraphBuilder:
    """
    Builds a document-level knowledge graph
    from selected parent chunks.

    Supports:
    - local chunk selection
    - API-call planning
    - checkpointing
    - resume after interruption
    """

    def __init__(self):
        self.entity_extractor = EntityExtractor()
        self.chunk_selector = GraphChunkSelector()

    def build(
        self,
        chunks: list[dict[str, Any]],
        checkpoint_path: Path | None = None,
    ) -> dict[str, Any]:

        entities_by_id: dict[str, dict[str, Any]] = {}

        relationships_by_key: dict[
            tuple[str, str, str],
            dict[str, Any],
        ] = {}

        processed_chunk_ids: set[str] = set()
        failed_chunks: list[dict[str, str]] = []

        if (
            checkpoint_path is not None
            and checkpoint_path.exists()
        ):
            checkpoint = json.loads(
                checkpoint_path.read_text(
                    encoding="utf-8"
                )
            )

            for entity in checkpoint.get(
                "entities",
                [],
            ):
                entities_by_id[
                    entity["entity_id"]
                ] = entity

            for relationship in checkpoint.get(
                "relationships",
                [],
            ):
                key = (
                    relationship["source_entity_id"],
                    relationship["target_entity_id"],
                    relationship["relationship_type"],
                )

                relationships_by_key[key] = relationship

            processed_chunk_ids.update(
                checkpoint.get(
                    "metadata",
                    {},
                ).get(
                    "processed_chunk_ids",
                    [],
                )
            )

            print(
                "Loaded checkpoint:"
                f" {len(processed_chunk_ids)}"
                " chunks already processed."
            )

        selection = self.chunk_selector.select(chunks)

        selected_chunks = selection[
            "selected_chunks"
        ]

        skipped_chunks = selection[
            "skipped_chunks"
        ]

        pending_chunks = [
            chunk
            for chunk in selected_chunks
            if chunk.get("chunk_id", "unknown")
            not in processed_chunk_ids
        ]

        print("\n========== GRAPH API PLAN ==========")
        print(f"Input chunks: {len(chunks)}")
        print(
            f"Selected locally: {len(selected_chunks)}"
        )
        print(
            f"Rejected locally: {len(skipped_chunks)}"
        )
        print(
            "Already checkpointed:"
            f" {len(selected_chunks) - len(pending_chunks)}"
        )
        print(
            f"Pending API calls: {len(pending_chunks)}"
        )
        print("====================================\n")

        for chunk in pending_chunks:
            chunk_id = chunk.get(
                "chunk_id",
                "unknown",
            )

            print(
                f"Extracting graph from {chunk_id}..."
            )

            try:
                result = (
                    self.entity_extractor.extract(
                        chunk
                    )
                )

                for entity in result.entities:
                    entities_by_id[
                        entity.entity_id
                    ] = entity.model_dump()

                for relationship in result.relationships:
                    key = (
                        relationship.source_entity_id,
                        relationship.target_entity_id,
                        relationship.relationship_type,
                    )

                    relationships_by_key[
                        key
                    ] = relationship.model_dump()

                processed_chunk_ids.add(chunk_id)

                if checkpoint_path is not None:
                    self._save_checkpoint(
                        checkpoint_path=checkpoint_path,
                        entities_by_id=entities_by_id,
                        relationships_by_key=(
                            relationships_by_key
                        ),
                        processed_chunk_ids=(
                            processed_chunk_ids
                        ),
                        failed_chunks=failed_chunks,
                        input_chunk_count=len(chunks),
                        selected_chunk_count=len(
                            selected_chunks
                        ),
                        skipped_chunks=skipped_chunks,
                    )

            except Exception as error:
                print(
                    f"Failed {chunk_id}: {error}"
                )

                failed_chunks.append(
                    {
                        "chunk_id": chunk_id,
                        "error": str(error),
                    }
                )

        return {
            "entities": list(
                entities_by_id.values()
            ),
            "relationships": list(
                relationships_by_key.values()
            ),
            "metadata": {
                "input_chunk_count": len(chunks),
                "selected_chunk_count": len(
                    selected_chunks
                ),
                "skipped_chunk_count": len(
                    skipped_chunks
                ),
                "processed_chunk_count": len(
                    processed_chunk_ids
                ),
                "processed_chunk_ids": sorted(
                    processed_chunk_ids
                ),
                "skipped_chunks": skipped_chunks,
                "failed_chunks": failed_chunks,
            },
        }

    def _save_checkpoint(
        self,
        checkpoint_path: Path,
        entities_by_id: dict[
            str,
            dict[str, Any],
        ],
        relationships_by_key: dict[
            tuple[str, str, str],
            dict[str, Any],
        ],
        processed_chunk_ids: set[str],
        failed_chunks: list[dict[str, str]],
        input_chunk_count: int,
        selected_chunk_count: int,
        skipped_chunks: list[dict[str, Any]],
    ) -> None:

        checkpoint = {
            "entities": list(
                entities_by_id.values()
            ),
            "relationships": list(
                relationships_by_key.values()
            ),
            "metadata": {
                "input_chunk_count": (
                    input_chunk_count
                ),
                "selected_chunk_count": (
                    selected_chunk_count
                ),
                "skipped_chunk_count": len(
                    skipped_chunks
                ),
                "processed_chunk_count": len(
                    processed_chunk_ids
                ),
                "processed_chunk_ids": sorted(
                    processed_chunk_ids
                ),
                "skipped_chunks": skipped_chunks,
                "failed_chunks": failed_chunks,
            },
        }

        self.save(
            graph=checkpoint,
            output_path=checkpoint_path,
        )

    def save(
        self,
        graph: dict[str, Any],
        output_path: Path,
    ) -> None:

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path.write_text(
            json.dumps(
                graph,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )