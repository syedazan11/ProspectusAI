import os
import base64
import json
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq
from PIL import Image


load_dotenv()

IMAGE_PATH = Path(
    "experiments/table_extraction/page_2.png"
)

OUTPUT_DIR = Path(
    "experiments/table_extraction/header_test"
)

MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

OUTPUT_DIR.mkdir(exist_ok=True)

api_key = os.getenv("LLM_API_KEY")

if not api_key:
    raise ValueError("LLM_API_KEY is missing in .env")

client = Groq(api_key=api_key)


def encode_image(image_path: Path) -> str:
    return base64.b64encode(
        image_path.read_bytes()
    ).decode("utf-8")


image = Image.open(IMAGE_PATH)

width, height = image.size

print(f"Image size: {width} x {height}")

# Crop the upper part containing the actual program headers.
header_top = int(height * 0.05)
header_bottom = int(height * 0.30)

header_section = image.crop(
    (0, header_top, width, header_bottom)
)

header_section.save(
    OUTPUT_DIR / "full_header_section.png"
)

# Same horizontal block boundaries as our successful numeric test.
column_blocks = [
    (0.00, 0.34),
    (0.27, 0.56),
    (0.49, 0.78),
    (0.71, 1.00),
]

all_blocks = []

for index, (left_ratio, right_ratio) in enumerate(
    column_blocks,
    start=1,
):
    left = int(width * left_ratio)
    right = int(width * right_ratio)

    block = header_section.crop(
        (left, 0, right, header_section.height)
    )

    block = block.resize(
        (
            block.width * 2,
            block.height * 2,
        )
    )

    block_path = (
        OUTPUT_DIR / f"header_block_{index}.png"
    )

    block.save(block_path)

    print(f"Processing header block {index}...")

    encoded = encode_image(block_path)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """
This image is a horizontal section of the HEADER
of a university seat-distribution table.

Extract ONLY actual program column abbreviations
visible in the table header.

Examples of the type of headers expected:
CE, CE (UE), PE, ME, CS, SE.

Return ONLY valid JSON:

{
  "columns": []
}

Rules:

1. Read headers strictly from left to right.
2. Preserve abbreviations exactly as visible.
3. Include only actual table column headers.
4. Do not include numbers from data rows.
5. Do not include the table title.
6. Do not invent headers outside the image.
7. If a header is cut off at a crop boundary,
   do not include it.
8. Return JSON only.
""",
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": (
                                "data:image/png;base64,"
                                + encoded
                            )
                        },
                    },
                ],
            }
        ],
        temperature=0,
        max_completion_tokens=2048,
    )

    result = (
        response.choices[0].message.content
        or ""
    ).strip()

    if result.startswith("```json"):
        result = result[7:]

    elif result.startswith("```"):
        result = result[3:]

    if result.endswith("```"):
        result = result[:-3]

    result = result.strip()

    output_path = (
        OUTPUT_DIR / f"header_block_{index}.json"
    )

    output_path.write_text(
        result,
        encoding="utf-8",
    )

    try:
        parsed = json.loads(result)
        all_blocks.append(parsed)

        print(
            f"Block {index}: "
            f"{len(parsed.get('columns', []))} headers"
        )

    except json.JSONDecodeError as error:
        print(f"Block {index}: invalid JSON")
        print(error)


combined_path = (
    OUTPUT_DIR / "all_headers.json"
)

combined_path.write_text(
    json.dumps(
        all_blocks,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

print("\nHeader test completed.")
print(f"Output: {combined_path}")