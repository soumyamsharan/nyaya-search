## Why

The search and reading experience changed a lot after the first specs were written: searchable filter pickers, a
calm editorial design, loading states and a session cache, and changes to how AI requests are sent and retried. None of
this was specified, so the specs no longer describe the product. This change records what is built and what is still open.

## What Changes

- Filter fields (judges, judgment author, outcome, match in, Act, section) become searchable pickers with a visible arrow.
- Date fields become typeable with a calendar that has month and year selection.
- The site uses an editorial visual design with a single accent colour and clickable elements show a hand cursor.
- Buttons show spinners and pages show placeholders while they load; read-only data is cached for the browser session.
- Model calls are queued on the server and provider rate limits are waited out before a user sees a message.
- The corpus scope (Supreme Court only, decisions 2024 to 2026) is stated in the specs.

## Non-goals

- Changing the ranking or the retrieval models.
- Upgrading the Groq plan.

## Open items

- A daily AI cap counted in tokens, not calls, so that requests stop before the provider's daily token limit (see tasks).
- Clear handling of "request too large" responses on breakdowns of very long judgments.
