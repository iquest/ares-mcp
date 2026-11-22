# Implementation Plan: ARES MCP Server

**Branch**: `001-ares-mcp-server` (label only; the repo is on `main`, no feature branch created) | **Date**: 2026-11-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-ares-mcp-server/spec.md`

## Summary

A read-only MCP server that exposes the 26 operations of the ARES public REST API (v1.4) to MCP clients. To keep the tool list small enough for an LLM to choose from, the 26 operations are grouped into 8 tools: entity lookup, entity search, per-register lookup, per-register search, code lists, standardised addresses, notification batch search, and notification batch fetch. A thin async HTTP client wraps ARES, validates input (IČO padding, page limits), and maps failures into three categories: not found, invalid input, registry unavailable. The server runs over stdio, built on the official MCP Python SDK (v2 docs) with `httpx` for outgoing calls.

## Technical Context

**Language/Version**: Python 3.12 (SDK requires >=3.10; 3.12 is installed locally)

**Primary Dependencies**: `mcp[cli]>=2,<3` (official SDK; PyPI latest is 2.3.0; every class name in this plan exists only in v2, and the `[cli]` extra provides the `mcp` command), `httpx` (0.28.x), `pydantic` (comes with the SDK)

**Storage**: N/A (no persistence, no cache in v1)

**Testing**: `pytest` with `anyio`, in-process MCP `Client` against the server object, and `httpx.MockTransport` for ARES. A small set of live smoke tests is opt-in via a marker

**Target Platform**: Linux/macOS/Windows developer machines, launched by an MCP client over stdio

**Project Type**: single project (a Python package with one console entrypoint)

**Performance Goals**: 95% of lookups/searches under 3 s (spec SC-003); dominated by ARES latency

**Constraints**: read-only; no credentials; every outgoing request has a bounded timeout; no raw ARES error payloads shown to the client

**Scale/Scope**: single local user per process; 8 tools covering 26 ARES operations

**Resolved by research** (see [research.md](research.md)): SDK class name and import path, error mapping, tool grouping, register list, paging limits.

**Decisions from the SDK docs** (read through a summarizing fetch, so the first task confirms them against the installed `mcp` version): one shared `httpx.AsyncClient` is created in an `@asynccontextmanager` lifespan passed as `MCPServer(name, lifespan=...)`, yielded in a small dataclass, closed in `finally`, and read in tools through a `ctx: Context[AppContext]` parameter as `ctx.request_context.lifespan_context`. Tools return pydantic models, TypedDicts or dicts, which become `structured_content`; list returns are wrapped under `result`, so search tools return a model, never a bare list. The entrypoint is `mcp.run()` under an `if __name__ == "__main__":` guard, which defaults to stdio.

## Constitution Check

Checked against constitution v1.0.0 (`.specify/memory/constitution.md`):

| Rule | Status |
|------|--------|
| I. Read-only by design | Pass: 8 read-only tools; POST only carries search filters (T035 enforces) |
| II. Faithful pass-through | Pass: results keep ARES field names; only `next_start` is added (T011, T015) |
| III. Categorised, safe errors | Pass with one documented exception (see Complexity Tracking). Values that matter to users (`register`, `batch_number`, IČO, paging ranges) are validated inside the tools and carry a tag (tasks T004, T010, T021, T022, T029) |
| IV. Test-first | Pass: tests precede each tool and foundation module; cross-cutting tests (T031, T034, T035) follow, as the constitution allows |
| V. Simplicity | Pass: 8 tools for 26 operations; no cache, auth or database; dependencies listed above |
| Additional constraints | Pass: pinned SDK major, stdio, environment configuration (T007), no secrets, concurrency limit and no POST retries (T006, T012), coverage test (T031) |

**Post-design re-check**: one documented exception to Principle III, recorded under Complexity Tracking. No other violations.

## Project Structure

### Documentation (this feature)

```text
specs/001-ares-mcp-server/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── tools.md
├── checklists/requirements.md
└── tasks.md             # created later by /speckit-tasks
```

### Source Code (repository root)

```text
pyproject.toml
README.md
src/ares_mcp/
├── __init__.py
├── __main__.py          # `python -m ares_mcp` -> run over stdio
├── server.py            # server object and tool registration
├── client.py            # async ARES HTTP client, timeouts, error mapping
├── config.py            # base URL, timeout, page-size limits from environment
├── validation.py        # IČO normalisation, register enum, paging checks
├── models.py            # PageRequest, SearchResultPage, search filter models
├── errors.py            # NotFound / InvalidInput / RegistryUnavailable
└── tools/
    ├── entities.py      # entity lookup + search
    ├── registers.py     # per-register lookup + search
    ├── reference.py     # code lists + standardised addresses
    └── notifications.py # notification batch search + fetch
tests/
├── conftest.py          # shared fixtures: server built with a mock transport, in-process client
├── fixtures/            # ares-openapi.json snapshot, expected-entities.json (pinned values)
├── unit/                # validation, error mapping, config
├── contract/            # in-process MCP client: tool list, schemas, results
└── integration/         # opt-in live ARES smoke tests
```

**Structure Decision**: single project with a `src/` layout. Tool modules are split by user story (P1/P2 entities, P3 registers, P4 reference, P5 notifications) so each story can be built and tested alone.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Principle III: the SDK rejects JSON type mismatches (for example text where a number is expected) and field errors in the typed search filter models before the tool runs, so those errors carry the SDK's text and no category tag | Typed schemas show the model which fields exist and what types they take, which makes correct tool calls far more likely | Declaring every input as a loose string and validating it all in code would remove that guidance and make each tool's schema nearly empty |

This is the written exception that the constitution's Development Workflow section allows. Range and value checks (`start >= 0`, `1 <= count <= max`, IČO format, register code, batch number) are done inside the tools, so they are tagged. The exception covers type mismatches only. If the maintainer prefers, a `/speckit-constitution` amendment limiting Principle III to failures raised by the server's own code would remove the need for it.
