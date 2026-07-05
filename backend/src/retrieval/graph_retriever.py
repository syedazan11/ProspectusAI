import json
import re
from pathlib import Path
from typing import Any


class GraphRetriever:
    """
    Retrieves relevant entities and relationships
    from a document-level knowledge graph.

    This version is fully local and uses zero API calls.
    """

    def __init__(
        self,
        graph_path: Path,
    ):
        self.graph_path = graph_path
        self.graph = self._load_graph()

        self.entities = self.graph.get(
            "entities",
            [],
        )

        self.relationships = self.graph.get(
            "relationships",
            [],
        )

        self.entities_by_id = {
            entity["entity_id"]: entity
            for entity in self.entities
        }

    def _load_graph(self) -> dict[str, Any]:

        if not self.graph_path.exists():
            raise FileNotFoundError(
                f"Graph file not found: "
                f"{self.graph_path}"
            )

        return json.loads(
            self.graph_path.read_text(
                encoding="utf-8"
            )
        )

    def retrieve(
        self,
        query: str,
        top_k_entities: int = 5,
    ) -> dict[str, Any]:

        query_tokens = self._tokenize(query)

        scored_entities = []

        for entity in self.entities:

            score = self._score_entity(
                query_tokens=query_tokens,
                entity=entity,
            )

            if score > 0:
                scored_entities.append(
                    {
                        "score": score,
                        "entity": entity,
                    }
                )

        scored_entities.sort(
            key=lambda item: item["score"],
            reverse=True,
        )

        if not scored_entities:
            return {
                "query": query,
                "matched_entities": [],
                "relationships": [],
                "metadata": {
                    "matched_entity_count": 0,
                    "relationship_count": 0,
                },
            }

        best_score = scored_entities[0]["score"]

        anchor_entities = [
            item
            for item in scored_entities
            if item["score"] == best_score
        ][:top_k_entities]

        anchor_ids = {
            item["entity"]["entity_id"]
            for item in anchor_entities
        }

        matched_relationships = []
        expanded_entity_ids = set(anchor_ids)

        for relationship in self.relationships:

            source_id = relationship[
                "source_entity_id"
            ]

            target_id = relationship[
                "target_entity_id"
            ]

            if (
                source_id in anchor_ids
                or target_id in anchor_ids
            ):
                matched_relationships.append(
                    {
                        **relationship,
                        "source_entity": (
                            self.entities_by_id.get(
                                source_id
                            )
                        ),
                        "target_entity": (
                            self.entities_by_id.get(
                                target_id
                            )
                        ),
                    }
                )

                expanded_entity_ids.add(source_id)
                expanded_entity_ids.add(target_id)

        matched_entities = [
            item
            for item in scored_entities
            if item["entity"]["entity_id"]
            in expanded_entity_ids
        ]

        return {
            "query": query,
            "matched_entities": matched_entities,
            "relationships": matched_relationships,
            "metadata": {
                "matched_entity_count": len(
                    matched_entities
                ),
                "relationship_count": len(
                    matched_relationships
                ),
                "anchor_entity_count": len(
                    anchor_entities
                ),
            },
        }

    def _score_entity(
        self,
        query_tokens: set[str],
        entity: dict[str, Any],
    ) -> int:

        name = entity.get(
            "name",
            "",
        )

        entity_type = entity.get(
            "entity_type",
            "",
        )

        properties = entity.get(
            "properties",
            {},
        )

        entity_text = " ".join(
            [
                name,
                entity_type,
                json.dumps(
                    properties,
                    ensure_ascii=False,
                ),
            ]
        )

        entity_tokens = self._tokenize(
            entity_text
        )

        overlap = query_tokens.intersection(
            entity_tokens
        )

        score = len(overlap)

        normalized_query = " ".join(
            sorted(query_tokens)
        )

        normalized_name = " ".join(
            sorted(self._tokenize(name))
        )

        if (
            normalized_name
            and normalized_name
            in normalized_query
        ):
            score += 5

        return score

    def _tokenize(
        self,
        text: str,
    ) -> set[str]:

        return {
            token
            for token in re.findall(
                r"[a-z0-9]+",
                text.lower(),
            )
            if len(token) > 1
        }