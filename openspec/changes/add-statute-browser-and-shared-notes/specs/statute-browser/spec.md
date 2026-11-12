## Purpose

Lets users start from a provision of law and see the judgments that interpret it, with the paragraph where each refers to it.

## ADDED Requirements

### Requirement: Act and section index
The system SHALL list the Acts that the corpus's judgments refer to, each with the number of judgments and the sections referred to.

#### Scenario: Browse Acts
- **WHEN** a user opens the statute index
- **THEN** Acts are listed by name with judgment counts, most referred-to first

### Requirement: Section page
The system SHALL show, for an Act and section, every judgment that refers to that section, with the referring paragraph (its ¶ label and text) and a link to the judgment.

#### Scenario: Section 138 of the NI Act
- **WHEN** a user opens Section 138 of the Negotiable Instruments Act, 1881
- **THEN** each judgment that refers to Section 138 is listed with the paragraph where it does so

#### Scenario: Section with no judgments
- **WHEN** a user opens a section that no judgment in the corpus refers to
- **THEN** the page says no judgments refer to it

### Requirement: Link from judgments
Each section referred to in a judgment's text SHALL link to its section page.

#### Scenario: Section mentioned in a judgment
- **WHEN** a judgment's paragraph refers to Section 138 of the NI Act
- **THEN** that reference links to the statute page for Section 138 of the NI Act

### Requirement: Accurate matching
A judgment SHALL be listed on a section page only when the section is referred to alongside the Act name in the same sentence. Judgments whose Act name cannot be matched SHALL NOT be guessed.

#### Scenario: Similar section numbers
- **WHEN** a judgment refers to Section 1380 and the user opens Section 138
- **THEN** that judgment is not listed for Section 138
