"""Exchange Sticky Notes source adapter."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol

from aikb.domain import SourceChange, SourceItem, SyncResult
from aikb.sources.exchange.client import ExchangeClient, ExchangeClientError


class IdentityStore(Protocol):
    def remember_locator(self, source: str, item_id: str, search_key: str) -> None: ...
    def identity_for_locator(self, source: str, item_id: str) -> str | None: ...


class ExchangeNotesAdapter:
    """Translate EWS locator changes to stable SearchKey-based changes."""

    source_name = "exchange_notes"

    def __init__(self, client: ExchangeClient, identities: IdentityStore) -> None:
        self._client = client
        self._identities = identities
        self._folder: Any = None

    def sync(self, checkpoint: str | None = None) -> SyncResult:
        if self._folder is None:
            self._client.connect()
            self._folder = self._client.get_target_folder()
        result = self._client.sync_items(self._folder, checkpoint)
        locators = [
            (change.item_id, change.change_key)
            for change in result.changes
            if change.change_type in {"create", "update"}
        ]
        fetched = self._client.fetch_items(locators) if locators else []
        by_id = {str(item.get("id")): item for item in fetched}
        changes: list[SourceChange] = []
        for change in result.changes:
            if change.change_type == "delete":
                identity = self._identities.identity_for_locator(
                    self.source_name, change.item_id
                )
                if identity is None:
                    raise ExchangeClientError(
                        f"cannot resolve deleted EWS locator {change.item_id} "
                        "to a SearchKey"
                    )
                changes.append(SourceChange.delete(identity))
                continue
            item = by_id.get(change.item_id)
            if item is None:
                raise ExchangeClientError(
                    f"Exchange did not return full Note data for {change.item_id}"
                )
            search_key = str(item.get("search_key") or "").strip().upper()
            if not search_key:
                raise ExchangeClientError(
                    f"Note {change.item_id} has no PidTagSearchKey"
                )
            self._identities.remember_locator(
                self.source_name, change.item_id, search_key
            )
            changes.append(SourceChange.upsert(self._source_item(search_key, item)))
        return SyncResult(tuple(changes), result.sync_state)

    def _source_item(self, search_key: str, item: dict[str, Any]) -> SourceItem:
        return SourceItem(
            source=self.source_name,
            external_id=search_key,
            title=str(item.get("subject") or "Untitled Note"),
            content=str(item.get("body") or ""),
            created_at=_datetime(item.get("datetime_created")),
            updated_at=_datetime(item.get("last_modified_time")),
            metadata={
                "exchange.item_class": item.get("item_class"),
                "exchange.change_key": item.get("changekey"),
            },
        )


def _datetime(value: Any) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
