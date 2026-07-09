import json
import os
from pathlib import Path

from dotenv import load_dotenv
from llama_cloud import LlamaCloud


PROJECT_ROOT = Path(__file__).resolve().parents[3]

load_dotenv(
    PROJECT_ROOT / "backend" / ".env"
)

api_key = os.getenv("LLAMA_CLOUD_API_KEY")

if not api_key:
    raise RuntimeError(
        "LLAMA_CLOUD_API_KEY is missing."
    )

input_path = (
    PROJECT_ROOT
    / "storage"
    / "rescue"
    / "experiments"
    / "page_38.pdf"
)

output_dir = (
    PROJECT_ROOT
    / "storage"
    / "rescue"
    / "experiments"
)

json_path = output_dir / "page_38_llamaparse.json"
markdown_path = output_dir / "page_38_llamaparse.md"

if not input_path.exists():
    raise FileNotFoundError(input_path)

print("Input:", input_path)
print("Starting exactly one LlamaParse request...")

client = LlamaCloud(api_key=api_key)

with input_path.open("rb") as pdf_file:
    result = client.parsing.parse(
        upload_file=pdf_file,
        tier="agentic",
        version="latest",
        expand=[
            "markdown",
            "text",
        ],
        verbose=False,
    )

data = (
    result.model_dump()
    if hasattr(result, "model_dump")
    else result
)

json_path.write_text(
    json.dumps(
        data,
        indent=2,
        ensure_ascii=False,
        default=str,
    ),
    encoding="utf-8",
)

pages = (
    data.get("markdown", {})
    .get("pages", [])
)

markdown = "\n\n".join(
    page.get("markdown", "")
    for page in pages
    if page.get("success", True)
).strip()

markdown_path.write_text(
    markdown,
    encoding="utf-8",
)

print("LlamaParse request complete.")
print("Pages returned:", len(pages))
print("Markdown characters:", len(markdown))
print("JSON:", json_path)
print("Markdown:", markdown_path)
