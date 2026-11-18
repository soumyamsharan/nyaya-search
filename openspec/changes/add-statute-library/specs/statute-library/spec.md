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

### Requirement: Descriptions for curated statutes
A plain-language description SHALL appear only for statutes on the curated list, and only when one has been written for them.

#### Scenario: Uncurated statute
- **WHEN** a user opens a statute that is not curated
- **THEN** no description is shown

### Requirement: Accurate matching
A reference SHALL be attributed to an Act only when the Act name appears in the same sentence. Section, article and rule
numbers SHALL be matched exactly.

#### Scenario: Similar numbers
- **WHEN** a judgment refers to Article 210 and the user opens Article 21
- **THEN** that judgment is not listed for Article 21

### Requirement: Provision pages for every statute kind
Each provision (a section of an Act, a Constitution article, a rule, a regulation or a notification) SHALL have its own page
at a stable address of the form /provisions/{kind}/{key}/{slug}. The page SHALL list every judgment that refers to the
provision, newest first, with the paragraphs where it does so.

#### Scenario: Article 21
- **WHEN** a user opens Article 21 of the Constitution of India from a judgment
- **THEN** the page lists the judgments that refer to Article 21 with their referring paragraphs

#### Scenario: Provision with no judgments
- **WHEN** no judgment in the corpus refers to a provision
- **THEN** the page says so and does not invent a judgment

### Requirement: Related judgments for a provision
A provision page SHALL also list judgments that refer to other provisions of the same Act, nearest in meaning first, up to
eight. A judgment already listed as referring to the provision SHALL NOT appear as related.

#### Scenario: Related judgments
- **WHEN** a user opens Section 138 of the Negotiable Instruments Act
- **THEN** up to eight judgments that discuss other sections of that Act are listed, and each excerpt cites a section of that Act

### Requirement: Provision API
The API SHALL return a provision at GET /v1/provisions/{kind}/{key}/{slug}, with the referring judgments, the related
judgments, the India Code search link and the description if one is written. An unknown provision SHALL return 404, and an
unknown kind SHALL return 422.

#### Scenario: Unknown kind
- **WHEN** a client requests /v1/provisions/chapter/penal-code/1
- **THEN** the API responds 422

### Requirement: Act name abbreviations
Common abbreviations SHALL be matched to the Act they stand for: N.I. Act and NI Act to the Negotiable Instruments Act; IPC
to the Indian Penal Code; CrPC and Cr.P.C. to the Code of Criminal Procedure; CPC to the Code of Civil Procedure.

#### Scenario: N.I. Act in a judgment
- **WHEN** a judgment refers to Section 138 of the N.I. Act
- **THEN** the reference links to Section 138 of the Negotiable Instruments Act, not to a separate Act

