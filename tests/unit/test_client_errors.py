import httpx
import pytest

from ares_mcp.client import AresClient
from ares_mcp.config import Settings
from ares_mcp.errors import (
    InvalidInputError,
    NotFoundError,
    RegistryRefusedError,
    RegistryUnavailableError,
)

pytestmark = pytest.mark.anyio

RAW = "SECRET-RAW-ARES-PAYLOAD-xyz"


def make_client(handler) -> AresClient:
    return AresClient(Settings(), transport=httpx.MockTransport(handler))


@pytest.mark.parametrize(
    ("status", "exc_type", "tag"),
    [
        (404, NotFoundError, "[not_found]"),
        (400, InvalidInputError, "[invalid_input]"),
        (401, RegistryRefusedError, "[registry_refused]"),
        (403, RegistryRefusedError, "[registry_refused]"),
        (429, RegistryUnavailableError, "[registry_unavailable]"),
        (500, RegistryUnavailableError, "[registry_unavailable]"),
        (502, RegistryUnavailableError, "[registry_unavailable]"),
        (503, RegistryUnavailableError, "[registry_unavailable]"),
    ],
)
async def test_status_maps_to_category(status, exc_type, tag):
    client = make_client(lambda request: httpx.Response(status, text=RAW))
    with pytest.raises(exc_type) as exc:
        await client.get("/ekonomicke-subjekty/00000001")
    assert tag in str(exc.value)
    assert RAW not in str(exc.value)
    await client.aclose()


async def test_too_many_results_400_is_summarised_without_raw_payload():
    payload = {
        "kod": "CHYBA_VSTUPU",
        "popis": "Zadaný dotaz vrací příliš mnoho výsledků (57 802). Povoleno je maximálně "
        "1 000 výsledků. Upravte parametry vyhledávání.|Chyba vstupu SECRET-DETAIL",
    }
    client = make_client(lambda request: httpx.Response(400, json=payload))
    with pytest.raises(InvalidInputError) as exc:
        await client.post("/ekonomicke-subjekty/vyhledat", {})
    message = str(exc.value)
    assert "[invalid_input]" in message
    assert "1000" in message
    assert "narrow" in message.lower()
    assert "SECRET-DETAIL" not in message
    assert "CHYBA_VSTUPU" not in message
    await client.aclose()


async def test_other_400_stays_generic():
    client = make_client(lambda request: httpx.Response(400, json={"popis": RAW}))
    with pytest.raises(InvalidInputError) as exc:
        await client.post("/x/vyhledat", {})
    assert RAW not in str(exc.value)
    await client.aclose()


async def test_unavailable_message_says_retry_later():
    client = make_client(lambda request: httpx.Response(500, text=RAW))
    with pytest.raises(RegistryUnavailableError) as exc:
        await client.post("/x/vyhledat", {})
    assert "retry" in str(exc.value).lower()
    await client.aclose()


async def test_timeout_and_connection_errors_are_unavailable():
    def timeout(request):
        raise httpx.ReadTimeout("slow", request=request)

    def refused(request):
        raise httpx.ConnectError("refused", request=request)

    for handler in (timeout, refused):
        client = make_client(handler)
        with pytest.raises(RegistryUnavailableError) as exc:
            await client.post("/x/vyhledat", {})
        assert "[registry_unavailable]" in str(exc.value)
        assert "retry" in str(exc.value).lower()
        await client.aclose()


async def test_success_returns_json():
    client = make_client(lambda request: httpx.Response(200, json={"ico": "00000001"}))
    assert await client.get("/ekonomicke-subjekty/00000001") == {"ico": "00000001"}
    await client.aclose()


async def test_get_retries_once_on_connection_error():
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ConnectError("blip", request=request)
        return httpx.Response(200, json={"ok": True})

    client = make_client(handler)
    assert await client.get("/a") == {"ok": True}
    assert len(calls) == 2
    await client.aclose()


@pytest.mark.parametrize("status", [502, 503])
async def test_get_retries_once_on_502_503(status):
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(status, text=RAW)
        return httpx.Response(200, json={"ok": True})

    client = make_client(handler)
    assert await client.get("/a") == {"ok": True}
    assert len(calls) == 2
    await client.aclose()


async def test_get_retry_is_bounded_to_one():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(503, text=RAW)

    client = make_client(handler)
    with pytest.raises(RegistryUnavailableError):
        await client.get("/a")
    assert len(calls) == 2
    await client.aclose()


async def test_get_does_not_retry_500_or_404():
    for status in (500, 404):
        calls = []

        def handler(request, calls=calls, status=status):
            calls.append(request)
            return httpx.Response(status, text=RAW)

        client = make_client(handler)
        with pytest.raises(Exception):  # noqa: B017
            await client.get("/a")
        assert len(calls) == 1
        await client.aclose()


@pytest.mark.parametrize("failure", ["connect", "503"])
async def test_post_is_never_retried(failure):
    calls = []

    def handler(request):
        calls.append(request)
        if failure == "connect":
            raise httpx.ConnectError("blip", request=request)
        return httpx.Response(503, text=RAW)

    client = make_client(handler)
    with pytest.raises(RegistryUnavailableError):
        await client.post("/x/vyhledat", {"a": 1})
    assert len(calls) == 1
    await client.aclose()


async def test_post_sends_json_body_to_base_url():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["body"] = request.content
        return httpx.Response(200, json={"pocetCelkem": 0, "ekonomickeSubjekty": []})

    client = make_client(handler)
    await client.post("/ekonomicke-subjekty/vyhledat", {"start": 0, "pocet": 5})
    assert seen["url"] == (
        "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/ekonomicke-subjekty/vyhledat"
    )
    assert b'"pocet":5' in seen["body"].replace(b" ", b"")
    await client.aclose()
