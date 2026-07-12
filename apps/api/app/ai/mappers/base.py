"""AIContextMapper — generic, stateless domain DTO → AIContext."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from app.ai.context import AIContext

T = TypeVar("T")


class AIContextMapper(ABC, Generic[T]):
    """
    Map a plain domain snapshot ``T`` into an ``AIContext``.

    Stateless and pure:
    - no repositories
    - no ORM / SQLAlchemy
    - no services
    - no network I/O
    """

    @abstractmethod
    def map(self, source: T) -> AIContext:
        """Return a prompt-safe ``AIContext`` for one AI feature."""
