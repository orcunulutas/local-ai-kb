"""Immutable values crossing module boundaries."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any


def _frozen_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    return MappingProxyType(dict(value))


class ChangeKind(StrEnum):
    """The source-level operation represented by a change."""

    UPSERT = "upsert"
    DELETE = "delete"


@dataclass(frozen=True, slots=True)
class SourceItem:
    """Canonical content emitted by any source adapter."""

    source: str
    external_id: str
    title: str
    content: str
    updated_at: datetime | None = None
    created_at: datetime | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.source.strip():
            raise ValueError("source must not be blank")
        if not self.external_id.strip():
            raise ValueError("external_id must not be blank")
        object.__setattr__(self, "metadata", _frozen_mapping(self.metadata))


@dataclass(frozen=True, slots=True)
class SourceChange:
    """An item upsert or deletion returned by a synchronization."""

    kind: ChangeKind
    external_id: str
    item: SourceItem | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.kind, ChangeKind):
            raise TypeError("kind must be a ChangeKind")
        if not self.external_id.strip():
            raise ValueError("external_id must not be blank")
        if self.kind is ChangeKind.UPSERT and self.item is None:
            raise ValueError("an upsert change requires an item")
        if self.kind is ChangeKind.DELETE and self.item is not None:
            raise ValueError("a delete change cannot carry an item")
        if self.item is not None and self.item.external_id != self.external_id:
            raise ValueError("change and item external IDs must match")

    @classmethod
    def upsert(cls, item: SourceItem) -> SourceChange:
        return cls(ChangeKind.UPSERT, item.external_id, item)

    @classmethod
    def delete(cls, external_id: str) -> SourceChange:
        return cls(ChangeKind.DELETE, external_id)


@dataclass(frozen=True, slots=True)
class SyncResult:
    """Changes and opaque next checkpoint produced by a source adapter."""

    changes: tuple[SourceChange, ...] = ()
    next_checkpoint: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "changes", tuple(self.changes))


@dataclass(frozen=True, slots=True)
class KnowledgeDocument:
    """Canonical processor output consumed by renderers and sinks."""

    document_id: str
    source: str
    source_external_id: str
    title: str
    content: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.document_id.strip():
            raise ValueError("document_id must not be blank")
        if not self.source.strip() or not self.source_external_id.strip():
            raise ValueError("source provenance must not be blank")
        object.__setattr__(self, "metadata", _frozen_mapping(self.metadata))
