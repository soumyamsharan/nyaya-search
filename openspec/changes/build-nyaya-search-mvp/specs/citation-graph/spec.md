## Purpose

Shows how a judgment sits in the body of case law: what it cites, which later judgments cite it and where, and whether any citing paragraph uses overruling language.

## ADDED Requirements

### Requirement: Citation extraction
The system SHALL find citations to other judgments inside each paragraph, covering SCC, AIR SC, SCR and INSC neutral citation formats, and record for each the citing judgment, citing paragraph and the citation text.

#### Scenario: Reported citation in a paragraph
- **WHEN** ¶18 of judgment A contains "(2016) 3 SCC 234"
- **THEN** a citation from A ¶18 with that text is recorded

### Requirement: Citation resolution
The system SHALL resolve each extracted citation to a judgment in the corpus by matching it against every known citation of that judgment, including parallel citations learned from reporters' "case law cited" lists. Citations that cannot be resolved SHALL be kept and shown as plain text, not linked; the system SHALL NOT guess a match.

#### Scenario: Resolvable citation
- **WHEN** the cited text matches a stored citation of judgment B
- **THEN** the citation links A ¶18 to B

#### Scenario: Resolved through a parallel citation
- **WHEN** A ¶18 cites "(2007) 3 SCC 755", judgment B is stored only as "[2007] 3 SCR 507", and some judgment's case law cited list pairs those two citations
- **THEN** the citation links A ¶18 to B

#### Scenario: Unresolvable citation
- **WHEN** the cited judgment is not in the corpus
- **THEN** the citation is listed as plain text without a link

### Requirement: Cites and cited-by
The judgment view SHALL list the judgments it cites and the judgments in the corpus that cite it. Each cited-by entry SHALL show the citing judgment's title, date and the citing paragraph, linked.

#### Scenario: Cited-by list
- **WHEN** judgment B is cited by judgments A and C
- **THEN** B's view lists A and C, each with the paragraph that cites B

#### Scenario: Count on search results
- **WHEN** a search result is shown
- **THEN** it shows how many judgments in the corpus cite it

### Requirement: Overruling language surfaced as evidence
When a citing paragraph contains overruling language about the cited judgment (for example "overruled", "no longer good law"), the cited judgment's view SHALL show a notice quoting that paragraph and linking to it. The notice SHALL say that overruling language was found and SHALL NOT state that the judgment is overruled.

#### Scenario: Overruling language found
- **WHEN** C ¶40 cites B and says B "is overruled"
- **THEN** B's view shows a notice "Overruling language found in C ¶40" with the paragraph text and link

#### Scenario: No overruling language
- **WHEN** no citing paragraph contains overruling language
- **THEN** no notice is shown and the view does not claim the judgment is good law

#### Scenario: Wording of the notice
- **WHEN** a notice is shown
- **THEN** it tells the user to read the citing paragraph and does not label the judgment "overruled"
