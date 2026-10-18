from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..semantic_hierarchy_walker import SemanticRecord


class BaseInterpreter(ABC):
    @abstractmethod
    def can_handle(self, record: Any) -> bool:
        raise NotImplementedError

    @abstractmethod
    def build(
        self,
        record: Any,
        path: list[str],
    ) -> SemanticRecord:
        raise NotImplementedError
