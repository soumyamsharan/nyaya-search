## ADDED Requirements

### Requirement: Loading feedback on buttons
A button that waits on a request SHALL show a spinner and a short label such as "Searching…" while it waits, and SHALL NOT
be pressable again until the request finishes.

#### Scenario: Asking a question
- **WHEN** a user presses Ask and the answer is pending
- **THEN** the button shows a spinner and "Answering…"

### Requirement: Placeholders while content loads
Results, judgments, statute pages and provisions SHALL show placeholder shapes resembling their content while loading,
instead of a bare loading line.

#### Scenario: Judgment loading
- **WHEN** a user opens a judgment that has not loaded yet
- **THEN** placeholder title and paragraph shapes are shown

### Requirement: Session cache for read-only data
Read-only responses (search results, judges, statutes, judgments, citations, breakdowns, provisions) SHALL be kept in memory
for the browser session, with a time limit per kind. Going Back to a page already loaded SHALL show it without repeating the
request. Failed requests SHALL NOT be cached. Shared notes and LLM questions SHALL NOT be cached.

#### Scenario: Going back to results
- **WHEN** a user opens a judgment from search and then goes Back
- **THEN** the results appear without a new search request

#### Scenario: Question is never reused
- **WHEN** a user asks the same question twice
- **THEN** each question is sent to the model

### Requirement: Prefetch on hover
When a user hovers over or focuses a search result, the judgment and its citations SHALL be requested in advance.

#### Scenario: Hover before click
- **WHEN** a user hovers over a result and then clicks it
- **THEN** the judgment opens with its data already requested
