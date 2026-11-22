"""Shared helper for the paged search tools."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from ..context import AppContext
from ..models import SearchResultPage
from ..validation import check_paging


async def run_search(
    app: AppContext,
    path: str,
    items_key: str,
    flt: BaseModel | None,
    start: int | None,
    count: int | None,
    sort: list[str] | None = None,
    local_paging: bool = False,
) -> SearchResultPage:
    """Validate paging, POST the search, and wrap the answer in a SearchResultPage.

    With ``local_paging`` the search is sent without paging fields and the returned list is cut
    into pages here. This is for the one ARES list that ignores ``start`` and ``pocet``.
    """
    start, count = check_paging(start, count, app.settings)
    body: dict[str, Any] = flt.model_dump(exclude_none=True) if flt is not None else {}
    if not local_paging:
        body["start"] = start
        body["pocet"] = count
        if sort:
            body["razeni"] = sort
    data = await app.client.post(path, body)
    items = list(data.get(items_key) or [])
    if local_paging:
        everything = items
        items = everything[start : start + count]
        next_start = start + len(items) if start + len(items) < len(everything) else None
        return SearchResultPage(
            total=len(everything), start=start, count=len(items), items=items, next_start=next_start
        )
    total = data.get("pocetCelkem")
    if total is not None:
        next_start = start + len(items) if items and start + len(items) < total else None
    else:
        next_start = start + len(items) if len(items) >= count else None
    return SearchResultPage(
        total=total, start=start, count=len(items), items=items, next_start=next_start
    )
