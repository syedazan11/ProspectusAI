import os
from threading import Lock

from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

_client: QdrantClient | None = None
_lock = Lock()


def get_qdrant_client() -> QdrantClient:
    """
    Returns a shared Qdrant client.

    The client is created only once and reused by
    every component of the application.
    """

    global _client

    if _client is None:

        with _lock:

            if _client is None:

                print(
                    "\n[QDRANT] Creating shared client..."
                )

                qdrant_host = os.getenv(
                    "QDRANT_HOST",
                    "",
                )
                if not qdrant_host:
                    raise ValueError(
                        "QDRANT_HOST is not configured."
                    )

                qdrant_port = os.getenv(
                    "QDRANT_PORT",
                    "",
                )

                qdrant_api_key = os.getenv(
                    "QDRANT_API_KEY",
                )

                if qdrant_host.startswith(
                    ("http://", "https://")
                ):

                    _client = QdrantClient(
                        url=qdrant_host,
                        api_key=qdrant_api_key,
                        cloud_inference=True,
                        timeout=180,
                        check_compatibility=False,
                    )

                else:

                    _client = QdrantClient(
                        host=qdrant_host,
                        port=int(
                            qdrant_port or "6333"
                        ),
                        api_key=qdrant_api_key,
                        timeout=180,
                        check_compatibility=False,
                    )

    return _client