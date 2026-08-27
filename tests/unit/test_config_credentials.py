from pathlib import Path

import pytest

from aikb.application.config import load_config


@pytest.mark.parametrize("field", ["password", "password_env"])
def test_inline_and_legacy_exchange_secret_fields_are_rejected(
    tmp_path: Path, field: str
) -> None:
    path = tmp_path / "config.yaml"
    path.write_text(
        f"sources:\n  exchange_notes:\n    {field}: must-not-be-here\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="secret fields are not allowed"):
        load_config(path)
