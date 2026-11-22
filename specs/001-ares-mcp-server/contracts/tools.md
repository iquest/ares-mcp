# Contract: MCP Tools

Transport: stdio. All tools are read-only (annotate `readOnlyHint: true`). Errors use the categories in [data-model.md](../data-model.md). The `register` parameter is the enumeration defined there.

| # | Tool | Inputs | Returns | ARES operations | Story |
|---|------|--------|---------|-----------------|-------|
| 1 | `get_entity` | `ico` | entity record | `GET /ekonomicke-subjekty/{ico}` | US1 |
| 2 | `search_entities` | `filter` (object; ARES filter fields, e.g. business name, municipality, legal form), `start`, `count`, `sort` | SearchResultPage | `POST /ekonomicke-subjekty/vyhledat` | US2 |
| 3 | `get_register_record` | `register`, `ico` | register record | `GET /ekonomicke-subjekty-{register}/{ico}` (10 operations) | US3 |
| 4 | `search_register` | `register`, `filter`, `start`, `count`, `sort` | SearchResultPage | `POST /ekonomicke-subjekty-{register}/vyhledat` (10 operations) | US3 |
| 5 | `search_code_lists` | `filter`, `start`, `count` | code list entries | `POST /ciselniky-nazevniky/vyhledat` | US4 |
| 6 | `search_addresses` | `filter` (free-text or structured address fields) | address candidates | `POST /standardizovane-adresy/vyhledat` | US4 |
| 7 | `search_notification_batches` | `filter`, `start`, `count` | batch list | `POST /ekonomicke-subjekty-notifikace/vyhledat` | US5 |
| 8 | `get_notification_batch` | `data_source`, `batch_number` | batch content | `GET /ekonomicke-subjekty-notifikace/datovy-zdroj/{ds}/cislo-davky/{n}` | US5 |

Coverage count: 1 + 1 + 10 + 10 + 1 + 1 + 1 + 1 = 26. All ten registers (`vr`, `res`, `rzp`, `nrpzs`, `rpsh`, `rcns`, `szr`, `rs`, `ros`, `ceu`) have both a lookup and a search operation. The contract test MUST assert that every operation in the ARES OpenAPI document is reachable through one of these tools (SC-004).

## Behaviour rules (all tools)

- `register` and `batch_number` are accepted as strings, with the valid values stated in the parameter description, and validated inside the tool so that a bad value returns `[invalid_input]` (constitution Principle III).
- `ico` is normalised per FR-008 before any call.
- `count` defaults to 20 and is rejected above the configured maximum (default 100).
- ARES does not page `search_notification_batches`; the server pages that list locally.
- `search_addresses` always sends `typStandardizaceAdresy` (default `VYHOVUJICI_ADRESY`), which ARES requires.
- A successful search with zero matches returns `total: 0`, `items: []`; it is not an error.
- `get_register_record` for an IČO absent from that register returns `not_found` with a message naming the register. A follow-up `get_entity` tells the caller whether the entity exists at all.
- Tool descriptions state what the tool does, in plain language, with one example input.
- The `filter` schema for each search mirrors the ARES request schema. Exact property lists are generated from the OpenAPI document during implementation and verified by a contract test.
