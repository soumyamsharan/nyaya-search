## Context

See proposal.md. Keyword retrieval uses pg_search (`|||`), and filters compile in `core/src/nyaya/search.py::filter_sql`. The ParadeDB image ships `pg_trgm` and `fuzzystrmatch`, and pg_search supports `paradedb.match(field, query, distance => n)`.

## Goals / Non-Goals

**Goals:** fix typos without changing results for correctly spelled queries; never auto-replace the user's query; reuse what Postgres already provides.

**Non-Goals:** typos in citations (a mistyped citation can be a different real case); phonetic or transliteration matching (Hindi names in Latin script); language-model spelling correction.

## Decisions

### 1. Vocabulary from the corpus
- **Table:** `vocabulary(word, freq)`, built by `pipeline vocabulary` with one SQL pass: lower-case alphabetic tokens of 3–30 letters, frequency ≥ 2. It has a GIN trigram index.
- **Known word:** freq ≥ 3. **Candidate correction:** freq ≥ 5.
- **Why the corpus, not a dictionary:** legal vocabulary (superannuation, compoundable, quash) and Indian names come for free, and every suggestion is a word that exists in the judgments.

### 2. Corrections (`core/src/nyaya/spelling.py`)
- **Which words:** for each unknown word of ≥ 4 letters, find candidates sharing trigrams (`word % $1`) within Levenshtein distance ≤ 2. Choose by smallest distance, then highest frequency.
- **Rewriting:** the corrected query rewrites only the misspelled tokens in the raw text, so operators, quotes and other words stay as typed.
- **Cost:** one indexed query per unknown word; queries rarely contain more than a few.

### 3. Fuzzy BM25 only when needed
- **When:** `SearchService` marks the parsed query `fuzzy` when it has unknown words. `Bm25Retriever` then uses `p.id @@@ paradedb.match('text', q, distance => 1)` instead of `p.text ||| q`.
- **Always exact:** required, excluded and phrase terms keep using the exact regex conditions.
- **Correct queries:** take the original path, so eval numbers and behaviour are unchanged.

### 4. Judges
- **List:** `GET /v1/judges` returns distinct `unnest(bench)` names with counts. It's small (about 50 names), so the web app loads it once into a `<datalist>`.
- **Tolerant filters:** `b ILIKE %x% OR (length(x) >= 5 AND word_similarity(x, b) >= 0.5)`. For example, word_similarity('pardivala', 'J.B. Pardiwala') = 0.54. The length rule keeps short inputs like "Oka" exact.

### 5. API and web
- **API:** `SearchResponse.suggestion: str | None`, and `GET /v1/judges` with the rate limit.
- **Web:** a "Did you mean:" link that navigates to the suggested query with the current filters, and `<datalist>` autocomplete on the Judge and Author fields.

## Risks / Trade-offs

- **[A rare but correct word gets a suggestion]** → It's only a suggestion, never applied automatically.
- **[Fuzzy matching broadens keyword results]** → It's only used when unknown words are present, and the reranker still orders the final results.
- **[Vocabulary must be rebuilt after ingestion]** → `pipeline all` runs it, and the Space dump is republished.
