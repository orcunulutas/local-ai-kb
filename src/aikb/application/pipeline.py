"""Single-process synchronization use case."""

from __future__ import annotations

from dataclasses import dataclass

from aikb.application.state import SqliteState
from aikb.domain import ChangeKind, EnrichmentProvider, Processor, SourceAdapter
from aikb.sinks.published import PublishedMarkdownSink
from aikb.sinks.qmd import QmdIndexer


@dataclass(frozen=True)
class SyncSummary:
    upserted: int = 0
    unpublished: int = 0


class SyncPipeline:
    def __init__(
        self,
        source_name: str,
        source: SourceAdapter,
        processor: Processor,
        enrichment: EnrichmentProvider,
        publisher: PublishedMarkdownSink,
        qmd: QmdIndexer,
        state: SqliteState,
    ) -> None:
        self._source_name = source_name
        self._source = source
        self._processor = processor
        self._enrichment = enrichment
        self._publisher = publisher
        self._qmd = qmd
        self._state = state

    def sync(self) -> SyncSummary:
        result = self._source.sync(self._state.checkpoint(self._source_name))
        upserted = unpublished = 0
        for change in result.changes:
            if change.kind is ChangeKind.UPSERT:
                assert change.item is not None
                document = self._enrichment.enrich(self._processor.process(change.item))
                path = self._publisher.write(document)
                self._state.record_document(
                    document.source,
                    document.source_external_id,
                    document.document_id,
                    path,
                )
                upserted += 1
            else:
                unpublished_path = self._state.unpublish(
                    self._source_name, change.external_id
                )
                self._publisher.delete(unpublished_path)
                unpublished += 1
        if result.changes:
            key = f"qmd.collection.{self._qmd.collection}"
            if self._state.setting(key) != str(self._qmd.root):
                self._qmd.register()
                self._state.set_setting(key, str(self._qmd.root))
            self._qmd.update()
        self._state.set_checkpoint(self._source_name, result.next_checkpoint)
        return SyncSummary(upserted, unpublished)
