"""SC-005: failure modes are categorised, and the server keeps working afterwards."""

import asyncio

import httpx
import pytest
from mcp import Client

from ares_mcp.server import build_server

pytestmark = pytest.mark.anyio

OK = {"ico": "00000001"}


def text_of(result) -> str:
    return " ".join(getattr(c, "text", "") for c in result.content)


async def test_each_failure_is_tagged_and_next_call_succeeds(client, ares_handler):
    def timeout(request):
        raise httpx.ReadTimeout("slow", request=request)

    def unreachable(request):
        raise httpx.ConnectError("no route", request=request)

    cases = [
        ("unreachable host", unreachable, "00000001", "[registry_unavailable]"),
        ("timeout", timeout, "00000001", "[registry_unavailable]"),
        ("malformed ico", None, "12ab", "[invalid_input]"),
        ("unknown ico", lambda r: httpx.Response(404, json={}), "00000001", "[not_found]"),
    ]
    for label, handler, ico, tag in cases:
        if handler is not None:
            ares_handler["fn"] = handler
        failed = await client.call_tool("get_entity", {"ico": ico})
        assert failed.is_error, label
        assert tag in text_of(failed), label

        ares_handler["fn"] = lambda request: httpx.Response(200, json=OK)
        ok = await client.call_tool("get_entity", {"ico": "00000001"})
        assert not ok.is_error, label
        assert ok.structured_content == OK, label


async def test_raw_payload_and_internals_never_reach_the_client(client, ares_handler):
    ares_handler["fn"] = lambda request: httpx.Response(
        500, text="Traceback (most recent call last): SECRET-INTERNALS"
    )
    result = await client.call_tool("get_entity", {"ico": "00000001"})
    assert result.is_error
    assert "SECRET-INTERNALS" not in text_of(result)
    assert "Traceback" not in text_of(result)


async def test_twenty_concurrent_calls_respect_the_concurrency_limit(monkeypatch):
    monkeypatch.setenv("ARES_MAX_CONCURRENCY", "3")
    running = 0
    peak = 0

    async def slow_handler(request: httpx.Request) -> httpx.Response:
        nonlocal running, peak
        running += 1
        peak = max(peak, running)
        await asyncio.sleep(0.02)
        running -= 1
        return httpx.Response(200, json=OK)

    server = build_server(httpx.MockTransport(slow_handler))
    async with Client(server) as c:
        results = await asyncio.gather(
            *(c.call_tool("get_entity", {"ico": str(i)}) for i in range(1, 21))
        )
    assert all(not r.is_error for r in results)
    assert len(results) == 20
    # Calls really overlap (peak reaches the limit) and never exceed it.
    assert peak == 3
