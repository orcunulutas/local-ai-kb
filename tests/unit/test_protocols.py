from aikb.domain import (
    EnrichmentProvider,
    KnowledgeDocument,
    KnowledgeSink,
    Processor,
    Renderer,
    SourceAdapter,
    SourceItem,
    SyncResult,
)


class FakeSource:
    def sync(self, checkpoint: str | None = None) -> SyncResult:
        return SyncResult(next_checkpoint=checkpoint)


class FakeProcessor:
    def process(self, item: SourceItem) -> KnowledgeDocument:
        return KnowledgeDocument(
            item.external_id, item.source, item.external_id, item.title, item.content
        )


class FakeEnrichment:
    def enrich(self, document: KnowledgeDocument) -> KnowledgeDocument:
        return document


class FakeRenderer:
    def render(self, document: KnowledgeDocument) -> str:
        return document.content


class FakeSink:
    def write(self, document: KnowledgeDocument) -> None:
        pass


def test_contracts_are_structural() -> None:
    assert isinstance(FakeSource(), SourceAdapter)
    assert isinstance(FakeProcessor(), Processor)
    assert isinstance(FakeEnrichment(), EnrichmentProvider)
    assert isinstance(FakeRenderer(), Renderer)
    assert isinstance(FakeSink(), KnowledgeSink)
