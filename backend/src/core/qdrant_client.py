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

    The connection mode is selected through environment variables:
    - local: localhost Qdrant server
    - cloud: Qdrant Cloud using QDRANT_HOST and QDRANT_API_KEY
    """

    global _client

    if _client is None:

        with _lock:

            if _client is None:

                print(
                    "\n[QDRANT] Creating shared client..."
                )

                qdrant_mode = os.getenv(
                    "QDRANT_MODE",
                    "local",
                ).strip().lower()

                qdrant_port = int(
                    os.getenv(
                        "QDRANT_PORT",
                        "6333",
                    )
                )

                if qdrant_mode == "local":

                    print(
                        "[QDRANT] Mode: local"
                    )

                    _client = QdrantClient(
                        host="localhost",
                        port=qdrant_port,
                        prefer_grpc=False,
                        timeout=180,
                        check_compatibility=False,
                    )

                elif qdrant_mode == "cloud":

                    print(
                        "[QDRANT] Mode: cloud"
                    )

                    qdrant_host = os.getenv(
                        "QDRANT_HOST",
                        "",
                    )

                    qdrant_api_key = os.getenv(
                        "QDRANT_API_KEY",
                    )

                    if not qdrant_host:
                        raise ValueError(
                            "QDRANT_HOST is required "
                            "when QDRANT_MODE=cloud."
                        )

                    if not qdrant_api_key:
                        raise ValueError(
                            "QDRANT_API_KEY is required "
                            "when QDRANT_MODE=cloud."
                        )

                    _client = QdrantClient(
                        url=qdrant_host,
                        api_key=qdrant_api_key,
                        cloud_inference=True,
                        prefer_grpc=True,
                        timeout=180,
                        check_compatibility=False,
                    )

                else:

                    raise ValueError(
                        "Unsupported QDRANT_MODE: "
                        f"{qdrant_mode}. "
                        "Use 'local' or 'cloud'."
                    )

    return _client