from pathlib import Path
from typing import Any

import cv2
import numpy as np


class TableLayoutAnalyzer:
    """
    Performs deterministic analysis of a table image.

    It does not assume:
    - a specific university
    - a fixed page size
    - a fixed orientation
    - a fixed number of columns
    """

    def analyze(
        self,
        image_path: Path,
    ) -> dict[str, Any]:

        if not image_path.exists():
            raise FileNotFoundError(
                f"Table image not found: {image_path}"
            )

        image = cv2.imread(str(image_path))

        if image is None:
            raise ValueError(
                f"Could not read table image: {image_path}"
            )

        height, width = image.shape[:2]

        if width <= 0 or height <= 0:
            raise ValueError(
                "Invalid table image dimensions."
            )

        aspect_ratio = width / height

        orientation = (
            "landscape"
            if width > height
            else "portrait"
        )

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY,
        )

        binary = cv2.adaptiveThreshold(
            gray,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            15,
            10,
        )

        vertical_lines = self._detect_vertical_lines(
            binary
        )

        horizontal_lines = self._detect_horizontal_lines(
            binary
        )

        vertical_count = self._count_line_groups(
            vertical_lines,
            axis="vertical",
        )

        horizontal_count = self._count_line_groups(
            horizontal_lines,
            axis="horizontal",
        )

        estimated_columns = max(
            vertical_count - 1,
            0,
        )

        estimated_rows = max(
            horizontal_count - 1,
            0,
        )

        complexity = self._classify_complexity(
            estimated_columns=estimated_columns,
            estimated_rows=estimated_rows,
        )

        return {
            "width": width,
            "height": height,
            "aspect_ratio": round(
                aspect_ratio,
                3,
            ),
            "orientation": orientation,
            "estimated_columns": estimated_columns,
            "estimated_rows": estimated_rows,
            "complexity": complexity,
            "requires_splitting": (
                complexity == "dense"
            ),
        }

    def _detect_vertical_lines(
        self,
        binary: np.ndarray,
    ) -> np.ndarray:

        height = binary.shape[0]

        kernel_height = max(
            height // 30,
            10,
        )

        kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (1, kernel_height),
        )

        return cv2.morphologyEx(
            binary,
            cv2.MORPH_OPEN,
            kernel,
        )

    def _detect_horizontal_lines(
        self,
        binary: np.ndarray,
    ) -> np.ndarray:

        width = binary.shape[1]

        kernel_width = max(
            width // 30,
            10,
        )

        kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT,
            (kernel_width, 1),
        )

        return cv2.morphologyEx(
            binary,
            cv2.MORPH_OPEN,
            kernel,
        )

    def _count_line_groups(
        self,
        line_image: np.ndarray,
        axis: str,
    ) -> int:

        if axis == "vertical":
            projection = np.sum(
                line_image > 0,
                axis=0,
            )

        elif axis == "horizontal":
            projection = np.sum(
                line_image > 0,
                axis=1,
            )

        else:
            raise ValueError(
                f"Unsupported axis: {axis}"
            )

        active = projection > 0

        groups = 0
        inside_group = False

        for is_active in active:

            if is_active and not inside_group:
                groups += 1
                inside_group = True

            elif not is_active:
                inside_group = False

        return groups

    def _classify_complexity(
        self,
        estimated_columns: int,
        estimated_rows: int,
    ) -> str:

        if estimated_columns >= 12:
            return "dense"

        if (
            estimated_columns >= 8
            and estimated_rows >= 15
        ):
            return "dense"

        return "standard"