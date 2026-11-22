"""Categorised errors. Every message begins with its category tag in square brackets."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from mcp.server.mcpserver.exceptions import ToolError


class AresError(Exception):
    category = "error"

    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(f"[{self.category}] {detail}")


class NotFoundError(AresError):
    category = "not_found"


class InvalidInputError(AresError):
    category = "invalid_input"


class RegistryUnavailableError(AresError):
    category = "registry_unavailable"


class RegistryRefusedError(AresError):
    category = "registry_refused"


def to_tool_error(exc: AresError) -> ToolError:
    """Convert to the SDK's ToolError so the client sees ``is_error=true`` with the tagged text."""
    return ToolError(str(exc))


@contextmanager
def tool_errors() -> Iterator[None]:
    """Wrap a tool body: categorised errors become ToolError, nothing else is touched."""
    try:
        yield
    except AresError as exc:
        raise to_tool_error(exc) from None
