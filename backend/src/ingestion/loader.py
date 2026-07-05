from pathlib import Path


class DocumentLoader:
    """
    Responsible for validating uploaded documents
    before they enter the ingestion pipeline.
    """

    ALLOWED_EXTENSIONS = {".pdf"}

    def validate(self, file_path: str | Path) -> Path:
        """
        Validate an uploaded document.

        Args:
            file_path: Path to the uploaded document.

        Returns:
            Validated Path object.

        Raises:
            FileNotFoundError
            ValueError
        """

        path = Path(file_path)

        # Check file exists
        if not path.exists():
            raise FileNotFoundError(
                f"File not found: {path}"
            )

        # Check file extension
        if path.suffix.lower() not in self.ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type: {path.suffix}"
            )

        # Check file is not empty
        if path.stat().st_size == 0:
            raise ValueError(
                "Uploaded file is empty."
            )

        return path