"""Atomic filesystem publication of rendered knowledge documents."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from aikb.domain import KnowledgeDocument, Renderer


class PublishedMarkdownSink:
    def __init__(self, root: Path, renderer: Renderer) -> None:
        self.root = root
        self._renderer = renderer
        root.mkdir(parents=True, exist_ok=True)

    def write(self, document: KnowledgeDocument) -> Path:
        path = self.root / f"{document.document_id}.md"
        rendered = self._renderer.render(document)
        descriptor, temporary = tempfile.mkstemp(prefix=".aikb-", dir=self.root)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as output:
                output.write(rendered)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, path)
        except Exception:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass
            raise
        return path

    def delete(self, path: Path | None) -> bool:
        if path is None:
            return False
        try:
            path.unlink()
            return True
        except FileNotFoundError:
            return False
