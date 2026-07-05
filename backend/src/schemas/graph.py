from typing import Any

from pydantic import BaseModel, Field


class GraphEntity(BaseModel):
    entity_id: str
    name: str
    entity_type: str
    properties: dict[str, Any] = Field(
        default_factory=dict
    )


class GraphRelationship(BaseModel):
    source_entity_id: str
    target_entity_id: str
    relationship_type: str
    properties: dict[str, Any] = Field(
        default_factory=dict
    )


class GraphExtractionResult(BaseModel):
    chunk_id: str
    entities: list[GraphEntity] = Field(
        default_factory=list
    )
    relationships: list[GraphRelationship] = Field(
        default_factory=list
    )