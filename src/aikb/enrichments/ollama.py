"""Local Ollama enrichment provider."""

from __future__ import annotations

import json
from urllib import request

from aikb.domain import KnowledgeDocument


class OllamaEnrichment:
    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float = 30,
        *,
        optional: bool = False,
    ) -> None:
        self._url = base_url.rstrip("/") + "/api/generate"
        self._model = model
        self._timeout = timeout_seconds
        self._optional = optional

    def enrich(self, document: KnowledgeDocument) -> KnowledgeDocument:
        prompt = (
            "Return JSON only with keys summary (string) and tags (array of strings). "
            "Do not invent facts.\n\nTitle: "
            + document.title
            + "\n\n"
            + document.content
        )
        payload = json.dumps(
            {"model": self._model, "prompt": prompt, "stream": False, "format": "json"}
        ).encode()
        try:
            response = request.urlopen(  # noqa: S310 - configured local endpoint
                request.Request(
                    self._url,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                ),
                timeout=self._timeout,
            )
            outer = json.loads(response.read().decode())
            enriched = json.loads(outer["response"])
        except (OSError, KeyError, ValueError) as exc:
            if not self._optional:
                raise RuntimeError(f"Ollama enrichment failed: {exc}") from exc
            return document
        metadata = dict(document.metadata)
        metadata["enrichment.ollama.model"] = self._model
        metadata["enrichment.summary"] = str(enriched.get("summary", ""))
        metadata["enrichment.tags"] = sorted(
            str(tag) for tag in enriched.get("tags", [])
        )
        return KnowledgeDocument(
            document.document_id,
            document.source,
            document.source_external_id,
            document.title,
            document.content,
            metadata,
        )
