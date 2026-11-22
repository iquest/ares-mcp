import json

import httpx
import pytest

pytestmark = pytest.mark.anyio


def text_of(result) -> str:
    return " ".join(getattr(c, "text", "") for c in result.content)


async def test_tools_listed_read_only(client):
    tools = {t.name: t for t in (await client.list_tools()).tools}
    for name in ("search_code_lists", "search_addresses"):
        assert tools[name].annotations is not None
        assert tools[name].annotations.read_only_hint is True


async def test_search_code_lists(client, ares_handler, requests_seen):
    entry = {"kodCiselniku": "PravniForma", "zdrojCiselniku": "res", "polozky": [{"kod": "112"}]}
    ares_handler["fn"] = lambda request: httpx.Response(
        200, json={"pocetCelkem": 1, "ciselniky": [entry]}
    )
    result = await client.call_tool(
        "search_code_lists", {"filter": {"kodCiselniku": "PravniForma"}, "count": 5}
    )
    assert not result.is_error
    page = result.structured_content
    assert page["total"] == 1
    assert page["items"] == [entry]
    assert page["next_start"] is None
    request = requests_seen[-1]
    assert request.method == "POST"
    assert request.url.path.endswith("/ciselniky-nazevniky/vyhledat")
    assert json.loads(request.content) == {"kodCiselniku": "PravniForma", "start": 0, "pocet": 5}


async def test_search_code_lists_empty_is_not_error(client, ares_handler):
    ares_handler["fn"] = lambda request: httpx.Response(
        200, json={"pocetCelkem": 0, "ciselniky": []}
    )
    result = await client.call_tool("search_code_lists", {"filter": {"kodCiselniku": "none"}})
    assert not result.is_error
    assert result.structured_content["items"] == []


async def test_search_code_lists_paging_error_is_tagged(client):
    result = await client.call_tool("search_code_lists", {"filter": {}, "count": 500})
    assert result.is_error
    assert "[invalid_input]" in text_of(result)


async def test_search_addresses(client, ares_handler, requests_seen):
    reply = {
        "pocetCelkem": 1,
        "standardizovaneAdresy": [{"kodAdresnihoMista": 123, "textovaAdresa": "Hlavní 1, Praha"}],
        "stavStandardizace": "STANDARDIZOVANA",
    }
    ares_handler["fn"] = lambda request: httpx.Response(200, json=reply)
    result = await client.call_tool("search_addresses", {"filter": {"textovaAdresa": "Hlavní 1"}})
    assert not result.is_error
    assert result.structured_content == reply
    request = requests_seen[-1]
    assert request.method == "POST"
    assert request.url.path.endswith("/standardizovane-adresy/vyhledat")
    # ARES requires typStandardizaceAdresy (found by live probe); the tool defaults it.
    assert json.loads(request.content) == {
        "textovaAdresa": "Hlavní 1",
        "typStandardizaceAdresy": "VYHOVUJICI_ADRESY",
    }


async def test_search_addresses_explicit_standardisation_type(
    client, ares_handler, requests_seen
):
    ares_handler["fn"] = lambda request: httpx.Response(200, json={"pocetCelkem": 0})
    result = await client.call_tool(
        "search_addresses",
        {"filter": {"textovaAdresa": "x", "typStandardizaceAdresy": "UPLNA_STANDARDIZACE"}},
    )
    assert not result.is_error
    body = json.loads(requests_seen[-1].content)
    assert body["typStandardizaceAdresy"] == "UPLNA_STANDARDIZACE"


async def test_search_addresses_bad_standardisation_type_is_tagged(client, requests_seen):
    result = await client.call_tool(
        "search_addresses", {"filter": {"textovaAdresa": "x", "typStandardizaceAdresy": "NOPE"}}
    )
    assert result.is_error
    message = text_of(result)
    assert "[invalid_input]" in message
    assert "UPLNA_STANDARDIZACE" in message
    assert "VYHOVUJICI_ADRESY" in message
    assert requests_seen == []


async def test_search_addresses_empty_is_not_error(client, ares_handler):
    ares_handler["fn"] = lambda request: httpx.Response(
        200, json={"pocetCelkem": 0, "standardizovaneAdresy": []}
    )
    result = await client.call_tool("search_addresses", {"filter": {"textovaAdresa": "zzz"}})
    assert not result.is_error
    assert result.structured_content["standardizovaneAdresy"] == []


async def test_search_addresses_registry_failure_is_tagged(client, ares_handler):
    ares_handler["fn"] = lambda request: httpx.Response(500, text="boom")
    result = await client.call_tool("search_addresses", {"filter": {"textovaAdresa": "x"}})
    assert result.is_error
    assert "[registry_unavailable]" in text_of(result)
