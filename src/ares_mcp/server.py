"""Server object, lifespan and tool registration."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from mcp.server import MCPServer

from .client import AresClient
from .config import load_settings
from .context import AppContext, get_client
from .tools import entities, notifications, reference, registers

__all__ = ["AppContext", "build_server", "get_client", "mcp"]


def build_server(transport: httpx.AsyncBaseTransport | None = None) -> MCPServer:
    """Create the MCP server. ``transport`` lets tests replace the network."""

    @asynccontextmanager
    async def lifespan(_server: MCPServer) -> AsyncIterator[AppContext]:
        settings = load_settings()
        client = AresClient(settings, transport=transport)
        try:
            yield AppContext(client=client, settings=settings)
        finally:
            await client.aclose()

    server = MCPServer("ares", lifespan=lifespan)
    entities.register(server)
    registers.register(server)
    reference.register(server)
    notifications.register(server)
    # Each story adds its `<module>.register(server)` call here.
    return server


mcp = build_server()
