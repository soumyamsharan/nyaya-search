## Purpose

Labels every paragraph of a judgment with the job it does (facts, issue, arguments, statute, precedent, reasoning, conclusion) so lawyers can read and search only the parts they need.

## ADDED Requirements

### Requirement: Every paragraph has a role
The system SHALL assign each paragraph exactly one role from: facts, issue, petitioner_argument, respondent_argument, statute, precedent, reasoning, conclusion. Assignment SHALL be deterministic: the same paragraphs always receive the same roles.

#### Scenario: Roles assigned during ingestion
- **WHEN** the roles stage runs over the corpus
- **THEN** every paragraph of every ingested judgment has one of the eight roles, and the run reports the count per role

#### Scenario: Deterministic
- **WHEN** the roles stage runs twice without changes to the paragraphs
- **THEN** every paragraph keeps the same role

### Requirement: Role cues
Roles SHALL follow recognisable cues in the text and position in the judgment: counsel's submissions are arguments for the side named; a stated question for consideration is an issue; a paragraph mainly quoting a provision is statute; discussion of a cited judgment is precedent; the closing disposal ("appeal is allowed", "set aside") is conclusion; unlabelled paragraphs before the first argument or issue are facts, and after it are reasoning.

#### Scenario: Counsel's submission
- **WHEN** a paragraph begins "Learned counsel for the appellant submitted that…"
- **THEN** its role is petitioner_argument

#### Scenario: Respondent's submission
- **WHEN** a paragraph says "Per contra, learned counsel for the respondent-State contended…"
- **THEN** its role is respondent_argument

#### Scenario: Disposal at the end
- **WHEN** one of the last paragraphs says "The appeal is accordingly allowed and the impugned order is set aside"
- **THEN** its role is conclusion

#### Scenario: Question for consideration
- **WHEN** a paragraph says "The question that arises for our consideration is…"
- **THEN** its role is issue

### Requirement: Labels shown as machine-assigned
The judgment view SHALL show each paragraph's role and state that roles are assigned automatically and may be wrong.

#### Scenario: Label visible
- **WHEN** a user opens a judgment
- **THEN** each paragraph shows its role tag and the page notes that roles are machine-assigned

### Requirement: Filter a judgment by role
The judgment view SHALL let the user choose one or more roles and then show only paragraphs with those roles, keeping their printed numbers; clearing the choice shows every paragraph again.

#### Scenario: Read only reasoning and conclusion
- **WHEN** the user selects Reasoning and Conclusion
- **THEN** only paragraphs with those roles are shown, with their original ¶ numbers

#### Scenario: Clear the filter
- **WHEN** the user clears the role selection
- **THEN** all paragraphs are shown
