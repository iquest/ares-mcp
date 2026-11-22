import json

import httpx
import pytest

pytestmark = pytest.mark.anyio

REGISTERS = ["vr", "res", "rzp", "nrpzs", "rpsh", "rcns", "szr", "rs", "ros", "ceu"]


def text_of(result) -> str:
    return " ".join(getattr(c, "text", "") for c in result.content)


async def test_tools_listed_read_only(client):
    tools = {t.name: t for t in (await client.list_tools()).tools}
    for name in ("get_register_record", "search_register"):
        assert tools[name].annotations is not None
        assert tools[name].annotations.read_only_hint is True
    props = tools["get_register_record"].input_schema["properties"]
    assert props["register"]["type"] == "string"  # loose, validated inside the tool
    assert all(code in props["register"]["description"] for code in REGISTERS)


@pytest.mark.parametrize("register", REGISTERS)
async def test_get_register_record_path(client, ares_handler, requests_seen, register):
    record = {"icoId": "00000001", "zaznamy": [{"x": register}]}
    ares_handler["fn"] = lambda request: httpx.Response(200, json=record)
    result = await client.call_tool("get_register_record", {"register": register, "ico": "1"})
    assert not result.is_error
    assert result.structured_content == record
    request = requests_seen[-1]
    assert request.method == "GET"
    assert request.url.path.endswith(f"/ekonomicke-subjekty-{register}/00000001")


@pytest.mark.parametrize("register", REGISTERS)
async def test_search_register_path_and_body(client, ares_handler, requests_seen, register):
    ares_handler["fn"] = lambda request: httpx.Response(
        200, json={"pocetCelkem": 1, "ekonomickeSubjekty": [{"ico": "00000001"}]}
    )
    result = await client.call_tool(
        "search_register",
        {"register": register, "filter": {"ico": ["00000001"]}, "count": 5},
    )
    assert not result.is_error
    page = result.structured_content
    assert page["total"] == 1
    assert page["items"] == [{"ico": "00000001"}]
    assert page["next_start"] is None
    request = requests_seen[-1]
    assert request.method == "POST"
    assert request.url.path.endswith(f"/ekonomicke-subjekty-{register}/vyhledat")
    assert json.loads(request.content) == {"ico": ["00000001"], "start": 0, "pocet": 5}


@pytest.mark.parametrize("tool", ["get_register_record", "search_register"])
async def test_unknown_register_is_invalid_input_listing_codes(client, requests_seen, tool):
    args = {"register": "xx"}
    args.update({"ico": "1"} if tool == "get_register_record" else {"filter": {}})
    result = await client.call_tool(tool, args)
    assert result.is_error
    message = text_of(result)
    assert "[invalid_input]" in message
    for code in REGISTERS:
        assert code in message
    assert requests_seen == []


async def test_not_found_names_the_register(client, ares_handler):
    ares_handler["fn"] = lambda request: httpx.Response(404, json={"kod": "NENALEZENO"})
    result = await client.call_tool("get_register_record", {"register": "vr", "ico": "1"})
    assert result.is_error
    message = text_of(result)
    assert "[not_found]" in message
    assert "vr" in message
    assert "get_entity" in message
    assert "NENALEZENO" not in message


async def test_bad_ico_is_invalid_input(client):
    result = await client.call_tool("get_register_record", {"register": "vr", "ico": "12ab"})
    assert result.is_error
    assert "[invalid_input]" in text_of(result)


async def test_search_register_paging_error_is_tagged(client):
    result = await client.call_tool(
        "search_register", {"register": "vr", "filter": {}, "count": 101}
    )
    assert result.is_error
    assert "[invalid_input]" in text_of(result)
