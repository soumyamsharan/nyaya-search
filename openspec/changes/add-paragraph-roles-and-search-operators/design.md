## Context

Builds on `build-nyaya-search-mvp` (see its design.md for the stack). See proposal.md for motivation and specs/ for behaviour. Paragraphs are already stored with stable `(judgment_id, seq)` and printed labels; search filters already compile to parameterised SQL in `core/src/nyaya/search.py::filter_sql`.

## Goals / Non-Goals

**Goals:** role labels that are explainable and cheap to recompute; operators that behave the same on both keyword and semantic retrieval; no new services.

**Non-Goals:** ML role classification (a later upgrade), nested Boolean expressions with parentheses, proximity operators, a court filter (one court only today).

## Decisions

### 1. Rule-based role labelling in `core/src/nyaya/roles.py`
- **How it works:** a pure function `assign_roles(texts) -> roles` checks rules in this order, so the first match wins:
  1. **Conclusion:** last 20% of paragraphs, with a disposal cue (allowed, dismissed, set aside, no order as to costs, pending applications…).
  2. **Arguments:** counsel cue plus side: appellant/petitioner/complainant → petitioner_argument; respondent/State/accused-respondent → respondent_argument. "Per contra" means the respondent.
  3. **Issue:** "question(s)… for consideration", "issue(s) that arise", "point for determination".
  4. **Statute:** quotation cue ("reads as under", "is extracted") with a section number, or mostly quoted text that starts with a section heading.
  5. **Precedent:** a citation or "X v. Y" together with a holding verb (held, observed, ruled).
  6. **Default by position:** before the first argument or issue paragraph → facts; otherwise → reasoning.
- **Why rules:** they are instant, deterministic, free and explainable. An ML model would need a download through the proxy, licence checks and evaluation. The function signature lets a model replace it later.
- **Alternative rejected for now:** LLM labelling of 71k paragraphs (days of calls locally or on the free tier).

### 2. Storage and pipeline
- **Storage:** migration 003 adds `paragraphs.role text` with an index.
- **Pipeline:** `pipeline roles` recomputes all judgments in seconds and reports counts per role, and `pipeline all` runs it after extract. Re-running is idempotent; only changed values are written.

### 3. Query language in `core/src/nyaya/text.py::parse_query`
- **Tokens:** quoted phrases and words. `AND` marks its neighbours as required; `NOT` marks the next token as excluded; `OR` is dropped (OR is the default).
- **Parsed query:** `ParsedQuery` gains `required: list[str]` and `excluded: list[str]`. `free_text` keeps every non-excluded word for ranking. Phrases stay required, as today.
- **Retrievers:** both get the same SQL conditions from one helper. Each required term must appear in the paragraph, and each excluded term must not, using a case-insensitive whole-word or phrase regex (`~*` with `\m…\M`). Terms are passed as parameters and regex-escaped in Python. This replaces the separate phrase handling, so BM25 and vector search can never disagree.
- **Only exclusions:** a query with only excluded terms is invalid (422).

### 4. Filters in `SearchFilters` and `filter_sql`
- **New fields:** `date_from`, `date_to` (date), `author` (ILIKE on `j.author`), `judges: list[str]` (each must match some bench member), `outcome` (enum, mapped to raw `disposal_nature` values in one dict), `roles: list[Role]` (`p.role = ANY(...)`).
- **Compatibility:** the existing single `judge` stays as an alias, so old links keep working.
- **API:** query parameters `judge` and `role` are repeatable. Validation uses Pydantic enums and dates, so unknown values become 422 in the existing error format.

### 5. Web
- **Search page:**
  - adds date from/to, an author field, an outcome select, and a "Match in" select (Anywhere / Court's reasoning & conclusion / Arguments / Facts & issues)
  - the Judge field takes commas for several judges
  - a one-line operators hint
- **Judgment page:**
  - a role tag on each paragraph
  - a row of role chips that filter the paragraph list, with a "Show all" option
  - a note that roles are machine-assigned
- **URLs:** role chips are reflected in the URL, so a filtered view can be shared.

## Risks / Trade-offs

- **[Rule accuracy, especially facts versus reasoning]** → Labels are marked machine-assigned. A spot check of 40 random paragraphs is recorded in test-scenarios.md, and the ML upgrade is documented.
- **[Regex filters on large candidate sets are slower]** → They only apply when operators are used. The candidate limit stays at 100 per retriever.
- **[Outcome data is missing for about 8% of judgments (empty disposal)]** → These fall under "other". The filter description says outcome comes from the dataset's metadata.
- **[Operator ambiguity]** → Only upper-case words are operators, which is documented in the search hint.
