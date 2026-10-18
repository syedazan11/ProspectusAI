from __future__ import annotations

from typing import Any

from ..semantic_hierarchy_walker import SemanticRecord
from .base_interpreter import BaseInterpreter


class DefaultInterpreter(BaseInterpreter):
    def can_handle(self, record: Any) -> bool:
        return True

    def build(
        self,
        record: Any,
        path: list[str],
    ) -> SemanticRecord:
        return SemanticRecord(
            record_type=self._classify(record),
            title=self._title(record),
            text=self._text(record),
            page=self._page(record),
            path=list(path),
            metadata=self._metadata(record),
        )

    def _classify(self, record: Any) -> str:
        kind = self._kind(record)
        depth = self._section_depth(record)
        rows = getattr(record, "rows", None) or []
        title = self._title(record)

        if depth >= 2:
            return "SECTION"

        if kind == "label":
            return "LABEL"

        if kind in ("numbered", "list_item"):
            return "LIST"

        if kind == "table":
            return "TABLE"

        if kind == "person":
            return "PERSON"

        if kind == "paragraph":
            return "PARAGRAPH"

        if kind == "text" and len(rows) == 1 and title:
            if len(title) <= 60 and not title.endswith((".", ";", ",")):
                return "LABEL"

        if kind == "text":
            return "PARAGRAPH"

        return "UNKNOWN"

    def _title(self, record: Any) -> str:
        rows = getattr(record, "rows", None) or []

        for row in rows:
            text = self._row_text(row)

            if text:
                return text

        marker = getattr(record, "marker", None)

        if isinstance(marker, dict):
            for key in ("title", "heading", "anchor_label", "label", "text"):
                value = marker.get(key)

                if isinstance(value, str) and value.strip():
                    return value.strip()

        return ""

    def _text(self, record: Any) -> str:
        rows = getattr(record, "rows", None) or []
        parts: list[str] = []

        for row in rows:
            text = self._row_text(row)

            if text:
                parts.append(text)

        if parts:
            return "\n".join(parts)

        marker = getattr(record, "marker", None)

        if isinstance(marker, dict):
            for key in ("text", "content"):
                value = marker.get(key)

                if isinstance(value, str) and value.strip():
                    return value.strip()

        return ""

    def _metadata(self, record: Any) -> dict:
        marker = getattr(record, "marker", None)
        children = self._children(record)
        rows = getattr(record, "rows", None) or []

        metadata: dict[str, Any] = {
            "kind": self._kind(record),
            "row_count": len(rows),
            "child_count": len(children),
        }

        column = getattr(record, "column", None)

        if column is not None:
            metadata["column"] = column

        if isinstance(marker, dict):
            metadata["marker"] = dict(marker)

        return metadata

    def _kind(self, record: Any) -> str:
        kind = getattr(record, "kind", None)

        if isinstance(kind, str) and kind:
            return kind

        if isinstance(record, dict):
            value = record.get("kind")

            if isinstance(value, str) and value:
                return value

        return "unknown"

    def _page(self, record: Any) -> int:
        page = getattr(record, "page", None)

        if isinstance(page, int):
            return page

        if isinstance(record, dict):
            value = record.get("page")

            if isinstance(value, int):
                return value

        return 0

    def _children(self, record: Any) -> list[Any]:
        children = getattr(record, "children", None)

        if children is None and isinstance(record, dict):
            children = record.get("children")

        if not children:
            return []

        return list(children)

    def _section_depth(self, record: Any) -> int:
        marker = getattr(record, "marker", None)

        if isinstance(marker, dict):
            depth = marker.get("depth")

            if isinstance(depth, int):
                return depth

        if isinstance(record, dict):
            marker = record.get("marker")

            if isinstance(marker, dict):
                depth = marker.get("depth")

                if isinstance(depth, int):
                    return depth

        return 0

    def _row_text(self, row: Any) -> str:
        if isinstance(row, dict):
            text = row.get("text")

            if isinstance(text, str):
                return text.strip()

            return ""

        text = getattr(row, "text", None)

        if isinstance(text, str):
            return text.strip()

        return ""
