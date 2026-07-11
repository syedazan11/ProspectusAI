import json
import os
from pathlib import Path

from dotenv import load_dotenv
from llama_cloud import LlamaCloud


class CurriculumParseService:
    """
    Parses complex curriculum-table pages with LlamaParse.

    This service is intended for ingestion only.
    Normal chatbot queries must never call LlamaParse.
    """

    def __init__(
        self,
        api_key: str | None = None,
    ) -> None:
        if api_key is None:
            load_dotenv()
            api_key = os.getenv(
                "LLAMA_CLOUD_API_KEY"
            )

        if not api_key:
            raise RuntimeError(
                "LLAMA_CLOUD_API_KEY is missing."
            )

        self.client = LlamaCloud(
            api_key=api_key,
            timeout=180,
        )

    def parse(
        self,
        input_path: Path,
        output_json_path: Path,
        *,
        force: bool = False,
    ) -> dict:
        input_path = Path(input_path)
        output_json_path = Path(
            output_json_path
        )

        if not input_path.exists():
            raise FileNotFoundError(
                input_path
            )

        if (
            output_json_path.exists()
            and not force
        ):
            return json.loads(
                output_json_path.read_text(
                    encoding="utf-8-sig"
                )
            )

        output_json_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with input_path.open("rb") as pdf_file:
            result = self.client.parsing.parse(
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

        output_json_path.write_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )

        return data
