import json
import re
from typing import Any

from src.llm.llm_service import LLMService
from src.schemas.graph import GraphExtractionResult


class EntityExtractor:
    """
    Extracts domain-specific graph entities and
    relationships from prospectus parent chunks.
    """

    SYSTEM_PROMPT = """
You are a knowledge graph extraction system for
university undergraduate prospectuses.

Extract only facts explicitly stated in the provided
text.

Allowed entity types:
- AdmissionCategory
- Qualification
- StudyStream
- EducationBoard
- Program
- Department
- Campus
- University
- EligibilityRule

Allowed relationship types:
- REQUIRES
- ALLOWS_STREAM
- ACCEPTS_FROM
- HAS_RULE
- OFFERS
- OFFERED_AT
- BELONGS_TO
- HAS_DEPARTMENT
- HAS_CAMPUS

Rules:
1. Do not invent entities or relationships.
2. Use concise canonical entity names.
3. Create stable lowercase entity IDs using underscores.
4. Every relationship source and target must refer to
   an entity returned in the entities list.
5. Preserve admission category codes exactly, such as
   R-2(b).
6. Extract only information supported by the text.
7. Return valid JSON only.
8. Do not use markdown code fences.

Return exactly this structure:

{
  "chunk_id": "",
  "entities": [
    {
      "entity_id": "",
      "name": "",
      "entity_type": "",
      "properties": {}
    }
  ],
  "relationships": [
    {
      "source_entity_id": "",
      "target_entity_id": "",
      "relationship_type": "",
      "properties": {}
    }
  ]
}
"""

    def __init__(self):
        self.llm_service = LLMService()

    def extract(
        self,
        chunk: dict[str, Any],
    ) -> GraphExtractionResult:

        chunk_id = chunk["chunk_id"]
        heading = chunk.get("heading", "")
        content = chunk.get("content", "")
        page_number = chunk.get("page_number")

        user_prompt = f"""
Extract knowledge graph facts from this prospectus
parent chunk.

CHUNK ID:
{chunk_id}

HEADING:
{heading}

PAGE NUMBER:
{page_number}

CONTENT:
{content}

The returned chunk_id must be exactly:
{chunk_id}
"""

        raw_response = (
            self.llm_service.generate_structured(
                system_prompt=self.SYSTEM_PROMPT,
                user_prompt=user_prompt,
            )
        )

        parsed_data = self._parse_json_response(
            raw_response
        )

        parsed_data["chunk_id"] = chunk_id

        return GraphExtractionResult.model_validate(
            parsed_data
        )

    def _parse_json_response(
        self,
        raw_response: str,
    ) -> dict[str, Any]:

        text = raw_response.strip()

        text = re.sub(
            r"^```(?:json)?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )

        text = re.sub(
            r"\s*```$",
            "",
            text,
        )

        try:
            return json.loads(text)

        except json.JSONDecodeError as error:
            raise ValueError(
                "Graph extractor returned invalid JSON."
            ) from error