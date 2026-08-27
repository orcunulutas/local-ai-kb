"""Durable local pipeline and Exchange identity state."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


class SqliteState:
    """Small SQLite repository shared by orchestration and the Notes adapter."""

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS checkpoints (
                    source TEXT PRIMARY KEY, value TEXT
                );
                CREATE TABLE IF NOT EXISTS exchange_identities (
                    source TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    search_key TEXT NOT NULL,
                    PRIMARY KEY (source, item_id)
                );
                CREATE TABLE IF NOT EXISTS documents (
                    source TEXT NOT NULL,
                    external_id TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    published_path TEXT,
                    published INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (source, external_id)
                );
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL
                );
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def checkpoint(self, source: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM checkpoints WHERE source = ?", (source,)
            ).fetchone()
        return None if row is None or row["value"] is None else str(row["value"])

    def set_checkpoint(self, source: str, value: str | None) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO checkpoints(source, value) VALUES (?, ?) "
                "ON CONFLICT(source) DO UPDATE SET value=excluded.value",
                (source, value),
            )

    def remember_locator(self, source: str, item_id: str, search_key: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO exchange_identities(source,item_id,search_key) "
                "VALUES (?,?,?) ON CONFLICT(source,item_id) DO UPDATE SET "
                "search_key=excluded.search_key",
                (source, item_id, search_key),
            )

    def identity_for_locator(self, source: str, item_id: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT search_key FROM exchange_identities "
                "WHERE source=? AND item_id=?",
                (source, item_id),
            ).fetchone()
        return None if row is None else str(row["search_key"])

    def record_document(
        self, source: str, external_id: str, document_id: str, path: Path
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO documents VALUES (?,?,?,?,1) "
                "ON CONFLICT(source,external_id) DO UPDATE SET "
                "document_id=excluded.document_id, "
                "published_path=excluded.published_path, "
                "published=1",
                (source, external_id, document_id, str(path)),
            )

    def unpublish(self, source: str, external_id: str) -> Path | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT published_path FROM documents WHERE source=? AND external_id=?",
                (source, external_id),
            ).fetchone()
            connection.execute(
                "UPDATE documents SET published=0 WHERE source=? AND external_id=?",
                (source, external_id),
            )
        if row is None or row["published_path"] is None:
            return None
        return Path(str(row["published_path"]))

    def setting(self, key: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM settings WHERE key=?", (key,)
            ).fetchone()
        return None if row is None else str(row["value"])

    def set_setting(self, key: str, value: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO settings VALUES (?,?) ON CONFLICT(key) DO UPDATE SET "
                "value=excluded.value",
                (key, value),
            )
