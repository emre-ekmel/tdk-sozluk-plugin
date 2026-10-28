import pytest

from src import definitions


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Tests must never call the real TDK API; inject a fake fetch instead."""
    def blocked(word, timeout):
        raise AssertionError(f"Unexpected network lookup for {word!r}")
    monkeypatch.setattr(definitions, "fetch_from_tdk", blocked)
