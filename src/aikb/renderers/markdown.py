"""Deterministic Markdown serialization."""

from __future__ import annotations

import json
from typing import Any

from aikb.domain import KnowledgeDocument


class MarkdownRenderer:
    def render(self, document: KnowledgeDocument) -> str:
        fields: dict[str, Any] = {
            "id": document.document_id,
            "source": document.source,
            "source_id": document.source_external_id,
            "title": document.title,
        }
        fields.update(sorted(document.metadata.items()))
        frontmatter = "\n".join(
            f"{key}: {json.dumps(value, ensure_ascii=False, sort_keys=True)}"
            for key, value in fields.items()
            if value is not None
        )
        body = document.content.rstrip()
        return f"---\n{frontmatter}\n---\n\n# {document.title}\n\n{body}\n"
