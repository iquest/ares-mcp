import httpx
import pytest

pytestmark = pytest.mark.anyio


async def test_server_starts_and_lists_tools(client):
    tools = await client.list_tools()
    assert isinstance(tools.tools, list)


async def test_lifespan_client_uses_mock_transport(server, ares_handler):
    ares_handler["fn"] = lambda request: httpx.Response(200, json={})
    # Server builds and tears down its lifespan without touching the network.
    from mcp import Client

    async with Client(server) as c:
        await c.list_tools()
