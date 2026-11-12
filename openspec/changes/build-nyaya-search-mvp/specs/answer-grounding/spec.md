## Purpose

Guarantees that every piece of generated text a lawyer sees can be traced to a real paragraph in the corpus, because one invented citation destroys trust in a legal research tool.

## ADDED Requirements

### Requirement: No invented judgments or citations
The system SHALL display only judgments that exist in the corpus. Case names and citations shown anywhere SHALL come from stored metadata and SHALL NOT be taken from language-model output.

#### Scenario: Model mentions an outside case
- **WHEN** generated text names a case or citation that is not one of the paragraphs supplied to it
- **THEN** that sentence is removed before display

### Requirement: Every generated sentence cites a supplied paragraph
Generated breakdowns and answers SHALL be produced only from paragraphs supplied with the request, and every sentence SHALL reference at least one of those paragraphs by id. Sentences with no reference, or whose references are not among the supplied paragraphs, SHALL be removed before display.

#### Scenario: Uncited sentence
- **WHEN** the model returns a sentence without a paragraph reference
- **THEN** the sentence is not shown

#### Scenario: Reference to a paragraph not supplied
- **WHEN** a sentence cites a paragraph id that was not in the supplied context
- **THEN** the sentence is not shown

### Requirement: Support check
Each remaining sentence SHALL be checked for support against the paragraphs it cites, and sentences that fall below a configured support score SHALL be removed before display. The number of removed sentences SHALL be recorded in metadata logs.

#### Scenario: Unsupported claim
- **WHEN** a sentence cites ¶12 but ¶12 does not support it
- **THEN** the sentence is removed

#### Scenario: Everything removed
- **WHEN** every sentence of an answer is removed by the checks
- **THEN** the system shows that it could not find a supported answer, not an empty or partial answer

### Requirement: Generated text is marked
Generated breakdowns and answers SHALL be visibly marked as machine-generated, with a note that results are research aids and the advocate must read the judgment before citing it.

#### Scenario: Notice shown
- **WHEN** a breakdown or answer is displayed
- **THEN** a machine-generated label and the research-aid note are visible

### Requirement: Disclosure of data sent to the model provider
The system SHALL send to the external language-model provider only judgment paragraphs and, for follow-up questions, the user's question text. The UI SHALL tell users, next to the question box, that the question is sent to an external model provider, and question text SHALL NOT be stored.

#### Scenario: Question box notice
- **WHEN** a user views the follow-up question box
- **THEN** a notice says the question is processed by an external model provider and not stored

#### Scenario: Question not persisted
- **WHEN** a follow-up question is answered
- **THEN** no database row or log line contains the question text

### Requirement: Generated text is rendered as plain text
Model output SHALL be rendered as text, never as HTML or executable markup.

#### Scenario: Markup in model output
- **WHEN** the model output contains HTML or script tags
- **THEN** they are displayed as literal text and not executed
