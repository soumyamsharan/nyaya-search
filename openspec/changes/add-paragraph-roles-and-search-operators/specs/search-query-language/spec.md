## Purpose

Gives precise control over search: Boolean keyword operators, restricting matches to chosen paragraph roles, and filters for decision date, author judge, bench and outcome.

## ADDED Requirements

### Requirement: Boolean operators
Search SHALL treat the upper-case words AND, OR and NOT as operators: terms joined by AND must all appear in the matching paragraph; OR between terms means either may appear (the default between plain words); a term or quoted phrase after NOT must not appear in the matching paragraph. Lower-case "and", "or" and "not" SHALL be treated as ordinary words. Operators SHALL constrain both keyword and semantic matching.

#### Scenario: AND requires both terms
- **WHEN** a user searches `cheque AND dishonour`
- **THEN** every result's matched paragraph contains both "cheque" and "dishonour"

#### Scenario: NOT excludes a term
- **WHEN** a user searches `bail NOT anticipatory`
- **THEN** no result's matched paragraph contains "anticipatory"

#### Scenario: NOT with a phrase
- **WHEN** a user searches `eviction NOT "bona fide requirement"`
- **THEN** no matched paragraph contains the phrase "bona fide requirement"

#### Scenario: Lower-case words are not operators
- **WHEN** a user searches `notice not received`
- **THEN** "not" is searched as a word and nothing is excluded

#### Scenario: Only operators
- **WHEN** a query contains only operators and excluded terms (for example `NOT bail`)
- **THEN** the system asks for at least one term to search for

### Requirement: Search within chosen roles
Search SHALL accept one or more paragraph roles and match only paragraphs with those roles.

#### Scenario: Match only in reasoning and conclusion
- **WHEN** a user searches with roles reasoning and conclusion
- **THEN** every result's matched paragraph has role reasoning or conclusion

### Requirement: Decision date range
Search SHALL accept an exact from-date and to-date and return only judgments decided within that range (inclusive).

#### Scenario: Date range
- **WHEN** a user searches with dates 2025-01-01 to 2025-03-31
- **THEN** every result was decided within that range

### Requirement: Author judge
Search SHALL accept an author judge and return only judgments written by that judge (partial, case-insensitive name match).

#### Scenario: Author filter
- **WHEN** a user filters by author "Pardiwala"
- **THEN** every result's author name contains "Pardiwala"

### Requirement: Bench with several judges
Search SHALL accept one or more judge names and return only judgments whose bench includes all of them.

#### Scenario: Two judges on the bench
- **WHEN** a user filters by judges "Pardiwala" and "Mahadevan"
- **THEN** every result's bench includes both judges

### Requirement: Outcome
Search SHALL accept an outcome of allowed, partly_allowed, dismissed, disposed or other, mapped from the dataset's disposal values, and return only judgments with that outcome.

#### Scenario: Dismissed appeals only
- **WHEN** a user filters by outcome dismissed
- **THEN** every result's recorded disposal is a dismissal or rejection

### Requirement: Invalid filters rejected
The API SHALL reject unknown roles or outcomes, malformed dates, and a from-date after the to-date, with the standard error format.

#### Scenario: Unknown role
- **WHEN** a request asks for role "verdict"
- **THEN** the API responds 422 with code invalid_request
