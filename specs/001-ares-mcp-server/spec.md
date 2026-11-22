# Feature Specification: ARES MCP Server

**Feature Branch**: `001-ares-mcp-server` (label only; no git branch was created)

**Created**: 2026-11-22

**Status**: Draft

**Input**: User description: "Create MCP server for API https://ares.gov.cz/ekonomicke-subjekty-v-be/rest/v3/api-docs using https://py.sdk.modelcontextprotocol.io/"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Look up a company by its ID (IČO) (Priority: P1)

A user working in an AI assistant asks about a Czech business ("Who is IČO 27082440?"). The assistant calls the server and gets the entity's basic record from the Czech public business register (ARES): name, legal form, registered address, status, and key dates.

**Why this priority**: Lookup by IČO is the most common ARES task and the smallest useful slice. On its own it lets the assistant verify a Czech business.

**Independent Test**: Connect an MCP client, request the record for a known valid IČO, and check that the returned data matches the same entity on the public ARES site.

**Acceptance Scenarios**:

1. **Given** a valid IČO of an existing entity, **When** the assistant requests its record, **Then** it receives the entity's name, legal form, address and status in a readable, structured form.
2. **Given** a well-formed IČO that does not exist in ARES, **When** the assistant requests it, **Then** it receives a clear "not found" result, not a crash or empty output.
3. **Given** a malformed IČO (more than 8 digits, or non-numeric), **When** the assistant requests it, **Then** it receives a validation message saying the IČO must be 8 digits.
4. **Given** an IČO written with fewer than 8 digits (for example `123456`), **When** the assistant requests it, **Then** the server pads it with leading zeros to 8 digits and looks up the padded value.

---

### User Story 2 - Search for entities by name and criteria (Priority: P2)

A user who does not know the IČO asks the assistant to find entities by name, municipality, legal form or similar criteria. The server returns a paged list of matches, and the assistant can follow up with a full record lookup.

**Why this priority**: Most real questions start with a name, not an IČO. Search turns a company name into an IČO that Story 1 can use.

**Independent Test**: Search for a known company name and confirm the expected entity is in the results, with paging working across result sets larger than one page.

**Acceptance Scenarios**:

1. **Given** a company name fragment, **When** the assistant searches, **Then** it receives matching entities, each with its IČO and name, plus the total number of matches.
2. **Given** a search with more matches than one page holds, **When** the assistant requests the next page, **Then** it receives the next distinct set of results.
3. **Given** criteria that match nothing, **When** the assistant searches, **Then** it receives an explicit empty result.

---

### User Story 3 - Query the source registers (Priority: P3)

A user needs data held in a specific source register behind ARES, for example the commercial register (VR) or the trade licence register (RZP). The server offers lookup and search for each register in the ARES public API, so the assistant can answer questions such as "who are the statutory bodies of this company?".

**Why this priority**: This is deeper detail. It is valuable but only after core lookup and search work.

**Independent Test**: For one entity present in several registers, request its record from each supported register and compare each result with ARES.

**Acceptance Scenarios**:

1. **Given** an IČO present in a specific source register, **When** the assistant requests that register's record, **Then** it receives the register-specific data.
2. **Given** an IČO that is not present in the chosen register, **When** the assistant requests it, **Then** it receives a "not found in this register" result that can be told apart from "entity does not exist at all".

---

### User Story 4 - Use code lists and standardised addresses (Priority: P4)

A user or assistant needs valid values for search filters (legal forms, activity codes, regions) or wants to resolve a free-text address to an official standardised address. The server offers code-list lookup and address search.

**Why this priority**: These are helpers that make Stories 2 and 3 more accurate, but the core flows work without them.

**Independent Test**: Look up a code list and confirm the values match ARES. Search an address fragment and confirm standardised address candidates are returned.

**Acceptance Scenarios**:

1. **Given** the name of a code list, **When** the assistant requests it, **Then** it receives the codes with their human-readable names.
2. **Given** a partial address, **When** the assistant searches, **Then** it receives matching standardised addresses.

---

### User Story 5 - Read notification batches (Priority: P5)

A user who tracks changes in the registers asks the assistant for the list of notification batches (change feeds) and for the content of one batch, identified by its data source and batch number.

**Why this priority**: Useful for monitoring, but not needed for lookups and searches.

**Independent Test**: Request the list of notification batches, pick one, request its content, and compare with ARES.

**Acceptance Scenarios**:

1. **Given** a request for notification batches, **When** the assistant searches, **Then** it receives a paged list of batches.
2. **Given** a data source and batch number that exist, **When** the assistant requests that batch, **Then** it receives the batch content.
3. **Given** a batch number that does not exist, **When** the assistant requests it, **Then** it receives a "not found" result.

---

### Edge Cases

- ARES is unreachable, times out, or returns a server error: the assistant gets a clear, non-technical message saying the registry is temporarily unavailable, and the server stays running.
- ARES rate-limits or rejects requests: the assistant is told to retry later and is not shown raw error payloads.
- A search matches very many entities: the ARES schema documents paging by offset (`start`) and count (`pocet`) but states no maximum. The server therefore enforces its own documented default and maximum page size, and tells the assistant how to request the next page.
- Input contains Czech diacritics or extra whitespace: the server removes all whitespace from an IČO (including internal spaces, as in "270 82 440") and passes diacritics in text searches through unchanged.
- ARES returns a field the server does not recognise, or omits a normally present field: the server still returns the usable parts of the record.
- Several tool calls are made in quick succession: the server stays responsive and does not overload ARES.
- ARES changes its API in a later version: the documentation states which ARES API version the server targets.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST run as an MCP server that any MCP-compatible client can connect to, and MUST advertise its available tools with clear names, descriptions and input definitions.
- **FR-002**: The system MUST let a client retrieve the basic record of an economic entity by its IČO.
- **FR-003**: The system MUST let a client search economic entities by name and by the other filter criteria ARES supports, with paging.
- **FR-004**: The system MUST provide lookup by IČO and search for each source register in the ARES public API: VR, RES, RZP, NRPZS, RPSH, RCNS, SZR, RS, ROS and CEU.
- **FR-005**: The system MUST let a client retrieve code lists (nomenclatures) used for search filters.
- **FR-006**: The system MUST let a client search standardised addresses.
- **FR-007**: The system MUST let a client list notification batches and retrieve one batch by data source and batch number.
- **FR-008**: The system MUST validate inputs before calling ARES. An IČO MUST be at most 8 digits and numeric, and is padded with leading zeros to 8 digits. Page size MUST stay within the server's documented limits. Invalid input MUST produce a specific message. The system MUST NOT reject an IČO for a failed check-digit test, because ARES itself requires only the 8-digit format.
- **FR-009**: The system MUST return results as readable structured data that preserves the field names and meaning from ARES, so an assistant can reason over them.
- **FR-010**: The system MUST distinguish in its responses between "no such entity", "invalid input", and "registry unavailable".
- **FR-011**: The system MUST NOT crash or hang when ARES is slow, unreachable, or returns unexpected data. Each outgoing request MUST have a bounded wait time.
- **FR-012**: The system MUST be read-only. It MUST NOT expose any operation that changes data.
- **FR-013**: The system MUST NOT require end-user credentials, because the ARES public API is open. Configuration such as the API base address and timeouts MUST be adjustable without code changes.
- **FR-014**: The system MUST document how to install it, start it, and connect an MCP client to it, and MUST list every tool with an example.

### Key Entities

- **Economic entity**: A business or organisation registered in the Czech Republic. Identified by its IČO. Has a name, legal form, registered address, status, and key dates (creation, deregistration).
- **Source register record**: The view of an economic entity held in one specific register. The data it contains differs by register.
- **Search query and result page**: The filter criteria the user supplies, and one page of matching entities with a total count and paging information.
- **Code list (nomenclature)**: A named list of codes and human-readable names used to filter or interpret entity data (legal forms, regions, activity classifications).
- **Standardised address**: An official, normalised Czech address that a free-text address can be resolved to.
- **Notification batch**: A unit of register changes published by a data source, identified by data source and batch number.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can get an entity's record from its IČO in a single assistant request, and the result matches the public ARES data for 100% of a sample of at least 20 known entities.
- **SC-002**: A user can go from a company name to its full record in two assistant requests or fewer (search, then lookup).
- **SC-003**: Under normal ARES availability, 95% of lookups and searches return a result to the user in under 3 seconds.
- **SC-004**: 100% of the read operations in the ARES public API (all 26 operations in version 1.4) are reachable through the server.
- **SC-005**: In failure tests (ARES unreachable, timeout, malformed IČO, unknown IČO), 100% of cases yield a clear, categorised message and the server keeps serving later requests.
- **SC-006**: A new user can install the server and complete their first successful lookup in an MCP client in under 10 minutes using only the documentation.

## Assumptions

- The server targets the public, unauthenticated ARES REST API, version 1.4 as published at the address in the feature description. ARES currently needs no API key.
- The server is implemented with the official MCP Python SDK referenced in the feature description. This is a given constraint of the project.
- The server is intended to run locally and talk to a client over a local process connection. A hosted multi-user deployment is out of scope for the first release.
- Scope is read-only access to every operation of the ARES public API, including notification batches. All ARES operations are queries; the search operations use POST only to carry the filter body.
- Czech-language field names and values from ARES are passed through as they are. Translation is out of scope.
- ARES usage terms and any rate limits apply. The server does not guarantee availability beyond that of ARES itself, and does not cache data in the first release.
- Users have a working internet connection and an MCP-compatible client.
