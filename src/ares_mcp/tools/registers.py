"""Per-register lookup and search (ten source registers)."""

from __future__ import annotations

from typing import Annotated, Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.types import ToolAnnotations
from pydantic import Field

from ..context import AppContext, get_app, get_client
from ..errors import NotFoundError, tool_errors
from ..models import RegisterSearchFilter, SearchResultPage
from ..validation import REGISTER_CODES, normalize_ico, parse_register
from ._search import run_search

READ_ONLY = ToolAnnotations(read_only_hint=True)

RegisterArg = Annotated[
    str,
    Field(description=f"Source register code. One of: {REGISTER_CODES}."),
]


def register(mcp: MCPServer) -> None:
    @mcp.tool(annotations=READ_ONLY)
    async def get_register_record(
        register: RegisterArg, ico: str, ctx: Context[AppContext]
    ) -> dict[str, Any]:
        """Fetch the record of one entity from a single ARES source register.

        Each register is an ARES data source named by its code (see the register parameter).
        Example: register="vr", ico="27082440".
        """
        with tool_errors():
            reg = parse_register(register)
            ico = normalize_ico(ico)
            try:
                return await get_client(ctx).get(f"/ekonomicke-subjekty-{reg.value}/{ico}")
            except NotFoundError:
                raise NotFoundError(
                    f"No record for IČO {ico} in register {reg.value}. Call get_entity to check "
                    "whether the entity exists at all."
                ) from None

    @mcp.tool(annotations=READ_ONLY)
    async def search_register(
        register: RegisterArg,
        filter: RegisterSearchFilter,
        ctx: Context[AppContext],
        start: int | None = None,
        count: int | None = None,
        sort: list[str] | None = None,
    ) -> SearchResultPage:
        """Search one ARES source register. Results are paged via next_start.

        count defaults to 20 (maximum 100). An empty result is not an error.
        Example: register="vr", filter={"ico": ["27082440"]}.
        """
        with tool_errors():
            reg = parse_register(register)
            return await run_search(
                get_app(ctx), f"/ekonomicke-subjekty-{reg.value}/vyhledat",
                "ekonomickeSubjekty", filter, start, count, sort,
            )
