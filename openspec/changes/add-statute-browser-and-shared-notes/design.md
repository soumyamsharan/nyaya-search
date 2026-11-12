## Context

See proposal.md. `judgment_acts` already holds (judgment, act, section) rows extracted from the reporters' Acts list and from section references in paragraphs. The research note is client-side (localStorage) and exported as Markdown.

## Decisions

### 1. Statute matching
- Use the existing `judgment_acts` table. A section page matches on normalised Act name and exact section number, as already stored.
- To avoid guessing, only rows where the section reference was found in the same sentence as the Act name are used (the extractor already requires this).
- Section numbers are compared exactly, so "138" never matches "1380".

### 2. Statute pages
- Index: `GET /v1/statutes` groups by act_norm with a display name and judgment counts.
- Section: `GET /v1/statutes/{act}/sections/{section}` returns judgments and the referring paragraph by joining `judgment_acts` to `paragraphs` on the paragraph that contains the reference.
- The referring paragraph is found by searching the paragraph text for the section reference, so each result shows the actual passage.

### 3. Shared notes
- Table `shared_notes(id uuid primary key, content jsonb, created_at timestamptz, revoked_at timestamptz)`.
- `content` is the note as the user sent it: an array of {case_name, citation, judgment_id, label, text}. The server stores only that array.
- Ids are random UUIDs, so links cannot be guessed. Revocation sets `revoked_at` and clears `content`.
- The web app keeps the existing localStorage note; "Share" posts it and shows the link.

### 4. Privacy
- The confirmation notice is required before the request is sent.
- The API never logs note content.
- No accounts: the owner keeps the link to revoke, and the revoke action is available from the same browser that created it via a returned owner token, stored in localStorage (lost if the user clears their browser). This is stated in the UI.

## Risks / Trade-offs
- **[Stale links]** A shared note never updates when the judgment does. Mitigation: the note stores the text and citation at share time, and shows the judgment link for the latest version.
- **[Section extraction gaps]** Sections referred to without the Act name in the same sentence are not listed. Mitigation: stated on the page; improved in a later change.
- **[Owner token lost]** Without the token the owner cannot revoke from another browser. Mitigation: every shared note expires 30 days after it is created unless the owner renews it from the browser that holds the token, which limits how long an unrevoked link stays live.
