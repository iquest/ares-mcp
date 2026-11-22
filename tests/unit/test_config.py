import dataclasses

import pytest

from ares_mcp.config import Settings, load_settings


def test_defaults():
    s = load_settings({})
    assert s.base_url == "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest"
    assert s.timeout_seconds == 10
    assert s.max_concurrency == 5
    assert s.default_count == 20
    assert s.max_count == 100


@pytest.mark.parametrize(
    ("variable", "raw", "field", "expected"),
    [
        ("ARES_BASE_URL", "http://localhost:9999/rest", "base_url", "http://localhost:9999/rest"),
        ("ARES_TIMEOUT_SECONDS", "2.5", "timeout_seconds", 2.5),
        ("ARES_MAX_CONCURRENCY", "2", "max_concurrency", 2),
        ("ARES_DEFAULT_COUNT", "7", "default_count", 7),
        ("ARES_MAX_COUNT", "50", "max_count", 50),
    ],
)
def test_each_override(variable, raw, field, expected):
    s = load_settings({variable: raw})
    assert getattr(s, field) == expected
    # all other fields keep their defaults
    default = Settings()
    for f in dataclasses.fields(Settings):
        if f.name != field:
            assert getattr(s, f.name) == getattr(default, f.name)


def test_settings_are_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        Settings().max_count = 1  # type: ignore[misc]


def test_load_settings_reads_process_environment(monkeypatch):
    monkeypatch.setenv("ARES_MAX_COUNT", "33")
    assert load_settings().max_count == 33
