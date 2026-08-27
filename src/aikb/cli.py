"""Command-line interface."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from aikb.application.composition import build_pipeline
from aikb.application.config import load_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="aikb")
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("sync", help="incrementally synchronize Exchange Notes")
    args = parser.parse_args(argv)
    try:
        summary = build_pipeline(load_config(args.config)).sync()
    except Exception as error:  # CLI translates adapter failures to a stable exit
        print(f"aikb sync failed: {error}", file=sys.stderr)
        return 1
    print(
        f"sync complete: upserted={summary.upserted} unpublished={summary.unpublished}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
