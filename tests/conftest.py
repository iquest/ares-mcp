from collections.abc import AsyncIterator, Callable

import httpx
import pytest
from mcp import Client

from ares_mcp.server import build_server


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def ares_handler() -> dict[str, Callable[[httpx.Request], httpx.Response]]:
    """Holder for the per-test ARES handler: ``ares_handler["fn"] = lambda request: ...``."""
    return {"fn": lambda request: httpx.Response(500, text="no handler set")}


@pytest.fixture
def requests_seen() -> list[httpx.Request]:
    return []


@pytest.fixture
def server(ares_handler, requests_seen):
    def handler(request: httpx.Request) -> httpx.Response:
        requests_seen.append(request)
        return ares_handler["fn"](request)

    return build_server(httpx.MockTransport(handler))


@pytest.fixture
async def client(server) -> AsyncIterator[Client]:
    async with Client(server) as c:
        yield c
