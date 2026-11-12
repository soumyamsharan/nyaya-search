## Purpose

Lets a lawyer find relevant Supreme Court judgments by describing the facts and legal issue in plain words, by exact phrase, or by citation, and shows which paragraph matched.

## ADDED Requirements

### Requirement: Fact-pattern search
The system SHALL accept a free-text description of facts and legal issue (up to 2,000 characters) and return up to 10 judgments ranked by relevance, combining keyword and semantic matching and a final reranking step. Results SHALL be grouped by judgment, so one judgment appears at most once.

#### Scenario: Plain-language query
- **WHEN** a user searches "cheque dishonoured, demand notice sent but never received, is the Section 138 complaint maintainable"
- **THEN** the system returns up to 10 distinct judgments ordered by relevance

#### Scenario: Query too long
- **WHEN** a query exceeds 2,000 characters
- **THEN** the system rejects it with a clear message and does not run the search

#### Scenario: Empty query
- **WHEN** a user submits an empty or whitespace-only query with no filters
- **THEN** the system returns a validation message and no results

### Requirement: Matching paragraph in results
Each search result SHALL show the case title, date, bench, primary citation, and the paragraph that best matched the query, with its display label and a link that opens the judgment at that paragraph.

#### Scenario: Result shows matched paragraph
- **WHEN** a result is returned
- **THEN** it includes the best-matching paragraph's text (or an excerpt) and label, e.g. "¶14"

#### Scenario: Jump to paragraph
- **WHEN** the user opens a result's matched paragraph link
- **THEN** the judgment view opens scrolled to that paragraph with it highlighted

### Requirement: Phrase search
The system SHALL treat text inside double quotes as an exact phrase that a matching paragraph must contain.

#### Scenario: Quoted phrase
- **WHEN** a user searches `"no longer good law" eviction`
- **THEN** every returned judgment contains the exact phrase "no longer good law" in at least one paragraph

### Requirement: Filters
The system SHALL let users restrict results by decision year range, judge name on the bench, and Act/section mentioned; filters SHALL apply before ranking.

#### Scenario: Year filter
- **WHEN** a user searches with years 2020–2022
- **THEN** every result has a decision date within 2020–2022

#### Scenario: Act and section filter
- **WHEN** a user filters by "Negotiable Instruments Act, Section 138"
- **THEN** every result mentions that Act and section

### Requirement: Search by citation
The system SHALL recognise a query that is a reported or neutral citation (for example "(2019) 5 SCC 123" or "2024 INSC 512") and return the matching judgment directly.

#### Scenario: Known citation
- **WHEN** a user searches a citation that belongs to a judgment in the corpus
- **THEN** that judgment is returned as the only result

#### Scenario: Citation not in corpus
- **WHEN** a user searches a well-formed citation that is not in the corpus
- **THEN** the system says the judgment is not in the corpus and does not show unrelated results as if they matched

### Requirement: No results
When nothing passes a minimum relevance threshold, the system SHALL say no relevant judgment was found rather than return weak matches without comment.

#### Scenario: Off-topic query
- **WHEN** a user searches for something the corpus does not cover
- **THEN** the system shows a "no relevant judgments found" message

### Requirement: Search latency
Fact-pattern search SHALL return results within 3 seconds at the 95th percentile on the deployed site, measured at the API with up to 3 concurrent users.

#### Scenario: Latency measured
- **WHEN** the eval queries are run against the deployed API
- **THEN** the measured p95 search latency is under 3 seconds and is reported

### Requirement: Search queries are not shared or stored
Search query text SHALL NOT be sent to any third-party service (it is processed only on our own server), and SHALL NOT be stored; logs SHALL record only metadata (timestamp, latency, result count, filters used).

#### Scenario: Query not persisted
- **WHEN** a search completes
- **THEN** no database row or log line contains the query text

### Requirement: Rate limiting
The API SHALL limit search and question requests per client IP and respond with HTTP 429 when the limit is exceeded.

#### Scenario: Burst of requests
- **WHEN** one IP exceeds the configured request rate
- **THEN** further requests receive 429 until the window resets
