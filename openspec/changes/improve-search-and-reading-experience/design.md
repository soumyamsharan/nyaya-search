## Context

Groq's free tier for `openai/gpt-oss-20b` allows 30 requests and 8,000 tokens per minute, and 1,000 requests and
200,000 tokens per day. A single request counts its instructions, paragraphs and reserved answer against the minute limit.

## Decisions

- **Queue inside the server, not in the browser.** Users never see that AI calls queue or that a limit exists. Only one
  model call runs at a time; a second waits up to 45 seconds. A provider rate limit (HTTP 429) is retried for up to 20
  seconds using the provider's Retry-After header.
- **Generic user message.** Busy and daily-limit states share one message, so budget is not revealed. The reason is kept
  in the logs.
- **Smaller breakdown context.** The paragraph budget is 3,500 estimated tokens (four characters per token), leaving room
  for the instructions and the answer under the per-request limit.
- **Session cache, not persistent storage.** Read-only API responses are kept in memory for the browser session.
  Shared notes and LLM questions are never cached.
- **Pickers reuse the API's own matching.** Act names are sent as the corpus names them; the backend's normalisation
  matches "NI Act", "Negotiable Instruments Act" and "negotiable" alike.
