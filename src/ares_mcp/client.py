"""Async ARES HTTP client: bounded timeouts, concurrency limit, status-to-error mapping."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from .config import Settings
from .errors import (
    AresError,
    InvalidInputError,
    NotFoundError,
    RegistryRefusedError,
    RegistryUnavailableError,
)

_RETRY_STATUSES = {502, 503}
_UNAVAILABLE = "ARES is unavailable ({cause}). Retry later."


_TOO_MANY_RESULTS_MARKER = "příliš mnoho výsledků"
_TOO_MANY_RESULTS = (
    "The search matches too many results: ARES refuses queries matching more than 1000 results, "
    "whatever the paging. Narrow the filter (add a name, address or legal form) and retry."
)


def _map_status(status: int, response: httpx.Response | None = None) -> AresError:
    if status == 404:
        return NotFoundError("ARES has no record for this request.")
    if status == 400:
        if response is not None and _TOO_MANY_RESULTS_MARKER in _error_text(response):
            return InvalidInputError(_TOO_MANY_RESULTS)
        return InvalidInputError("ARES rejected the request as invalid.")
    if status in (401, 403):
        return RegistryRefusedError(f"ARES refused the request (HTTP {status}).")
    return RegistryUnavailableError(_UNAVAILABLE.format(cause=f"HTTP {status}"))


def _error_text(response: httpx.Response) -> str:
    """Read ARES's error description for matching only; it is never forwarded."""
    try:
        return str(response.json().get("popis", ""))
    except (ValueError, AttributeError):
        return ""


class AresClient:
    def __init__(self, settings: Settings, transport: httpx.AsyncBaseTransport | None = None):
        self._settings = settings
        self._semaphore = asyncio.Semaphore(settings.max_concurrency)
        self._http = httpx.AsyncClient(
            base_url=settings.base_url.rstrip("/"),
            timeout=httpx.Timeout(settings.timeout_seconds),
            transport=transport,
            headers={"Accept": "application/json"},
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def get(self, path: str) -> Any:
        return await self._request("GET", path, None, retries=1)

    async def post(self, path: str, body: Any) -> Any:
        return await self._request("POST", path, body, retries=0)

    async def _request(self, method: str, path: str, body: Any, retries: int) -> Any:
        attempt = 0
        while True:
            try:
                async with self._semaphore:
                    response = await self._http.request(method, path, json=body)
            except httpx.TimeoutException:
                raise RegistryUnavailableError(_UNAVAILABLE.format(cause="timeout")) from None
            except httpx.TransportError:
                if attempt < retries:
                    attempt += 1
                    continue
                raise RegistryUnavailableError(
                    _UNAVAILABLE.format(cause="connection error")
                ) from None
            if response.status_code in _RETRY_STATUSES and attempt < retries:
                attempt += 1
                continue
            if response.status_code >= 400:
                raise _map_status(response.status_code, response)
            try:
                return response.json()
            except ValueError:
                raise RegistryUnavailableError(
                    _UNAVAILABLE.format(cause="unreadable response")
                ) from None
