"""SC-004: every operation in the ARES OpenAPI snapshot is reachable through one of the 8 tools."""

import json
from pathlib import Path

import httpx
import pytest

from ares_mcp.validation import Register

pytestmark = pytest.mark.anyio

SNAPSHOT = Path(__file__).parent.parent / "fixtures" / "ares-openapi.json"
HTTP_METHODS = {"get", "post", "put", "delete", "patch", "head", "options"}

# Tool -> arguments that make it call ARES, and the (method, path template) it must produce.
# For register tools, {register} is expanded over all ten codes.
SIMPLE = {
    ("get", "/ekonomicke-subjekty/{ico}"): ("get_entity", {"ico": "1"}),
    ("post", "/ekonomicke-subjekty/vyhledat"): ("search_entities", {"filter": {}}),
    ("post", "/ciselniky-nazevniky/vyhledat"): ("search_code_lists", {"filter": {}}),
    ("post", "/standardizovane-adresy/vyhledat"): ("search_addresses", {"filter": {}}),
    ("post", "/ekonomicke-subjekty-notifikace/vyhledat"): (
        "search_notification_batches",
        {"filter": {}},
    ),
    (
        "get",
        "/ekonomicke-subjekty-notifikace/datovy-zdroj/{datovyZdroj}/cislo-davky/{cisloDavky}",
    ): ("get_notification_batch", {"data_source": "vr", "batch_number": "1"}),
}


def tool_for(method: str, path: str):
    """Return (tool, args) for an OpenAPI operation, or None if no tool covers it."""
    if (method, path) in SIMPLE:
        return SIMPLE[(method, path)]
    for reg in Register:
        base = f"/ekonomicke-subjekty-{reg.value}"
        if (method, path) == ("get", f"{base}/{{ico}}"):
            return "get_register_record", {"register": reg.value, "ico": "1"}
        if (method, path) == ("post", f"{base}/vyhledat"):
            return "search_register", {"register": reg.value, "filter": {}}
    return None


def operations():
    spec = json.loads(SNAPSHOT.read_text())
    return [
        (method, path)
        for path, item in spec["paths"].items()
        for method in item
        if method in HTTP_METHODS
    ]


def test_snapshot_has_26_operations():
    assert len(operations()) == 26


@pytest.mark.parametrize(("method", "path"), operations())
async def test_operation_is_reachable_through_a_tool(
    client, ares_handler, requests_seen, method, path
):
    mapping = tool_for(method, path)
    assert mapping is not None, f"No tool covers {method.upper()} {path}"
    tool, args = mapping
    ares_handler["fn"] = lambda request: httpx.Response(
        200, json={"pocetCelkem": 0, "ekonomickeSubjekty": [], "notifikacniDavky": []}
    )
    result = await client.call_tool(tool, args)
    assert not result.is_error, f"{tool} failed for {method.upper()} {path}"
    request = requests_seen[-1]
    assert request.method == method.upper()

    expected = path
    if "{ico}" in expected:
        expected = expected.replace("{ico}", "00000001")
    expected = expected.replace("{datovyZdroj}", "vr").replace("{cisloDavky}", "1")
    assert request.url.path.endswith(expected), (
        f"{tool} called {request.method} {request.url.path}, expected …{expected}"
    )
