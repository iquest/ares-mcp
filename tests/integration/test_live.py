"""Opt-in smoke tests against the real ARES API. Run with: uv run pytest -m live."""

import json
import statistics
import time
from pathlib import Path

import pytest
from mcp import Client

from ares_mcp.server import build_server

pytestmark = [pytest.mark.live, pytest.mark.anyio]

FIXTURE = Path(__file__).parent.parent / "fixtures" / "expected-entities.json"
MIN_SAMPLE = 20


def text_of(result) -> str:
    return " ".join(getattr(c, "text", "") for c in result.content)


@pytest.fixture
async def live_client():
    async with Client(build_server()) as c:
        yield c


def load_expected() -> list[dict]:
    entities = json.loads(FIXTURE.read_text())["entities"]
    if len(entities) < MIN_SAMPLE:
        pytest.fail(
            f"{FIXTURE.name} has {len(entities)} entities; SC-001 needs at least {MIN_SAMPLE}. "
            "Copy them by hand from the public ARES website (do not generate from the API)."
        )
    return entities


async def test_known_entities_match_pinned_values_and_latency(live_client):
    expected = load_expected()
    timings = []
    for entry in expected:
        started = time.perf_counter()
        result = await live_client.call_tool("get_entity", {"ico": entry["ico"]})
        timings.append(time.perf_counter() - started)
        assert not result.is_error, f"{entry['ico']}: {text_of(result)}"
        record = result.structured_content
        assert record["ico"] == entry["ico"]
        assert record["obchodniJmeno"] == entry["obchodniJmeno"]
        assert record["pravniForma"] == entry["pravniForma"]
    p95 = statistics.quantiles(timings, n=20)[-1]  # SC-003
    assert p95 < 3.0, f"95th-percentile latency {p95:.2f}s"


async def test_name_search_finds_expected_entity_in_two_calls(live_client):
    entry = load_expected()[0]
    found = await live_client.call_tool(
        "search_entities", {"filter": {"obchodniJmeno": entry["obchodniJmeno"]}, "count": 20}
    )
    assert not found.is_error
    icos = [item["ico"] for item in found.structured_content["items"]]
    assert entry["ico"] in icos
    record = await live_client.call_tool("get_entity", {"ico": entry["ico"]})  # SC-002: call 2
    assert not record.is_error


async def test_unused_ico_is_not_found(live_client):
    result = await live_client.call_tool("get_entity", {"ico": "00000001"})
    assert result.is_error
    assert "[not_found]" in text_of(result)


async def test_broad_query_is_rejected_by_ares_with_a_narrowing_hint(live_client):
    """T033: ARES refuses queries matching more than 1000 results, whatever the paging."""
    result = await live_client.call_tool(
        "search_entities", {"filter": {"obchodniJmeno": "a"}, "count": 5}
    )
    assert result.is_error
    assert "[invalid_input]" in text_of(result)
    assert "1000" in text_of(result)


async def test_start_beyond_the_end_is_an_empty_page_not_an_error(live_client):
    """T033: ARES has no cap on ``start`` itself; a deep start just returns no items."""
    result = await live_client.call_tool(
        "search_entities", {"filter": {"obchodniJmeno": "Seznam"}, "start": 5000, "count": 5}
    )
    assert not result.is_error
    assert result.structured_content["items"] == []
    assert result.structured_content["next_start"] is None
