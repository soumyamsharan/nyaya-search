## Purpose

Makes a single judgment fast to read and cite: a paragraph-linked headnote-style breakdown, grounded follow-up questions, the original PDF and an exportable research note.

## ADDED Requirements

### Requirement: Judgment view
The system SHALL show a judgment's metadata (title, date, bench, citations, Acts/sections) and its full text as numbered paragraphs, each addressable by a stable link.

#### Scenario: Open a judgment
- **WHEN** a user opens a judgment
- **THEN** the page shows its metadata and all paragraphs with their display labels

#### Scenario: Derived numbering is labelled
- **WHEN** the judgment's paragraph numbers were derived rather than printed
- **THEN** the view says the numbering is not from the original judgment

### Requirement: Reporter headnotes
When a judgment has reporter-prepared front matter, the judgment view SHALL show it in a separate section labelled as prepared by the law reporter, not by the court, with any "[Para N]" references linked to those paragraphs.

#### Scenario: Reporter headnote shown
- **WHEN** a user opens a judgment that has reporter headnotes
- **THEN** the headnotes appear in their own labelled section and "[Para 27]" links to paragraph 27

### Requirement: Headnote-style breakdown
The system SHALL provide a breakdown of each judgment with sections Facts, Issues, Held and Ratio. Every line SHALL cite one or more paragraphs of that judgment and link to them. The breakdown SHALL be generated the first time it is requested and served from cache afterwards.

#### Scenario: First request
- **WHEN** a user opens the breakdown of a judgment with no cached breakdown
- **THEN** the system generates it, stores it, and shows it with paragraph links on every line

#### Scenario: Cached breakdown
- **WHEN** a breakdown already exists for the judgment and the current prompt version
- **THEN** it is shown without calling the language model

#### Scenario: Generation unavailable
- **WHEN** the language model provider fails or is rate-limited
- **THEN** the view shows the judgment text with a message that the breakdown is temporarily unavailable, and no partial or uncited breakdown is shown

### Requirement: Follow-up questions on one judgment
The system SHALL let a user ask a question about the open judgment and answer only from that judgment's paragraphs, with paragraph citations on every sentence. Questions SHALL be limited to 1,000 characters.

#### Scenario: Answerable question
- **WHEN** a user asks "What did the court hold on service of the demand notice?"
- **THEN** the answer cites the paragraphs it relies on, each linking into the judgment

#### Scenario: Question the judgment does not answer
- **WHEN** a user asks something the judgment does not address
- **THEN** the system says the judgment does not address it and gives no other answer

### Requirement: Original PDF
The judgment view SHALL link to the original PDF.

#### Scenario: Open source PDF
- **WHEN** the user clicks the PDF link
- **THEN** the original judgment PDF opens

### Requirement: Copy a paragraph with its citation
The system SHALL let the user copy any paragraph together with its pinpoint citation: the paragraph text in quotation marks, followed by "<case title>, <primary citation>, ¶<label>", where the title and citation are built only from stored metadata.

#### Scenario: Copy a paragraph with its citation
- **WHEN** the user copies paragraph 14
- **THEN** the clipboard holds paragraph 14's text followed by the case title, primary citation and "¶14"

### Requirement: Research-note export
The system SHALL let the user collect paragraphs from one or more judgments during a session and export them as a Markdown research note listing case title, citation, paragraph label and paragraph text, without requiring a login. The collection SHALL be kept only in the user's browser.

#### Scenario: Export a note
- **WHEN** the user has collected three paragraphs from two judgments and chooses Export
- **THEN** a Markdown file downloads with both cases, their citations and the three paragraphs with labels

#### Scenario: Nothing collected
- **WHEN** the user chooses Export with nothing collected
- **THEN** the system explains that the note is empty and downloads nothing
