---

description: "Task list for the ARES MCP Server"
---

# Tasks: ARES MCP Server

**Input**: Design documents from `specs/001-ares-mcp-server/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/tools.md, quickstart.md

**Tests**: Included. plan.md specifies pytest unit, contract and live-integration tests, and the spec's success criteria (SC-001, SC-004, SC-005) need them.

**Organization**: Tasks are grouped by user story (US1 to US5) so each story can be built and tested alone.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: US1 to US5, from spec.md
- Paths follow the layout in plan.md (`src/ares_mcp/`, `tests/`). One addition to that layout: `src/ares_mcp/models.py` holds the shared result shapes from data-model.md.
- The SDK is `mcp[cli]>=2,<3`; the docs were read through a summarizing fetch, so T004 confirms every import against the installed package before any code relies on it.
- Do not commit as part of any task. Commit only when the user asks.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialisation and SDK verification

- [X] T001 Create `pyproject.toml` at the repository root: package `ares-mcp`, `requires-python = ">=3.10"`, `src/` layout, dependencies `mcp[cli]>=2,<3` and `httpx>=0.28,<0.29`, dev dependencies `pytest`, `anyio`, `ruff`, and a console script `ares-mcp = "ares_mcp.__main__:main"`. Run `uv sync`.
- [X] T002 Create the package skeleton from plan.md: empty `src/ares_mcp/__init__.py`, `src/ares_mcp/tools/__init__.py`, `tests/unit/`, `tests/contract/`, `tests/integration/` (each with `__init__.py`). Also save the ARES OpenAPI document to `tests/fixtures/ares-openapi.json` by downloading `https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/v3/api-docs`; later tasks hand-write their request models from its schemas and the coverage test reads it.
- [X] T003 [P] Configure pytest and ruff in `pyproject.toml`: use `anyio` for async tests (`@pytest.mark.anyio`, with an `anyio_backend` fixture returning `"asyncio"` in `tests/conftest.py`), register the `live` marker, and skip `live` tests unless `-m live` is given.
- [X] T004 Verify the SDK against the installed package: run `uv run python -c` imports for `from mcp.server import MCPServer`, `from mcp.server.mcpserver import Context`, `from mcp.server.mcpserver.exceptions import ToolError`, `from mcp import Client`. Also confirm that an `httpx.AsyncClient` can be created before `yield` in an `@asynccontextmanager` lifespan passed as `MCPServer(name, lifespan=...)` and read in a tool via `ctx.request_context.lifespan_context`. Also record, from a throwaway tool call through `mcp.Client`: (a) the exact text the SDK returns for a schema-validation failure (for example a bad enum value or a string passed for an int), and (b) the exact `content` text produced when a tool raises `ToolError("[not_found] x")`, including any tool-name prefix. Record any difference from plan.md, plus (a) and (b), in `specs/001-ares-mcp-server/research.md` sections 1, 6 and 7.

**Error-text rule used by all later tasks**: the SDK validates typed inputs before the tool runs, and prepends the tool name to `ToolError` text. So tests assert that the category tag (for example `[not_found]`) is *contained* in the error text, never that it starts the text. Constitution Principle III requires every failure to carry a category tag. So any input whose invalid values matter to the user (`register`, `batch_number`) is declared loosely (`str`) with the valid values listed in its description, and is validated inside the tool, so the failure carries `[invalid_input]`. All range and value checks (`start >= 0`, `1 <= count <= max`) are done in `check_paging`, not in schema bounds. The only untagged failures are the SDK's own rejection of a JSON type mismatch on a typed field, including the typed filter models (for example `start` given as text); this is the documented exception in plan.md "Complexity Tracking". Assert `is_error` with the parameter name for that case.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared pieces every tool needs. No user story can start before this phase is done.

**CRITICAL**: Tests first. Write T005 to T007 and see them fail before implementing T008 to T012.

- [X] T005 [P] Write unit tests for validation in `tests/unit/test_validation.py`. IČO: input of 1 to 8 digits with whitespace ignored (`"270 82 440"`, `" 123456 "`) normalises to exactly 8 digits left-padded with `0` (`"123456"` → `"00123456"`); empty, non-digit (`"12ab"`), and more than 8 digits (`"123456789"`) raise invalid input with a message saying the IČO must be 8 digits; a number failing a check-digit test is NOT rejected. Register: `parse_register` accepts only `vr`, `res`, `rzp`, `nrpzs`, `rpsh`, `rcns`, `szr`, `rs`, `ros`, `ceu` and raises invalid input, listing those codes, for anything else. Paging (`check_paging` does all range checks; `count: 0`, `count: -1` and `start: -1` raise invalid input): `start` is an integer >= 0, default 0; `count` is an integer 1..max, default 20, max 100, configurable; larger values are rejected with a message stating the maximum.
- [X] T006 [P] Write unit tests for error mapping in `tests/unit/test_client_errors.py` using `httpx.MockTransport`: ARES 404 → `[not_found]`, 400 → `[invalid_input]`, 401/403 → `[registry_refused]`, 429, 5xx, timeout and connection error → `[registry_unavailable]` with text telling the caller to retry later; raw ARES payload text never appears in the message; GET retries once on connection error and on 502/503; POST is never retried.
- [X] T007 [P] Write unit tests for config in `tests/unit/test_config.py`: defaults (base URL `https://ares.gov.cz/ekonomicke-subjekty-v-be/rest`, total timeout 10 s, concurrency limit 5, default count 20, max count 100) and override of each through environment variables `ARES_BASE_URL`, `ARES_TIMEOUT_SECONDS`, `ARES_MAX_CONCURRENCY`, `ARES_DEFAULT_COUNT`, `ARES_MAX_COUNT`.
- [X] T008 [P] Implement `src/ares_mcp/config.py`: a frozen dataclass `Settings` with the defaults and environment overrides from T007, plus `load_settings()`.
- [X] T009 [P] Implement `src/ares_mcp/errors.py`: exceptions `NotFoundError`, `InvalidInputError`, `RegistryUnavailableError`, `RegistryRefusedError`, each producing a message that begins with its category tag in square brackets (`[not_found]`, `[invalid_input]`, `[registry_unavailable]`, `[registry_refused]`; the SDK may prepend the tool name, so only containment is testable at the client) and a function that converts them to the SDK's `ToolError` so the client sees `is_error=true` with that text.
- [X] T010 Implement `src/ares_mcp/validation.py` so T005 passes: `normalize_ico`, a `Register` enum with the ten codes, `parse_register(value: str) -> Register` (an unknown value raises invalid input listing the ten codes), and `check_paging(start, count, settings)`. Imports the exceptions from T009 and `Settings` from T008, so it follows them.
- [X] T011 [P] Implement `src/ares_mcp/models.py`: pydantic models `PageRequest` (`start` plain int, default 0, checked as >= 0 in `check_paging`; `count` int with default 20 and NO range bound in the schema (neither `>= 1` nor an upper limit): the range `1 <= count <= max` (maximum default 100, configurable through `ARES_MAX_COUNT`) is enforced in `check_paging`, so `count: 0` also returns `[invalid_input]`; likewise `start` is a plain int checked as `>= 0` in `check_paging`; optional `sort` list of strings) and `SearchResultPage` (`total`, `start`, `count`, `items`, `next_start` which is null when exhausted; `next_start` is the only server-computed field). Search tools must return this model, never a bare list.
- [X] T012 Implement `src/ares_mcp/client.py` so T006 passes: class `AresClient` wrapping one shared `httpx.AsyncClient` with explicit timeouts and a concurrency semaphore; `get(path)` and `post(path, body)` methods; status-to-error mapping from research.md section 6; one bounded retry for GET only. Depends on T008, T009.
- [X] T013 Implement `src/ares_mcp/server.py` and `src/ares_mcp/__main__.py`. `server.py` defines `build_server(transport: httpx.AsyncBaseTransport | None = None) -> MCPServer`: its `@asynccontextmanager` lifespan closure captures `transport`, builds `AresClient` from `load_settings()`, yields it in a small dataclass `AppContext`, and closes it in `finally`; `build_server` creates `MCPServer("ares", lifespan=...)` and then calls the `register(mcp)` function of every module in `src/ares_mcp/tools/` (none exist yet; add each call as its story is built). Each tool module exposes `register(mcp: MCPServer) -> None` and does NOT import `server.py`, which avoids a circular import. `server.py` also provides `get_client(ctx)` and a module-level `mcp = build_server()`. `__main__.py` has `main()` calling `mcp.run()` (stdio) under an `if __name__ == "__main__":` guard. Depends on T012.
- [X] T014 Write shared test fixtures in `tests/conftest.py`: a fixture that builds the server with `build_server(httpx.MockTransport(handler))` for a per-test handler, and an in-process `mcp.Client(server)` fixture on top of it. Extend the `tests/conftest.py` created in T003; do not overwrite it. Depends on T013.

**Checkpoint**: Foundation ready. User stories can begin.

---

## Phase 3: User Story 1 - Look up a company by IČO (Priority: P1) MVP

**Goal**: An assistant can fetch an entity's basic record by IČO.

**Independent Test**: Call `get_entity` through an MCP client for a known IČO, compare with the public ARES site, and check the not-found and invalid-input cases.

### Tests for User Story 1

- [X] T015 [P] [US1] Contract test in `tests/contract/test_get_entity.py`: the tool list contains `get_entity` with an `ico` string input and a read-only hint; a mocked 200 returns the record in `structured_content` with ARES field names unchanged; a mocked 200 with an extra unknown field and a missing normally-present field still returns the usable fields; mocked 404 gives `is_error` with text containing `[not_found]`; `"12ab"` gives text containing `[invalid_input]` and mentioning 8 digits; `"123456"` makes the outgoing request path end in `/00123456`; a mocked timeout gives text containing `[registry_unavailable]` and a later call still succeeds.

### Implementation for User Story 1

- [X] T016 [US1] Implement `get_entity(ico: str, ctx)` in `src/ares_mcp/tools/entities.py` inside a `register(mcp)` function (decorated with `@mcp.tool()`), calling `GET /ekonomicke-subjekty/{ico}` after `normalize_ico`; docstring with one example input; annotate read-only.
- [X] T017 [US1] Add `entities.register(mcp)` to `build_server` in `src/ares_mcp/server.py`.

**Checkpoint**: User Story 1 works alone. Suggested MVP.

---

## Phase 4: User Story 2 - Search entities by name and criteria (Priority: P2)

**Goal**: An assistant can search entities and page through results.

**Independent Test**: Search a known company name with `count` 5, see the expected entity, then request the next page with `next_start`.

### Tests for User Story 2

- [X] T018 [P] [US2] Contract test in `tests/contract/test_search_entities.py`: a search returns a `SearchResultPage` with `total`, `items` and `next_start`; a second call with `start` = previous `next_start` returns different items; zero matches return `total: 0`, `items: []` and no error; `count` of 101 is rejected with a message stating the maximum 100; the outgoing body maps `start` and `count` to the ARES `start` and `pocet` fields.

### Implementation for User Story 2

- [X] T019 [US2] Hand-write the `filter` input model for entity search in `src/ares_mcp/models.py` from the request schema of `POST /ekonomicke-subjekty/vyhledat` in `tests/fixtures/ares-openapi.json` (saved in T002), keeping ARES field names and optional fields.
- [X] T020 [US2] Implement `search_entities(filter, start, count, sort, ctx)` inside `register(mcp)` in `src/ares_mcp/tools/entities.py`, calling `POST /ekonomicke-subjekty/vyhledat`, applying `check_paging`, and returning `SearchResultPage` with `next_start` computed from `start`, `count` and `total`. It uses the existing `entities.register(mcp)` call in `build_server`.

**Checkpoint**: User Stories 1 and 2 both work alone.

---

## Phase 5: User Story 3 - Query the source registers (Priority: P3)

**Goal**: An assistant can look up and search each of the ten source registers.

**Independent Test**: For one entity present in several registers, call `get_register_record` for each register and compare with ARES.

### Tests for User Story 3

- [X] T021 [P] [US3] Contract test in `tests/contract/test_registers.py`, parametrised over all ten register codes: `get_register_record` calls `GET /ekonomicke-subjekty-{register}/{ico}`; `search_register` calls `POST /ekonomicke-subjekty-{register}/vyhledat`; an unknown register value gives text containing `[invalid_input]` that lists the valid register codes; a 404 gives text containing `[not_found]` that names the register.

### Implementation for User Story 3

- [X] T022 [US3] Implement `get_register_record(register: str, ico: str, ctx)` inside `register(mcp)` in `src/ares_mcp/tools/registers.py`, converting `register` with `parse_register` from `validation.py` (the parameter description lists the ten codes; `search_register` does the same); the not-found message names the register and suggests calling `get_entity` to check whether the entity exists at all.
- [X] T023 [US3] Implement `search_register(register, filter, start, count, sort, ctx)` in `src/ares_mcp/tools/registers.py`, returning `SearchResultPage`. Hand-write the `filter` model from the OpenAPI request schemas of the ten register search operations in `tests/fixtures/ares-openapi.json`; where several registers share a schema, reuse one model. Add `registers.register(mcp)` to `build_server` in `src/ares_mcp/server.py`.

**Checkpoint**: User Stories 1 to 3 work alone.

---

## Phase 6: User Story 4 - Code lists and standardised addresses (Priority: P4)

**Goal**: An assistant can look up valid filter codes and resolve addresses.

**Independent Test**: Search a code list and compare with ARES; search a partial address and get candidates.

### Tests for User Story 4

- [X] T024 [P] [US4] Contract test in `tests/contract/test_reference.py`: `search_code_lists` calls `POST /ciselniky-nazevniky/vyhledat` and returns codes with names; `search_addresses` calls `POST /standardizovane-adresy/vyhledat` and returns candidates; empty results are not errors.

### Implementation for User Story 4

- [X] T025 [US4] Implement `search_code_lists(filter, start, count, ctx)` inside `register(mcp)` in `src/ares_mcp/tools/reference.py`, with a filter model hand-written from the OpenAPI request schema in `tests/fixtures/ares-openapi.json`.
- [X] T026 [US4] Implement `search_addresses(filter, ctx)` in the same `register(mcp)` in `src/ares_mcp/tools/reference.py`, with a filter model hand-written from the OpenAPI request schema. Add `reference.register(mcp)` to `build_server` in `src/ares_mcp/server.py`.

**Checkpoint**: User Stories 1 to 4 work alone.

---

## Phase 7: User Story 5 - Read notification batches (Priority: P5)

**Goal**: An assistant can list notification batches and fetch one.

**Independent Test**: List batches, pick one, fetch its content, compare with ARES.

### Tests for User Story 5

- [X] T027 [P] [US5] Contract test in `tests/contract/test_notifications.py`: `search_notification_batches` calls `POST /ekonomicke-subjekty-notifikace/vyhledat` and returns a paged list; `get_notification_batch(data_source, batch_number)` calls `GET /ekonomicke-subjekty-notifikace/datovy-zdroj/{ds}/cislo-davky/{n}`; a 404 gives `[not_found]`; path parameters are URL-encoded.

### Implementation for User Story 5

- [X] T028 [US5] Implement `search_notification_batches(filter, start, count, ctx)` inside `register(mcp)` in `src/ares_mcp/tools/notifications.py`, returning `SearchResultPage`.
- [X] T029 [US5] Implement `get_notification_batch(data_source: str, batch_number: str, ctx)` in the same `register(mcp)`; check the real parameter types in `tests/fixtures/ares-openapi.json`, declare `batch_number` loosely and validate it inside the tool so a bad value gives `[invalid_input]`. Add `notifications.register(mcp)` to `build_server` in `src/ares_mcp/server.py`.

**Checkpoint**: All five stories work alone.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Documentation, full-coverage checks, and live validation

- [X] T030 [P] Write `README.md` (FR-014, SC-006): install, start, the MCP client connection example from quickstart.md, environment variables from T007, a table of all 8 tools with one example call each, the targeted ARES API version (1.4), and a statement that all 26 operations are covered.
- [X] T031 Write `tests/contract/test_coverage.py` for SC-004, reading `tests/fixtures/ares-openapi.json`: every path and method in the snapshot is reachable through one of the 8 tools, using a hard-coded mapping from tool and register to operation; the test fails and names the operation if one is missing.
- [ ] T032 [P] Write live smoke tests in `tests/integration/test_live.py`, marked `live`: a sample of at least 20 known IČOs matches pinned expected values (IČO, name, legal form) stored in `tests/fixtures/expected-entities.json`, not values re-read from ARES (SC-001). The maintainer copies the expected values once by hand from the public ARES website into that file; do not generate it from the API, because that would make the check circular; a name search finds an expected entity and a name-to-record flow takes two calls (SC-002); 95th-percentile latency over the sample is under 3 s (SC-003); an unused IČO gives `[not_found]`.
- [X] T033 Probe the ARES paging cap in `tests/integration/test_live.py` (marked `live`): request a deep `start` (for example 10000) and record whether ARES rejects it. Update `specs/001-ares-mcp-server/research.md` section 5 with the result and, if a cap exists, have `check_paging` in `src/ares_mcp/validation.py` report it.
- [X] T034 [P] Failure-mode test in `tests/contract/test_failures.py` for SC-005: for unreachable host, timeout, malformed IČO and unknown IČO, each yields error text containing the right category tag and a following valid call succeeds on the same server instance. Also fire 20 concurrent calls: all succeed and no more than the configured concurrency limit run at once.
- [X] T035 Confirm the server is read-only (FR-012): a test in `tests/contract/test_readonly.py` that every registered tool has the read-only hint and that no tool issues a method other than GET or a search POST.
- [X] T036 Run `uv run ruff check .` and `uv run pytest tests/unit tests/contract`, then run the manual scenarios in `specs/001-ares-mcp-server/quickstart.md` and tick the "Done when" list there.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies. T004 gates all code.
- **Foundational (Phase 2)**: depends on Setup. Blocks every user story.
- **User Stories (Phase 3 to 7)**: all depend on Phase 2. They can run in parallel or in priority order P1 → P5.
- **Polish (Phase 8)**: depends on the stories you want to ship. T031 needs all of US1 to US5.

### User Story Dependencies

- **US1**: only Phase 2.
- **US2**: only Phase 2. Reuses `SearchResultPage` from T011.
- **US3**: only Phase 2. Reuses the same models, and shares `src/ares_mcp/server.py` with every story.
- **US4, US5**: only Phase 2.

Every story edits `src/ares_mcp/server.py` (one `register` call each) and most edit `src/ares_mcp/models.py` (filter models), so tasks that touch the same file must not run at the same time even across stories.

### Within Each Story

- Contract test first, and see it fail.
- Models and filter schemas before tools.
- Register the tool last.

### Parallel Opportunities

- Phase 2: T005, T006, T007 together; then T008, T009, T011 together; T010 after T008 and T009.
- Each story's test task can run alongside the other stories' tests, but a story's tests still come before its implementation.
- Polish: T030, T032 and T034 together.

---

## Parallel Example: Foundational phase

```text
Task: "Write unit tests for validation in tests/unit/test_validation.py"
Task: "Write unit tests for error mapping in tests/unit/test_client_errors.py"
Task: "Write unit tests for config in tests/unit/test_config.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1: Setup (including the SDK check in T004).
2. Phase 2: Foundational.
3. Phase 3: User Story 1.
4. Stop and validate: run the US1 rows of quickstart.md.

### Incremental Delivery

1. Setup + Foundational.
2. Add US1 → test → usable MVP.
3. Add US2 → test (name-to-record flow now works, SC-002).
4. Add US3, US4, US5 in turn, testing each.
5. Polish: README, coverage test (SC-004), live checks.

## Notes

- [P] tasks touch different files and have no unfinished dependency.
- The [Story] label maps each task to a spec user story.
- Stop at any checkpoint to validate that story alone.
- Avoid same-file conflicts, especially in `server.py` and `models.py`.
