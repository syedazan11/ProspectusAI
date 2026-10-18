from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ============================================================
# Retrieval Intent
# ============================================================

class RetrievalIntent(str, Enum):

    GENERAL = "general"

    PEOPLE = "people"

    FEES = "fees"

    ADMISSION_CATEGORY = "admission_category"


@dataclass(slots=True)
class RetrievalPlan:

    raw_query: str

    intent: RetrievalIntent

    keywords: list[str]

    phrases: list[str]

    admission_codes: list[str]

    entities: list[str]

    topics: list[str]

    is_follow_up: bool

# ============================================================
# Lexical Match
# ============================================================

@dataclass(frozen=True, slots=True)
class LexicalMatch:
    matched_terms: list[str]
    heading_matches: list[str]
    phrase_matches: list[str]
    code_matches: list[str]
    term_coverage: float
    heading_coverage: float
    matched_query_weight: float


# ============================================================
# Query Analysis
# ============================================================

@dataclass(frozen=True, slots=True)
class QueryAnalysis:
    raw_query: str

    intent: RetrievalIntent

    terms: list[str]

    phrases: list[str]

    codes: list[str]

    role: str | None

    entities: list[str]

    is_follow_up: bool


# ============================================================
# Chunk Kind
# ============================================================

class ChunkKind(str, Enum):
    """
    High-level storage type.

    Semantic:
        Normal layout-aware chunks.

    Structured:
        Structured records like People,
        Fees and Admission Categories.
    """

    SEMANTIC = "semantic"
    STRUCTURED = "structured"


# ============================================================
# Structured Record Type
# ============================================================

class StructuredRecordType(str, Enum):
    PEOPLE = "people"
    FEES = "fees"
    ADMISSION_CATEGORIES = "admission_categories"


# ============================================================
# Semantic Category
# ============================================================

class ChunkCategory(str, Enum):
    GENERAL = "general"

    TABLE_OF_CONTENTS = "table_of_contents"

    CURRICULUM = "curriculum"


# ============================================================
# Retrieval Candidate
# ============================================================

@dataclass(slots=True)
class RetrievalCandidate:
    """
    Internal representation used throughout retrieval.

    Every collector returns RetrievalCandidate.

    Ranking, expansion and finalization only operate
    on this object.
    """

    chunk: dict[str, Any]

    kind: ChunkKind

    category: ChunkCategory | None = None

    semantic_score: float = 0.0

    lexical_score: float = 0.0

    heading_score: float = 0.0

    metadata_score: float = 0.0

    structured_score: float = 0.0

    final_score: float = 0.0

    matched_terms: set[str] = field(default_factory=set)
    
    is_context: bool = False

@dataclass(slots=True)
class NormalizedChunk:
    """
    Canonical representation of every chunk used by the
    General Retriever.

    Semantic and structured chunks are converted into this
    format exactly once.

    Curriculum records are never normalized here because
    they are handled by CurriculumRetriever.
    """

    chunk_id: str

    kind: ChunkKind

    page: int

    content: str

    embedding_text: str

    heading: str | None

    record_type: StructuredRecordType | None

    raw: dict[str, Any]