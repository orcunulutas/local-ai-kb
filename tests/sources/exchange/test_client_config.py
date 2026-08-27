from unittest.mock import patch

import pytest

from aikb.sources.exchange.client import (
    ExchangeClient,
    ExchangeClientError,
    ExchangeConfig,
)


def test_service_endpoint_takes_precedence():
    config = ExchangeConfig(
        server="server.invalid",
        service_endpoint="https://endpoint.invalid/EWS/Exchange.asmx",
        email="test@example.com",
        username="DOMAIN\\test",
        password="password123",
    )
    client = ExchangeClient(config)

    with patch("aikb.sources.exchange.client.Configuration") as mock_config_cls, \
         patch("aikb.sources.exchange.client.Account"):
        client.connect()
        mock_config_cls.assert_called_once()
        kwargs = mock_config_cls.call_args[1]
        assert kwargs.get("service_endpoint") == "https://endpoint.invalid/EWS/Exchange.asmx"
        assert "server" not in kwargs

def test_server_used_if_no_endpoint():
    config = ExchangeConfig(
        server="server.invalid",
        service_endpoint=None,
        email="test@example.com",
        username="DOMAIN\\test",
        password="password123",
    )
    client = ExchangeClient(config)

    with patch("aikb.sources.exchange.client.Configuration") as mock_config_cls, \
         patch("aikb.sources.exchange.client.Account"):
        client.connect()
        mock_config_cls.assert_called_once()
        kwargs = mock_config_cls.call_args[1]
        assert kwargs.get("server") == "server.invalid"
        assert "service_endpoint" not in kwargs

def test_missing_both_endpoint_and_server():
    config = ExchangeConfig(
        server=None,
        service_endpoint=None,
        email="test@example.com",
        username="DOMAIN\\test",
        password="password123",
    )
    client = ExchangeClient(config)

    with pytest.raises(
        ExchangeClientError,
        match="Either service_endpoint or server must be provided."
    ):
        client.connect()

@pytest.mark.parametrize("auth_type_str, expected_auth", [
    ("NTLM", "NTLM"),
    ("ntlm", "NTLM"),
    ("Basic", "basic"),
    ("basic", "basic"),
])
def test_auth_type_mapping(auth_type_str, expected_auth):
    config = ExchangeConfig(
        server="server.invalid",
        email="test@example.com",
        username="DOMAIN\\test",
        password="password123",
        auth_type=auth_type_str,
    )
    client = ExchangeClient(config)

    with patch("aikb.sources.exchange.client.Configuration") as mock_config_cls, \
         patch("aikb.sources.exchange.client.Account"):
        client.connect()
        kwargs = mock_config_cls.call_args[1]
        assert kwargs.get("auth_type") == expected_auth

def test_invalid_auth_type():
    config = ExchangeConfig(
        server="server.invalid",
        email="test@example.com",
        username="DOMAIN\\test",
        password="password123",
        auth_type="OAuth",
    )
    client = ExchangeClient(config)

    with pytest.raises(ExchangeClientError, match="Unsupported auth_type: OAuth"):
        client.connect()
