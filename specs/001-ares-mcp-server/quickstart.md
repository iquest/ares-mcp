# Quickstart: Validating the ARES MCP Server

A run-and-check guide. Tool shapes are in [contracts/tools.md](contracts/tools.md); data shapes in [data-model.md](data-model.md).

## Prerequisites

- Python 3.10+ (3.12 used in development) and `uv`.
- Internet access to `https://ares.gov.cz` for the live checks.

## Setup

```bash
uv sync
```

## Automated checks (no network)

```bash
uv run pytest tests/unit tests/contract
```

Expected: all pass. This covers IČO normalisation, page limits, error categories, tool list and schemas, and that all 26 ARES operations map to a tool.

## Live smoke checks (network)

```bash
uv run pytest tests/integration -m live
```

Expected: a known IČO returns its record (SC-001 sample), a name search returns the expected entity, and an unknown IČO returns `not_found`.

## Manual check with an MCP client

1. Start the server over stdio: `uv run python -m ares_mcp` (or the console script `uv run ares-mcp`), from an MCP client.
2. Call each scenario below and compare with the public ARES site.

`uv run mcp dev src/ares_mcp/server.py` does not work: `server.py` uses relative imports, so loading it by file path fails.

| Scenario | Call | Expected |
|----------|------|----------|
| US1 happy path | `get_entity` with a valid IČO | name, legal form, address, status |
| US1 short IČO | `get_entity` with `123456` | looked up as `00123456` |
| US1 bad input | `get_entity` with `12ab` | `invalid_input`, says 8 digits |
| US1 unknown | `get_entity` with a well-formed unused IČO | `not_found` |
| US2 search | `search_entities` by name, `count` 5 | up to 5 items, `total`, `next_start` |
| US2 paging | repeat with `start` = previous `next_start` | distinct next items |
| US3 register | `get_register_record` with `register=vr` | register data or `not_found` naming `vr` |
| US4 lists | `search_code_lists` with `filter` `{"kodCiselniku": "PravniForma"}` (an empty filter is rejected by ARES) | codes with names |
| US4 address | `search_addresses` with a partial address | candidates |
| US5 batches | `search_notification_batches`, then `get_notification_batch` | list (paged locally by the server), then content |
| Failure | set an unreachable base URL in config, call `get_entity` | `registry_unavailable`, server keeps running |

## Connecting an MCP client

Add the server to a client's MCP configuration so the client launches it over stdio. Replace the path with the absolute path of this repository:

```json
{
  "mcpServers": {
    "ares": {
      "command": "uv",
      "args": ["--directory", "/absolute/path/to/ares-mcp", "run", "python", "-m", "ares_mcp"]
    }
  }
}
```

For Claude Code the equivalent is `claude mcp add ares -- uv --directory /absolute/path/to/ares-mcp run python -m ares_mcp`.

## Done when

- [X] All automated checks pass (169 tests, ruff clean; 2026-11-23).
- [X] Every scenario row behaves as expected (run against the live ARES through an in-process MCP client, 2026-11-23).
- [ ] A new reader can reach the first successful lookup from this file and the README in under 10 minutes (SC-006). Needs a human reader; not checked.
