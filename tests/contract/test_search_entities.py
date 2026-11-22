import json

import httpx
import pytest

pytestmark = pytest.mark.anyio

ALL = [{"ico": f"0000000{i}", "obchodniJmeno": f"Firma {i}"} for i in range(1, 8)]


def fake_ares(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    start, pocet = body.get("start", 0), body.get("pocet", 20)
    return httpx.Response(
        200, json={"pocetCelkem": len(ALL), "ekonomickeSubjekty": ALL[start : start + pocet]}
    )


def text_of(result) -> str:
    return " ".join(getattr(c, "text", "") for c in result.content)


async def test_tool_listed_read_only(client):
    tools = {t.name: t for t in (await client.list_tools()).tools}
    tool = tools["search_entities"]
    assert tool.annotations is not None and tool.annotations.read_only_hint is True
    assert "filter" in tool.input_schema["properties"]
    assert "obchodniJmeno" in json.dumps(tool.input_schema)


async def test_returns_page_with_total_items_next_start(client, ares_handler):
    ares_handler["fn"] = fake_ares
    result = await client.call_tool(
        "search_entities", {"filter": {"obchodniJmeno": "Firma"}, "count": 3}
    )
    assert not result.is_error
    page = result.structured_content
    assert page["total"] == 7
    assert page["start"] == 0
    assert page["count"] == 3
    assert page["items"] == ALL[:3]
    assert page["next_start"] == 3


async def test_second_page_differs_and_last_page_has_null_next_start(client, ares_handler):
    ares_handler["fn"] = fake_ares
    page_one = await client.call_tool("search_entities", {"filter": {}, "count": 5})
    first = page_one.structured_content
    second = (
        await client.call_tool(
            "search_entities", {"filter": {}, "count": 5, "start": first["next_start"]}
        )
    ).structured_content
    assert first["items"] != second["items"]
    assert second["items"] == ALL[5:]
    assert second["next_start"] is None


async def test_zero_matches_is_not_an_error(client, ares_handler):
    ares_handler["fn"] = lambda request: httpx.Response(
        200, json={"pocetCelkem": 0, "ekonomickeSubjekty": []}
    )
    result = await client.call_tool("search_entities", {"filter": {"obchodniJmeno": "zzz"}})
    assert not result.is_error
    page = result.structured_content
    assert page["total"] == 0
    assert page["items"] == []
    assert page["next_start"] is None


@pytest.mark.parametrize("args", [{"count": 101}, {"count": 0}, {"count": -1}, {"start": -1}])
async def test_paging_range_errors_are_tagged(client, requests_seen, args):
    result = await client.call_tool("search_entities", {"filter": {}, **args})
    assert result.is_error
    assert "[invalid_input]" in text_of(result)
    assert requests_seen == []


async def test_count_over_max_states_maximum(client):
    result = await client.call_tool("search_entities", {"filter": {}, "count": 101})
    assert "100" in text_of(result)


async def test_request_body_maps_start_count_sort_and_filter(
    client, ares_handler, requests_seen
):
    ares_handler["fn"] = fake_ares
    await client.call_tool(
        "search_entities",
        {
            "filter": {"obchodniJmeno": "Firma", "pravniForma": ["112"]},
            "start": 2,
            "count": 4,
            "sort": ["obchodniJmeno"],
        },
    )
    request = requests_seen[-1]
    assert request.method == "POST"
    assert request.url.path.endswith("/ekonomicke-subjekty/vyhledat")
    assert json.loads(request.content) == {
        "obchodniJmeno": "Firma",
        "pravniForma": ["112"],
        "start": 2,
        "pocet": 4,
        "razeni": ["obchodniJmeno"],
    }


async def test_default_count_is_20(client, ares_handler, requests_seen):
    ares_handler["fn"] = fake_ares
    await client.call_tool("search_entities", {"filter": {}})
    assert json.loads(requests_seen[-1].content)["pocet"] == 20


async def test_registry_failure_is_tagged(client, ares_handler):
    ares_handler["fn"] = lambda request: httpx.Response(503, text="boom")
    result = await client.call_tool("search_entities", {"filter": {}})
    assert result.is_error
    assert "[registry_unavailable]" in text_of(result)
