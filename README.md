# ares-mcp

A read-only [MCP](https://modelcontextprotocol.io) server for **ARES**, the Czech register of
economic entities. It lets an AI assistant look up companies by IČO, search by name and other
criteria, and read the source registers behind ARES. It needs no credentials.

It targets ARES REST API **version 1.4** and covers **all 26 operations** of that API through
8 tools. Results keep ARES's own (Czech) field names.

## Install and start

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
uv run python -m ares_mcp        # serves MCP over stdio
```

## Connect an MCP client

Add this to the client's MCP configuration, with the absolute path of this repository:

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

For Claude Code:
`claude mcp add ares -- uv --directory /absolute/path/to/ares-mcp run python -m ares_mcp`

## Tools

All tools are read-only.

| Tool | What it does | Example call |
|------|--------------|--------------|
| `get_entity` | Basic record of one entity by IČO | `{"ico": "27082440"}` |
| `search_entities` | Search entities by name, address, legal form, ... (paged) | `{"filter": {"obchodniJmeno": "Seznam"}, "count": 5}` |
| `get_register_record` | Record of one entity in one source register | `{"register": "vr", "ico": "27082440"}` |
| `search_register` | Search one source register (paged) | `{"register": "vr", "filter": {"ico": ["27082440"]}}` |
| `search_code_lists` | Find valid codes for filters (paged) | `{"filter": {"kodCiselniku": "PravniForma"}}` |
| `search_addresses` | Resolve a partial address to standardised candidates | `{"filter": {"textovaAdresa": "Praha, Hlavní 1"}}` |
| `search_notification_batches` | List notification batches (paged) | `{"filter": {"datovyZdroj": "vr"}, "count": 10}` |
| `get_notification_batch` | Fetch one notification batch | `{"data_source": "vr", "batch_number": "7"}` |

Registers: `vr`, `res`, `rzp`, `nrpzs`, `rpsh`, `rcns`, `szr`, `rs`, `ros`, `ceu`.

- An IČO may contain spaces or lack leading zeros: `"123456"` is looked up as `00123456`.
- Searches return `total`, `start`, `count`, `items` and `next_start`. Pass `next_start` as
  `start` to get the next page. `next_start` is null on the last page. ARES does not page the
  notification batch list, so the server pages it locally and `total` is its length.
- `count` defaults to 20 and is at most 100.
- ARES refuses any search that matches more than 1000 results. Narrow the filter.
- `search_code_lists` needs at least one filter field. `search_addresses` sends
  `typStandardizaceAdresy`, default `VYHOVUJICI_ADRESY` (the other value is `UPLNA_STANDARDIZACE`).

### Errors

A failed call returns an MCP tool error whose text contains one tag:

| Tag | Meaning |
|-----|---------|
| `[not_found]` | ARES has no such record |
| `[invalid_input]` | Bad input (IČO, register, paging) or ARES rejected the request |
| `[registry_unavailable]` | Timeout, connection error, rate limit or ARES server error. Retry later |
| `[registry_refused]` | ARES refused the request (HTTP 401 or 403) |

The SDK puts the tool name in front of the tag. Raw ARES error payloads are never forwarded.
If a typed field gets the wrong JSON type (for example `start` as text), the SDK rejects the call
before the tool runs and the error has no tag.

## Configuration

Set these environment variables in the client's server entry (all optional):

| Variable | Default | Meaning |
|----------|---------|---------|
| `ARES_BASE_URL` | `https://ares.gov.cz/ekonomicke-subjekty-v-be/rest` | ARES API base URL |
| `ARES_TIMEOUT_SECONDS` | `10` | Total timeout per request |
| `ARES_MAX_CONCURRENCY` | `5` | Most requests in flight at once |
| `ARES_DEFAULT_COUNT` | `20` | Page size when `count` is omitted |
| `ARES_MAX_COUNT` | `100` | Largest accepted `count` |

GET requests are retried once on a connection error or HTTP 502/503. POST requests are never
retried.

## Develop

```bash
uv run ruff check .
uv run pytest tests/unit tests/contract      # no network
uv run pytest -m live                        # real ARES; see below
```

Live tests need `tests/fixtures/expected-entities.json` to hold at least 20 IČOs with their name
and legal form, copied by hand from the public ARES website. Do not generate them from the API.

`tests/fixtures/ares-openapi.json` is a snapshot of the ARES OpenAPI document. A test checks that
every operation in it is reachable through one of the 8 tools.
