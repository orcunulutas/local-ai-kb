"""YAML configuration loading for the built-in local pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AppConfig:
    raw: dict[str, Any]
    config_path: Path

    @property
    def state_db(self) -> Path:
        value = self.raw.get("application", {}).get(
            "state_database", "./var/state/aikb.db"
        )
        return self._path(value)

    @property
    def published(self) -> Path:
        value = self.raw.get("application", {}).get(
            "published_directory", "./published"
        )
        return self._path(value)

    def _path(self, value: str) -> Path:
        path = Path(value).expanduser()
        return (
            path if path.is_absolute() else (self.config_path.parent / path).resolve()
        )


def load_config(path: Path) -> AppConfig:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except OSError as error:
        raise ValueError(f"cannot read configuration {path}: {error}") from error
    if not isinstance(data, dict):
        raise ValueError("configuration root must be a mapping")
    _reject_inline_exchange_secret(data)
    return AppConfig(data, path.resolve())


def _reject_inline_exchange_secret(data: dict[str, Any]) -> None:
    sources = data.get("sources", {})
    exchange = sources.get("exchange_notes", {}) if isinstance(sources, dict) else {}
    if not isinstance(exchange, dict):
        return
    forbidden = sorted({"password", "password_env"}.intersection(exchange))
    if forbidden:
        fields = ", ".join(forbidden)
        raise ValueError(
            f"Exchange secret fields are not allowed in configuration: {fields}; "
            "use a named credential reference"
        )
