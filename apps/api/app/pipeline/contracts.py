"""Engine contracts — Protocol every engine adapter must satisfy."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.pipeline.context import AuditContext
from app.pipeline.result import EngineResult


@runtime_checkable
class Engine(Protocol):
    """
    Generic engine interface (ENGINE_SPEC §4.2).

    Implementations must be pure-ish: side effects only via injected clients
    or documented network calls (e.g. DNS). Never import sibling engines.
    """

    @property
    def name(self) -> str:
        """Stable engine key used in registry and results (e.g. ``url_validation``)."""
        ...

    async def run(self, context: AuditContext) -> EngineResult:
        """
        Execute the engine against ``context``.

        May enrich the mutable context on success. Must return an ``EngineResult``
        (prefer returning ``success=False`` over raising for expected failures).
        """
        ...
