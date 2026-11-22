"""Shared result shapes and search filter models (see data-model.md).

ARES record data is passed through unchanged. Filter models are hand-written from the request
schemas in ``tests/fixtures/ares-openapi.json`` and keep ARES field names. Paging fields
(``start``, ``pocet``, ``razeni``) are NOT part of the filters: they come from the tool's
``start``, ``count`` and ``sort`` arguments.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PageRequest(BaseModel):
    """Paging inputs. Ranges are enforced in ``check_paging``, not in this schema."""

    start: int = Field(default=0, description="Offset of the first result, 0 or greater.")
    count: int = Field(default=20, description="Number of results to return (1 to the maximum).")
    sort: list[str] | None = Field(default=None, description="Optional ARES sort names.")


class SearchResultPage(BaseModel):
    total: int | None = Field(
        description="Total matches reported by ARES (for notification batches, the length of the "
        "list ARES returned)."
    )
    start: int = Field(description="Offset of the first returned item.")
    count: int = Field(description="Number of items returned in this page.")
    items: list[dict[str, Any]] = Field(description="Result items, with ARES field names.")
    next_start: int | None = Field(
        description="Offset for the next page, or null when the results are exhausted."
    )


class _Filter(BaseModel):
    model_config = ConfigDict(extra="forbid")

    def to_body(self) -> dict[str, Any]:
        return self.model_dump(exclude_none=True)


class AddressFilter(_Filter):
    """Address part of an entity search (ARES ``AdresaFiltr``)."""

    kodObce: int | None = Field(default=None, description="Municipality code.")
    kodCastiObce: int | None = Field(default=None, description="Municipality part code.")
    kodSpravnihoObvodu: int | None = Field(
        default=None, description="Administrative district code."
    )
    kodMestskeCastiObvodu: int | None = Field(default=None, description="City district part code.")
    kodUlice: int | None = Field(default=None, description="Street code.")
    cisloDomovni: int | None = Field(default=None, description="House number.")
    cisloOrientacni: int | None = Field(default=None, description="Orientation number.")
    cisloOrientacniPismeno: str | None = Field(default=None, description="Orientation letter.")
    textovaAdresa: str | None = Field(default=None, description="Free-text address.")


class EntitySearchFilter(_Filter):
    """Filter for the entity search (ARES ``EkonomickeSubjektyKomplexFiltr``)."""

    ico: list[str] | None = Field(default=None, description="IČO values, each exactly 8 digits.")
    obchodniJmeno: str | None = Field(default=None, description="Business name, e.g. 'Seznam'.")
    sidlo: AddressFilter | None = Field(default=None, description="Registered office address.")
    pravniForma: list[str] | None = Field(
        default=None, description="Legal form codes, each 3 digits, e.g. ['112']."
    )
    financniUrad: list[str] | None = Field(
        default=None, description="Tax office codes, each 3 digits."
    )
    pravniFormaRos: list[str] | None = Field(
        default=None, description="Legal form codes from ROS, each 3 digits."
    )
    czNace: list[str] | None = Field(default=None, description="CZ-NACE activity codes.")


class RegisterSearchFilter(_Filter):
    """Filter for the ten per-register searches (ARES ``EkonomickeSubjektyRegistraceFiltr``)."""

    ico: list[str] | None = Field(default=None, description="IČO values, each exactly 8 digits.")


class CodeListFilter(_Filter):
    """Filter for the code-list search (ARES ``CiselnikyZakladniFiltr``)."""

    zdrojCiselniku: str | None = Field(default=None, description="Code list source.")
    kodCiselniku: str | None = Field(default=None, description="Code list code.")


class AddressSearchFilter(_Filter):
    """Filter for the standardised-address search (ARES ``StandardizovanaAdresaFiltr``)."""

    kodObce: int | None = Field(default=None, description="Municipality code.")
    nazevObce: str | None = Field(default=None, description="Municipality name.")
    kodCastiObce: int | None = Field(default=None, description="Municipality part code.")
    nazevCastiObce: str | None = Field(default=None, description="Municipality part name.")
    kodMestskehoCastiObvodu: int | None = Field(
        default=None, description="City district part code."
    )
    nazevMestskehoCastiObvodu: str | None = Field(
        default=None, description="City district part name."
    )
    kodUlice: int | None = Field(default=None, description="Street code.")
    nazevUlice: str | None = Field(default=None, description="Street name.")
    cisloDomovni: int | None = Field(default=None, description="House number.")
    cisloOrientacni: int | None = Field(default=None, description="Orientation number.")
    cisloOrientacniPismeno: str | None = Field(default=None, description="Orientation letter.")
    kodAdresnihoMista: int | None = Field(default=None, description="Address point code.")
    textovaAdresa: str | None = Field(
        default=None, description="Free-text address, e.g. 'Praha, Hlavní 1'."
    )
    typStandardizaceAdresy: str | None = Field(
        default=None,
        description="Standardisation type: VYHOVUJICI_ADRESY (all matching addresses, the "
        "default) or UPLNA_STANDARDIZACE (full standardisation of one address). ARES requires it.",
    )


class NotificationFilter(_Filter):
    """Filter for the notification batch search (ARES ``EkonomickeSubjektyNotifikaceFiltr``)."""

    datovyZdroj: str | None = Field(default=None, description="Data source code of the batch.")
