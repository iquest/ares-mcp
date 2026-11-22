# Research: ARES MCP Server

## 1. SDK and server class

- **Decision**: Use the official `mcp` package. Per the v2 docs the server class is `MCPServer`, imported from `mcp.server`, with `@mcp.tool()` on plain typed functions. The in-process test client is `mcp.Client`.
- **Rationale**: This is what the user-given docs site (py.sdk.modelcontextprotocol.io) describes. v1 used `mcp.server.fastmcp.FastMCP`; the names differ.
- **Alternatives**: FastMCP v1 import (older API, not what the docs show); the standalone `fastmcp` package (not the SDK the user named).
- **Caveat**: The docs were read through a summarizing fetch. The first implementation task MUST confirm import paths against the installed package.
- **Verified (T004, installed `mcp` 2.3.0)**: `from mcp.server import MCPServer`, `from mcp.server.mcpserver import Context`, `from mcp.server.mcpserver.exceptions import ToolError` and `from mcp import Client` all import. No difference from this plan. The read-only hint is set with `@mcp.tool(annotations=ToolAnnotations(read_only_hint=True))` (`from mcp.types import ToolAnnotations`). A tool returning `dict[str, Any]` or a pydantic model gets `structured_content`; a tool annotated plain `dict` gets none (text only), so annotate tools `dict[str, Any]`.

## 2. Transport

- **Decision**: stdio by default (local use, per spec assumptions). Streamable HTTP is not built in v1.
- **Rationale**: Matches the spec's local, single-user scope and needs no auth design.
- **Alternatives**: Streamable HTTP (needs auth and hosting decisions, out of scope).

## 3. Tool grouping (26 operations → 8 tools)

- **Decision**: One tool per user intent, with a `register` enum parameter for the ten register endpoints.
- **Rationale**: 26 near-identical tools would hurt an LLM's tool selection and bloat the tool list. Grouping keeps FR-004 and SC-004 satisfied: every operation is still reachable.
- **Alternatives**: One tool per ARES operation (26 tools, simple 1:1 mapping, worse for models); a single generic "call ARES" tool (loses validation and clear schemas).
- **Register enum**: `vr`, `res`, `rzp`, `nrpzs`, `rpsh`, `rcns`, `szr`, `rs`, `ros`, `ceu`. Verified against the live API docs: each has `GET /ekonomicke-subjekty-<code>/{ico}` and `POST .../vyhledat`. The base entity endpoints are `/ekonomicke-subjekty/{ico}` and `/ekonomicke-subjekty/vyhledat`.

## 4. ARES API facts (from the live OpenAPI document, v1.4)

- Base URL: `https://ares.gov.cz/ekonomicke-subjekty-v-be/rest`.
- IČO path parameter: string matching `^\d{8}$`. No check-digit rule in the schema.
- Search requests are POST with a JSON filter body; paging fields are `start` (offset, min 0) and `pocet` (count, min 0), plus `razeni` (sort). The schema states no maximum.
- Responses: 200, 400, 401, 403, 404, 500 are documented for lookups.
- Other operations: `POST /ciselniky-nazevniky/vyhledat`, `POST /standardizovane-adresy/vyhledat`, `POST /ekonomicke-subjekty-notifikace/vyhledat`, `GET /ekonomicke-subjekty-notifikace/datovy-zdroj/{datovyZdroj}/cislo-davky/{cisloDavky}`.

## 5. Page-size limits

- **Decision**: Server default `count=20`, server maximum `count=100`, both configurable by environment variable. Reject larger values with an invalid-input message that states the maximum.
- **Rationale**: Keeps responses small for model context.
- **Probed live (T033, 2026-11-23)**: ARES has no cap on `start` or on `start + count`. A `start` beyond the end of a result set returns 200 with an empty list. The real limit is on the result set: a query that matches more than 1000 results gets HTTP 400 (`CHYBA_VSTUPU`, "příliš mnoho výsledků ... maximálně 1 000"), whatever `start` and `pocet` are, even `pocet: 5`. The client summarises this case as `[invalid_input]` with a hint to narrow the filter and does not forward the ARES text. `check_paging` is unchanged because the limit depends on the query, not on the paging values. Consequence: a search can page through at most 1000 matches.

## 6. Error mapping

- **Decision**: ARES 404 → "not found"; 400 → "invalid input" (with the ARES message summarised); timeouts, connection errors, 5xx, 429 → "registry unavailable, retry later". 401/403 → "registry refused the request". Raise the SDK's tool-error exception so the client sees `is_error=true` with a short message; never forward raw payloads.
- **Encoding**: the tool-error exception carries text only (`structured_content` is `None`), so the category is a fixed tag in the message text: `[not_found]`, `[invalid_input]`, `[registry_unavailable]`, `[registry_refused]`. The SDK may prepend the tool name, so contract tests assert that the text contains the tag, not that it starts with it. To keep every failure tagged (constitution Principle III), inputs such as `register` and `batch_number` are declared loosely and validated inside the tool, because the SDK would otherwise reject them with its own untagged text before the tool runs.
- **Verified (T004, `mcp` 2.3.0)**: (a) a schema-validation failure gives `is_error=true` and text `Error executing tool t_int: 1 validation error for t_intArguments\nn\n  Input should be a valid integer, unable to parse string as an integer [type=int_parsing, ...]` (an enum failure reads `Input should be 'red' [type=enum, ...]`); it has no category tag. (b) `raise ToolError("[not_found] x")` gives `is_error=true` and text `Error executing tool t_err: [not_found] x`, so the tool-name prefix exists and the tag is contained, not leading. (c) Any other exception gives only `Error executing tool t_boom`, with no detail. `call_tool` returns the error result; it does not raise.
- **Rationale**: The docs state that only the SDK's tool-error exception gives a controlled message; other exceptions yield a generic message and the detail is lost.
- **Alternatives**: Returning error text as a normal result (the client cannot tell it is an error).

## 7. HTTP client and resilience

- **Decision**: One shared `httpx.AsyncClient` with explicit connect/read timeouts (default 10 s total), no automatic retries on POST, one bounded retry on GET for connection errors and 502/503. A small concurrency limit (default 5) protects ARES.
- **Rationale**: Meets FR-011 and the rapid-calls edge case without caching.
- **Decision**: hold the shared client in the SDK lifespan (created before `yield`, closed in `finally`) and read it from `ctx.request_context.lifespan_context` inside tools. The docs show this pattern with a database object, not `httpx`; the first task confirms it works for `httpx.AsyncClient`. **Verified (T004)**: an `httpx.AsyncClient` created before `yield` in an `@asynccontextmanager` lifespan passed as `MCPServer(name, lifespan=...)` is readable in a tool as `ctx.request_context.lifespan_context` (typed `Context[App]`) and is closed in `finally`.

## 8. IČO handling

- **Decision**: Strip all whitespace (including internal spaces, e.g. "270 82 440"), require digits only, length 1–8, left-pad with zeros to 8. No check-digit rejection.
- **Rationale**: Matches the spec (FR-008) and ARES's own schema.

## 9. Testing

- **Decision**: Unit tests for validation and error mapping; contract tests that call tools through the in-process client with ARES mocked by `httpx.MockTransport`; opt-in live smoke tests for SC-001/SC-003.
- **Rationale**: Deterministic CI, with real-API checks available on demand.
