import json
import os
from pathlib import Path

from dotenv import load_dotenv
from llama_cloud import LlamaCloud


PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / "backend" / ".env")

api_key = os.getenv("LLAMA_CLOUD_API_KEY")

if not api_key:
    raise RuntimeError(
        "LLAMA_CLOUD_API_KEY is missing."
    )

input_path = (
    PROJECT_ROOT
    / "storage"
    / "uploads"
    / "UGProspectus2025.pdf"
)

output_path = (
    PROJECT_ROOT
    / "storage"
    / "rescue"
    / "UGProspectus2025_llamaparse.json"
)

print("Starting full 122-page LlamaParse job...")
print("This is the only full parse we need.")

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
        verbose=True,
    )

data = (
    result.model_dump()
    if hasattr(result, "model_dump")
    else result
)

output_path.write_text(
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

print("\n=== FULL PARSE COMPLETE ===")
print("PAGES:", len(pages))
print("SAVED:", output_path)
