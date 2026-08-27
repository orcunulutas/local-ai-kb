"""Composition root for the built-in MVP pipeline."""

from __future__ import annotations

from aikb.application.config import AppConfig
from aikb.application.credentials import resolve_credential
from aikb.application.pipeline import SyncPipeline
from aikb.application.state import SqliteState
from aikb.enrichments.ollama import OllamaEnrichment
from aikb.processors.default import DefaultProcessor
from aikb.renderers.markdown import MarkdownRenderer
from aikb.sinks.published import PublishedMarkdownSink
from aikb.sinks.qmd import QmdIndexer
from aikb.sources.exchange.client import ExchangeClient, ExchangeConfig
from aikb.sources.exchange.notes import ExchangeNotesAdapter


def build_pipeline(config: AppConfig) -> SyncPipeline:
    source = config.raw.get("sources", {}).get("exchange_notes")
    if not isinstance(source, dict):
        raise ValueError("sources.exchange_notes must be configured")
    credential_reference = _required(source, "credential")
    folder = source.get("folder", {})
    state = SqliteState(config.state_db)
    exchange = ExchangeClient(
        ExchangeConfig(
            server=source.get("server"),
            service_endpoint=source.get("endpoint"),
            email=_required(source, "email"),
            username=_required(source, "username"),
            password=resolve_credential(config.raw, credential_reference),
            auth_type=str(source.get("auth_type", "NTLM")),
            ca_cert_path=source.get("ca_cert_path"),
            folder_root=str(folder.get("root", "tois")),
            folder_path=str(folder.get("path", "KB")),
        )
    )
    enrichment = config.raw.get("enrichments", {}).get("ollama", {})
    ollama = OllamaEnrichment(
        str(enrichment.get("base_url", "http://127.0.0.1:11434")),
        _required(enrichment, "model"),
        float(enrichment.get("timeout_seconds", 30)),
        optional=bool(enrichment.get("optional", False)),
    )
    qmd_config = config.raw.get("sinks", {}).get("qmd", {})
    publisher = PublishedMarkdownSink(config.published, MarkdownRenderer())
    return SyncPipeline(
        "exchange_notes",
        ExchangeNotesAdapter(exchange, state),
        DefaultProcessor(),
        ollama,
        publisher,
        QmdIndexer(
            str(qmd_config.get("executable", "qmd")),
            str(qmd_config.get("collection", "local-ai-kb")),
            config.published,
        ),
        state,
    )


def _required(mapping: dict[str, object], key: str) -> str:
    value = str(mapping.get(key, "")).strip()
    if not value:
        raise ValueError(f"required configuration value is missing: {key}")
    return value
