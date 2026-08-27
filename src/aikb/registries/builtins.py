"""Explicit built-in factory maps, populated as implementations are added."""

from aikb.domain import (
    EnrichmentProvider,
    KnowledgeSink,
    Processor,
    Renderer,
    SourceAdapter,
)
from aikb.registries.registry import Registry

SOURCE_ADAPTERS = Registry[SourceAdapter]()
PROCESSORS = Registry[Processor]()
ENRICHMENT_PROVIDERS = Registry[EnrichmentProvider]()
RENDERERS = Registry[Renderer]()
KNOWLEDGE_SINKS = Registry[KnowledgeSink]()

