"""Notification batch search and fetch."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.types import ToolAnnotations

from ..context import AppContext, get_app, get_client
from ..errors import tool_errors
from ..models import NotificationFilter, SearchResultPage
from ..validation import parse_batch_number, parse_data_source
from ._search import run_search

READ_ONLY = ToolAnnotations(read_only_hint=True)


def register(mcp: MCPServer) -> None:
    @mcp.tool(annotations=READ_ONLY)
    async def search_notification_batches(
        filter: NotificationFilter,
        ctx: Context[AppContext],
        start: int | None = None,
        count: int | None = None,
    ) -> SearchResultPage:
        """List ARES notification batches, optionally for one data source.

        ARES does not page this list, so the server pages it: total is the number of batches ARES
        returned, and next_start gives the next page. count defaults to 20 (maximum 100).
        Example: filter={"datovyZdroj": "vr"}, count=10.
        """
        with tool_errors():
            return await run_search(
                get_app(ctx), "/ekonomicke-subjekty-notifikace/vyhledat", "notifikacniDavky",
                filter, start, count, local_paging=True,
            )

    @mcp.tool(annotations=READ_ONLY)
    async def get_notification_batch(
        data_source: str, batch_number: str, ctx: Context[AppContext]
    ) -> dict[str, Any]:
        """Fetch one ARES notification batch by its data source code and batch number.

        batch_number is a whole number given as text. Find both values with
        search_notification_batches. Example: data_source="vr", batch_number="7".
        """
        with tool_errors():
            source = parse_data_source(data_source)
            number = parse_batch_number(batch_number)
            path = (
                "/ekonomicke-subjekty-notifikace/datovy-zdroj/"
                f"{quote(source, safe='')}/cislo-davky/{number}"
            )
            return await get_client(ctx).get(path)
