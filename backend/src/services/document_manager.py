from datetime import datetime, timezone
from pathlib import Path
import json
import os
import shutil
from typing import Any

from dotenv import load_dotenv
from qdrant_client import QdrantClient


class DocumentManager:
    """
    Central source of truth for prospectus documents.

    Responsibilities:
    - manage the document registry
    - resolve the active ready prospectus
    - derive all storage paths
    - retain only the newest two prospectus years
    - remove all generated data for older documents
    """

    def __init__(self) -> None:

        self.project_root = (
            Path(__file__).resolve().parents[3]
        )

        self.storage_dir = (
            self.project_root / "storage"
        )

        self.registry_path = (
            self.storage_dir / "registry.json"
        )

    def load_registry(self) -> dict[str, Any]:

        if not self.registry_path.exists():
            return {
                "active_document_id": None,
                "documents": [],
            }

        return json.loads(
            self.registry_path.read_text(
                encoding="utf-8"
            )
        )

    def save_registry(
        self,
        registry: dict[str, Any],
    ) -> None:

        self.storage_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.registry_path.write_text(
            json.dumps(
                registry,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

    def register_document(
        self,
        pdf_path: Path,
        year: int,
        status: str = "uploaded",
    ) -> dict[str, Any]:

        pdf_path = pdf_path.resolve()

        if not pdf_path.exists():
            raise FileNotFoundError(
                f"PDF not found: {pdf_path}"
            )

        if pdf_path.suffix.lower() != ".pdf":
            raise ValueError(
                "Only PDF documents can be registered."
            )

        document_id = pdf_path.stem

        registry = self.load_registry()

        documents = [
            document
            for document in registry["documents"]
            if document["document_id"] != document_id
        ]

        entry = {
            "document_id": document_id,
            "filename": pdf_path.name,
            "year": year,
            "status": status,
            "uploaded_at": (
                datetime.now(timezone.utc).isoformat()
            ),
        }

        documents.append(entry)

        registry["documents"] = documents

        self.save_registry(registry)

        return entry

    def mark_ready(
        self,
        document_id: str,
    ) -> None:

        registry = self.load_registry()

        target = None

        for document in registry["documents"]:

            if (
                document["document_id"]
                == document_id
            ):
                document["status"] = "ready"
                target = document
                break

        if target is None:
            raise ValueError(
                f"Unknown document: {document_id}"
            )

        registry["active_document_id"] = (
            document_id
        )

        self.save_registry(registry)

        self.enforce_retention()

    def get_active_document(
        self,
    ) -> dict[str, Any]:

        registry = self.load_registry()

        active_id = registry.get(
            "active_document_id"
        )

        if not active_id:
            raise FileNotFoundError(
                "No active prospectus is configured."
            )

        for document in registry["documents"]:

            if (
                document["document_id"]
                == active_id
                and document["status"] == "ready"
            ):
                return document

        raise FileNotFoundError(
            "The active prospectus is not ready."
        )

    def get_active_document_id(self) -> str:

        return self.get_active_document()[
            "document_id"
        ]

    def get_upload_path(
        self,
        document_id: str,
    ) -> Path:

        registry = self.load_registry()

        for document in registry["documents"]:

            if (
                document["document_id"]
                == document_id
            ):
                return (
                    self.storage_dir
                    / "uploads"
                    / document["filename"]
                )

        raise FileNotFoundError(
            f"Unknown document: {document_id}"
        )

    def get_parsed_path(
        self,
        document_id: str,
    ) -> Path:

        return (
            self.storage_dir
            / "parsed"
            / f"{document_id}.json"
        )

    def get_cleaned_path(
        self,
        document_id: str,
    ) -> Path:

        return (
            self.storage_dir
            / "cleaned"
            / f"{document_id}.json"
        )

    def get_chunks_path(
        self,
        document_id: str,
    ) -> Path:

        return (
            self.storage_dir
            / "chunks"
            / f"{document_id}.json"
        )

    def get_tables_path(
        self,
        document_id: str,
    ) -> Path:

        return (
            self.storage_dir
            / "tables"
            / f"{document_id}.json"
        )

    def get_graph_path(
        self,
        document_id: str,
    ) -> Path:

        return (
            self.storage_dir
            / "graph"
            / f"{document_id}.json"
        )

    def get_pages_dir(
        self,
        document_id: str,
    ) -> Path:

        return (
            self.storage_dir
            / "pages"
            / document_id
        )

    def list_documents(
        self,
    ) -> list[dict[str, Any]]:

        registry = self.load_registry()

        return sorted(
            registry["documents"],
            key=lambda document: (
                int(document["year"]),
                document.get("uploaded_at", ""),
            ),
            reverse=True,
        )


    def delete_document(
        self,
        document_id: str,
    ) -> None:

        registry = self.load_registry()

        target = None

        for document in registry["documents"]:

            if (
                document["document_id"]
                == document_id
            ):
                target = document
                break

        if target is None:
            raise ValueError(
                f"Unknown document: {document_id}"
            )

        self._delete_document_files(
            target
        )

        remaining = [
            document
            for document in registry["documents"]
            if (
                document["document_id"]
                != document_id
            )
        ]

        registry["documents"] = remaining

        if (
            registry.get("active_document_id")
            == document_id
        ):

            ready_documents = [
                document
                for document in remaining
                if document["status"] == "ready"
            ]

            ready_documents.sort(
                key=lambda document: (
                    int(document["year"]),
                    document.get(
                        "uploaded_at",
                        "",
                    ),
                ),
                reverse=True,
            )

            registry["active_document_id"] = (
                ready_documents[0]["document_id"]
                if ready_documents
                else None
            )

        self.save_registry(registry)


    def enforce_retention(self) -> None:
        """
        Keep documents from only the newest two
        prospectus years currently registered.
        """

        registry = self.load_registry()

        documents = registry["documents"]

        if not documents:
            return

        years = sorted(
            {
                int(document["year"])
                for document in documents
            },
            reverse=True,
        )

        keep_years = set(years[:2])

        kept_documents = []

        for document in documents:

            if int(document["year"]) in keep_years:
                kept_documents.append(document)
                continue

            self._delete_document_files(
                document
            )

        registry["documents"] = kept_documents

        self.save_registry(registry)

    def _delete_document_files(
        self,
        document: dict[str, Any],
    ) -> None:

        document_id = document["document_id"]

        file_paths = [
            (
                self.storage_dir
                / "uploads"
                / document["filename"]
            ),
            self.get_parsed_path(document_id),
            self.get_cleaned_path(document_id),
            self.get_chunks_path(document_id),
            self.get_tables_path(document_id),
            self.get_graph_path(document_id),
        ]

        for path in file_paths:

            if path.exists():
                path.unlink()

        pages_dir = self.get_pages_dir(
            document_id
        )

        if pages_dir.exists():
            shutil.rmtree(pages_dir)

        rescue_dir = (
            self.storage_dir
            / "rescue"
            / document_id
        )

        if rescue_dir.exists():
            shutil.rmtree(
                rescue_dir
            )

        collection_name = document.get(
            "collection_name"
        )

        if collection_name:

            try:

                load_dotenv(
                    self.project_root
                    / "backend"
                    / ".env"
                )

                qdrant = QdrantClient(
                    url=os.getenv(
                        "QDRANT_HOST"
                    ),
                    api_key=os.getenv(
                        "QDRANT_API_KEY"
                    ),
                    timeout=180,
                    check_compatibility=False,
                )

                if qdrant.collection_exists(
                    collection_name
                ):

                    qdrant.delete_collection(
                        collection_name=(
                            collection_name
                        )
                    )

            except Exception as error:

                print(
                    "WARNING: Could not delete "
                    f"Qdrant collection "
                    f"{collection_name}: {error}"
                )
