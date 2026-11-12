## Purpose

Lets users find every kind of law that judgments refer to, with the judgments for each and a link to the official source.

## ADDED Requirements

### Requirement: All statute kinds are captured
The system SHALL recognise references to Acts and Codes, Constitution articles, Rules, Regulations, and Notifications or
Ordinances in judgment text, and SHALL list the judgments for each.

#### Scenario: Constitution article
- **WHEN** a paragraph refers to Article 21 of the Constitution
- **THEN** the judgment appears on the Article 21 page

#### Scenario: Rule under its parent Act
- **WHEN** a paragraph refers to Order XII Rule 6 of the Code of Civil Procedure
- **THEN** the reference appears under the Code of Civil Procedure, as Order XII Rule 6

#### Scenario: Rule whose parent Act is not identified
- **WHEN** a paragraph refers to a rule without naming the Act it belongs to
- **THEN** it is not guessed to belong to any Act, and is listed under "Rules, parent not identified"

### Requirement: Official source link
Every statute page SHALL link to India Code's search results for the statute's name. The link SHALL NOT be produced by
automated collection of India Code item identifiers.

#### Scenario: Link to the official text
- **WHEN** a user opens any statute page
- **THEN** a "Find the official text on India Code" link opens India Code's search for that name, in a new window

### Requirement: Descriptions only when reviewed
A description SHALL appear only for statutes on the curated list, after review by a named reviewer on a stated date.

#### Scenario: Uncurated statute
- **WHEN** a user opens a statute that is not curated
- **THEN** no description is shown

### Requirement: Accurate matching
A reference SHALL be attributed to an Act only when the Act name appears in the same sentence. Section, article and rule
numbers SHALL be matched exactly.

#### Scenario: Similar numbers
- **WHEN** a judgment refers to Article 210 and the user opens Article 21
- **THEN** that judgment is not listed for Article 21
