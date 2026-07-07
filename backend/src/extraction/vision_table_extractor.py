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
from src.processing.table_layout_analyzer import (
    TableLayoutAnalyzer,
)

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
        self.provider = os.getenv("VISION_PROVIDER")

        self.api_key = os.getenv("VISION_API_KEY") or os.getenv("LLM_API_KEY")

        self.model = os.getenv("VISION_MODEL")

        if not self.provider:
            raise ValueError("VISION_PROVIDER is missing.")

        self.provider = self.provider.lower()

        if not self.api_key:
            raise ValueError("Vision API key is missing.")

        if not self.model:
            raise ValueError("Vision model is missing.")

        if self.provider == "groq":
            self.client = Groq(api_key=self.api_key)

        elif self.provider == "openai":
            self.client = OpenAI(api_key=self.api_key)

        elif self.provider == "anthropic":
            self.client = Anthropic(api_key=self.api_key)

        else:
            raise ValueError(
                f"Unsupported vision provider: {self.provider}"
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

1. Preserve all visible column names exactly.
2. Preserve every visually separate table row as a
   separate JSON object.
3. NEVER merge two adjacent rows, row labels, categories,
   abbreviations, or values into one row.
4. If two labels appear on separate horizontal rows,
   they MUST produce two separate JSON row objects.
5. Keep each value aligned with the row and column where
   it visibly appears.
6. Every row must be a JSON object.
7. Row keys must match the column names exactly.
8. Preserve zero values. Do not skip them.
9. Use null for genuinely unreadable cells.
10. Do not guess missing information.
11. Do not calculate, combine, summarize, or reconstruct
    values from multiple rows.
12. Before returning JSON, verify that no two visually
    separate rows were merged together.
13. If a row label or category is accidentally repeated
    identically within the same cell, keep it only once.
    Example: "ABC ABC" must become "ABC".
14. Return JSON only.
"""

        raw_response = self._send_vision_request(
            image_path=image_path,
            prompt=prompt,
        )

        debug_dir = (
            image_path.parent
            / "vision_debug"
        )

        debug_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        debug_path = (
            debug_dir
            / f"page_{page_number}_raw.txt"
        )

        debug_path.write_text(
            raw_response,
            encoding="utf-8",
        )

        print(
            f"Saved raw vision response: "
            f"{debug_path}"
        )

        result = self._parse_json_response(
            raw_response
        )

        for row in result.get("rows", []):
            for key, value in row.items():

                if not isinstance(value, str):
                    continue

                parts = value.strip().split()

                if (
                    len(parts) % 2 == 0
                    and parts[: len(parts) // 2]
                    == parts[len(parts) // 2 :]
                ):
                    row[key] = " ".join(
                        parts[: len(parts) // 2]
                    )

        if (
            "columns" not in result
            or "rows" not in result
        ):
            raise ValueError(
                "Single-table vision response "
                "is missing columns or rows."
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

        output_dir.mkdir(parents=True, exist_ok=True)

        with Image.open(image_path) as source_image:

            # Dense prospectus tables may be stored sideways.
            # Rotate portrait table crops 90 degrees clockwise
            # before adaptive block extraction.
            if source_image.height > source_image.width:
                image = source_image.rotate(
                    270,
                    expand=True,
                )

                normalized_path = (
                    output_dir
                    / f"page_{page_number}_normalized.png"
                )

                image.save(normalized_path)

                print(
                    f"Rotated page {page_number} "
                    f"90 degrees clockwise."
                )

            else:
                image = source_image.copy()

            width, height = image.size

            # Re-analyze the normalized image.
            # The original layout is stale after rotation.
            if source_image.height > source_image.width:
                normalized_layout = TableLayoutAnalyzer().analyze(
                    image_path=normalized_path,
                )
            else:
                normalized_layout = layout

            print(
                "Normalized layout:",
                normalized_layout,
            )

            blocks = self._create_adaptive_blocks(
                width=width,
                height=height,
                layout=normalized_layout,
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
                    output_dir / f"block_{block['block_index']}.png"
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

            block_path = Path(block["image_path"])

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

            debug_dir = output_dir / "vision_debug"
            debug_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            debug_path = (
                debug_dir
                / f"block_{block['block_index']}_raw.txt"
            )

            debug_path.write_text(
                raw_response,
                encoding="utf-8",
            )

            try:
                extracted_data = self._parse_json_response(
                    raw_response
                )

            except ValueError:

                print(
                    f"Block {block['block_index']} "
                    f"returned invalid JSON. Retrying once..."
                )

                retry_prompt = """
            Extract the visible table block.

            Return ONLY compact valid JSON:

            {
              "columns": [],
              "rows": [
                {
                  "category": "",
                  "description": "",
                  "values": []
                }
              ]
            }

            Rules:
            1. One visible table row = one JSON row.
            2. Never merge adjacent rows.
            3. Keep values in exact left-to-right order.
            4. Preserve zero values.
            5. Use null only for unreadable cells.
            6. No explanations.
            7. No markdown.
            8. Return compact JSON only.
            """

                raw_response = self._send_vision_request(
                    image_path=block_path,
                    prompt=retry_prompt,
                )

                debug_path.write_text(
                    raw_response,
                    encoding="utf-8",
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
            row["row_index"]: row for row in recovery_rows
        }

        source_by_index = {
            block["block_index"]: block for block in source_blocks
        }

        for recovery_block in recovery_blocks:

            block_index = recovery_block["block_index"]

            source_block = source_by_index.get(block_index)

            if not source_block:
                continue

            image_path = Path(source_block["image_path"])

            requested_rows = []

            for row_index in recovery_block["row_indexes"]:

                recovery_row = recovery_by_index.get(row_index)

                if not recovery_row:
                    continue

                requested_rows.append(
                    {
                        "row_index": row_index,
                        "category": recovery_row["category"],
                        "recovery_scope": recovery_row["recovery_scope"],
                        "missing_columns": recovery_row["missing_columns"],
                    }
                )

            if not requested_rows:
                continue

            prompt = f"""
    Re-extract only the requested rows from this
    visible table block.

    Requested rows:

    {json.dumps(requested_rows, indent=2)}

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

            extracted_data = self._parse_json_response(raw_response)

            recovery_results.append(
                {
                    "block_index": block_index,
                    "rows": extracted_data.get("rows", []),
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

        column_count = max(
            2,
            (
                estimated_columns
                + target_columns_per_block
                - 1
            )
            // target_columns_per_block,
        )

        column_count = min(column_count, 8)

        # Dense tables must also be split vertically.
        # Keep roughly 8-10 visible rows per block.
        row_band_count = 3

        column_width = width / column_count
        row_band_height = height / row_band_count

        column_overlap = int(column_width * 0.15)
        row_overlap = int(row_band_height * 0.08)

        blocks = []
        block_index = 1

        for row_band_index in range(row_band_count):

            top = int(
                row_band_index * row_band_height
            )

            bottom = int(
                (row_band_index + 1)
                * row_band_height
            )

            if row_band_index > 0:
                top -= row_overlap

            if row_band_index < row_band_count - 1:
                bottom += row_overlap

            top = max(top, 0)
            bottom = min(bottom, height)

            for column_band_index in range(column_count):

                left = int(
                    column_band_index * column_width
                )

                right = int(
                    (column_band_index + 1)
                    * column_width
                )

                if column_band_index > 0:
                    left -= column_overlap

                if column_band_index < column_count - 1:
                    right += column_overlap

                left = max(left, 0)
                right = min(right, width)

                blocks.append(
                    {
                        "block_index": block_index,
                        "row_band_index": (
                            row_band_index
                        ),
                        "column_band_index": (
                            column_band_index
                        ),
                        "left": left,
                        "top": top,
                        "right": right,
                        "bottom": bottom,
                    }
                )

                block_index += 1

        return blocks

    def _encode_image(
        self,
        image_path: Path,
    ) -> str:

        return base64.b64encode(image_path.read_bytes()).decode("utf-8")

    def _parse_json_response(
        self,
        response_text: str,
    ) -> dict[str, Any]:

        text = response_text.strip()

        if not text:
            raise ValueError(
                "Vision model returned an empty response."
            )

        if text.startswith("```json"):
            text = text[7:]

        elif text.startswith("```"):
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        try:
            result = json.loads(text)

        except json.JSONDecodeError:
            raise ValueError(
                "Vision model response was truncated "
                "or contained invalid JSON."
            )

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

        encoded_image = self._encode_image(image_path)

        if self.provider in ("groq", "openai"):

            response = self.client.chat.completions.create(
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
                max_tokens=8192,
            )

            return response.choices[0].message.content or ""

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

        raise ValueError(f"Unsupported vision provider: {self.provider}")