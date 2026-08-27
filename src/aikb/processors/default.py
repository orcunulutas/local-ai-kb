"""Deterministic source-neutral baseline processor."""

from __future__ import annotations

import hashlib

from aikb.domain import KnowledgeDocument, SourceItem


class DefaultProcessor:
    def process(self, item: SourceItem) -> KnowledgeDocument:
        digest = hashlib.sha256(
            f"{item.source}\0{item.external_id}".encode()
        ).hexdigest()[:24]
        metadata = dict(item.metadata)
        metadata.update(
            {
                "source.created_at": _iso(item.created_at),
                "source.updated_at": _iso(item.updated_at),
            }
        )
        return KnowledgeDocument(
            digest, item.source, item.external_id, item.title, item.content, metadata
        )


def _iso(value: object) -> str | None:
    return value.isoformat() if hasattr(value, "isoformat") else None
