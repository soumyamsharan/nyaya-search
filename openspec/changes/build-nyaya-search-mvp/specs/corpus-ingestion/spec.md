## Purpose

Turns the open Supreme Court judgments dataset into a searchable corpus of judgments split into stable, citable paragraphs, with metadata and an ingestion quality report.

## ADDED Requirements

### Requirement: Acquire judgments from the open dataset
The system SHALL obtain judgment PDFs and their metadata only from the open Indian Supreme Court Judgments dataset, selectable by year range, without scraping any website. Re-running acquisition for a year range SHALL fetch only files not already present.

#### Scenario: Sync a year range
- **WHEN** the operator runs acquisition for years 2023–2025
- **THEN** PDFs and metadata for judgments dated in those years are stored locally and judgments outside the range are not fetched

#### Scenario: Re-run is incremental
- **WHEN** acquisition runs again for a year range that was already synced
- **THEN** no already-present file is downloaded again

### Requirement: Stable paragraph identity
The system SHALL split each judgment into an ordered list of paragraphs. Each paragraph SHALL carry the judgment's id, a sequence number unique within the judgment, and a display label (the paragraph number printed in the judgment when one exists). Ingesting the same PDF again with the same extractor version SHALL produce identical paragraph ids, labels and text.

#### Scenario: Numbered paragraphs keep their printed numbers
- **WHEN** a judgment prints paragraphs numbered 1 to 42
- **THEN** the stored paragraphs have display labels "1" to "42" in order

#### Scenario: Numbering restarts in a separate opinion
- **WHEN** a concurring opinion restarts paragraph numbering at 1
- **THEN** every paragraph still has a unique sequence number within the judgment and the display label identifies the opinion as well as the number, so two paragraphs never share a label

#### Scenario: Unnumbered judgment
- **WHEN** a judgment has no printed paragraph numbers
- **THEN** paragraphs are split on text structure, given derived labels, and marked as derived so the UI can say the numbering is not from the original

#### Scenario: Re-ingestion is deterministic
- **WHEN** a judgment already in the corpus is ingested again with the same extractor version
- **THEN** its paragraph ids, labels and text are unchanged

### Requirement: Clean judgment text
The system SHALL remove running headers, footers and page numbers from extracted text so they do not appear inside paragraphs.

#### Scenario: Page furniture removed
- **WHEN** a judgment's PDF repeats a header and a page number on every page
- **THEN** no stored paragraph contains that header or page number

### Requirement: Reporter front matter kept separate from the judgment
Where a PDF opens with reporter-prepared front matter (issue for consideration, headnotes, case law cited, list of Acts, keywords, appearances), the system SHALL store that front matter separately, marked as prepared by the reporter, and SHALL NOT number it as judgment paragraphs.

#### Scenario: Digital SCR judgment
- **WHEN** a PDF contains a "Headnotes" section before the court's judgment begins
- **THEN** the headnotes are stored as reporter front matter and paragraph 1 of the judgment is the court's first paragraph

#### Scenario: Case law cited captured
- **WHEN** the front matter lists cases cited with parallel citations (for example an SCR citation and an SCC citation for the same case)
- **THEN** each listed case and all its citations are stored for citation resolution

### Requirement: Judgment metadata
The system SHALL store for each judgment: case title, decision date, bench (judge names), reported citations, and the Acts and sections it mentions. Fields that cannot be determined SHALL be left empty rather than guessed.

#### Scenario: Metadata available for filtering
- **WHEN** a judgment is ingested
- **THEN** its title, date, bench, citations and mentioned Acts/sections are stored and usable by search filters

#### Scenario: Unknown field stays empty
- **WHEN** the bench cannot be determined from the dataset metadata or the text
- **THEN** the bench field is empty and the judgment is still ingested

### Requirement: Scanned pages are flagged, not OCR'd
The system SHALL flag judgments whose pages yield too little extractable text, and SHALL NOT run OCR in this version.

#### Scenario: Scanned judgment
- **WHEN** most pages of a PDF yield almost no text
- **THEN** the judgment is marked as scanned and excluded from the search index, and it appears in the ingestion report

### Requirement: Per-document idempotent pipeline
Each ingestion stage SHALL be re-runnable for a single judgment or for the whole corpus, and a failure on one judgment SHALL NOT stop the others.

#### Scenario: One bad PDF
- **WHEN** one PDF in a batch is corrupt
- **THEN** that judgment is recorded as failed with a reason and the rest of the batch completes

### Requirement: Ingestion quality report
Each ingestion run SHALL report counts of judgments processed, failed, flagged as scanned, duplicates, and empty paragraphs, and SHALL exit with a failure status when the failure share exceeds a configured threshold.

#### Scenario: Run summary
- **WHEN** an ingestion run finishes
- **THEN** it prints and saves the counts above

#### Scenario: Too many failures
- **WHEN** more than the configured share of judgments fail extraction
- **THEN** the run exits with a non-zero status

### Requirement: Dataset attribution
The system SHALL credit the dataset maintainers and its CC-BY-4.0 licence in the web UI footer and the README.

#### Scenario: Attribution visible
- **WHEN** any page of the web UI is shown
- **THEN** the footer names the dataset and its licence
