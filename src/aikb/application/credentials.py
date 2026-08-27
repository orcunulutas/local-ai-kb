"""Narrow credential lookup boundary for Exchange authentication."""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from typing import Any, Protocol


class CredentialError(RuntimeError):
    """A configured credential could not be resolved."""


@dataclass(frozen=True, slots=True)
class CredentialReference:
    name: str
    provider: str
    service: str | None = None
    username: str | None = None
    variable: str | None = None


class CredentialProvider(Protocol):
    def password(self, reference: CredentialReference) -> str: ...


class _KeyringApi(Protocol):
    def get_password(self, service_name: str, username: str) -> str | None: ...


class KeyringCredentialProvider:
    """Read a password from the active OS keyring backend."""

    def __init__(self, keyring_api: _KeyringApi | None = None) -> None:
        self._keyring_api = keyring_api

    def password(self, reference: CredentialReference) -> str:
        if not reference.service or not reference.username:
            raise CredentialError(
                f"keyring credential {reference.name!r} requires service and username"
            )
        try:
            api = self._keyring_api or importlib.import_module("keyring")
            value = api.get_password(reference.service, reference.username)
        except Exception as error:
            raise CredentialError(
                f"could not access system keyring for credential {reference.name!r}: "
                f"{error}"
            ) from error
        if not value:
            raise CredentialError(
                f"credential {reference.name!r} was not found in the system keyring"
            )
        return value


class EnvironmentCredentialProvider:
    """Explicit headless/test fallback; never selected implicitly."""

    def password(self, reference: CredentialReference) -> str:
        if not reference.variable:
            raise CredentialError(
                f"environment credential {reference.name!r} requires variable"
            )
        value = os.environ.get(reference.variable)
        if not value:
            raise CredentialError(
                f"credential environment variable is not set: {reference.variable}"
            )
        return value


def resolve_credential(
    raw: dict[str, Any], reference_name: str, *, keyring_api: _KeyringApi | None = None
) -> str:
    credentials = raw.get("credentials", {})
    configured = (
        credentials.get(reference_name) if isinstance(credentials, dict) else None
    )
    if not isinstance(configured, dict):
        raise CredentialError(f"unknown credential reference: {reference_name}")
    reference = CredentialReference(
        name=reference_name,
        provider=str(configured.get("provider", "keyring")).lower(),
        service=_optional_string(configured.get("service")),
        username=_optional_string(configured.get("username")),
        variable=_optional_string(configured.get("variable")),
    )
    if reference.provider == "keyring":
        return KeyringCredentialProvider(keyring_api).password(reference)
    if reference.provider == "environment":
        return EnvironmentCredentialProvider().password(reference)
    raise CredentialError(
        f"unsupported provider for credential {reference_name!r}: {reference.provider}"
    )


def _optional_string(value: object) -> str | None:
    result = str(value).strip() if value is not None else ""
    return result or None
