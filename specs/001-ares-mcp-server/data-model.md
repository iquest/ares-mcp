# Data Model: ARES MCP Server

The server stores nothing. These are the shapes that pass through it. ARES field names (Czech) are preserved in results (FR-009); the server adds only the envelope fields below.

## Ico (value)

- Input: string of 1–8 digits, whitespace ignored.
- Normalised: exactly 8 digits, left-padded with `0`.
- Invalid when: empty, contains non-digits, or longer than 8 digits.

## Register (enumeration)

`vr`, `res`, `rzp`, `nrpzs`, `rpsh`, `rcns`, `szr`, `rs`, `ros`, `ceu`. Maps to the ARES path segment `ekonomicke-subjekty-<code>`.

## PageRequest

| Field | Rule |
|-------|------|
| `start` | integer >= 0, default 0 |
| `count` | integer 1..max (default 20, max 100, configurable). The maximum is enforced in code, not in the tool schema, because it is configurable |
| `sort` | optional list of ARES sort names |

## SearchResultPage

| Field | Meaning |
|-------|---------|
| `total` | total matches reported by ARES. For the notification batch list, which ARES does not page, it is the length of the list ARES returned |
| `start`, `count` | the window actually returned |
| `items` | list of entity summaries (IČO, name, and the other fields ARES returns) |
| `next_start` | offset for the next page, or null when exhausted |

`next_start` is the only field computed by the server, apart from `total` of the notification list. Live probe (2026-11-23): ARES ignores `start` and `pocet` for the notification batch search and returns every batch, so the server cuts that list into pages itself.

## EconomicEntity / SourceRegisterRecord

Passed through from ARES unchanged. The entity record is keyed by IČO. Register records differ per register.

## CodeList

A named list of codes and names returned by the code-list search.

## StandardisedAddress

An address candidate returned by the standardised-address search. ARES requires the filter field `typStandardizaceAdresy` (`VYHOVUJICI_ADRESY` or `UPLNA_STANDARDIZACE`) although its OpenAPI schema does not say so; the server defaults it to `VYHOVUJICI_ADRESY`.

## NotificationBatch

Identified by `data source` and `batch number`. Passed through unchanged.

## ToolFailure (error envelope)

Raised as an MCP tool error. The message text contains the category in square brackets (the SDK may prepend the tool name), for example `[not_found] No entity with IČO 00000001.`, because the error carries no structured data:

| Category | Source |
|----------|--------|
| `not_found` | ARES 404 |
| `invalid_input` | local validation failure or ARES 400 |
| `registry_unavailable` | timeout, connection error, 429, 5xx |
| `registry_refused` | ARES 401/403 |

## State transitions

None. Every call is stateless and independent.
