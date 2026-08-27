import dataclasses
import os
from typing import Any

from exchangelib import (
    BASIC,
    DELEGATE,
    NTLM,
    Account,
    Configuration,
    Credentials,
    FaultTolerance,
)
from exchangelib.folders import Folder


@dataclasses.dataclass(frozen=True)
class ExchangeConfig:
    server: str | None
    email: str
    username: str
    password: str
    auth_type: str = "NTLM"  # NTLM or Basic
    ca_cert_path: str | None = None
    service_endpoint: str | None = None
    folder_root: str = "tois"
    folder_path: str = "KB"


@dataclasses.dataclass(frozen=True)
class ExchangeItemChange:
    item_id: str
    change_key: str
    change_type: str  # 'create', 'update', 'delete'


@dataclasses.dataclass(frozen=True)
class SyncStateResult:
    sync_state: str
    changes: list[ExchangeItemChange]


class ExchangeClientError(Exception):
    pass


class ExchangeClient:
    """
    Encapsulates exchangelib functionality to maintain an abstraction boundary.
    The application and other adapters should not depend on exchangelib directly.
    """

    def __init__(self, config: ExchangeConfig):
        self._config = config
        self._account: Account | None = None

    def _setup_tls(self) -> None:
        """Configures TLS using custom CA if provided."""
        if self._config.ca_cert_path:
            # Note: This affects global ssl context in Python which is what
            # exchangelib uses by default. In a full production scenario, we'd
            # want to inject this more carefully into the transport.
            # But for the spike, we'll set the environment variable that requests uses.
            os.environ["REQUESTS_CA_BUNDLE"] = self._config.ca_cert_path

    def connect(self) -> None:
        """Connects to the Exchange EWS endpoint."""
        self._setup_tls()

        auth_type = NTLM
        if self._config.auth_type.lower() == "basic":
            auth_type = BASIC
        elif self._config.auth_type.lower() == "ntlm":
            auth_type = NTLM
        else:
            raise ExchangeClientError(
                f"Unsupported auth_type: {self._config.auth_type}"
            )

        credentials = Credentials(
            username=self._config.username, password=self._config.password
        )

        config_kwargs = {
            "credentials": credentials,
            "auth_type": auth_type,
            "retry_policy": FaultTolerance(max_wait=3600),
        }

        if self._config.service_endpoint:
            config_kwargs["service_endpoint"] = self._config.service_endpoint
        elif self._config.server:
            config_kwargs["server"] = self._config.server
        else:
            raise ExchangeClientError(
                "Either service_endpoint or server must be provided."
            )

        config = Configuration(**config_kwargs)

        try:
            self._account = Account(
                primary_smtp_address=self._config.email,
                config=config,
                autodiscover=False,
                access_type=DELEGATE,
            )
        except Exception as e:
            raise ExchangeClientError(f"Failed to connect to Exchange: {e}") from e

    def _get_root_folder(self) -> Folder:
        if not self._account:
            raise ExchangeClientError("Client not connected.")

        try:
            folder_root = self._config.folder_root.lower()
            if folder_root == "notes":
                return self._account.notes
            elif folder_root == "tois":
                return self._account.root.tois
            else:
                # Naive fallback for generic root retrieval
                for child in self._account.root.children:
                    if child.name.lower() == folder_root:
                        return child
                raise ExchangeClientError(
                    f"Root folder '{self._config.folder_root}' not found."
                )
        except ExchangeClientError:
            raise
        except Exception as e:
            raise ExchangeClientError(
                f"Could not locate root folder '{self._config.folder_root}': {e}"
            ) from e

    def get_target_folder(self) -> Folder:
        current_folder = self._get_root_folder()
        parts = self._config.folder_path.replace("\\", "/").split("/")
        path_parts = [p for p in parts if p]

        try:
            for part in path_parts:
                found = False
                for child in current_folder.children:
                    if child.name == part:
                        current_folder = child
                        found = True
                        break
                if not found:
                    raise ExchangeClientError(
                        f"Folder path '{part}' not found under root "
                        f"'{self._config.folder_root}'."
                    )

            return current_folder
        except ExchangeClientError:
            raise
        except Exception as e:
            raise ExchangeClientError(
                f"Error navigating '{self._config.folder_path}': {e}"
            ) from e

    def enumerate_items(self, folder: Folder) -> list[dict[str, Any]]:
        """
        Enumerates items in a folder and returns diagnostic properties.
        """
        items_data = []
        try:
            for item in folder.all():
                items_data.append(
                    {
                        "id": getattr(item, "id", None),
                        "changekey": getattr(item, "changekey", None),
                        "subject": getattr(item, "subject", None),
                        # exchangelib Note class often uses text_body or body
                        "body": getattr(item, "text_body", None)
                        or getattr(item, "body", None),
                        "datetime_created": getattr(item, "datetime_created", None),
                        "last_modified_time": getattr(item, "last_modified_time", None),
                        "item_class": getattr(item, "item_class", None),
                    }
                )
        except Exception as e:
            raise ExchangeClientError(f"Error enumerating items: {e}") from e
        return items_data

    def sync_items(
        self, folder: Folder, sync_state: str | None = None
    ) -> SyncStateResult:
        """
        Performs incremental synchronization using SyncFolderItems.
        Returns the new sync state and a list of changes (create, update, delete).
        """
        try:
            # exchangelib's folder.sync_items returns a generator yielding
            # (change_type, item_or_id).
            # The sync state is updated on the folder object as 'item_sync_state'
            # once the generator is exhausted.
            sync_generator = folder.sync_items(sync_state=sync_state)

            changes = []
            for change_type, item in sync_generator:
                if change_type in ("create", "update"):
                    changes.append(
                        ExchangeItemChange(
                            item_id=getattr(item, "id", ""),
                            change_key=getattr(item, "changekey", ""),
                            change_type=change_type,
                        )
                    )
                elif change_type == "delete":
                    # For delete, exchangelib yields an ItemId object
                    item_id_val = getattr(item, "id", str(item))
                    changes.append(
                        ExchangeItemChange(
                            item_id=item_id_val,
                            change_key=getattr(item, "changekey", "")
                            if hasattr(item, "changekey")
                            else "",
                            change_type="delete",
                        )
                    )

            # Retrieve the new sync state directly from the folder API
            # after consuming the generator
            new_sync_state = folder.item_sync_state
            return SyncStateResult(sync_state=new_sync_state, changes=changes)

        except Exception as e:
            raise ExchangeClientError(f"Error during sync_items: {e}") from e

    def fetch_items(self, item_ids: list[tuple[str, str]]) -> list[dict[str, Any]]:
        """
        Fetches full item details for a list of (item_id, change_key) tuples.
        Useful for retrieving bodies after sync_items.
        """
        if not self._account:
            raise ExchangeClientError("Client not connected.")

        try:
            # We can use account.fetch to bulk fetch items
            items_data = []
            for item in self._account.fetch(item_ids):
                if isinstance(item, Exception):
                    # Handle error for individual item
                    continue
                items_data.append(
                    {
                        "id": getattr(item, "id", None),
                        "changekey": getattr(item, "changekey", None),
                        "subject": getattr(item, "subject", None),
                        "body": getattr(item, "text_body", None)
                        or getattr(item, "body", None),
                        "datetime_created": getattr(item, "datetime_created", None),
                        "last_modified_time": getattr(item, "last_modified_time", None),
                        "item_class": getattr(item, "item_class", None),
                    }
                )
            return items_data
        except Exception as e:
            raise ExchangeClientError(f"Error fetching items: {e}") from e
