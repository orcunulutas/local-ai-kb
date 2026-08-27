from unittest.mock import patch

import pytest

from aikb.sources.exchange.client import (
    ExchangeClient,
    ExchangeClientError,
    ExchangeConfig,
)


@pytest.fixture
def mock_config():
    return ExchangeConfig(
        server="mail.example.com",
        email="test@example.com",
        username="DOMAIN\\test",
        password="password123",
        auth_type="NTLM",
        service_endpoint="https://mail.example.com/EWS/Exchange.asmx",
        folder_root="notes",
        folder_path="SomeFolder/KB"
    )

class MockFolder:
    def __init__(self, name="Folder", children=None):
        self.name = name
        self.children = children or []
        self._items = []
        self.item_sync_state = None

    def all(self):
        return self._items

    def sync_items(self, sync_state=None):
        # Store a reference to folder to update its state
        folder = self
        class MockSyncGenerator:
            def __iter__(self):
                class MockItem:
                    def __init__(self, id, changekey):
                        self.id = id
                        self.changekey = changekey

                yield ("create", MockItem("id1", "ck1"))
                yield ("update", MockItem("id2", "ck2"))
                # exchangelib yields an ItemId object or string for delete
                yield ("delete", "id3")

                # simulate side effect of updating folder.item_sync_state
                folder.item_sync_state = "new_state_123"

        return MockSyncGenerator()

class MockAccount:
    def __init__(self):
        self.notes = MockFolder(name="Notes", children=[
            MockFolder(name="SomeFolder", children=[
                MockFolder(name="KB")
            ]),
        ])

    def fetch(self, item_ids):
        class MockItem:
            def __init__(self, id):
                self.id = id
                self.subject = f"Subject {id}"
                self.body = f"Body {id}"

        return [MockItem(id_val) for id_val, _ in item_ids]

@patch("aikb.sources.exchange.client.Account")
def test_client_connect_success(mock_account_cls, mock_config):
    client = ExchangeClient(mock_config)
    client.connect()

    # Verify account was instantiated
    mock_account_cls.assert_called_once()

@patch("aikb.sources.exchange.client.Account")
def test_client_connect_failure(mock_account_cls, mock_config):
    mock_account_cls.side_effect = Exception("Auth failed")
    client = ExchangeClient(mock_config)

    with pytest.raises(ExchangeClientError, match="Failed to connect"):
        client.connect()

@patch("aikb.sources.exchange.client.Account")
def test_get_target_folder_success(mock_account_cls, mock_config):
    mock_account_cls.return_value = MockAccount()
    client = ExchangeClient(mock_config)
    client.connect()

    folder = client.get_target_folder()
    assert folder.name == "KB"

@patch("aikb.sources.exchange.client.Account")
def test_get_target_folder_not_found(mock_account_cls, mock_config):
    mock_account = MockAccount()
    # Remove KB
    mock_account.notes.children[0].children = []
    mock_account_cls.return_value = mock_account

    client = ExchangeClient(mock_config)
    client.connect()

    with pytest.raises(ExchangeClientError, match="Folder path 'KB' not found"):
        client.get_target_folder()

@patch("aikb.sources.exchange.client.Account")
def test_enumerate_items(mock_account_cls, mock_config):
    client = ExchangeClient(mock_config)
    client.connect()

    folder = MockFolder()
    class MockItem:
        id = "1"
        changekey = "ck1"
        subject = "Note 1"
        text_body = "Body 1"
        datetime_created = "2024-01-01"
        last_modified_time = "2024-01-02"
        item_class = "IPM.Note"

    folder._items = [MockItem()]

    items = client.enumerate_items(folder)
    assert len(items) == 1
    assert items[0]["id"] == "1"
    assert items[0]["subject"] == "Note 1"
    assert items[0]["body"] == "Body 1"

@patch("aikb.sources.exchange.client.Account")
def test_sync_items(mock_account_cls, mock_config):
    client = ExchangeClient(mock_config)
    client.connect()

    folder = MockFolder()
    result = client.sync_items(folder, sync_state="old_state")

    assert result.sync_state == "new_state_123"
    assert len(result.changes) == 3

    assert result.changes[0].change_type == "create"
    assert result.changes[0].item_id == "id1"

    assert result.changes[1].change_type == "update"

    assert result.changes[2].change_type == "delete"
    assert result.changes[2].item_id == "id3"

@patch("aikb.sources.exchange.client.Account")
def test_fetch_items(mock_account_cls, mock_config):
    mock_account_cls.return_value = MockAccount()
    client = ExchangeClient(mock_config)
    client.connect()

    items = client.fetch_items([("id1", "ck1"), ("id2", "ck2")])
    assert len(items) == 2
    assert items[0]["id"] == "id1"
    assert items[0]["subject"] == "Subject id1"
