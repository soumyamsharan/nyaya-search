## Why

Misspellings break search in ways lawyers won't expect. On the live site, `tennant evicton arears of rent` found nothing, `"demand notise"` found nothing, and the judge filter `Pardivala` found nothing, even though the corpus has many matching judgments. Plain-language queries with one or two typos already work through semantic search; short queries with several typos, keyword matching and the name filters do not.

## What Changes

- **Did you mean:** when a query contains words the corpus doesn't know, search suggests a corrected query, built from the corpus's own vocabulary, that the user can run with one click. The suggestion is never applied silently.
- **Fuzzy keyword matching:** when a query contains unknown words, keyword (BM25) retrieval tolerates one-letter differences per word. Correctly spelled queries are unchanged. Quoted phrases, AND and NOT stay exact; the suggestion corrects them.
- **Judge names:** a list of judges (`GET /v1/judges`) powers autocomplete in the Judge and Author fields, and both filters accept close misspellings of a name.
- **Pipeline:** a `vocabulary` stage builds the word list with frequencies from all paragraphs.

## Capabilities

### New Capabilities

- `typo-tolerance`: Spelling suggestions, typo-tolerant keyword matching, and tolerant judge and author filters with a judge list.

### Modified Capabilities

(none: earlier capabilities are not archived yet; this is a separate capability)

## Impact

- **Database:** migration 004 adds the `pg_trgm` extension, a `vocabulary` table with a trigram index, and trigram indexes for judge-name matching. `fuzzystrmatch` is already present.
- **API:** search responses gain an optional `suggestion`; new `GET /v1/judges`.
- **Web:** a "Did you mean" link above results, and autocomplete on the Judge and Author fields.
- **Hosting:** the Space's database dump must be republished after the vocabulary is built, and the Space rebuilt.
