## 1. Paragraph roles

- [x] 1.1 `core/src/nyaya/roles.py`: Role enum and rule-based `assign_roles`, with unit tests for each spec scenario and for determinism
- [x] 1.2 Migration 003: `paragraphs.role` with an index
- [x] 1.3 `pipeline roles` stage (also run by `pipeline all`) writing only changed roles and reporting counts per role; run it on the corpus
- [x] 1.4 Expose `role` on paragraphs in `GET /v1/judgments/{id}`
- [x] 1.5 Spot-check 40 random paragraphs and record agreement in test-scenarios.md

## 2. Query language and filters

- [x] 2.1 Parse AND / OR / NOT and phrases into required, excluded and free-text terms, with unit tests
- [x] 2.2 One SQL helper for required and excluded terms used by both retrievers, replacing the separate phrase handling
- [x] 2.3 `SearchFilters` and `filter_sql`: date range, author, several judges, outcome mapping, roles
- [x] 2.4 API parameters and validation (repeatable `judge` and `role`, enums, dates, only-excluded query → 422), with API tests
- [x] 2.5 Integration tests against the live corpus for each search-query-language scenario

## 3. Web

- [x] 3.1 Search page: date, author, outcome and "Match in" fields; several judges; operators hint
- [x] 3.2 Judgment page: role tags, role filter chips reflected in the URL, machine-assigned note
- [x] 3.3 Build, lint, and verify both features in the browser
