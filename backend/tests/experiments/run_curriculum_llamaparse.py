from pathlib import Path

from src.processing.prospectus.curriculum_parse_service import (
    CurriculumParseService,
)


PROJECT_ROOT = Path.cwd().parent

input_path = (
    PROJECT_ROOT
    / "storage"
    / "rescue"
    / "curriculum"
    / "UGProspectus2025_pages_38_74.pdf"
)

output_path = (
    PROJECT_ROOT
    / "storage"
    / "processed"
    / "UGProspectus2025"
    / "curriculum_llamaparse_v1.json"
)

already_cached = output_path.exists()

print("Input:", input_path)
print("Output:", output_path)
print("Cached before run:", already_cached)

service = CurriculumParseService()

data = service.parse(
    input_path=input_path,
    output_json_path=output_path,
)

pages = (
    data.get("markdown", {})
    .get("pages", [])
)

successful = sum(
    page.get("success", True)
    for page in pages
)

markdown_chars = sum(
    len(page.get("markdown", ""))
    for page in pages
)

print("Parse complete.")
print("Pages returned:", len(pages))
print("Successful pages:", successful)
print("Markdown characters:", markdown_chars)
print("Output exists:", output_path.exists())
print("Output size:", output_path.stat().st_size)
