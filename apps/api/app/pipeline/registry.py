"""Engine registry — name → Engine mapping with duplicate protection."""

from __future__ import annotations

from collections.abc import Sequence

from app.pipeline.contracts import Engine
from app.pipeline.exceptions import RegistrationError


class EngineRegistry:
    """
    In-process registry of engine adapters.

    Prevents duplicate names. Order of ``list()`` follows registration order
    unless callers supply an explicit execution order to the runtime.
    """

    def __init__(self) -> None:
        self._engines: dict[str, Engine] = {}
        self._order: list[str] = []

    def register(self, engine: Engine) -> None:
        """Register an engine. Raises ``RegistrationError`` on duplicate name."""
        name = engine.name
        if not name or not str(name).strip():
            raise RegistrationError("Engine name must be a non-empty string.")
        if name in self._engines:
            raise RegistrationError(
                f"Engine '{name}' is already registered.",
                code="DUPLICATE_ENGINE",
            )
        self._engines[name] = engine
        self._order.append(name)

    def unregister(self, name: str) -> None:
        """Remove an engine by name. Raises if unknown."""
        if name not in self._engines:
            raise RegistrationError(
                f"Engine '{name}' is not registered.",
                code="ENGINE_NOT_FOUND",
            )
        del self._engines[name]
        self._order.remove(name)

    def get(self, name: str) -> Engine:
        """Return a registered engine or raise ``RegistrationError``."""
        try:
            return self._engines[name]
        except KeyError as exc:
            raise RegistrationError(
                f"Engine '{name}' is not registered.",
                code="ENGINE_NOT_FOUND",
            ) from exc

    def list(self) -> Sequence[Engine]:
        """Return engines in registration order."""
        return tuple(self._engines[name] for name in self._order)

    def names(self) -> tuple[str, ...]:
        """Return registered engine names in registration order."""
        return tuple(self._order)

    def __contains__(self, name: str) -> bool:
        return name in self._engines

    def __len__(self) -> int:
        return len(self._engines)

    def __bool__(self) -> bool:
        # Avoid empty registries being falsy via ``__len__`` (breaks ``x or default``).
        return True
