## ADDED Requirements

### Requirement: Corpus scope is stated
The corpus SHALL contain Supreme Court of India judgments decided in 2024, 2025 and 2026. High Court judgments are not included.
Search with a date range entirely outside those years SHALL return no results with a message saying so.

#### Scenario: Date range before the corpus
- **WHEN** a user searches with decision dates between 2000 and 2023
- **THEN** no results are shown and the page says no relevant judgments were found

#### Scenario: Date range within the corpus
- **WHEN** a user searches with decision dates between 2024 and 2026
- **THEN** results come from the corpus
