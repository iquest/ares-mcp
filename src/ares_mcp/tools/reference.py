"""Code lists and standardised addresses."""

from __future__ import annotations

from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.types import ToolAnnotations

from ..context import AppContext, get_app, get_client
from ..errors import InvalidInputError, tool_errors
from ..models import AddressSearchFilter, CodeListFilter, SearchResultPage
from ._search import run_search

READ_ONLY = ToolAnnotations(read_only_hint=True)

STANDARDISATION_TYPES = ("UPLNA_STANDARDIZACE", "VYHOVUJICI_ADRESY")
DEFAULT_STANDARDISATION = "VYHOVUJICI_ADRESY"


def register(mcp: MCPServer) -> None:
    @mcp.tool(annotations=READ_ONLY)
    async def search_code_lists(
        filter: CodeListFilter,
        ctx: Context[AppContext],
        start: int | None = None,
        count: int | None = None,
    ) -> SearchResultPage:
        """Search ARES code lists, to find valid codes (for example legal forms) for filters.

        At least one filter field is required (ARES rejects an empty filter). Results are paged
        via next_start. count defaults to 20 (maximum 100).
        Example: filter={"kodCiselniku": "PravniForma"}.
        """
        with tool_errors():
            return await run_search(
                get_app(ctx), "/ciselniky-nazevniky/vyhledat", "ciselniky",
                filter, start, count,
            )

    @mcp.tool(annotations=READ_ONLY)
    async def search_addresses(
        filter: AddressSearchFilter, ctx: Context[AppContext]
    ) -> dict[str, Any]:
        """Resolve a free-text or partial address to standardised ARES address candidates.

        The ARES answer is returned unchanged. An empty result is not an error. ARES requires
        typStandardizaceAdresy; it defaults to VYHOVUJICI_ADRESY when omitted.
        Example: filter={"textovaAdresa": "Praha, Hlavní 1"}.
        """
        with tool_errors():
            body = filter.model_dump(exclude_none=True)
            kind = body.setdefault("typStandardizaceAdresy", DEFAULT_STANDARDISATION)
            if kind not in STANDARDISATION_TYPES:
                raise InvalidInputError(
                    f"typStandardizaceAdresy must be one of: {', '.join(STANDARDISATION_TYPES)}."
                )
            return await get_client(ctx).post("/standardizovane-adresy/vyhledat", body)
