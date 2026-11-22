# ARES MCP Server Constitution

## Core Principles

### I. Read-Only by Design

The server MUST expose only read operations of the ARES public API. No tool may create, change or
delete data anywhere. Every tool MUST carry the MCP read-only hint. A POST to ARES is allowed only to
carry a search filter.

Rationale: ARES is a public register and the server is a window onto it. A read-only guarantee is
what makes it safe to give to an AI assistant without supervision.

### II. Faithful Pass-Through

Record data in results MUST keep ARES field names and meaning. The server MAY validate input,
normalise an IČO, page results and categorise errors (error text may summarise the cause). It MUST
NOT translate, rename, summarise or invent record data.

Rationale: users compare answers with the public ARES site. Any rewriting would make the server a
second source of truth that can drift from the first.

### III. Categorised, Safe Errors

Every failure MUST map to one of four categories: `not_found`, `invalid_input`,
`registry_unavailable`, `registry_refused`. The message MUST carry the category tag and a short
cause. Raw ARES payloads, stack traces and secrets MUST NOT reach the client. Every outgoing request
MUST have a bounded wait time, and one failing call MUST NOT stop the server.

Rationale: an assistant can only recover from an error it can tell apart.

### IV. Test-First (NON-NEGOTIABLE)

Tests for each tool and each foundation module (validation, configuration, error mapping, client)
MUST be written, and seen to fail, before its implementation. Cross-cutting regression tests that
check the finished server (operation coverage, failure modes, read-only guarantee) MAY be written
after the behaviour exists, but MUST be in place before release. Unit and contract tests MUST run
without network access, using a mocked ARES transport. Tests against the live
ARES MUST be opt-in and kept apart from the default run. A change that weakens or removes a test to
get a green run is not allowed.

Rationale: the real ARES is slow, can change, and is not ours. Deterministic tests are the only
dependable check on behaviour.

### V. Simplicity and Small Tool Surface

Prefer few tools with clear schemas over one tool per ARES operation, as long as every ARES read
operation stays reachable. Do not add caching, authentication, a database or a hosted transport
until a written requirement asks for it. A new dependency MUST be justified in the plan.

Rationale: a small tool list is easier for a model to choose from, and unused machinery is cost
with no benefit.

## Additional Constraints

- **Stack**: Python with the official MCP Python SDK (`mcp`, major version pinned) and `httpx`.
  Changing the SDK major version is a plan-level change.
- **Transport**: stdio for the first release. A network transport needs its own specification,
  including how callers are authenticated.
- **Configuration**: base URL, timeouts, concurrency and page limits MUST be configurable by
  environment variable. Defaults MUST be documented.
- **Secrets**: the server needs no credentials. No secret, token or personal data may be stored in
  the repository or written to logs.
- **Courtesy to ARES**: the server MUST limit its concurrent requests and MUST NOT retry POST calls.
- **Coverage**: every read operation in the targeted ARES API version MUST be reachable through a
  tool, and a test MUST fail when one is not.

## Development Workflow

- Work follows the Spec Kit order: specify, plan, tasks, implement. Each change is traced to a
  requirement (FR or SC) in `specs/`.
- Before merging, `ruff check` and the offline test suite MUST pass.
- Commits are made only when the maintainer asks. Commit messages describe the change and its
  reason.
- Review MUST check each change against this constitution. A violation needs either a fix or a
  written exception in the plan's Complexity Tracking section.
- Docs MUST be complete before a feature counts as done: `README.md` lists every tool with an
  example and states the targeted ARES API version.

## Governance

This constitution outranks other project practices. Amendments are made by editing this file with a
stated reason, a version bump and an updated "Last Amended" date, and the maintainer MUST approve
them. If an amendment changes how existing specs, plans or tasks must be written, those documents
MUST be reviewed in the same change.

Versioning follows semantic versioning. MAJOR is for removing or redefining a principle in a way
that breaks earlier work. MINOR is for adding a principle or section, or materially widening one.
PATCH is for wording and clarifications.

Compliance is checked at plan time (the plan's Constitution Check) and at review time. `/speckit-analyze`
treats a conflict with a MUST rule as CRITICAL.

**Version**: 1.0.0 | **Ratified**: 2026-11-22 | **Last Amended**: 2026-11-22
