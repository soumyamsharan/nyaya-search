## Purpose

Keeps search useful when users misspell words or judge names: suggests corrections from the corpus's own vocabulary, tolerates small typos in keyword matching, and matches judge names approximately.

## ADDED Requirements

### Requirement: Spelling suggestion
When a search query contains words of four or more letters that occur fewer than three times in the corpus, the system SHALL suggest a corrected query in which each such word is replaced by the most frequent corpus word within two edits, when one exists. Operators (AND, OR, NOT), quotation marks and other words SHALL be kept as typed. The suggestion SHALL be returned with the results and SHALL NOT replace the user's query unless they choose it.

#### Scenario: Misspelled words
- **WHEN** a user searches `tennant evicton arears of rent`
- **THEN** the response suggests `tenant eviction arrears of rent`

#### Scenario: Misspelled word inside a phrase
- **WHEN** a user searches `"demand notise" cheque`
- **THEN** the response suggests `"demand notice" cheque`

#### Scenario: Correct spelling
- **WHEN** every word of the query is common in the corpus
- **THEN** no suggestion is returned

#### Scenario: Citation query
- **WHEN** the query is a citation
- **THEN** no suggestion is computed

### Requirement: Typo-tolerant keyword matching
When a query contains unknown words (as defined above), keyword matching SHALL accept words within one edit of each query word. Queries whose words are all known SHALL be matched exactly as before. Quoted phrases and words required or excluded by AND or NOT SHALL still match exactly.

#### Scenario: Short query with several typos
- **WHEN** a user searches `tennant evicton arears of rent`
- **THEN** results are returned, about tenancy and eviction

#### Scenario: Correct query unchanged
- **WHEN** a user searches a correctly spelled query
- **THEN** keyword matching is exact, and results are the same as without this feature

### Requirement: Judge list
The API SHALL list every judge who appears on a bench in the corpus, with the number of judgments, for use as suggestions.

#### Scenario: Judge list
- **WHEN** a client requests the judge list
- **THEN** it receives judge names sorted by name, each with a judgment count

### Requirement: Tolerant judge and author filters
The judge and author filters SHALL match a name when it is contained in the stored name (case-insensitive), or, for inputs of five or more letters, when it closely resembles a word sequence in the stored name (trigram word similarity of at least 0.5).

#### Scenario: Misspelled judge
- **WHEN** a user filters by judge `Pardivala`
- **THEN** results include judgments with Justice J.B. Pardiwala on the bench

#### Scenario: Short input stays exact
- **WHEN** a user filters by author `Oka`
- **THEN** only names containing "Oka" match

### Requirement: Suggestions in the UI
The search page SHALL show the suggestion as a "Did you mean" link that runs the corrected query, and SHALL offer judge names as autocomplete in the Judge and Author fields.

#### Scenario: Click the suggestion
- **WHEN** a user clicks "Did you mean: tenant eviction arrears of rent"
- **THEN** that query runs, with the same filters

#### Scenario: Autocomplete
- **WHEN** a user starts typing a judge's name in the Judge field
- **THEN** matching judge names are offered
