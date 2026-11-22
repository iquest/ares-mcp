"""Input validation: IČO normalisation, register codes and paging ranges."""

from __future__ import annotations

from enum import Enum

from .config import Settings
from .errors import InvalidInputError


class Register(str, Enum):
    VR = "vr"
    RES = "res"
    RZP = "rzp"
    NRPZS = "nrpzs"
    RPSH = "rpsh"
    RCNS = "rcns"
    SZR = "szr"
    RS = "rs"
    ROS = "ros"
    CEU = "ceu"


REGISTER_CODES = ", ".join(r.value for r in Register)


def normalize_ico(value: str) -> str:
    """Strip whitespace, require 1-8 digits, left-pad with zeros to 8. No check-digit test."""
    cleaned = "".join(str(value).split())
    if not cleaned or not cleaned.isascii() or not cleaned.isdigit() or len(cleaned) > 8:
        raise InvalidInputError("The IČO must be 8 digits (shorter numbers are padded with zeros).")
    return cleaned.zfill(8)


def parse_register(value: str) -> Register:
    try:
        return Register(value)
    except ValueError:
        raise InvalidInputError(
            f"Unknown register {value!r}. Valid registers: {REGISTER_CODES}."
        ) from None


def parse_batch_number(value: str) -> int:
    """A notification batch number is a non-negative integer."""
    cleaned = str(value).strip()
    if not cleaned or not cleaned.isascii() or not cleaned.isdigit():
        raise InvalidInputError("batch_number must be a whole number such as 7.")
    return int(cleaned)


def parse_data_source(value: str) -> str:
    """A data source code is a non-empty string of at most 30 characters."""
    cleaned = str(value).strip()
    if not cleaned or len(cleaned) > 30:
        raise InvalidInputError("data_source must be a code of 1 to 30 characters, such as 'vr'.")
    return cleaned


def check_paging(start: int | None, count: int | None, settings: Settings) -> tuple[int, int]:
    """Apply defaults and range checks; return the validated ``(start, count)``."""
    start = 0 if start is None else start
    count = settings.default_count if count is None else count
    if start < 0:
        raise InvalidInputError("start must be 0 or greater.")
    if count < 1:
        raise InvalidInputError("count must be at least 1.")
    if count > settings.max_count:
        raise InvalidInputError(f"count must be at most {settings.max_count}.")
    return start, count
