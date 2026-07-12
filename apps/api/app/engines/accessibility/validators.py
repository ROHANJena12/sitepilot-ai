"""Validators for Accessibility engine inputs."""

from __future__ import annotations

from app.engines.accessibility.exceptions import InvalidDocumentError, MissingDocumentError
from app.engines.parser.document import Document
from app.pipeline.context import AuditContext


def resolve_document(context: AuditContext) -> Document:
    """
    Load the immutable Document from shared state.

    Never parses HTML — Document must already exist from the Parser engine.
    """
    if "document" not in context.shared_state:
        raise MissingDocumentError()
    document = context.shared_state["document"]
    if not isinstance(document, Document):
        raise InvalidDocumentError(
            f"Expected Document, got {type(document).__name__}.",
        )
    return document
