import json
from pathlib import Path

from experiments.layout_reconstruction_test import (
    LayoutReconstructionExperiment,
)

from experiments.markdown_converter import (
    MarkdownConverter,
)

from experiments.semantic_chunker import (
    create_semantic_chunks,
)

experiment = LayoutReconstructionExperiment()
experiment.run()

ROOT = Path(__file__).resolve().parent.parent

layout_path = (
    ROOT
    / "storage"
    / "experiments"
    / "layout_reconstruction.json"
)

with open(
    layout_path,
    "r",
    encoding="utf-8",
) as f:
    layout_document = json.load(f)

converter = MarkdownConverter()

markdown = converter.convert(
    layout_document
)

markdown_path = (
    ROOT
    / "storage"
    / "experiments"
    / "document.md"
)

markdown_path.write_text(
    markdown,
    encoding="utf-8",
)

print(f"Markdown saved -> {markdown_path}")

chunks = create_semantic_chunks(
    markdown_path,
)

print(
    f"Semantic chunks created: {len(chunks)}"
)

