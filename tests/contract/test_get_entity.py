import httpx
import pytest

pytestmark = pytest.mark.anyio

RECORD = {
    "ico": "00000001",
    "obchodniJmeno": "Test s.r.o.",
    "pravniForma": "112",
    "sidlo": {"textovaAdresa": "Hlavní 1, Praha"},
}


def text_of(result) -> str:
    return " ".join(getattr(c, "text", "") for c in result.content)


async def test_tool_listed_with_ico_input_and_read_only_hint(client):
    tools = {t.name: t for t in (await client.list_tools()).tools}
    tool = tools["get_entity"]
    assert tool.input_schema["properties"]["ico"]["type"] == "string"
    assert "ico" in tool.input_schema["required"]
    assert tool.annotations is not None and tool.annotations.read_only_hint is True


async def test_returns_record_with_ares_field_names(client, ares_handler):
    ares_handler["fn"] = lambda request: httpx.Response(200, json=RECORD)
    result = await client.call_tool("get_entity", {"ico": "00000001"})
    assert not result.is_error
    assert result.structured_content == RECORD


async def test_tolerates_unknown_and_missing_fields(client, ares_handler):
    partial = {"ico": "00000001", "nejakeNoveDoplnenePole": [1, 2, 3]}  # no obchodniJmeno
    ares_handler["fn"] = lambda request: httpx.Response(200, json=partial)
    result = await client.call_tool("get_entity", {"ico": "00000001"})
    assert not result.is_error
    assert result.structured_content == partial


async def test_not_found(client, ares_handler):
    ares_handler["fn"] = lambda request: httpx.Response(404, json={"kod": "NENALEZENO"})
    result = await client.call_tool("get_entity", {"ico": "00000001"})
    assert result.is_error
    assert "[not_found]" in text_of(result)
    assert "NENALEZENO" not in text_of(result)


async def test_bad_ico_is_invalid_input_and_makes_no_request(client, requests_seen):
    result = await client.call_tool("get_entity", {"ico": "12ab"})
    assert result.is_error
    assert "[invalid_input]" in text_of(result)
    assert "8 digits" in text_of(result)
    assert requests_seen == []


async def test_short_ico_is_padded_in_request_path(client, ares_handler, requests_seen):
    ares_handler["fn"] = lambda request: httpx.Response(200, json=RECORD)
    await client.call_tool("get_entity", {"ico": "123456"})
    assert requests_seen[-1].method == "GET"
    assert requests_seen[-1].url.path.endswith("/ekonomicke-subjekty/00123456")


async def test_timeout_is_unavailable_and_server_keeps_working(client, ares_handler):
    def timeout(request):
        raise httpx.ReadTimeout("slow", request=request)

    ares_handler["fn"] = timeout
    failed = await client.call_tool("get_entity", {"ico": "00000001"})
    assert failed.is_error
    assert "[registry_unavailable]" in text_of(failed)

    ares_handler["fn"] = lambda request: httpx.Response(200, json=RECORD)
    ok = await client.call_tool("get_entity", {"ico": "00000001"})
    assert not ok.is_error
    assert ok.structured_content == RECORD
