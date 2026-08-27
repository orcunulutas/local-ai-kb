from unittest.mock import Mock

import pytest

from aikb.application.credentials import CredentialError, resolve_credential


def test_keyring_credential_is_resolved_by_reference() -> None:
    keyring = Mock()
    keyring.get_password.return_value = "from-system-keyring"
    config = {
        "credentials": {
            "exchange-kb": {
                "provider": "keyring",
                "service": "local-ai-kb.exchange",
                "username": "user@example.invalid",
            }
        }
    }

    assert (
        resolve_credential(config, "exchange-kb", keyring_api=keyring)
        == "from-system-keyring"
    )
    keyring.get_password.assert_called_once_with(
        "local-ai-kb.exchange", "user@example.invalid"
    )


def test_missing_keyring_credential_does_not_fall_back_to_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AIKB_EXCHANGE_PASSWORD", "must-not-be-used")
    keyring = Mock()
    keyring.get_password.return_value = None
    config = {
        "credentials": {
            "exchange-kb": {
                "provider": "keyring",
                "service": "local-ai-kb.exchange",
                "username": "user@example.invalid",
            }
        }
    }

    with pytest.raises(CredentialError, match="not found in the system keyring"):
        resolve_credential(config, "exchange-kb", keyring_api=keyring)


def test_environment_provider_is_an_explicit_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AIKB_EXCHANGE_PASSWORD", "headless-secret")
    config = {
        "credentials": {
            "headless": {
                "provider": "environment",
                "variable": "AIKB_EXCHANGE_PASSWORD",
            }
        }
    }

    assert resolve_credential(config, "headless") == "headless-secret"


def test_unknown_provider_and_reference_are_rejected() -> None:
    with pytest.raises(CredentialError, match="unknown credential reference"):
        resolve_credential({}, "missing")

    config = {"credentials": {"exchange-kb": {"provider": "vault"}}}
    with pytest.raises(CredentialError, match="unsupported provider"):
        resolve_credential(config, "exchange-kb")
