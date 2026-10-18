from __future__ import annotations

import re
from typing import Any

from ..semantic_hierarchy_walker import SemanticRecord
from .base_interpreter import BaseInterpreter


class PersonInterpreter(BaseInterpreter):
    ROLE_LABELS = {
        "chairperson",
        "chairman",
        "co-chairperson",
        "vice chancellor",
        "pro vice chancellor",
        "dean",
        "director",
        "registrar",
        "professor",
        "associate professor",
        "assistant professor",
        "lecturer",
    }

    PERSON_PREFIX_PATTERN = re.compile(
        r"^(?:Prof\.?|Dr\.?|Mr\.?|Mrs\.?|Ms\.?|Engr\.?)\s+\S",
        re.IGNORECASE,
    )

    def can_handle(self, record: Any) -> bool:
        role = self._role_label(record)

        if not role:
            return False

        if not self._has_person_children(record):
            return False

        return True

    def build(
        self,
        record: Any,
        path: list[str],
    ) -> SemanticRecord:
        role = self._role_label(record) or self._record_text(record)
        people = self._collect_people(record)

        return SemanticRecord(
            record_type="PERSON_GROUP",
            title=role,
            text=self._group_text(people),
            page=self._page(record),
            path=list(path),
            metadata={
                "role": role,
                "people": people,
            },
        )

    def _role_label(self, record: Any) -> str | None:
        text = self._record_text(record)

        if not text:
            return None

        normalized = re.sub(r"\s+", " ", text).strip().lower()

        if normalized in self.ROLE_LABELS:
            return text.strip()

        return None

    def _has_person_children(self, record: Any) -> bool:
        for child in self._children(record):
            text = self._record_text(child)

            if self.PERSON_PREFIX_PATTERN.match(text):
                return True

            if self._has_person_children(child):
                return True

        return False

    def _collect_people(self, record: Any) -> list[dict[str, str]]:
        people: list[dict[str, str]] = []
        current_person: dict[str, str] | None = None

        for child in self._walk_children(record):
            text = self._record_text(child)

            if not text:
                continue

            if self.PERSON_PREFIX_PATTERN.match(text):
                if current_person is not None:
                    people.append(current_person)

                current_person = {
                    "name": text,
                    "qualifications": "",
                }
                continue

            if current_person is None:
                continue

            qualifications = current_person["qualifications"]

            if qualifications:
                current_person["qualifications"] = f"{qualifications}\n{text}"
            else:
                current_person["qualifications"] = text

        if current_person is not None:
            people.append(current_person)

        return people

    def _walk_children(self, record: Any) -> list[Any]:
        items: list[Any] = []

        for child in self._children(record):
            items.append(child)
            items.extend(self._walk_children(child))

        return items

    def _group_text(self, people: list[dict[str, str]]) -> str:
        lines: list[str] = []

        for person in people:
            name = person.get("name", "").strip()
            qualifications = person.get("qualifications", "").strip()

            if name:
                lines.append(name)

            if qualifications:
                lines.append(qualifications)

        return "\n".join(lines)

    def _children(self, record: Any) -> list[Any]:
        children = getattr(record, "children", None)

        if children is None and isinstance(record, dict):
            children = record.get("children")

        if not children:
            return []

        return list(children)

    def _record_text(self, record: Any) -> str:
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

    def _page(self, record: Any) -> int:
        page = getattr(record, "page", None)

        if isinstance(page, int):
            return page

        if isinstance(record, dict):
            value = record.get("page")

            if isinstance(value, int):
                return value

        return 0
