import base64
import json
import os
from pathlib import Path
from typing import Any
from PIL import Image

from anthropic import Anthropic
from dotenv import load_dotenv
from groq import Groq
from openai import OpenAI


load_dotenv()


class VisionTableExtractor:
    """
    Extracts structured tables from images using a
    vision-capable LLM.

    Supports:
    - single-image extraction for standard tables
    - adaptive block extraction for dense tables
    """

    def __init__(self):
        self.provider = os.getenv(
            "VISION_PROVIDER"
        )

        self.api_key = (
            os.getenv("VISION_API_KEY")
            or os.getenv("LLM_API_KEY")
        )

        self.model = os.getenv(
            "VISION_MODEL"
        )

        if not self.provider:
            raise ValueError(
                "VISION_PROVIDER is missing."
            )

        self.provider = self.provider.lower()

        if not self.api_key:
            raise ValueError(
                "Vision API key is missing."
            )

        if not self.model:
            raise ValueError(
                "Vision model is missing."
            )

        if self.provider == "groq":
            self.client = Groq(
                api_key=self.api_key
            )

        elif self.provider == "openai":
            self.client = OpenAI(
                api_key=self.api_key
            )

        elif self.provider == "anthropic":
            self.client = Anthropic(
                api_key=self.api_key
            )

        else:
            raise ValueError(
                f"Unsupported vision provider: "
                f"{self.provider}"
            )

    def extract_single(
        self,
        image_path: Path,
        page_number: int,
    ) -> dict[str, Any]:

        if not image_path.exists():
            raise FileNotFoundError(
                f"Table image not found: {image_path}"
            )

        prompt = """
Extract the complete table visible in this image.

Return ONLY valid JSON with this structure:

{
  "table_title": "",
  "columns": [],
  "rows": []
}

Rules:

1. Preserve all visible column names.
2. Preserve all visible row values.
3. Every row must be a JSON object.
4. Row keys must match the column names.
5. Use null for unreadable cells.
6. Do not guess missing information.
7. Do not add information not visible in the image.
8. Return JSON only.
"""

        raw_response = self._send_vision_request(
            image_path=image_path,
            prompt=prompt,
        )

        result = self._parse_json_response(
            raw_response
        )

        result["metadata"] = {
            **result.get("metadata", {}),
            "extraction_strategy": "single",
            "page_number": page_number,
        }

        return result
    
    def extract_adaptive(
        self,
        image_path: Path,
        page_number: int,
        layout: dict[str, Any],
    ) -> dict[str, Any]:

        if not image_path.exists():
            raise FileNotFoundError(
                f"Table image not found: {image_path}"
            )

        output_dir = (
            image_path.parent
            / "adaptive_blocks"
            / f"page_{page_number}"
        )

        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        with Image.open(image_path) as image:

            width, height = image.size

            blocks = self._create_adaptive_blocks(
                width=width,
                height=height,
                layout=layout,
            )

            saved_blocks = []

            for block in blocks:

                cropped_image = image.crop(
                    (
                        block["left"],
                        block["top"],
                        block["right"],
                        block["bottom"],
                    )
                )

                block_path = (
                    output_dir
                    / f"block_{block['block_index']}.png"
                )

                cropped_image.save(block_path)

                saved_blocks.append(
                    {
                        **block,
                        "image_path": str(block_path),
                    }
                )

        extracted_blocks = []

        for block in saved_blocks:

            block_path = Path(
                block["image_path"]
            )

            prompt = f"""
        Extract the visible portion of this table.

        This is overlapping block {block["block_index"]}
        of {len(saved_blocks)}.

        Return ONLY valid JSON:

        {{
          "columns": [],
          "rows": [
            {{
              "category": "",
              "description": "",
              "values": []
            }}
          ]
        }}

        Rules:

        1. Preserve columns exactly from left to right.
        2. Preserve every visible data row.
        3. Keep numeric values in exact left-to-right order.
        4. Use null only for unreadable cells.
        5. Do not infer values outside this image block.
        6. Do not calculate totals.
        7. Do not skip zero values.
        8. Return JSON only.
        """

            raw_response = self._send_vision_request(
                image_path=block_path,
                prompt=prompt,
            )

            extracted_data = self._parse_json_response(
                raw_response
            )

            extracted_blocks.append(
                {
                    **block,
                    "extracted_data": extracted_data,
                }
            )

        return {
            "page_number": page_number,
            "image_path": str(image_path),
            "blocks": extracted_blocks,
            "metadata": {
                "extraction_strategy": "adaptive_blocks",
                "block_count": len(extracted_blocks),
                "output_dir": str(output_dir),
            },
        }
    

    def recover_rows(
        self,
        recovery_blocks: list[dict[str, Any]],
        source_blocks: list[dict[str, Any]],
        recovery_rows: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:

        recovery_results = []

        recovery_by_index = {
            row["row_index"]: row
            for row in recovery_rows
        }

        source_by_index = {
            block["block_index"]: block
            for block in source_blocks
        }

        for recovery_block in recovery_blocks:

            block_index = recovery_block[
                "block_index"
            ]

            source_block = source_by_index.get(
                block_index
            )

            if not source_block:
                continue

            image_path = Path(
                source_block["image_path"]
            )

            requested_rows = []

            for row_index in recovery_block[
                "row_indexes"
            ]:

                recovery_row = recovery_by_index.get(
                    row_index
                )

                if not recovery_row:
                    continue

                requested_rows.append(
                    {
                        "row_index": row_index,
                        "category": recovery_row[
                            "category"
                        ],
                        "recovery_scope": recovery_row[
                            "recovery_scope"
                        ],
                        "missing_columns": recovery_row[
                            "missing_columns"
                        ],
                    }
                )

            if not requested_rows:
                continue

            prompt = f"""
    Re-extract only the requested rows from this
    visible table block.

    Requested rows:

    {json.dumps(
        requested_rows,
        indent=2,
    )}

    Return ONLY valid JSON:

    {{
      "rows": [
        {{
          "row_index": 0,
          "category": "",
          "cells": {{
            "exact visible column name": 0
          }}
        }}
      ]
    }}

    Rules:

    1. Return only requested rows visible in this image.
    2. Return cells as column-name-to-value mappings.
    3. Use the exact visible column names from this image.
    4. Include only cells actually visible in this image block.
    5. Do not include leading placeholders for columns outside the image.
    6. Do not calculate totals.
    7. Do not guess unreadable values; use null.
    8. Do not skip zero values.
    9. Keep row_index exactly as provided.
    10. Return JSON only.
    """

            raw_response = self._send_vision_request(
                image_path=image_path,
                prompt=prompt,
            )

            extracted_data = (
                self._parse_json_response(
                    raw_response
                )
            )

            recovery_results.append(
                {
                    "block_index": block_index,
                    "rows": extracted_data.get(
                        "rows",
                        [],
                    ),
                }
            )

        return recovery_results


    def _create_adaptive_blocks(
        self,
        width: int,
        height: int,
        layout: dict[str, Any],
    ) -> list[dict[str, int]]:

        estimated_columns = max(
            layout.get("estimated_columns", 1),
            1,
        )

        target_columns_per_block = 10

        column_based_count = (
            estimated_columns
            + target_columns_per_block
            - 1
        ) // target_columns_per_block

        target_block_width = max(
            int(height * 0.40),
            1,
        )

        geometry_based_count = (
            width
            + target_block_width
            - 1
        ) // target_block_width

        block_count = max(
            2,
            column_based_count,
            geometry_based_count,
        )

        block_count = min(
            block_count,
            8,
        )

        overlap_ratio = 0.15

        block_width = width / block_count
        overlap = int(
            block_width * overlap_ratio
        )

        blocks = []

        for index in range(block_count):

            left = int(
                index * block_width
            )

            right = int(
                (index + 1) * block_width
            )

            if index > 0:
                left -= overlap

            if index < block_count - 1:
                right += overlap

            left = max(left, 0)
            right = min(right, width)

            blocks.append(
                {
                    "block_index": index + 1,
                    "left": left,
                    "top": 0,
                    "right": right,
                    "bottom": height,
                }
            )

        return blocks

    def _encode_image(
        self,
        image_path: Path,
    ) -> str:

        return base64.b64encode(
            image_path.read_bytes()
        ).decode("utf-8")

    def _parse_json_response(
        self,
        response_text: str,
    ) -> dict[str, Any]:

        text = response_text.strip()

        if text.startswith("```json"):
            text = text[7:]

        elif text.startswith("```"):
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        try:
            result = json.loads(text)

        except json.JSONDecodeError as error:
            raise ValueError(
                "Vision model returned invalid JSON."
            ) from error

        if not isinstance(result, dict):
            raise ValueError(
                "Vision response must be a JSON object."
            )

        return result

    def _send_vision_request(
        self,
        image_path: Path,
        prompt: str,
    ) -> str:

        encoded_image = self._encode_image(
            image_path
        )

        if self.provider in ("groq", "openai"):

            response = (
                self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt,
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": (
                                            "data:image/png;base64,"
                                            + encoded_image
                                        )
                                    },
                                },
                            ],
                        }
                    ],
                    temperature=0,
                )
            )

            return (
                response.choices[0]
                .message.content
                or ""
            )

        if self.provider == "anthropic":

            response = self.client.messages.create(
                model=self.model,
                max_tokens=8192,
                temperature=0,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": encoded_image,
                                },
                            },
                            {
                                "type": "text",
                                "text": prompt,
                            },
                        ],
                    }
                ],
            )

            return response.content[0].text

        raise ValueError(
            f"Unsupported vision provider: "
            f"{self.provider}"
        )