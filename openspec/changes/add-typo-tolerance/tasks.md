## 1. Vocabulary and suggestions

- [x] 1.1 Migration 004: `pg_trgm`, `vocabulary(word, freq)` with a trigram index
- [x] 1.2 `pipeline vocabulary` stage (also in `pipeline all`); run it on the corpus
- [x] 1.3 `core/src/nyaya/spelling.py`: unknown-word detection and corrected query that keeps operators and quotes; unit tests
- [x] 1.4 `SearchResponse.suggestion`, computed for non-citation queries

## 2. Fuzzy keyword matching

- [x] 2.1 `ParsedQuery.fuzzy`, set by the search service when the query has unknown words
- [x] 2.2 BM25 retriever uses `paradedb.match(..., distance => 1)` when fuzzy, exact otherwise; required/excluded terms stay exact

## 3. Judges

- [x] 3.1 `GET /v1/judges` with counts
- [x] 3.2 Tolerant judge and author filters (ILIKE or word similarity ≥ 0.5 for inputs of 5+ letters)

## 4. Web and verification

- [x] 4.1 "Did you mean" link on the search page; judge and author autocomplete
- [x] 4.2 Unit, API and live integration tests for every scenario; lint and build
- [ ] 4.3 Republish the database dump and the Space; verify on the live site
