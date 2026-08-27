"""Small registry primitive; deliberately not a plugin loader."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Generic, TypeVar

T = TypeVar("T")
Factory = Callable[..., T]


class Registry(Generic[T]):
    """Map stable built-in names to factories."""

    def __init__(self) -> None:
        self._factories: dict[str, Factory[T]] = {}

    def register(self, name: str, factory: Factory[T]) -> None:
        normalized = name.strip()
        if not normalized:
            raise ValueError("registry name must not be blank")
        if normalized in self._factories:
            raise ValueError(f"implementation already registered: {normalized}")
        self._factories[normalized] = factory

    def get(self, name: str) -> Factory[T]:
        try:
            return self._factories[name]
        except KeyError as error:
            raise KeyError(f"unknown implementation: {name}") from error

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._factories))

    def __iter__(self) -> Iterator[str]:
        return iter(self.names())

