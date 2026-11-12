## Why

Lawyers often start from a provision of law: "what does the court say about Section 138 of the NI Act?" Today the site only answers from a case. Separately, the research note lives in one browser, so a lawyer cannot send their findings to a colleague or client. Both features reuse data we already have (`judgment_acts`) or small additions to what exists (the research note).

## What Changes

- **Statute browser:** each Act and section gets a page listing the judgments that refer to it, with the paragraph where each refers to it. Reachable from any section mentioned in a judgment.
- **Shared research notes:** a research note can be saved as a link. Anyone with the link can open it read-only, with its paragraphs, case names, citations and ¶ numbers. Links do not require accounts; the owner can revoke a link.

## Capabilities

### New Capabilities

- `statute-browser`: browsing judgments by Act and section.
- `shared-research-notes`: saving, opening, and revoking shared read-only notes.

## Impact

- Database: a `statute_refs` view or query over `judgment_acts`, and a `shared_notes` table (id, content, created_at, revoked_at). Notes store only the paragraph text and citation metadata chosen by the user, never queries.
- API: `GET /v1/statutes`, `GET /v1/statutes/{act}/sections/{section}`, `POST /v1/notes` (returns an id), `GET /v1/notes/{id}`, `DELETE /v1/notes/{id}`.
- Web: a statute page, a "Share note" button in the research note bar, and a read-only note page.
- Privacy: a shared note is public to anyone with the link, so the UI must say so before sharing and must not include anything the user did not add to the note.
