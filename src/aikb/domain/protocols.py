"""Structural interfaces implemented by internal adapters."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from aikb.domain.models import KnowledgeDocument, SourceItem, SyncResult


@runtime_checkable
class SourceAdapter(Protocol):
    """Synchronize an external source into source-neutral items."""

    def sync(self, checkpoint: str | None = None) -> SyncResult: ...


@runtime_checkable
class Processor(Protocol):
    """Transform one source-neutral item into one knowledge document."""

    def process(self, item: SourceItem) -> KnowledgeDocument: ...


@runtime_checkable
class EnrichmentProvider(Protocol):
    """Return a document enriched without changing its source identity."""

    def enrich(self, document: KnowledgeDocument) -> KnowledgeDocument: ...


@runtime_checkable
class Renderer(Protocol):
    """Render canonical knowledge content without persisting it."""

    def render(self, document: KnowledgeDocument) -> str: ...


@runtime_checkable
class KnowledgeSink(Protocol):
    """Persist or index a canonical knowledge document."""

    def write(self, document: KnowledgeDocument) -> None: ...

