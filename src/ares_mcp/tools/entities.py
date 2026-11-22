"""Entity lookup by IČO and entity search."""

from __future__ import annotations

from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.types import ToolAnnotations

from ..context import AppContext, get_app, get_client
from ..errors import tool_errors
from ..models import EntitySearchFilter, SearchResultPage
from ..validation import normalize_ico
from ._search import run_search

READ_ONLY = ToolAnnotations(read_only_hint=True)


def register(mcp: MCPServer) -> None:
    @mcp.tool(annotations=READ_ONLY)
    async def get_entity(ico: str, ctx: Context[AppContext]) -> dict[str, Any]:
        """Fetch the basic record of one economic entity from ARES by its IČO.

        The IČO may be given with spaces or without leading zeros; it is padded to 8 digits.
        Result field names are ARES's own. Example: ico="27082440".
        """
        with tool_errors():
            ico = normalize_ico(ico)
            return await get_client(ctx).get(f"/ekonomicke-subjekty/{ico}")

    @mcp.tool(annotations=READ_ONLY)
    async def search_entities(
        filter: EntitySearchFilter,
        ctx: Context[AppContext],
        start: int | None = None,
        count: int | None = None,
        sort: list[str] | None = None,
    ) -> SearchResultPage:
        """Search economic entities in ARES by name, address, legal form and other criteria.

        Results are paged: pass the returned next_start as start to get the next page.
        count defaults to 20 (maximum 100). An empty result is not an error.
        Example: filter={"obchodniJmeno": "Seznam"}, count=5.
        """
        with tool_errors():
            return await run_search(
                get_app(ctx), "/ekonomicke-subjekty/vyhledat", "ekonomickeSubjekty",
                filter, start, count, sort,
            )
