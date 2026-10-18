from __future__ import annotations

from typing import Any

from ..semantic_hierarchy_walker import SemanticRecord
from .base_interpreter import BaseInterpreter


class AdmissionCategoryInterpreter(BaseInterpreter):
    def can_handle(self, record: Any) -> bool:
        return False

    def build(
        self,
        record: Any,
        path: list[str],
    ) -> SemanticRecord:
        raise NotImplementedError