"""Lifespan context shared by all tools.

Lives apart from ``server.py`` so tool modules can import it without a circular import.
"""

from __future__ import annotations

from dataclasses import dataclass

from mcp.server.mcpserver import Context

from .client import AresClient
from .config import Settings


@dataclass
class AppContext:
    client: AresClient
    settings: Settings


def get_app(ctx: Context[AppContext]) -> AppContext:
    return ctx.request_context.lifespan_context


def get_client(ctx: Context[AppContext]) -> AresClient:
    return get_app(ctx).client
