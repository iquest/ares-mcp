"""Server settings, with defaults and environment-variable overrides."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass

DEFAULT_BASE_URL = "https://ares.gov.cz/ekonomicke-subjekty-v-be/rest"


@dataclass(frozen=True)
class Settings:
    base_url: str = DEFAULT_BASE_URL
    timeout_seconds: float = 10
    max_concurrency: int = 5
    default_count: int = 20
    max_count: int = 100


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    """Build Settings from ``ARES_*`` environment variables (process env by default)."""
    env = os.environ if env is None else env
    defaults = Settings()
    return Settings(
        base_url=env.get("ARES_BASE_URL", defaults.base_url),
        timeout_seconds=float(env.get("ARES_TIMEOUT_SECONDS", defaults.timeout_seconds)),
        max_concurrency=int(env.get("ARES_MAX_CONCURRENCY", defaults.max_concurrency)),
        default_count=int(env.get("ARES_DEFAULT_COUNT", defaults.default_count)),
        max_count=int(env.get("ARES_MAX_COUNT", defaults.max_count)),
    )
