## Purpose

Shows which paragraphs refer to earlier cases, and makes each citation inside a paragraph visible and, where possible, clickable.

## ADDED Requirements

### Requirement: Cites-cases paragraphs
A paragraph SHALL be marked as citing cases when it contains a recognised citation, a "X v. Y" case name, "(supra)", or a "[See: …]" reference. The judgment view SHALL offer a "Cites cases only" toggle that shows only such paragraphs, combined with any role chips.

#### Scenario: Paragraph with a short reference
- **WHEN** a paragraph reads "[See: Balraj Taneja v. Sunil Madan, (1999) 8 SCC 396]"
- **THEN** it is marked as citing cases and appears under "Cites cases only"

#### Scenario: Paragraph without references
- **WHEN** a paragraph only states the court's own reasoning
- **THEN** it is not shown under "Cites cases only"

### Requirement: Inline citation annotation
Each citation found in a paragraph SHALL be highlighted where it appears in the text. If the cited judgment is in the corpus, the highlight SHALL link to it and show its title on hover; otherwise it SHALL be marked as not in the corpus.

#### Scenario: Citation in the corpus
- **WHEN** a paragraph cites "(2000) 7 SCC 120" and that judgment is in the corpus
- **THEN** the citation is a link to that judgment

#### Scenario: Citation outside the corpus
- **WHEN** a paragraph cites "AIR 1946 Mad 151"
- **THEN** the citation is highlighted and marked "not in the Nyaya Search corpus"

### Requirement: Broader citation formats
The system SHALL recognise AIR High Court reports (e.g. "AIR 1946 Mad 151"), Delhi Law Times (e.g. "(2000) 84 DLT 337") and English reports (e.g. "(1876) 3 Ch D 637", "[1990] 1 AC 109").

#### Scenario: English report
- **WHEN** a paragraph cites "(1876) 3 Ch D 637"
- **THEN** the citation is recognised and highlighted

### Requirement: Quoted numbering does not split paragraphs
When a judgment quotes another court's judgment with that court's own paragraph numbers, the quoted run SHALL stay inside the quoting paragraph, and the judgment's own numbering SHALL resume after it.

#### Scenario: Quoted High Court paragraphs
- **WHEN** the judgment's paragraph 29 quotes a High Court's paragraphs 13 to 29 and then resumes with its own paragraph 30
- **THEN** the judgment has its own paragraphs 13 through 48 with no paragraph merged into 29
