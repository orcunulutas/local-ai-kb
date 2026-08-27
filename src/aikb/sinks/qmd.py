"""QMD command boundary."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path

Runner = Callable[[Sequence[str]], None]


def _run(command: Sequence[str]) -> None:
    subprocess.run(command, check=True, timeout=120)  # noqa: S603


class QmdIndexer:
    def __init__(
        self, executable: str, collection: str, root: Path, runner: Runner = _run
    ) -> None:
        self.executable = executable
        self.collection = collection
        self.root = root
        self._runner = runner

    def register(self) -> None:
        self._runner(
            [
                self.executable,
                "collection",
                "add",
                str(self.root),
                "--name",
                self.collection,
            ]
        )

    def update(self) -> None:
        self._runner([self.executable, "update"])
