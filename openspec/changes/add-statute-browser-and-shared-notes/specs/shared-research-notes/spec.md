## Purpose

Lets a lawyer send their research note to a colleague or client as a read-only link, without an account.

## ADDED Requirements

### Requirement: Share a note as a link
The user SHALL be able to save the current research note as a shared note and receive a link to it. The shared note SHALL contain only the paragraphs, case names, citations and ¶ numbers the user added to the note.

#### Scenario: Share a note
- **WHEN** the user has added three paragraphs and chooses Share
- **THEN** a link is created and shown, and the shared note contains exactly those three paragraphs

#### Scenario: Empty note
- **WHEN** the user chooses Share with no paragraphs in the note
- **THEN** no link is created and the user is told the note is empty

### Requirement: Read-only view
Anyone with the link SHALL see the note read-only, with each paragraph, its case name, citation and ¶ number, and a link to the judgment. The view SHALL NOT allow editing, and SHALL NOT show the search history or any other data of the owner.

#### Scenario: Recipient opens the link
- **WHEN** a recipient opens the link without signing in
- **THEN** they see the note's paragraphs and citations, read-only

### Requirement: Disclosure before sharing
Before creating a link, the UI SHALL state that anyone with the link can read the note, and that the note is not a legal opinion.

#### Scenario: Confirm before sharing
- **WHEN** the user clicks Share
- **THEN** a notice explains that anyone with the link can read the note, and the link is created only after the user confirms

### Requirement: Revoke a link
The owner SHALL be able to revoke a shared note. A revoked link SHALL show "This note has been withdrawn" and show no content.

#### Scenario: Revoke
- **WHEN** the owner revokes a shared note and a recipient opens the link
- **THEN** the page shows that the note has been withdrawn, and no paragraphs

### Requirement: No query or question storage
Shared notes SHALL NOT store search queries, questions or AI answers, and SHALL NOT be logged with their content.

#### Scenario: Logs
- **WHEN** a note is shared or opened
- **THEN** logs contain only the route, status and timing, not the note's content
