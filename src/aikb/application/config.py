"""YAML configuration loading for the built-in local pipeline."""

from __future__ import annotations

import os
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
    return AppConfig(data, path.resolve())


def required_secret(source: dict[str, Any]) -> str:
    variable = str(source.get("password_env", "EXCHANGE_PASSWORD"))
    value = os.environ.get(variable)
    if not value:
        raise ValueError(f"required environment variable is not set: {variable}")
    return value
