import argparse
import hashlib
import os
import sys
from typing import Any

import yaml

from aikb.sources.exchange.client import (
    ExchangeClient,
    ExchangeClientError,
    ExchangeConfig,
)


def load_config(config_path: str) -> dict[str, Any]:
    if not os.path.exists(config_path):
        print(f"Error: Config file '{config_path}' not found.")
        sys.exit(1)

    with open(config_path) as f:
        # safe_load returns Any, explicitly cast to dict
        return dict(yaml.safe_load(f))


def _get_password() -> str:
    password = os.environ.get("EXCHANGE_PASSWORD")
    if not password:
        import getpass

        password = getpass.getpass("Exchange Password: ")
    if not password:
        print("Error: Exchange password required via env or interactively.")
        sys.exit(1)
    return password


def _setup_client(config_path: str) -> ExchangeClient:
    raw_config = load_config(config_path)
    # the config was moved to sources -> exchange_notes
    sources = raw_config.get("sources", {})
    exchange_cfg = sources.get("exchange_notes", {})

    endpoint = exchange_cfg.get("endpoint")
    server = exchange_cfg.get("server")
    email = exchange_cfg.get("email")
    username = exchange_cfg.get("username")
    auth_type = exchange_cfg.get("auth_type", "NTLM")
    ca_cert_path = exchange_cfg.get("ca_cert_path")

    if not all([email, username]) or not (endpoint or server):
        print("Error: Missing required config (email, username, and either endpoint or server).")
        sys.exit(1)

    password = _get_password()

    config = ExchangeConfig(
        server=server,
        email=email,
        username=username,
        password=password,
        auth_type=auth_type,
        ca_cert_path=ca_cert_path,
        service_endpoint=endpoint,
    )

    client = ExchangeClient(config)
    try:
        client.connect()
    except ExchangeClientError as e:
        print(f"Connection failed: {e}")
        sys.exit(1)

    return client


def _print_item(item: dict[str, Any]) -> None:
    print("Item")
    print("----")
    print(f"ID: {item.get('id')}")
    print(f"ChangeKey: {item.get('changekey')}")
    print(f"Subject: {item.get('subject')}")
    print(f"Class: {item.get('item_class')}")
    print(f"Created: {item.get('datetime_created')}")
    print(f"Modified: {item.get('last_modified_time')}")

    body = item.get("body")
    body_str = str(body)[:100] + "..." if body and len(str(body)) > 100 else str(body)
    print(f"Body: {body_str}")
    print()


def list_items(config_path: str) -> None:
    print("Connecting to Exchange...")
    client = _setup_client(config_path)

    try:
        print("Locating Notes/AI-KB folder...")
        ai_kb_folder = client.get_ai_kb_folder()
        print("Found AI-KB folder. Enumerating items...\n")

        items = client.enumerate_items(ai_kb_folder)
        print(f"Total items found: {len(items)}\n")

        for item in items:
            _print_item(item)

    except ExchangeClientError as e:
        print(f"Exchange error: {e}")
        sys.exit(1)


def sync_items(config_path: str) -> None:
    sync_state_file = ".sync_state.txt"

    print("Connecting to Exchange...")
    client = _setup_client(config_path)

    try:
        print("Locating Notes/AI-KB folder...")
        ai_kb_folder = client.get_ai_kb_folder()

        existing_sync_state: str | None = None
        if os.path.exists(sync_state_file):
            with open(sync_state_file) as f:
                existing_sync_state = f.read().strip()
                if not existing_sync_state:
                    existing_sync_state = None

        if existing_sync_state:
            print("Incremental Sync")
            print("----------------")
            print("sync_state_present: yes")
            print(f"sync_state_length: {len(existing_sync_state)}")
            fp = hashlib.sha256(existing_sync_state.encode()).hexdigest()[:8]
            print(f"sync_state_fingerprint: {fp}")
        else:
            print("Initial Sync")
            print("------------")
            print("sync_state_present: no")

        print("Executing sync_items...")
        result = client.sync_items(ai_kb_folder, sync_state=existing_sync_state)

        created = [c for c in result.changes if c.change_type == "create"]
        updated = [c for c in result.changes if c.change_type == "update"]
        deleted = [c for c in result.changes if c.change_type == "delete"]

        print(f"created: {len(created)}")
        print(f"updated: {len(updated)}")
        print(f"deleted: {len(deleted)}")

        print(f"new_sync_state_present: {'yes' if result.sync_state else 'no'}")
        if result.sync_state:
            print(f"new_sync_state_length: {len(result.sync_state)}")
            nfp = hashlib.sha256(result.sync_state.encode()).hexdigest()[:8]
            print(f"new_sync_state_fingerprint: {nfp}")
        print("\nChanges:")
        for change in result.changes:
            c_type = change.change_type.upper()
            print(f"- {c_type}: ID={change.item_id}, ChangeKey={change.change_key}")

        if result.sync_state:
            with open(sync_state_file, "w") as f:
                f.write(result.sync_state)
            print(f"\nSaved new sync state to {sync_state_file}")

    except ExchangeClientError as e:
        print(f"Exchange error: {e}")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Exchange Compatibility Spike")
    parser.add_argument("mode", choices=["list", "sync"], help="Mode of operation")
    parser.add_argument("--config", default="config.example.yaml", help="Config file")

    args = parser.parse_args()

    if args.mode == "list":
        list_items(args.config)
    elif args.mode == "sync":
        sync_items(args.config)


if __name__ == "__main__":
    main()
