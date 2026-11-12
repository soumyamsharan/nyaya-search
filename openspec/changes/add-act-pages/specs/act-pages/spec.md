## Purpose

Lets users see every judgment that refers to an Act, and understand what the Act is, with an official source.

## ADDED Requirements

### Requirement: Act page lists judgments for any section
The system SHALL show, for an Act, every judgment that refers to any section of that Act, newest first, with the sections each
judgment refers to. The list SHALL be paginated at 25 judgments per page.

#### Scenario: Act with judgments referring to other sections
- **WHEN** a user opens the Negotiable Instruments Act page
- **THEN** judgments that refer only to other sections (for example Section 141) are included, each showing its sections

#### Scenario: Second page
- **WHEN** an Act has more than 25 judgments and the user chooses the next page
- **THEN** the next 25 judgments are shown in the same order

### Requirement: About this Act
The Act page SHALL show the Act's name, year and official source link. For Acts in the curated list, it SHALL also show a
plain-language description, the name of the reviewer and the date reviewed. Acts not in the curated list SHALL show the
name and source link only, without a description.

#### Scenario: Curated Act
- **WHEN** a user opens a curated Act
- **THEN** the description, reviewer, review date and official source link are shown

#### Scenario: Uncurated Act
- **WHEN** a user opens an Act that is not curated
- **THEN** only its name, year and official source link are shown, and no description is invented

### Requirement: Descriptions stay factual
Descriptions SHALL describe only what the Act governs, in one to three sentences, and SHALL NOT state how courts have
interpreted it.

#### Scenario: Description content
- **WHEN** a curated description is reviewed
- **THEN** it names what the Act governs and contains no statement about any judgment

### Requirement: Links to Act names
Act names in the statute index, section pages and judgment text SHALL link to the Act page.

#### Scenario: Act name in a judgment
- **WHEN** a judgment's paragraph names the Negotiable Instruments Act
- **THEN** the name links to the Act page
