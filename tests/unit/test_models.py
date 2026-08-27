from dataclasses import FrozenInstanceError

import pytest

from aikb.domain import (
    ChangeKind,
    KnowledgeDocument,
    SourceChange,
    SourceItem,
    SyncResult,
)


def test_source_item_is_immutable_and_copies_metadata() -> None:
    metadata = {"folder": "notes"}
    item = SourceItem("exchange_notes", "42", "Title", "Body", metadata=metadata)
    metadata["folder"] = "changed"

    assert item.metadata["folder"] == "notes"
    with pytest.raises(TypeError):
        item.metadata["new"] = "value"  # type: ignore[index]
    with pytest.raises(FrozenInstanceError):
        item.title = "Changed"  # type: ignore[misc]


def test_source_change_enforces_upsert_and_delete_invariants() -> None:
    item = SourceItem("fixture", "one", "Title", "Body")
    assert SourceChange.upsert(item).kind is ChangeKind.UPSERT
    assert SourceChange.delete("one").item is None

    with pytest.raises(ValueError, match="requires an item"):
        SourceChange(ChangeKind.UPSERT, "one")
    with pytest.raises(ValueError, match="cannot carry"):
        SourceChange(ChangeKind.DELETE, "one", item)


def test_knowledge_document_requires_source_provenance() -> None:
    with pytest.raises(ValueError, match="source provenance"):
        KnowledgeDocument("doc-1", "", "item-1", "Title", "Body")


def test_sync_result_copies_changes_into_an_immutable_tuple() -> None:
    changes = [SourceChange.delete("one")]
    result = SyncResult(changes)  # type: ignore[arg-type]
    changes.append(SourceChange.delete("two"))

    assert result.changes == (SourceChange.delete("one"),)
