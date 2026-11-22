"""FR-012 / Constitution I: the server is read-only."""

import httpx
import pytest

pytestmark = pytest.mark.anyio

EXPECTED_TOOLS = {
    "get_entity",
    "search_entities",
    "get_register_record",
    "search_register",
    "search_code_lists",
    "search_addresses",
    "search_notification_batches",
    "get_notification_batch",
}


async def test_exactly_eight_tools_all_read_only(client):
    tools = (await client.list_tools()).tools
    assert {t.name for t in tools} == EXPECTED_TOOLS
    for tool in tools:
        assert tool.annotations is not None, tool.name
        assert tool.annotations.read_only_hint is True, tool.name


CALLS = [
    ("get_entity", {"ico": "1"}),
    ("search_entities", {"filter": {}}),
    ("get_register_record", {"register": "vr", "ico": "1"}),
    ("search_register", {"register": "vr", "filter": {}}),
    ("search_code_lists", {"filter": {}}),
    ("search_addresses", {"filter": {}}),
    ("search_notification_batches", {"filter": {}}),
    ("get_notification_batch", {"data_source": "vr", "batch_number": "1"}),
]


async def test_only_get_and_search_post_are_issued(client, ares_handler, requests_seen):
    ares_handler["fn"] = lambda request: httpx.Response(200, json={})
    for name, args in CALLS:
        await client.call_tool(name, args)
    assert len(requests_seen) == len(CALLS)
    for request in requests_seen:
        path = request.url.path
        if request.method == "POST":
            assert path.endswith("/vyhledat"), f"POST to non-search path {path}"
        else:
            assert request.method == "GET", f"{request.method} {path}"
