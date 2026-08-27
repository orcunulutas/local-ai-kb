from pathlib import Path

from aikb.application.pipeline import SyncPipeline
from aikb.application.state import SqliteState
from aikb.domain import KnowledgeDocument
from aikb.processors.default import DefaultProcessor
from aikb.renderers.markdown import MarkdownRenderer
from aikb.sinks.published import PublishedMarkdownSink
from aikb.sinks.qmd import QmdIndexer
from aikb.sources.exchange.client import ExchangeItemChange, SyncStateResult
from aikb.sources.exchange.notes import ExchangeNotesAdapter


class FakeExchangeClient:
    def __init__(self) -> None:
        self.step = 0
        self.fetches = {
            ("locator-1", "ck-1"): note(
                "locator-1", "ck-1", "First title", "First body"
            ),
            ("locator-1", "ck-2"): note(
                "locator-1", "ck-2", "Edited title", "Edited body"
            ),
            ("locator-2", "ck-3"): note(
                "locator-2", "ck-3", "Returned title", "Returned body"
            ),
        }
        self.batches = [
            (None, SyncStateResult("state-1", [change("locator-1", "ck-1", "create")])),
            (
                "state-1",
                SyncStateResult("state-2", [change("locator-1", "ck-2", "update")]),
            ),
            (
                "state-2",
                SyncStateResult("state-3", [change("locator-1", "", "delete")]),
            ),
            (
                "state-3",
                SyncStateResult("state-4", [change("locator-2", "ck-3", "create")]),
            ),
            ("state-4", SyncStateResult("state-5", [])),
        ]

    def connect(self) -> None:
        pass

    def get_target_folder(self) -> object:
        return object()

    def sync_items(self, folder: object, sync_state: str | None) -> SyncStateResult:
        expected, result = self.batches[self.step]
        assert sync_state == expected
        self.step += 1
        return result

    def fetch_items(self, ids: list[tuple[str, str]]) -> list[dict[str, object]]:
        return [self.fetches[(item_id, key)] for item_id, key in ids]


class FakeEnrichment:
    def enrich(self, document: KnowledgeDocument) -> KnowledgeDocument:
        metadata = dict(document.metadata)
        metadata.update(
            {
                "enrichment.ollama.model": "fixture-model",
                "enrichment.summary": f"Summary of {document.title}",
                "enrichment.tags": ["kb", "note"],
            }
        )
        return KnowledgeDocument(
            document.document_id,
            document.source,
            document.source_external_id,
            document.title,
            document.content,
            metadata,
        )


def change(item_id: str, key: str, kind: str) -> ExchangeItemChange:
    return ExchangeItemChange(item_id, key, kind)


def note(item_id: str, key: str, title: str, body: str) -> dict[str, object]:
    return {
        "id": item_id,
        "changekey": key,
        "search_key": "AABBCCDD",
        "subject": title,
        "body": body,
        "datetime_created": "2026-01-01T10:00:00+00:00",
        "last_modified_time": "2026-01-02T10:00:00+00:00",
        "item_class": "IPM.StickyNote",
    }


def test_add_edit_move_out_and_move_back_pipeline(tmp_path: Path) -> None:
    state = SqliteState(tmp_path / "state" / "aikb.db")
    published = tmp_path / "published"
    commands: list[list[str]] = []
    qmd = QmdIndexer(
        "qmd",
        "test-kb",
        published,
        runner=lambda command: commands.append(list(command)),
    )
    pipeline = SyncPipeline(
        "exchange_notes",
        ExchangeNotesAdapter(FakeExchangeClient(), state),  # type: ignore[arg-type]
        DefaultProcessor(),
        FakeEnrichment(),
        PublishedMarkdownSink(published, MarkdownRenderer()),
        qmd,
        state,
    )

    assert pipeline.sync().upserted == 1
    paths = list(published.glob("*.md"))
    assert len(paths) == 1
    stable_path = paths[0]
    first = stable_path.read_text()
    assert "# First title" in first
    assert 'source_id: "AABBCCDD"' in first

    assert pipeline.sync().upserted == 1
    assert list(published.glob("*.md")) == [stable_path]
    assert "# Edited title" in stable_path.read_text()
    assert stable_path.read_text() == MarkdownRenderer().render(
        FakeEnrichment().enrich(
            DefaultProcessor().process(
                ExchangeNotesAdapter(FakeExchangeClient(), state)._source_item(
                    "AABBCCDD", note("locator-1", "ck-2", "Edited title", "Edited body")
                )
            )
        )
    )

    assert pipeline.sync().unpublished == 1
    assert not stable_path.exists()

    assert pipeline.sync().upserted == 1
    assert stable_path.exists()
    assert "# Returned title" in stable_path.read_text()
    assert state.checkpoint("exchange_notes") == "state-4"

    # Persist Exchange's mutated opaque state without reindexing when no items changed.
    assert pipeline.sync().upserted == 0
    assert state.checkpoint("exchange_notes") == "state-5"
    assert commands[0] == [
        "qmd",
        "collection",
        "add",
        str(published),
        "--name",
        "test-kb",
    ]
    assert commands.count(["qmd", "update"]) == 4
    assert sum("collection" in command for command in commands) == 1
