import json

import httpx
import pytest

pytestmark = pytest.mark.anyio


def text_of(result) -> str:
    return " ".join(getattr(c, "text", "") for c in result.content)


def batches(n: int) -> list[dict]:
    return [{"datovyZdroj": "vr", "cisloDavky": i} for i in range(1, n + 1)]


async def test_tools_listed_read_only(client):
    tools = {t.name: t for t in (await client.list_tools()).tools}
    for name in ("search_notification_batches", "get_notification_batch"):
        assert tools[name].annotations is not None
        assert tools[name].annotations.read_only_hint is True
    props = tools["get_notification_batch"].input_schema["properties"]
    assert props["batch_number"]["type"] == "string"  # loose, validated inside the tool


async def test_search_batches_pages_locally_because_ares_does_not(
    client, ares_handler, requests_seen
):
    # Live probe: ARES ignores start/pocet for this list and returns every batch.
    ares_handler["fn"] = lambda request: httpx.Response(
        200, json={"notifikacniDavky": batches(7)}
    )
    first = await client.call_tool(
        "search_notification_batches", {"filter": {"datovyZdroj": "vr"}, "count": 3}
    )
    assert not first.is_error
    page = first.structured_content
    assert page["items"] == batches(7)[:3]
    assert page["total"] == 7
    assert page["start"] == 0
    assert page["count"] == 3
    assert page["next_start"] == 3
    request = requests_seen[-1]
    assert request.method == "POST"
    assert request.url.path.endswith("/ekonomicke-subjekty-notifikace/vyhledat")
    assert json.loads(request.content) == {"datovyZdroj": "vr"}  # no paging sent to ARES

    last = await client.call_tool(
        "search_notification_batches", {"filter": {}, "start": 6, "count": 3}
    )
    assert last.structured_content["items"] == batches(7)[6:]
    assert last.structured_content["next_start"] is None


async def test_search_batches_empty_is_not_error(client, ares_handler):
    ares_handler["fn"] = lambda request: httpx.Response(200, json={"notifikacniDavky": []})
    result = await client.call_tool("search_notification_batches", {"filter": {}})
    assert not result.is_error
    assert result.structured_content["items"] == []
    assert result.structured_content["total"] == 0
    assert result.structured_content["next_start"] is None


async def test_search_batches_paging_error_is_tagged(client):
    result = await client.call_tool("search_notification_batches", {"filter": {}, "start": -5})
    assert result.is_error
    assert "[invalid_input]" in text_of(result)


async def test_get_batch_path(client, ares_handler, requests_seen):
    content = {"cisloDavky": 7, "zaznamy": []}
    ares_handler["fn"] = lambda request: httpx.Response(200, json=content)
    result = await client.call_tool(
        "get_notification_batch", {"data_source": "vr", "batch_number": "7"}
    )
    assert not result.is_error
    assert result.structured_content == content
    request = requests_seen[-1]
    assert request.method == "GET"
    assert request.url.path.endswith(
        "/ekonomicke-subjekty-notifikace/datovy-zdroj/vr/cislo-davky/7"
    )


async def test_get_batch_path_parameters_are_url_encoded(client, ares_handler, requests_seen):
    ares_handler["fn"] = lambda request: httpx.Response(200, json={})
    await client.call_tool(
        "get_notification_batch", {"data_source": "a b/c?d", "batch_number": "7"}
    )
    raw = requests_seen[-1].url.raw_path.decode()
    assert "/datovy-zdroj/a%20b%2Fc%3Fd/cislo-davky/7" in raw


@pytest.mark.parametrize("bad", ["abc", "", "1.5", "-1", "7/8"])
async def test_bad_batch_number_is_invalid_input(client, requests_seen, bad):
    result = await client.call_tool(
        "get_notification_batch", {"data_source": "vr", "batch_number": bad}
    )
    assert result.is_error
    assert "[invalid_input]" in text_of(result)
    assert requests_seen == []


@pytest.mark.parametrize("bad", ["", "   ", "x" * 31])
async def test_bad_data_source_is_invalid_input(client, requests_seen, bad):
    result = await client.call_tool(
        "get_notification_batch", {"data_source": bad, "batch_number": "1"}
    )
    assert result.is_error
    assert "[invalid_input]" in text_of(result)
    assert requests_seen == []


async def test_get_batch_not_found(client, ares_handler):
    ares_handler["fn"] = lambda request: httpx.Response(404, json={"kod": "NENALEZENO"})
    result = await client.call_tool(
        "get_notification_batch", {"data_source": "vr", "batch_number": "999"}
    )
    assert result.is_error
    assert "[not_found]" in text_of(result)
    assert "NENALEZENO" not in text_of(result)
