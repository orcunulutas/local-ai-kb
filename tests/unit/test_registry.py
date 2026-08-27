import pytest

from aikb.registries.registry import Registry


def test_registry_resolves_factories_and_sorts_names() -> None:
    registry = Registry[object]()
    registry.register("zeta", object)
    registry.register("alpha", dict)

    assert registry.names() == ("alpha", "zeta")
    assert registry.get("alpha") is dict


def test_registry_rejects_duplicate_and_unknown_names() -> None:
    registry = Registry[object]()
    registry.register("fixture", object)

    with pytest.raises(ValueError, match="already registered"):
        registry.register("fixture", dict)
    with pytest.raises(KeyError, match="unknown implementation"):
        registry.get("missing")

