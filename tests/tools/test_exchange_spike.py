# Dynamically import tools/exchange_spike.py
import importlib.util
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
import yaml

spec = importlib.util.spec_from_file_location(
    "exchange_spike", "tools/exchange_spike.py"
)
spike = importlib.util.module_from_spec(spec)
sys.modules["exchange_spike"] = spike
spec.loader.exec_module(spike)

@pytest.fixture
def mock_config_file(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_data = {
        "sources": {
            "exchange_notes": {
                "endpoint": "https://endpoint.invalid",
                "server": "server.invalid",
                "email": "user@example.invalid",
                "username": "user@example.invalid",
                "auth_type": "NTLM",
                "password_env": "CUSTOM_PASSWORD_ENV",
            }
        }
    }
    with open(config_path, "w") as f:
        yaml.dump(config_data, f)
    return str(config_path)

@patch.dict(os.environ, {"CUSTOM_PASSWORD_ENV": "secret123"}, clear=True)
def test_spike_config_parsing(mock_config_file):
    with patch("exchange_spike.ExchangeClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        spike._setup_client(mock_config_file)

        mock_client_cls.assert_called_once()
        config = mock_client_cls.call_args[0][0]

        assert config.service_endpoint == "https://endpoint.invalid"
        assert config.server == "server.invalid"
        assert config.email == "user@example.invalid"
        assert config.username == "user@example.invalid"
        assert config.auth_type == "NTLM"
        assert config.password == "secret123"

@patch.dict(os.environ, {"EXCHANGE_PASSWORD": "fallback123"}, clear=True)
def test_spike_password_fallback(mock_config_file):
    # CUSTOM_PASSWORD_ENV is not set, it should fallback to EXCHANGE_PASSWORD
    with patch("exchange_spike.ExchangeClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        spike._setup_client(mock_config_file)
        config = mock_client_cls.call_args[0][0]

        assert config.password == "fallback123"

@patch("getpass.getpass")
@patch.dict(os.environ, {}, clear=True)
def test_spike_password_interactive(mock_getpass, mock_config_file):
    # Neither env is set, interactive fallback
    mock_getpass.return_value = "interactive123"

    with patch("exchange_spike.ExchangeClient") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        spike._setup_client(mock_config_file)
        config = mock_client_cls.call_args[0][0]

        assert config.password == "interactive123"
        mock_getpass.assert_called_once()
