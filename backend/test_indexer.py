from pathlib import Path

from src.indexing.indexer import Indexer

chunks_path = (
    Path(__file__).resolve().parent.parent
    / "storage"
    / "chunks"
    / "testingnedprospect.json"
)

indexer = Indexer()

indexer.index(chunks_path)